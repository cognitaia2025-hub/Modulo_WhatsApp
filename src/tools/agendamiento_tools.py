"""
Herramientas de agendamiento de citas.

IMPORTANTE: Estas tools usan Pydantic para validación automática.
El LLM debe pasar datos en formato correcto o recibirá error descriptivo.
"""

from langchain_core.tools import tool
from .models import FechaCita, HoraCita, DatosPaciente
import psycopg
import os
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@tool
def agendar_cita_paciente(
    fecha: FechaCita,
    hora: HoraCita,
    paciente_id: int,
    motivo: str
) -> str:
    """
    Agenda una cita médica para un paciente existente.
    
    Esta herramienta valida automáticamente:
    - Formato de fecha (YYYY-MM-DD)
    - Fecha sea futura (no pasada)
    - Formato de hora (HH:MM en 24h)
    - Hora dentro del horario laboral
    - Hora en intervalos de 30 minutos
    
    Args:
        fecha: Fecha de la cita (FechaCita validado)
        hora: Hora de la cita (HoraCita validado)
        paciente_id: ID del paciente en la base de datos
        motivo: Motivo de la consulta
        
    Returns:
        Mensaje de confirmación con ID de cita
        
    Examples:
        >>> agendar_cita_paciente(
        ...     fecha=FechaCita(fecha="2026-02-15"),
        ...     hora=HoraCita(hora="14:30"),
        ...     paciente_id=123,
        ...     motivo="Consulta general"
        ... )
        "✅ Cita 456 agendada para 2026-02-15 a las 14:30"
    """
    
    # Si llegamos aquí, Pydantic ya validó todo ✅
    # No necesitamos try/except para validación de formato
    
    try:
        DATABASE_URL = os.getenv("DATABASE_URL")
        
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                # Verificar que el paciente existe
                cur.execute("SELECT id FROM pacientes WHERE id = %s", (paciente_id,))
                if not cur.fetchone():
                    return f"❌ Error: No existe paciente con ID {paciente_id}"
                
                # Verificar disponibilidad del horario
                fecha_hora = f"{fecha.fecha} {hora.hora}:00"
                cur.execute("""
                    SELECT id FROM citas_medicas 
                    WHERE fecha_hora_inicio = %s 
                    AND estado != 'cancelada'
                """, (fecha_hora,))
                
                if cur.fetchone():
                    return f"❌ El horario {fecha.fecha} a las {hora.hora} ya está ocupado. Elija otro horario."
                
                # Insertar cita
                query = """
                    INSERT INTO citas_medicas 
                    (paciente_id, fecha_hora_inicio, motivo_consulta, estado, created_at)
                    VALUES (%s, %s, %s, 'agendada', NOW())
                    RETURNING id
                """
                
                cur.execute(query, (paciente_id, fecha_hora, motivo))
                cita_id = cur.fetchone()[0]
                conn.commit()
                
                logger.info(f"Cita {cita_id} agendada para paciente {paciente_id} el {fecha_hora}")
                
                return f"✅ Cita {cita_id} agendada exitosamente para {fecha.fecha} a las {hora.hora}. Motivo: {motivo}"
                
    except psycopg.Error as e:
        logger.error(f"Error de base de datos al agendar cita: {e}")
        return f"❌ Error al agendar cita. Por favor intente nuevamente."
    
    except Exception as e:
        logger.error(f"Error inesperado al agendar cita: {e}")
        return f"❌ Error inesperado. Por favor contacte al administrador."


@tool
def reagendar_cita(
    cita_id: int,
    nueva_fecha: FechaCita,
    nueva_hora: HoraCita
) -> str:
    """
    Reagenda una cita existente a nueva fecha/hora.
    
    Valida automáticamente el nuevo horario con Pydantic.
    
    Args:
        cita_id: ID de la cita a reagendar
        nueva_fecha: Nueva fecha (validada por Pydantic)
        nueva_hora: Nueva hora (validada por Pydantic)
        
    Returns:
        Mensaje de confirmación
    """
    
    try:
        DATABASE_URL = os.getenv("DATABASE_URL")
        
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                # Verificar que la cita existe
                cur.execute("""
                    SELECT id, estado 
                    FROM citas_medicas 
                    WHERE id = %s
                """, (cita_id,))
                
                result = cur.fetchone()
                if not result:
                    return f"❌ No existe cita con ID {cita_id}"
                
                if result[1] == 'completada':
                    return f"❌ No se puede reagendar una cita ya completada"
                
                # Verificar disponibilidad del nuevo horario
                nueva_fecha_hora = f"{nueva_fecha.fecha} {nueva_hora.hora}:00"
                cur.execute("""
                    SELECT id FROM citas_medicas 
                    WHERE fecha_hora_inicio = %s 
                    AND estado != 'cancelada'
                    AND id != %s
                """, (nueva_fecha_hora, cita_id))
                
                if cur.fetchone():
                    return f"❌ El horario {nueva_fecha.fecha} a las {nueva_hora.hora} ya está ocupado"
                
                # Actualizar cita
                cur.execute("""
                    UPDATE citas_medicas 
                    SET fecha_hora_inicio = %s,
                        updated_at = NOW()
                    WHERE id = %s
                """, (nueva_fecha_hora, cita_id))
                
                conn.commit()
                
                logger.info(f"Cita {cita_id} reagendada a {nueva_fecha_hora}")
                
                return f"✅ Cita {cita_id} reagendada para {nueva_fecha.fecha} a las {nueva_hora.hora}"
                
    except Exception as e:
        logger.error(f"Error al reagendar cita: {e}")
        return f"❌ Error al reagendar. Intente nuevamente."


@tool
def cancelar_cita(cita_id: int, motivo_cancelacion: str = "") -> str:
    """
    Cancela una cita existente.
    
    Args:
        cita_id: ID de la cita a cancelar
        motivo_cancelacion: Motivo opcional de la cancelación
        
    Returns:
        Mensaje de confirmación
    """
    
    try:
        DATABASE_URL = os.getenv("DATABASE_URL")
        
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                # Verificar que existe
                cur.execute("""
                    SELECT id, estado, fecha_hora_inicio 
                    FROM citas_medicas 
                    WHERE id = %s
                """, (cita_id,))
                
                result = cur.fetchone()
                if not result:
                    return f"❌ No existe cita con ID {cita_id}"
                
                if result[1] == 'cancelada':
                    return f"⚠️ La cita {cita_id} ya estaba cancelada"
                
                if result[1] == 'completada':
                    return f"❌ No se puede cancelar una cita ya completada"
                
                # Cancelar
                cur.execute("""
                    UPDATE citas_medicas 
                    SET estado = 'cancelada',
                        motivo_cancelacion = %s,
                        updated_at = NOW()
                    WHERE id = %s
                """, (motivo_cancelacion, cita_id))
                
                conn.commit()
                
                logger.info(f"Cita {cita_id} cancelada. Motivo: {motivo_cancelacion}")
                
                return f"✅ Cita {cita_id} cancelada exitosamente"
                
    except Exception as e:
        logger.error(f"Error al cancelar cita: {e}")
        return f"❌ Error al cancelar. Intente nuevamente."
