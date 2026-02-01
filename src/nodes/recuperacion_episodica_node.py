"""
Nodo 3: Recuperación de Memoria Episódica (pgvector)

Este nodo recupera conversaciones previas relevantes usando búsqueda semántica.

Responsabilidades:
- Generar embedding del último mensaje del usuario (384 dims)
- Buscar TOP 5 resúmenes similares en pgvector
- Filtrar por relevancia (similarity >= 0.5)
- Formatear contexto legible para LLMs
- Actualizar state['contexto_episodico']
- Manejo robusto de errores (continuar sin contexto si falla)
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import psycopg
from psycopg.rows import dict_row

from langgraph.types import Command
from src.state.agent_state import WhatsAppAgentState
from src.embeddings.local_embedder import get_embedder, generate_embedding
from src.database.db_config import get_db_connection
from src.utils.time_utils import get_current_time
from src.utils.logging_config import (
    log_separator,
    log_node_io,
    log_user_message
)

logger = logging.getLogger(__name__)

# Threshold de similitud (cosine similarity)
# Threshold de similitud: 0.5 (50% similar o más)
SIMILARITY_THRESHOLD = 0.5
MAX_EPISODIOS = 5

# ==================== CONSTANTES ====================

# Estados conversacionales que requieren saltar recuperación
ESTADOS_FLUJO_ACTIVO = [
    'ejecutando_herramienta',
    'esperando_confirmacion',
    'procesando_resultado',
    'recolectando_fecha',
    'recolectando_hora'
]


def extraer_ultimo_mensaje_usuario(state: WhatsAppAgentState) -> str:
    """
    Extrae el contenido del último mensaje del usuario.
    
    Args:
        state: Estado actual del agente
        
    Returns:
        String con el mensaje del usuario o vacío si no hay
    """
    messages = state.get('messages', [])
    
    if not messages:
        return ""
    
    # Buscar último mensaje de tipo 'human' o con role='user'
    for mensaje in reversed(messages):
        if isinstance(mensaje, dict):
            if mensaje.get('role') == 'user':
                return mensaje.get('content', '')
        elif hasattr(mensaje, 'type'):
            if mensaje.type == 'human':
                return mensaje.content
    
    return ""


def buscar_episodios_similares(
    user_id: str,
    query_embedding: List[float],
    max_results: int = MAX_EPISODIOS,
    threshold: float = SIMILARITY_THRESHOLD
) -> List[Dict[str, Any]]:
    """
    Busca episodios similares en pgvector usando cosine similarity.
    
    MEJORAS:
    ✅ Filtro threshold en SQL (no post-query en Python)
    ✅ Usa psycopg3 (alineado con N3B)
    ✅ Más eficiente: BD filtra antes de retornar
    
    Args:
        user_id: ID del usuario para filtrar resultados
        query_embedding: Vector de 384 dimensiones del mensaje actual
        max_results: Número máximo de episodios a recuperar
        threshold: Umbral mínimo de similitud (0.0 a 1.0)
        
    Returns:
        Lista de dicts con {resumen, metadata, timestamp, similarity}
    """
    try:
        # ✅ NUEVO: psycopg3 con dict_row
        with psycopg.connect(
            "postgresql://postgres:postgres@localhost:5434/agente_whatsapp"
        ) as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                
                # ✅ MEJORADO: Filtro threshold en SQL (no post-query)
                query = """
                    SELECT 
                        resumen,
                        metadata,
                        timestamp,
                        1 - (embedding <=> %s::vector) as similarity
                    FROM memoria_episodica
                    WHERE user_id = %s
                      AND 1 - (embedding <=> %s::vector) >= %s
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                """
                
                # Convertir embedding a formato string para pgvector
                embedding_str = f"[{','.join(map(str, query_embedding))}]"
                
                cursor.execute(
                    query, 
                    (embedding_str, user_id, embedding_str, threshold, embedding_str, max_results)
                )
                
                resultados = cursor.fetchall()
                
                logger.info(f"    📊 Encontrados {len(resultados)} episodios sobre threshold {threshold}")
                
                return resultados
        
    except Exception as e:
        logger.error(f"    ❌ Error en búsqueda pgvector: {e}")
        return []


def formatear_contexto_episodico(episodios: List[Dict[str, Any]]) -> str:
    """
    Formatea los episodios recuperados en texto legible para LLMs.
    
    MEJORAS:
    ✅ Trunca resúmenes largos (>200 chars)
    ✅ Formato más compacto
    
    Args:
        episodios: Lista de episodios con resumen, metadata, timestamp, similarity
        
    Returns:
        String formateado con el contexto histórico
    """
    if not episodios:
        return "No hay conversaciones previas relevantes para este contexto."
    
    texto = "CONVERSACIONES PREVIAS RELEVANTES:\n\n"
    
    for i, episodio in enumerate(episodios, 1):
        resumen = episodio.get('resumen', 'Sin resumen')
        timestamp = episodio.get('timestamp')
        similarity = episodio.get('similarity', 0.0)
        metadata = episodio.get('metadata', {})
        
        # Formatear fecha
        if isinstance(timestamp, datetime):
            fecha_str = timestamp.strftime('%d/%m/%Y %H:%M')
        else:
            fecha_str = str(timestamp)
        
        # ✅ NUEVO: Truncar resúmenes muy largos
        MAX_RESUMEN_CHARS = 200
        if len(resumen) > MAX_RESUMEN_CHARS:
            resumen_truncado = resumen[:MAX_RESUMEN_CHARS - 3] + "..."
        else:
            resumen_truncado = resumen
        
        # Agregar episodio al contexto
        texto += f"{i}. [{fecha_str}] (Relevancia: {similarity:.2f})\n"
        texto += f"   {resumen_truncado}\n"
        
        # Agregar metadata relevante si existe
        if metadata:
            tipo = metadata.get('tipo', '')
            if tipo:
                texto += f"   Tipo: {tipo}\n"
        
        texto += "\n"
    
    return texto.strip()


def nodo_recuperacion_episodica(state: WhatsAppAgentState) -> Command:
    """
    Nodo 3A: Recupera memoria episódica relevante usando búsqueda semántica.
    
    MEJORAS APLICADAS:
    ✅ Command pattern con routing directo
    ✅ Detección de estado conversacional
    ✅ psycopg3 (alineado con N3B)
    ✅ Filtro threshold en SQL
    
    Flujo:
    1. Verifica estado conversacional (saltar si activo)
    2. Extrae último mensaje del usuario
    3. Genera embedding del mensaje (384 dims)
    4. Busca episodios similares en pgvector (threshold en SQL)
    5. Formatea contexto para LLMs
    6. Actualiza state['contexto_episodico']
    
    Args:
        state: WhatsAppAgentState con messages y user_id
        
    Returns:
        Command con update y goto
    """
    log_separator(logger, "NODO_3A_RECUPERACION_EPISODICA", "INICIO")
    
    user_id = state.get('user_id')
    estado_conversacion = state.get('estado_conversacion', 'inicial')
    
    # Log de input
    input_data = f"user_id: {user_id}\nestado: {estado_conversacion}\nmensajes: {len(state.get('messages', []))}"
    log_node_io(logger, "INPUT", "NODO_3A_RECUPERACION", input_data)
    
    logger.info(f"    👤 User ID: {user_id}")
    logger.info(f"    🔄 Estado: {estado_conversacion}")
    
    # ✅ NUEVA VALIDACIÓN: Si hay flujo activo, saltar recuperación
    if estado_conversacion in ESTADOS_FLUJO_ACTIVO:
        logger.info(f"   🔄 Flujo activo detectado (estado: {estado_conversacion}) - Saltando recuperación")
        
        return Command(
            update={'contexto_episodico': None},
            goto="seleccion_herramientas"
        )
    
    # Validar que tenemos user_id
    if not user_id:
        logger.warning("    ⚠️  Sin user_id, no se puede recuperar memoria")
        return Command(
            update={
                'contexto_episodico': {
                    'episodios_recuperados': 0,
                    'texto_formateado': 'Sin identificación de usuario.',
                    'timestamp_recuperacion': get_current_time().to_iso8601_string(),
                    'error': 'missing_user_id'
                }
            },
            goto="seleccion_herramientas"
        )
    
    try:
        # Paso 1: Extraer último mensaje del usuario
        mensaje_usuario = extraer_ultimo_mensaje_usuario(state)
        
        if not mensaje_usuario.strip():
            logger.info("    ℹ️  Sin mensaje del usuario para analizar")
            return Command(
                update={
                    'contexto_episodico': {
                        'episodios_recuperados': 0,
                        'texto_formateado': 'No hay mensaje para analizar.',
                        'timestamp_recuperacion': get_current_time().to_iso8601_string()
                    }
                },
                goto="seleccion_herramientas"
            )
        
        log_user_message(logger, mensaje_usuario)
        
        # Paso 2: Generar embedding del mensaje
        logger.info("    🔢 Generando embedding del mensaje...")
        query_embedding = generate_embedding(mensaje_usuario)
        logger.info(f"    ✅ Embedding generado (384 dims)")
        
        # Paso 3: Buscar episodios similares en pgvector
        logger.info(f"    🔍 Buscando episodios similares (threshold >= {SIMILARITY_THRESHOLD})...")
        episodios = buscar_episodios_similares(
            user_id=user_id,
            query_embedding=query_embedding,
            max_results=MAX_EPISODIOS,
            threshold=SIMILARITY_THRESHOLD
        )
        
        # Paso 4: Formatear contexto
        if episodios:
            logger.info(f"    ✅ {len(episodios)} episodios recuperados")
            texto_formateado = formatear_contexto_episodico(episodios)
        else:
            logger.info("    ℹ️  No se encontraron episodios relevantes")
            texto_formateado = "No hay conversaciones previas relevantes para este contexto."
        
        # Paso 5: Actualizar estado
        contexto = {
            'episodios_recuperados': len(episodios),
            'texto_formateado': texto_formateado,
            'timestamp_recuperacion': get_current_time().to_iso8601_string(),
            'similarity_threshold': SIMILARITY_THRESHOLD
        }
        
        # Agregar detalles de episodios para debugging
        if episodios:
            contexto['episodios_detalle'] = [
                {
                    'fecha': ep.get('timestamp').isoformat() if isinstance(ep.get('timestamp'), datetime) else str(ep.get('timestamp')),
                    'similarity': float(ep.get('similarity', 0.0)),
                    'preview': ep.get('resumen', '')[:100]
                }
                for ep in episodios
            ]
        
        # Log de output
        output_data = f"episodios_recuperados: {len(episodios)}\nthreshold: {SIMILARITY_THRESHOLD}"
        log_node_io(logger, "OUTPUT", "NODO_3A_RECUPERACION", output_data)
        log_separator(logger, "NODO_3A_RECUPERACION_EPISODICA", "FIN")
        
        # ✅ Retornar Command (no Dict)
        return Command(
            update={'contexto_episodico': contexto},
            goto="seleccion_herramientas"
        )
        
    except Exception as e:
        # Manejo robusto: no bloquear el flujo si falla la recuperación
        logger.error(f"    ❌ Error en recuperación episódica: {e}")
        logger.info("    ⚡ Continuando sin contexto histórico...")
        
        log_separator(logger, "NODO_3A_RECUPERACION_EPISODICA", "FIN")
        
        return Command(
            update={
                'contexto_episodico': {
                    'episodios_recuperados': 0,
                    'texto_formateado': 'Error al recuperar memoria (continuando sin contexto).',
                    'timestamp_recuperacion': get_current_time().to_iso8601_string(),
                    'error': str(e)
                }
            },
            goto="seleccion_herramientas"
        )


# Wrapper para compatibilidad con LangGraph
def nodo_recuperacion_episodica_wrapper(state: WhatsAppAgentState) -> Command:
    """Wrapper para LangGraph - retorna Command directamente."""
    return nodo_recuperacion_episodica(state)


# ============================================================================
# TEST STANDALONE
# ============================================================================

if __name__ == "__main__":
    """
    Test standalone del nodo de recuperación episódica.
    
    Uso:
        python -m src.nodes.recuperacion_episodica_node
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )
    
    print("=" * 80)
    print("TEST: Nodo de Recuperación Episódica")
    print("=" * 80)
    
    # Estado de prueba
    from langchain_core.messages import HumanMessage
    
    test_state = {
        'user_id': 'test_user_123',
        'session_id': 'test_session_456',
        'messages': [
            HumanMessage(content="¿Qué eventos tengo esta semana?")
        ],
        'contexto_episodico': None
    }
    
    print("\n1. Estado inicial:")
    print(f"   User ID: {test_state['user_id']}")
    print(f"   Mensaje: {test_state['messages'][0].content}")
    
    print("\n2. Ejecutando nodo de recuperación...")
    resultado = nodo_recuperacion_episodica(test_state)
    
    print("\n3. Contexto recuperado:")
    contexto = resultado['contexto_episodico']
    print(f"   Episodios recuperados: {contexto['episodios_recuperados']}")
    print(f"   Timestamp: {contexto['timestamp_recuperacion']}")
    print(f"   Threshold: {contexto.get('similarity_threshold', 'N/A')}")
    
    if contexto['episodios_recuperados'] > 0:
        print("\n4. Texto formateado para LLM:")
        print("-" * 80)
        print(contexto['texto_formateado'])
        print("-" * 80)
        
        if 'episodios_detalle' in contexto:
            print("\n5. Detalles de episodios:")
            for ep in contexto['episodios_detalle']:
                print(f"   - {ep['fecha']} (Sim: {ep['similarity']:.3f})")
                print(f"     {ep['preview']}...")
    else:
        print("\n4. No se encontraron episodios relevantes")
        print(f"   Mensaje: {contexto['texto_formateado']}")
    
    print("\n" + "=" * 80)
    print("✅ Test completado")
    print("=" * 80)
