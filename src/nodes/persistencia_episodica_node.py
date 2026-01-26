"""
Nodo 7: Persistencia Episódica (pgvector)

Este es el nodo final del grafo. Su misión es archivar el conocimiento
extraído en el Nodo 6 para memoria a largo plazo.

Responsabilidades:
- Generar embedding del resumen con modelo local (384 dims)
- Guardar en PostgreSQL tabla memoria_episodica
- Limpiar estado para próxima interacción
- Manejo robusto de errores (no bloquear si DB falla)

OPTIMIZACIÓN: Usa el singleton de embeddings para evitar recargas.
"""

import logging
from typing import Dict, Any
from datetime import datetime
import json
import psycopg2
from psycopg2.extras import execute_values
from langchain_core.messages import RemoveMessage
from langgraph.graph.message import REMOVE_ALL_MESSAGES

from src.utils.time_utils import get_current_time
from src.database.db_config import get_db_connection
from src.embeddings.local_embedder import generate_embedding, is_model_loaded

logger = logging.getLogger(__name__)


def guardar_en_pgvector(
    user_id: str,
    session_id: str,
    resumen: str,
    embedding: list,
    sesion_expirada: bool
) -> bool:
    """
    Guarda el resumen y su embedding en PostgreSQL con pgvector.
    
    Args:
        user_id: ID del usuario de WhatsApp
        session_id: ID de la sesión
        resumen: Texto del resumen generado
        embedding: Vector de 384 dimensiones
        sesion_expirada: Si fue cierre por timeout
        
    Returns:
        True si se guardó exitosamente, False si falló
    """
    try:
        # Obtener conexión
        conn = get_db_connection()
        if not conn:
            logger.error("    ❌ No se pudo conectar a PostgreSQL")
            return False
        
        cursor = conn.cursor()
        
        # Preparar metadata
        timestamp = get_current_time()
        metadata = {
            'fecha': timestamp.format('YYYY-MM-DD HH:mm:ss'),
            'session_id': session_id,
            'tipo': 'cierre_expiracion' if sesion_expirada else 'normal',
            'timezone': 'America/Tijuana'
        }
        
        # Query de inserción
        query = """
        INSERT INTO memoria_episodica 
        (user_id, resumen, embedding, metadata, timestamp)
        VALUES (%s, %s, %s::vector, %s, %s)
        RETURNING id
        """
        
        # Convertir embedding a string para pgvector
        embedding_str = '[' + ','.join(map(str, embedding)) + ']'
        
        cursor.execute(query, (
            user_id,
            resumen,
            embedding_str,
            json.dumps(metadata),
            timestamp.to_datetime_string()
        ))
        
        # Obtener ID insertado
        row_id = cursor.fetchone()[0]
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"    ✅ Resumen guardado en memoria episódica (ID: {row_id})")
        logger.info(f"    📊 Vector: 384 dims | Tipo: {metadata['tipo']}")
        
        return True
        
    except psycopg2.Error as e:
        logger.error(f"    ❌ Error de PostgreSQL: {e}")
        return False
    except Exception as e:
        logger.error(f"    ❌ Error guardando en pgvector: {e}")
        return False


def nodo_persistencia_episodica(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Nodo 7: Archiva el resumen en memoria a largo plazo (pgvector).
    
    Este es el nodo final del grafo. Cierra el ciclo de aprendizaje del agente.
    
    Flujo:
    1. Obtener resumen del Nodo 6
    2. Generar embedding (384 dims)
    3. Guardar en PostgreSQL
    4. Limpiar estado para próxima interacción
    
    Args:
        state: Estado del grafo con resumen_actual
        
    Returns:
        State limpio y listo para nueva conversación
    """
    logger.info("💾 [7] NODO_PERSISTENCIA_EPISODICA - Archivando conocimiento")
    
    resumen = state.get('resumen_actual')
    user_id = state.get('user_id', 'unknown')
    session_id = state.get('session_id', 'unknown')
    sesion_expirada = state.get('sesion_expirada', False)
    
    # Validar que hay resumen para guardar
    if not resumen or resumen == "Sin cambios relevantes":
        logger.info("    ⚠️  No hay resumen relevante para persistir")
        return {
            **state,
            'resumen_actual': None,
            'cambio_de_tema': False,
            'sesion_expirada': False
        }
    
    logger.info(f"    📝 Resumen a guardar: {len(resumen)} caracteres")
    logger.info(f"    👤 Usuario: {user_id} | Sesión: {session_id}")
    logger.info(f"    {'⏰' if sesion_expirada else '✅'} Tipo: {'Cierre por expiración' if sesion_expirada else 'Normal'}")
    
    try:
        # 1. Generar embedding usando el singleton
        if not is_model_loaded():
            logger.warning("    ⚠️  Modelo no pre-cargado, se cargará bajo demanda")
        
        logger.info("    🔢 Generando embedding (384 dims)...")
        embedding = generate_embedding(resumen)
        logger.info(f"    ✅ Embedding generado: [{embedding[0]:.4f}, {embedding[1]:.4f}, ...]")
        
        # 2. Guardar en PostgreSQL
        logger.info("    💾 Guardando en PostgreSQL (pgvector)...")
        guardado_exitoso = guardar_en_pgvector(
            user_id=user_id,
            session_id=session_id,
            resumen=resumen,
            embedding=embedding,
            sesion_expirada=sesion_expirada
        )
        
        if not guardado_exitoso:
            # Fallback: Loguear el resumen en consola
            logger.warning("    ⚠️  PostgreSQL no disponible, logueando resumen:")
            logger.warning(f"    📄 [{user_id}] {resumen}")
        
    except Exception as e:
        logger.error(f"    ❌ Error en persistencia: {e}")
        logger.warning(f"    📄 Resumen (no guardado): {resumen}")
    
    # 3. Limpieza del estado
    logger.info("    🧹 Limpiando estado para próxima interacción...")
    
    nuevo_state = {
        **state,
        'resumen_actual': None,
        'cambio_de_tema': False,
        'sesion_expirada': False
    }
    
    # Si la sesión expiró, limpiar mensajes del checkpointer
    if sesion_expirada:
        logger.info("    🗑️  Limpiando mensajes del checkpointer (sesión expirada)")
        nuevo_state['messages'] = [RemoveMessage(id=REMOVE_ALL_MESSAGES)]
    
    logger.info("    ✅ Estado limpio y listo para nueva conversación")
    
    return nuevo_state


def nodo_persistencia_episodica_wrapper(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Wrapper para compatibilidad con LangGraph.
    """
    return nodo_persistencia_episodica(state)


if __name__ == "__main__":
    """
    Test standalone del Nodo 7.
    """
    print("\n🧪 Test del Nodo 7: Persistencia Episódica\n")
    
    # Test 1: Guardar resumen normal
    print("Test 1: Persistencia de resumen normal")
    state_test1 = {
        'user_id': 'test_user_123',
        'session_id': 'session_test_001',
        'resumen_actual': '[24/01/2026 12:30] Se agendó reunión para mañana a las 15:00. Estado: Completada.',
        'sesion_expirada': False,
        'messages': [
            {'role': 'user', 'content': 'Agendar reunión mañana 3pm'},
            {'role': 'ai', 'content': 'Listo, agendado'}
        ]
    }
    
    resultado1 = nodo_persistencia_episodica(state_test1)
    print(f"✅ Resumen actual: {resultado1['resumen_actual']}")
    print(f"✅ Cambio de tema: {resultado1['cambio_de_tema']}\n")
    
    # Test 2: Cierre por expiración
    print("Test 2: Persistencia con sesión expirada")
    state_test2 = {
        'user_id': 'test_user_456',
        'session_id': 'session_test_002',
        'resumen_actual': '[24/01/2026 14:00] Usuario pidió cita para miércoles 10am. Pendiente: Confirmar ubicación. Estado: Interrumpida.',
        'sesion_expirada': True,
        'messages': [
            {'role': 'user', 'content': 'Ponme cita el miércoles'},
            {'role': 'ai', 'content': '¿En qué lugar?'}
        ]
    }
    
    resultado2 = nodo_persistencia_episodica(state_test2)
    print(f"✅ Sesión expirada: {resultado2['sesion_expirada']}")
    print(f"✅ Mensajes limpiados: {len(resultado2.get('messages', []))} messages\n")
    
    # Test 3: Sin resumen relevante
    print("Test 3: Sin contenido relevante")
    state_test3 = {
        'user_id': 'test_user_789',
        'session_id': 'session_test_003',
        'resumen_actual': 'Sin cambios relevantes',
        'sesion_expirada': False
    }
    
    resultado3 = nodo_persistencia_episodica(state_test3)
    print(f"✅ Manejado correctamente sin persistir\n")
    
    print("🎉 Tests completados")
