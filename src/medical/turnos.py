"""
Sistema de Turnos Rotativos para Doctores

Este módulo implementa la lógica de asignación equitativa de citas
entre Doctor Santiago (ID=1) y Doctora Joana (ID=2).

NO usa LLM - solo lógica determinística SQL + if/else
"""

import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime

import psycopg
from dotenv import load_dotenv

try:
    from src.medical.connection_pool import get_connection
except ImportError:
    get_connection = None

# Cargar variables de entorno
load_dotenv()

# Configuración
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5434/agente_whatsapp")

# Logger
logger = logging.getLogger(__name__)


def obtener_siguiente_doctor_turno() -> Dict[str, Any]:
    """
    Obtiene el doctor que corresponde al turno actual según alternancia.
    
    Lógica de turnos rotativos:
    - Si ultimo_doctor_id == NULL (primera vez) → Santiago (ID=1)
    - Si ultimo_doctor_id == 1 (Santiago) → Joana (ID=2)
    - Si ultimo_doctor_id == 2 (Joana) → Santiago (ID=1)
    
    Returns:
        {
            "doctor_id": int,
            "nombre_completo": str,
            "especialidad": str,
            "total_citas_asignadas": int,
            "en_turno": True
        }
    
    Raises:
        Exception: Si no hay doctores en BD o hay error de conexión
    
    Nota: Esta función NO actualiza la BD, solo consulta.
    """
    try:
        conn_manager = get_connection() if get_connection else psycopg.connect(DATABASE_URL)
        with conn_manager as conn:
            with conn.cursor() as cur:
                # Obtener último doctor que recibió cita
                cur.execute("""
                    SELECT ultimo_doctor_id 
                    FROM control_turnos 
                    ORDER BY id DESC 
                    LIMIT 1
                """)
                
                result = cur.fetchone()
                ultimo_doctor_id = result[0] if result else None
                
                # Determinar siguiente doctor según alternancia
                if ultimo_doctor_id is None:
                    siguiente_doctor_id = 1  # Primera vez: Santiago
                    logger.info("🔄 Primer turno: Asignando a Doctor Santiago (ID=1)")
                elif ultimo_doctor_id == 1:
                    siguiente_doctor_id = 2  # Santiago → Joana
                    logger.info("🔄 Turno: Santiago → Joana (ID=2)")
                else:
                    siguiente_doctor_id = 1  # Joana → Santiago
                    logger.info("🔄 Turno: Joana → Santiago (ID=1)")
                
                # Obtener información completa del doctor
                cur.execute("""
                    SELECT 
                        d.id,
                        d.nombre_completo,
                        d.especialidad,
                        d.total_citas_asignadas,
                        d.phone_number
                    FROM doctores d
                    WHERE d.id = %s
                """, (siguiente_doctor_id,))
                
                doctor_data = cur.fetchone()
                
                if not doctor_data:
                    raise Exception(f"Doctor con ID {siguiente_doctor_id} no encontrado en BD")
                
                resultado = {
                    "doctor_id": doctor_data[0],
                    "nombre_completo": doctor_data[1],
                    "especialidad": doctor_data[2],
                    "total_citas_asignadas": doctor_data[3],
                    "phone_number": doctor_data[4],
                    "en_turno": True
                }
                
                logger.info(f"✅ Doctor en turno: {resultado['nombre_completo']}")
                return resultado
                
    except Exception as e:
        logger.error(f"❌ Error obteniendo siguiente doctor en turno: {e}")
        raise


def actualizar_control_turnos(doctor_id: int) -> bool:
    """
    Actualiza el estado de turnos después de asignar una cita.
    
    Operaciones:
    1. UPDATE ultimo_doctor_id = doctor_id
    2. Incrementar contador del doctor (citas_santiago o citas_joana)
    3. Incrementar total_turnos_asignados
    4. UPDATE timestamp = NOW()
    
    Args:
        doctor_id: ID del doctor que recibió la cita (1=Santiago, 2=Joana)
    
    Returns:
        True si se actualizó correctamente, False en caso de error
    
    Example:
        >>> actualizar_control_turnos(1)  # Santiago recibió una cita
        True
    """
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                # Actualizar control de turnos usando la función SQL
                cur.execute("SELECT actualizar_turno_asignado(%s)", (doctor_id,))
                resultado = cur.fetchone()[0]
                
                conn.commit()
                
                if resultado:
                    # Obtener estadísticas actualizadas
                    cur.execute("""
                        SELECT 
                            total_turnos_asignados,
                            citas_santiago,
                            citas_joana
                        FROM control_turnos
                        ORDER BY id DESC
                        LIMIT 1
                    """)
                    
                    stats = cur.fetchone()
                    if stats:
                        total, santiago, joana = stats
                        logger.info(f"✅ Control turnos actualizado: Doctor ID={doctor_id}")
                        logger.info(f"   📊 Total: {total} | Santiago: {santiago} | Joana: {joana}")
                    
                    return True
                else:
                    logger.warning("⚠️  No se actualizó control_turnos")
                    return False
                    
    except Exception as e:
        logger.error(f"❌ Error actualizando control de turnos: {e}")
        return False


def obtener_estadisticas_turnos() -> Dict[str, Any]:
    """
    Obtiene estadísticas del sistema de turnos.
    
    Returns:
        {
            "total_turnos": int,
            "citas_santiago": int,
            "citas_joana": int,
            "ultimo_turno": str,  # "Santiago" o "Joana"
            "porcentaje_santiago": float,
            "porcentaje_joana": float,
            "ultima_actualizacion": datetime
        }
    """
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT * FROM estadisticas_turnos
                """)
                
                result = cur.fetchone()
                if result:
                    return {
                        "total_turnos": result[0],
                        "citas_santiago": result[1],
                        "citas_joana": result[2],
                        "ultimo_turno": result[3],
                        "ultima_actualizacion": result[4],
                        "porcentaje_santiago": float(result[5]) if result[5] else 0.0,
                        "porcentaje_joana": float(result[6]) if result[6] else 0.0
                    }
                else:
                    return {
                        "total_turnos": 0,
                        "citas_santiago": 0,
                        "citas_joana": 0,
                        "ultimo_turno": "Ninguno",
                        "porcentaje_santiago": 0.0,
                        "porcentaje_joana": 0.0
                    }
                    
    except Exception as e:
        logger.error(f"❌ Error obteniendo estadísticas: {e}")
        return {}


def obtener_otro_doctor(doctor_id: int) -> Optional[Dict[str, Any]]:
    """
    Obtiene el otro doctor (fallback cuando el del turno está ocupado).
    
    Args:
        doctor_id: ID del doctor actual (1 o 2)
    
    Returns:
        Información del otro doctor o None si no existe
    """
    otro_id = 2 if doctor_id == 1 else 1
    
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        id,
                        nombre_completo,
                        especialidad,
                        total_citas_asignadas,
                        phone_number
                    FROM doctores
                    WHERE id = %s
                """, (otro_id,))
                
                result = cur.fetchone()
                if result:
                    return {
                        "doctor_id": result[0],
                        "nombre_completo": result[1],
                        "especialidad": result[2],
                        "total_citas_asignadas": result[3],
                        "phone_number": result[4],
                        "en_turno": False
                    }
                return None
                
    except Exception as e:
        logger.error(f"❌ Error obteniendo otro doctor: {e}")
        return None
