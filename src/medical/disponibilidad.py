"""
Validación de Disponibilidad de Doctores

Verifica horarios de atención, conflictos de citas y días de clínica.
"""

import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime, time
from functools import lru_cache

import psycopg
import pytz
from dotenv import load_dotenv

try:
    from src.medical.connection_pool import get_connection
except ImportError:
    get_connection = None

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5434/agente_whatsapp")
TIMEZONE = pytz.timezone("America/Tijuana")

logger = logging.getLogger(__name__)

# Días de atención de la clínica: Jueves(3), Viernes(4), Sábado(5), Domingo(6), Lunes(0)
DIAS_ATENCION = [0, 3, 4, 5, 6]

# Caché simple para disponibilidad (key: doctor_id|fecha_inicio_iso)
_cache_disponibilidad: Dict[str, Dict[str, Any]] = {}
_MAX_CACHE_SIZE = 500


def check_doctor_availability(
    doctor_id: int,
    fecha_hora_inicio: datetime,
    fecha_hora_fin: datetime,
    use_cache: bool = True
) -> Dict[str, Any]:
    """
    Verifica si un doctor está disponible en el horario solicitado.
    
    Validaciones realizadas:
    1. Día de la semana está en días de atención (Jueves-Lunes)
    2. Horario está dentro del horario de atención del doctor
    3. No hay citas conflictivas (overlap de horarios)
    4. Doctor está activo en la BD
    
    Args:
        doctor_id: ID del doctor (1=Santiago, 2=Joana)
        fecha_hora_inicio: Inicio de la cita (timezone-aware)
        fecha_hora_fin: Fin de la cita (timezone-aware)
    
    Returns:
        {
            "disponible": bool,
            "razon": str,  # Si no disponible
            "conflicto_con": Optional[int],  # ID de cita conflictiva
            "detalles": Optional[Dict]
        }
    
    Example:
        >>> fecha_inicio = datetime(2026, 1, 30, 10, 30, tzinfo=TIMEZONE)
        >>> fecha_fin = datetime(2026, 1, 30, 11, 30, tzinfo=TIMEZONE)
        >>> check_doctor_availability(1, fecha_inicio, fecha_fin)
        {"disponible": True, "razon": None}
    """
    # Revisar caché primero
    if use_cache:
        cache_key = f"{doctor_id}|{fecha_hora_inicio.isoformat()}"
        if cache_key in _cache_disponibilidad:
            return _cache_disponibilidad[cache_key]
    
    try:
        # Asegurar que las fechas tienen timezone
        if fecha_hora_inicio.tzinfo is None:
            fecha_hora_inicio = TIMEZONE.localize(fecha_hora_inicio)
        if fecha_hora_fin.tzinfo is None:
            fecha_hora_fin = TIMEZONE.localize(fecha_hora_fin)
        
        # 1. Verificar día de atención
        dia_semana = fecha_hora_inicio.weekday()  # 0=Lunes, 6=Domingo
        
        if dia_semana not in DIAS_ATENCION:
            dias_texto = "Jueves a Lunes"
            return {
                "disponible": False,
                "razon": "dia_cerrado",
                "conflicto_con": None,
                "detalles": {
                    "mensaje": f"La clínica solo atiende {dias_texto}",
                    "dia_solicitado": fecha_hora_inicio.strftime("%A")
                }
            }
        
        # Usar connection pool si está disponible
        conn_manager = get_connection() if get_connection else psycopg.connect(DATABASE_URL)
        
        with conn_manager as conn:
            with conn.cursor() as cur:
                # 2. Verificar que el doctor existe y está activo
                cur.execute("""
                    SELECT nombre_completo
                    FROM doctores
                    WHERE id = %s
                """, (doctor_id,))
                
                doctor = cur.fetchone()
                if not doctor:
                    return {
                        "disponible": False,
                        "razon": "doctor_no_existe",
                        "conflicto_con": None,
                        "detalles": {"mensaje": f"Doctor ID {doctor_id} no encontrado"}
                    }
                
                # 3. Verificar horario de atención (hardcoded: 8:30-18:30)
                hora_solicitada_inicio = fecha_hora_inicio.time()
                hora_solicitada_fin = fecha_hora_fin.time()
                
                # Horarios de clínica
                if dia_semana in [5, 6]:  # Sábado, Domingo
                    hora_inicio_clinica = time(10, 30)
                    hora_fin_clinica = time(17, 30)
                else:  # Jueves, Viernes, Lunes
                    hora_inicio_clinica = time(8, 30)
                    hora_fin_clinica = time(18, 30)
                
                # Validar que el inicio esté dentro del horario Y que el fin no exceda
                if not (hora_inicio_clinica <= hora_solicitada_inicio < hora_fin_clinica):
                    return {
                        "disponible": False,
                        "razon": "fuera_de_horario",
                        "conflicto_con": None,
                        "detalles": {
                            "mensaje": f"Horario de clínica: {hora_inicio_clinica} - {hora_fin_clinica}",
                            "solicitado": f"{hora_solicitada_inicio} - {hora_solicitada_fin}"
                        }
                    }
                
                if hora_solicitada_fin > hora_fin_clinica:
                    return {
                        "disponible": False,
                        "razon": "fuera_de_horario",
                        "conflicto_con": None,
                        "detalles": {
                            "mensaje": f"La cita terminaría después del horario ({hora_fin_clinica})",
                            "solicitado": f"{hora_solicitada_inicio} - {hora_solicitada_fin}"
                        }
                    }
                
                # 4. Verificar conflictos con citas existentes usando función SQL
                cur.execute("""
                    SELECT * FROM check_conflicto_horario(%s, %s, %s)
                """, (doctor_id, fecha_hora_inicio, fecha_hora_fin))
                
                conflicto = cur.fetchone()
                tiene_conflicto, cita_id, descripcion = conflicto
                
                if tiene_conflicto:
                    return {
                        "disponible": False,
                        "razon": "ocupado",
                        "conflicto_con": cita_id,
                        "detalles": {
                            "mensaje": descripcion,
                            "cita_conflictiva_id": cita_id
                        }
                    }
                
                # ✅ Doctor disponible
                logger.info(f"✅ Doctor {doctor_id} disponible: {fecha_hora_inicio.strftime('%Y-%m-%d %H:%M')}")
                return {
                    "disponible": True,
                    "razon": None,
                    "conflicto_con": None,
                    "detalles": {
                        "mensaje": "Doctor disponible",
                        "doctor": doctor[0]
                    }
                }
                
    except Exception as e:
        logger.error(f"❌ Error verificando disponibilidad: {e}")
        return {
            "disponible": False,
            "razon": "error_sistema",
            "conflicto_con": None,
            "detalles": {"mensaje": f"Error: {str(e)}"}
        }


def validar_horario_clinica(fecha_hora: datetime) -> Dict[str, Any]:
    """
    Valida que la fecha/hora esté dentro del horario de la clínica.
    
    Horario: Jueves-Lunes, 8:30 AM - 6:30 PM
    
    Args:
        fecha_hora: Datetime a validar
    
    Returns:
        {"valido": bool, "razon": str}
    """
    if fecha_hora.tzinfo is None:
        fecha_hora = TIMEZONE.localize(fecha_hora)
    
    dia_semana = fecha_hora.weekday()
    hora = fecha_hora.time()
    
    # Validar día
    if dia_semana not in DIAS_ATENCION:
        return {
            "valido": False,
            "razon": "La clínica solo atiende de Jueves a Lunes"
        }
    
    # Validar horario (8:30 AM - 6:30 PM)
    hora_inicio = time(8, 30)
    hora_fin = time(18, 30)
    
    if not (hora_inicio <= hora < hora_fin):
        return {
            "valido": False,
            "razon": f"Horario de atención: 8:30 AM - 6:30 PM. Solicitado: {hora.strftime('%H:%M')}"
        }
    
    return {"valido": True, "razon": None}


def obtener_horarios_doctor(doctor_id: int) -> list[Dict[str, Any]]:
    """
    Obtiene todos los horarios configurados de un doctor.
    
    Args:
        doctor_id: ID del doctor
    
    Returns:
        Lista de horarios por día de la semana
    """
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        dia_semana,
                        hora_inicio,
                        hora_fin,
                        duracion_cita,
                        disponible
                    FROM disponibilidad_medica
                    WHERE doctor_id = %s
                    ORDER BY dia_semana
                """, (doctor_id,))
                
                dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
                horarios = []
                
                for row in cur.fetchall():
                    dia_num, hora_ini, hora_fin, duracion, disponible = row
                    horarios.append({
                        "dia_semana": dia_num,
                        "dia_nombre": dias[dia_num],
                        "hora_inicio": str(hora_ini),
                        "hora_fin": str(hora_fin),
                        "duracion_cita_minutos": duracion,
                        "disponible": disponible
                    })
                
                return horarios
                
    except Exception as e:
        logger.error(f"❌ Error obteniendo horarios del doctor: {e}")
        return []
