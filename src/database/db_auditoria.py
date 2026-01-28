"""
Módulo de Auditoría - Guarda conversaciones en PostgreSQL

Registra todos los mensajes (usuario y asistente) para auditoría y compliance.
Retención: 6 meses (limpieza manual via SQL)
"""

import logging
from typing import Optional
import psycopg2
from src.database.db_config import get_db_connection
from src.utils.time_utils import get_current_time

logger = logging.getLogger(__name__)


def insertar_auditoria(
    user_id: str,
    session_id: str,
    rol: str,
    contenido: str
) -> bool:
    """
    Inserta un mensaje en la tabla auditoria_conversaciones.

    Args:
        user_id: ID del usuario de WhatsApp (ej: "521234567890")
        session_id: ID de la sesión actual
        rol: 'user', 'assistant' o 'system'
        contenido: Texto del mensaje

    Returns:
        True si se insertó exitosamente, False si falló

    Note:
        Esta función NO debe bloquear el flujo principal si falla.
        Los errores se loguean pero no se propagan.
    """
    try:
        # Validar rol
        if rol not in ['user', 'assistant', 'system']:
            logger.warning(f"    ⚠️  Rol de auditoría inválido: {rol}")
            return False

        # Validar contenido no vacío
        if not contenido or not contenido.strip():
            logger.debug("    ⚠️  Contenido vacío, omitiendo auditoría")
            return False

        # Obtener conexión
        conn = get_db_connection()
        if not conn:
            logger.warning("    ⚠️  Auditoría: No se pudo conectar a PostgreSQL")
            return False

        cursor = conn.cursor()

        # Query de inserción
        query = """
        INSERT INTO auditoria_conversaciones
        (user_id, session_id, rol, contenido, timestamp)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
        """

        # Obtener timestamp actual
        timestamp = get_current_time().to_datetime_string()

        # Ejecutar
        cursor.execute(query, (
            user_id,
            session_id,
            rol,
            contenido.strip(),
            timestamp
        ))

        audit_id = cursor.fetchone()[0]

        # Commit
        conn.commit()
        cursor.close()
        conn.close()

        logger.debug(f"    📝 Auditoría registrada (ID: {audit_id}, rol: {rol})")
        return True

    except psycopg2.Error as e:
        logger.warning(f"    ⚠️  Error PostgreSQL en auditoría: {e}")
        return False
    except Exception as e:
        logger.warning(f"    ⚠️  Error inesperado en auditoría: {e}")
        return False


def obtener_historial_usuario(
    user_id: str,
    limite: int = 50
) -> list:
    """
    Obtiene el historial de conversaciones de un usuario.

    Args:
        user_id: ID del usuario
        limite: Máximo de registros a retornar

    Returns:
        Lista de diccionarios con {rol, contenido, timestamp}
    """
    try:
        conn = get_db_connection()
        if not conn:
            return []

        cursor = conn.cursor()

        query = """
        SELECT rol, contenido, timestamp
        FROM auditoria_conversaciones
        WHERE user_id = %s
        ORDER BY timestamp DESC
        LIMIT %s
        """

        cursor.execute(query, (user_id, limite))
        resultados = cursor.fetchall()

        cursor.close()
        conn.close()

        return [
            {
                'rol': row[0],
                'contenido': row[1],
                'timestamp': row[2].isoformat() if row[2] else None
            }
            for row in resultados
        ]

    except Exception as e:
        logger.error(f"Error obteniendo historial: {e}")
        return []


def contar_mensajes_usuario(user_id: str) -> int:
    """
    Cuenta el total de mensajes de un usuario en auditoría.

    Args:
        user_id: ID del usuario

    Returns:
        Número total de mensajes
    """
    try:
        conn = get_db_connection()
        if not conn:
            return 0

        cursor = conn.cursor()

        cursor.execute(
            "SELECT COUNT(*) FROM auditoria_conversaciones WHERE user_id = %s",
            (user_id,)
        )

        count = cursor.fetchone()[0]

        cursor.close()
        conn.close()

        return count

    except Exception as e:
        logger.error(f"Error contando mensajes: {e}")
        return 0
