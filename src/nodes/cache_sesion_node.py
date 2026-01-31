"""
Nodo N1: Cache de Sesión

Gestiona sesiones activas con rolling window de 24 horas.
Recupera mensajes previos del checkpointer de LangGraph para mantener contexto.

Responsabilidades:
- Verificar si existe sesión activa (< 24h inactividad)
- Recuperar mensajes del checkpointer si sesión activa
- Crear nueva sesión si no existe o expiró
- Marcar sesiones expiradas para auto-resumen
- Actualizar timestamp de actividad
"""

import logging
import os
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from uuid import uuid4
import psycopg
from dotenv import load_dotenv

from src.state.agent_state import WhatsAppAgentState
from src.utils.logging_config import setup_colored_logging

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logger = setup_colored_logging()

# Configuración
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5434/agente_whatsapp")
SESSION_TTL_HOURS = 24  # Sesión expira después de 24h inactividad
CLEANUP_THRESHOLD_DAYS = 30  # Limpiar sesiones > 30 días


# ==================== FUNCIONES DE GESTIÓN DE SESIÓN ====================

def buscar_sesion_activa(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Busca si existe una sesión activa para el usuario (< 24h inactividad).
    
    Args:
        user_id: ID del usuario (phone_number)
        
    Returns:
        Dict con datos de sesión si existe, None si no
    """
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                query = """
                    SELECT 
                        thread_id,
                        last_activity,
                        messages_count,
                        EXTRACT(EPOCH FROM (NOW() - last_activity))/3600 as hours_inactive
                    FROM user_sessions
                    WHERE user_id = %s 
                      AND last_activity > NOW() - INTERVAL '24 hours'
                    ORDER BY last_activity DESC
                    LIMIT 1
                """
                
                cur.execute(query, (user_id,))
                result = cur.fetchone()
                
                if result:
                    thread_id, last_activity, messages_count, hours_inactive = result
                    
                    logger.info(f"    ✓ Sesión encontrada: {thread_id}")
                    logger.info(f"      Última actividad: {last_activity}")
                    logger.info(f"      Inactividad: {hours_inactive:.1f} horas")
                    logger.info(f"      Mensajes: {messages_count}")
                    
                    return {
                        'thread_id': thread_id,
                        'last_activity': last_activity,
                        'messages_count': messages_count,
                        'hours_inactive': hours_inactive
                    }
                else:
                    logger.info(f"    ✗ No hay sesión activa para {user_id}")
                    return None
                    
    except Exception as e:
        logger.error(f"❌ Error buscando sesión: {e}")
        return None


def crear_nueva_sesion(user_id: str, phone_number: str) -> str:
    """
    Crea una nueva sesión en la BD.
    
    Args:
        user_id: ID del usuario
        phone_number: Número de teléfono del usuario
        
    Returns:
        thread_id de la nueva sesión
    """
    try:
        # Generar thread_id único
        thread_id = f"thread_{user_id.replace('+', '')}_{uuid4().hex[:8]}"
        
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                query = """
                    INSERT INTO user_sessions (user_id, thread_id, phone_number, last_activity, messages_count)
                    VALUES (%s, %s, %s, NOW(), 0)
                    ON CONFLICT (user_id, thread_id) DO UPDATE
                    SET last_activity = NOW()
                    RETURNING thread_id
                """
                
                cur.execute(query, (user_id, thread_id, phone_number))
                result = cur.fetchone()
                conn.commit()
                
                logger.info(f"    ✓ Nueva sesión creada: {thread_id}")
                return result[0] if result else thread_id
                
    except Exception as e:
        logger.error(f"❌ Error creando sesión: {e}")
        # Fallback: generar thread_id aunque falle la BD
        return f"thread_{user_id.replace('+', '')}_{uuid4().hex[:8]}"


def actualizar_actividad_sesion(thread_id: str, user_id: str) -> bool:
    """
    Actualiza el timestamp de última actividad de la sesión.
    
    Args:
        thread_id: ID de la sesión
        user_id: ID del usuario
        
    Returns:
        True si se actualizó correctamente
    """
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                query = """
                    UPDATE user_sessions
                    SET last_activity = NOW(),
                        messages_count = messages_count + 1
                    WHERE thread_id = %s AND user_id = %s
                    RETURNING messages_count
                """
                
                cur.execute(query, (thread_id, user_id))
                result = cur.fetchone()
                conn.commit()
                
                if result:
                    logger.info(f"    ✓ Sesión actualizada: {result[0]} mensajes totales")
                    return True
                else:
                    logger.warning(f"    ⚠️ No se pudo actualizar sesión {thread_id}")
                    return False
                    
    except Exception as e:
        logger.error(f"❌ Error actualizando sesión: {e}")
        return False


def limpiar_sesiones_antiguas() -> int:
    """
    Limpia sesiones con más de 30 días de inactividad.
    
    Returns:
        Número de sesiones eliminadas
    """
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                query = """
                    DELETE FROM user_sessions
                    WHERE last_activity < NOW() - INTERVAL '30 days'
                    RETURNING thread_id
                """
                
                cur.execute(query)
                deleted = cur.fetchall()
                conn.commit()
                
                count = len(deleted)
                if count > 0:
                    logger.info(f"    🧹 Limpiadas {count} sesiones antiguas (> 30 días)")
                
                return count
                
    except Exception as e:
        logger.error(f"❌ Error limpiando sesiones antiguas: {e}")
        return 0


def recuperar_mensajes_checkpointer(thread_id: str, checkpointer) -> tuple:
    """
    Recupera mensajes previos Y estado conversacional del checkpointer.
    
    Args:
        thread_id: ID de la sesión
        checkpointer: Instancia de PostgresSaver
        
    Returns:
        Tupla (mensajes: list, estado_conversacion: str)
    """
    try:
        # Configuración para recuperar del checkpointer
        config = {"configurable": {"thread_id": thread_id}}
        
        # Obtener estado del checkpoint
        checkpoint = checkpointer.get(config)
        
        if checkpoint and 'channel_values' in checkpoint:
            messages = checkpoint['channel_values'].get('messages', [])
            estado_conversacion = checkpoint['channel_values'].get('estado_conversacion', 'inicial')
            
            logger.info(f"    ✓ Recuperados {len(messages)} mensajes del checkpointer")
            logger.info(f"    ✓ Estado conversación: {estado_conversacion}")
            
            return messages, estado_conversacion
        else:
            logger.info(f"    ℹ️ No hay datos previos en checkpointer")
            return [], 'inicial'
            
    except Exception as e:
        logger.warning(f"⚠️ Error recuperando del checkpointer: {e}")
        return [], 'inicial'


# ==================== NODO PRINCIPAL ====================

def nodo_cache_sesion(state: WhatsAppAgentState, checkpointer=None) -> WhatsAppAgentState:
    """
    Nodo N1: Cache de Sesión
    
    Gestiona sesiones activas con TTL de 24 horas.
    
    Flujo:
    1. Buscar sesión activa (< 24h inactividad)
    2. Si existe:
       - Recuperar mensajes del checkpointer
       - Agregar al estado actual
       - Actualizar timestamp
    3. Si NO existe o expiró:
       - Crear nueva sesión
       - Marcar sesion_expirada = True
    4. Limpiar sesiones antiguas (> 30 días) periódicamente
    
    Args:
        state: Estado del grafo con user_id ya identificado
        checkpointer: Instancia de PostgresSaver (inyectado por LangGraph)
        
    Returns:
        Estado actualizado con sesión y mensajes previos si aplica
    """
    logger.info("🗄️  [N1] CACHE_SESION - Verificando caché de sesión")
    
    user_id = state.get('user_id', '')
    phone_number = user_id  # El user_id ES el phone_number
    
    if not user_id:
        logger.error("❌ No hay user_id en el state")
        state['sesion_expirada'] = True
        state['timestamp'] = datetime.now().isoformat()
        return state
    
    logger.info(f"    User ID: {user_id}")
    
    # ========================================
    # PASO 1: Buscar sesión activa
    # ========================================
    sesion_activa = buscar_sesion_activa(user_id)
    
    # ========================================
    # PASO 2A: Sesión activa encontrada
    # ========================================
    if sesion_activa and sesion_activa['hours_inactive'] < SESSION_TTL_HOURS:
        thread_id = sesion_activa['thread_id']
        
        logger.info(f"    ✅ SESIÓN ACTIVA - Thread: {thread_id}")
        
        # Recuperar mensajes previos del checkpointer
        if checkpointer:
            mensajes_previos, estado_conversacion = recuperar_mensajes_checkpointer(thread_id, checkpointer)
            
            if mensajes_previos:
                # Agregar mensajes previos ANTES de los mensajes actuales
                # Esto mantiene el contexto conversacional
                state['messages'] = mensajes_previos + state.get('messages', [])
                logger.info(f"    📝 Contexto restaurado: {len(mensajes_previos)} mensajes previos")
            
            # Preservar estado conversacional si existe
            if estado_conversacion != 'inicial':
                state['estado_conversacion'] = estado_conversacion
                logger.info(f"    🔄 Estado conversacional restaurado: {estado_conversacion}")
        
        # Actualizar sesión
        state['session_id'] = thread_id
        state['sesion_expirada'] = False
        
        # Actualizar timestamp de actividad en BD
        actualizar_actividad_sesion(thread_id, user_id)
    
    # ========================================
    # PASO 2B: NO hay sesión activa (nueva o expirada)
    # ========================================
    else:
        logger.info(f"    🆕 SESIÓN NUEVA/EXPIRADA")
        
        # Crear nueva sesión
        thread_id = crear_nueva_sesion(user_id, phone_number)
        
        state['session_id'] = thread_id
        state['sesion_expirada'] = True  # Marcar para auto-resumen
        
        logger.info(f"    ✓ Nueva sesión: {thread_id}")
    
    # ========================================
    # PASO 3: Limpieza periódica (cada 100 sesiones creadas)
    # ========================================
    # Ejecutar limpieza de forma probabilística
    import random
    if random.random() < 0.01:  # 1% de probabilidad por llamada
        limpiar_sesiones_antiguas()
    
    # ========================================
    # PASO 4: Actualizar timestamp
    # ========================================
    state['timestamp'] = datetime.now().isoformat()
    
    logger.info(f"    ✅ Cache de sesión completado")
    return state


# ==================== WRAPPER PARA LANGGRAPH ====================

def nodo_cache_sesion_wrapper(state: WhatsAppAgentState) -> WhatsAppAgentState:
    """
    Wrapper para que el nodo funcione con LangGraph.
    
    El checkpointer se inyecta automáticamente por LangGraph cuando el grafo
    está compilado con checkpointer=PostgresSaver.
    
    Para acceder al checkpointer en runtime, necesitamos obtenerlo del contexto.
    Por ahora, dejamos checkpointer=None y LangGraph maneja la persistencia.
    """
    # TODO: Obtener checkpointer del contexto de ejecución de LangGraph
    # Por ahora, la persistencia la maneja automáticamente LangGraph
    return nodo_cache_sesion(state, checkpointer=None)
