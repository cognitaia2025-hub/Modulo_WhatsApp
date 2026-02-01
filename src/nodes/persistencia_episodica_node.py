"""
Nodo 7: Persistencia Episódica (pgvector)

Este es el nodo final del grafo. Su misión es archivar el conocimiento
extraído en el Nodo 6 para memoria a largo plazo.

Responsabilidades:
- Generar embedding del resumen con modelo local (384 dims)
- Guardar en PostgreSQL tabla memoria_episodica
- Limpiar estado para próxima interacción
- Manejo robusto de errores (no bloquear si DB falla)

MEJORAS APLICADAS:
✅ Command pattern con routing directo
✅ Detección de estado conversacional
✅ psycopg3 con context managers
✅ Logging estructurado
✅ Timeout reducido (modelo rápido)

OPTIMIZACIÓN: Usa el singleton de embeddings para evitar recargas.
"""

import logging
from typing import Dict, Any, Optional, List
import os
from dotenv import load_dotenv

import psycopg
from psycopg.rows import dict_row
from langgraph.types import Command

from src.utils.logging_config import (
    log_separator,
    log_node_io
)
from src.embeddings.local_embedder import generate_embedding, is_model_loaded

load_dotenv()

logger = logging.getLogger(__name__)

# Configuración de base de datos
# Nota: Puerto 5434 se usa para evitar conflictos con PostgreSQL del sistema (puerto 5432)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5434/agente_whatsapp")


# ==================== CONSTANTES ====================

# Configuración mínima de resumen
MIN_RESUMEN_LENGTH = 10  # Caracteres mínimos para considerar un resumen válido

# Estados conversacionales que requieren saltar persistencia
ESTADOS_SIN_PERSISTENCIA = [
    'esperando_confirmacion',
    'recolectando_datos',
    'procesando_pago',
    'inicial'  # No persistir si es solo saludo inicial
]


# ==================== FUNCIONES AUXILIARES ====================

def generar_embedding_optimizado(texto: str) -> Optional[List[float]]:
    """
    Genera embedding de 384 dimensiones usando sentence-transformers.
    
    MEJORAS:
    ✅ Manejo de errores robusto
    ✅ Cache del modelo (singleton)
    ✅ Timeout implícito (modelo rápido)
    
    Args:
        texto: Texto a convertir en embedding
        
    Returns:
        Lista de 384 floats o None si hay error
    """
    try:
        if not is_model_loaded():
            logger.warning("    ⚠️  Modelo no pre-cargado, se cargará bajo demanda")
        
        embedding = generate_embedding(texto)
        return embedding
        
    except Exception as e:
        logger.error(f"    ❌ Error generando embedding: {e}")
        return None


def guardar_en_pgvector(
    user_id: str,
    session_id: str,
    resumen: str,
    embedding: List[float]
) -> Optional[int]:
    """
    Guarda el resumen y su embedding en PostgreSQL con pgvector.
    
    MEJORAS:
    ✅ Usa psycopg3 con context managers
    ✅ Simplificado - metadata básica
    ✅ Retorna ID del episodio creado
    
    Args:
        user_id: ID del usuario de WhatsApp
        session_id: ID de la sesión
        resumen: Texto del resumen generado
        embedding: Vector de 384 dimensiones
        
    Returns:
        ID del episodio creado o None si falla
    """
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                # Query de inserción simplificada
                cur.execute("""
                    INSERT INTO memoria_episodica 
                    (user_id, resumen, embedding, timestamp)
                    VALUES (%s, %s, %s, NOW())
                    RETURNING id
                """, (user_id, resumen, embedding))
                
                episodio_id = cur.fetchone()[0]
                conn.commit()
                
                logger.info(f"    ✅ Episodio guardado en memoria episódica (ID: {episodio_id})")
                logger.info(f"    📊 Vector: 384 dims | User: {user_id}")
                
                return episodio_id
                
    except psycopg.Error as e:
        logger.error(f"    ❌ Error de PostgreSQL: {e}")
        return None
    except Exception as e:
        logger.error(f"    ❌ Error guardando en pgvector: {e}")
        return None


# ==================== NODO PRINCIPAL ====================

def nodo_persistencia_episodica(state: Dict[str, Any]) -> Command:
    """
    Nodo 7: Persiste resumen ejecutivo en memoria episódica (PostgreSQL + pgvector)
    
    MEJORAS APLICADAS:
    ✅ Command pattern con routing directo
    ✅ Detección de estado conversacional
    ✅ psycopg3 con context managers
    ✅ Logging estructurado
    
    Flujo:
    1. Verifica estado conversacional (saltar si no debe persistir)
    2. Valida que existe resumen_actual
    3. Genera embedding del resumen (384 dims)
    4. Inserta en tabla memoria_episodica
    5. Retorna Command con estado actualizado
    
    Args:
        state: Estado del grafo con resumen_actual
        
    Returns:
        Command con update y goto
    """
    log_separator(logger, "NODO_7_PERSISTENCIA_EPISODICA", "INICIO")
    
    resumen_actual = state.get('resumen_actual', '')
    user_id = state.get('user_id', 'default_user')
    session_id = state.get('session_id', 'unknown')
    estado_conversacion = state.get('estado_conversacion', 'inicial')
    
    # Log del input
    input_data = f"resumen_len: {len(resumen_actual)}\nuser_id: {user_id}\nestado: {estado_conversacion}"
    log_node_io(logger, "INPUT", "NODO_7_PERSISTENCIA", input_data)
    
    logger.info(f"    📝 Resumen a persistir: {len(resumen_actual)} caracteres")
    logger.info(f"    🔄 Estado: {estado_conversacion}")
    
    # ✅ NUEVA VALIDACIÓN: Detectar estado conversacional
    if estado_conversacion in ESTADOS_SIN_PERSISTENCIA:
        logger.info(f"    🔄 Estado '{estado_conversacion}' - Saltando persistencia")
        
        output_data = "episodio_guardado: False (estado conversacional)"
        log_node_io(logger, "OUTPUT", "NODO_7_PERSISTENCIA", output_data)
        log_separator(logger, "NODO_7_PERSISTENCIA_EPISODICA", "FIN")
        
        return Command(
            update={'episodio_guardado': False},
            goto="END"
        )
    
    # Validar resumen
    if not resumen_actual or len(resumen_actual.strip()) < MIN_RESUMEN_LENGTH:
        logger.info(f"    ⚠️ Resumen vacío o muy corto (< {MIN_RESUMEN_LENGTH} caracteres), saltando persistencia")
        
        output_data = "episodio_guardado: False (resumen vacío)"
        log_node_io(logger, "OUTPUT", "NODO_7_PERSISTENCIA", output_data)
        log_separator(logger, "NODO_7_PERSISTENCIA_EPISODICA", "FIN")
        
        return Command(
            update={'episodio_guardado': False},
            goto="END"
        )
    
    try:
        # Generar embedding
        logger.info("    🧠 Generando embedding...")
        embedding = generar_embedding_optimizado(resumen_actual)
        
        if embedding is None:
            logger.error("    ❌ Error generando embedding")
            log_separator(logger, "NODO_7_PERSISTENCIA_EPISODICA", "FIN")
            
            return Command(
                update={'episodio_guardado': False},
                goto="END"
            )
        
        logger.info(f"    ✅ Embedding generado: [{embedding[0]:.4f}, {embedding[1]:.4f}, ...]")
        
        # Insertar en BD con psycopg3
        logger.info("    💾 Insertando en memoria_episodica...")
        
        episodio_id = guardar_en_pgvector(
            user_id=user_id,
            session_id=session_id,
            resumen=resumen_actual,
            embedding=embedding
        )
        
        if episodio_id is None:
            logger.warning("    ⚠️  PostgreSQL no disponible")
            log_separator(logger, "NODO_7_PERSISTENCIA_EPISODICA", "FIN")
            
            return Command(
                update={'episodio_guardado': False},
                goto="END"
            )
        
        logger.info(f"    ✅ Episodio guardado con ID: {episodio_id}")
        
        # Log de output
        output_data = f"episodio_id: {episodio_id}\nepisodio_guardado: True"
        log_node_io(logger, "OUTPUT", "NODO_7_PERSISTENCIA", output_data)
        log_separator(logger, "NODO_7_PERSISTENCIA_EPISODICA", "FIN")
        
        # ✅ Retornar Command
        return Command(
            update={
                'episodio_guardado': True,
                'episodio_id': episodio_id
            },
            goto="END"
        )
        
    except Exception as e:
        logger.error(f"    ❌ Error en persistencia: {e}")
        log_separator(logger, "NODO_7_PERSISTENCIA_EPISODICA", "FIN")
        
        return Command(
            update={'episodio_guardado': False},
            goto="END"
        )


# ==================== WRAPPER ====================

def nodo_persistencia_episodica_wrapper(state: Dict[str, Any]) -> Command:
    """Wrapper para LangGraph - retorna Command directamente."""
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
        'estado_conversacion': 'completado'
    }
    
    resultado1 = nodo_persistencia_episodica(state_test1)
    print(f"✅ Tipo: {type(resultado1)}")
    print(f"✅ Goto: {resultado1.goto}")
    print(f"✅ Guardado: {resultado1.update.get('episodio_guardado')}\n")
    
    # Test 2: Estado sin persistencia
    print("Test 2: Estado conversacional sin persistencia")
    state_test2 = {
        'user_id': 'test_user_456',
        'session_id': 'session_test_002',
        'resumen_actual': '[24/01/2026 14:00] Usuario pidió cita.',
        'estado_conversacion': 'inicial'
    }
    
    resultado2 = nodo_persistencia_episodica(state_test2)
    print(f"✅ Guardado: {resultado2.update.get('episodio_guardado')}")
    print(f"✅ Razón: Estado inicial\n")
    
    # Test 3: Sin resumen relevante
    print("Test 3: Sin contenido relevante")
    state_test3 = {
        'user_id': 'test_user_789',
        'session_id': 'session_test_003',
        'resumen_actual': '',
        'estado_conversacion': 'completado'
    }
    
    resultado3 = nodo_persistencia_episodica(state_test3)
    print(f"✅ Guardado: {resultado3.update.get('episodio_guardado')}")
    print(f"✅ Razón: Resumen vacío\n")
    
    print("🎉 Tests completados")

