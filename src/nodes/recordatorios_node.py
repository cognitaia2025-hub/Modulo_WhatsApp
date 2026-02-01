"""
Nodo 9: Recordatorios Automáticos

Envía recordatorios de WhatsApp antes de citas médicas:
- 24 horas antes
- 2 horas antes

MEJORAS DESDE INICIO:
✅ Command pattern
✅ psycopg3
✅ Logging estructurado
✅ Integración WhatsApp
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
import psycopg
from psycopg.rows import dict_row
import os
from dotenv import load_dotenv
from langgraph.types import Command
from src.utils.logging_config import (
    log_separator,
    log_node_io
)
from src.utils import get_current_time

load_dotenv()
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

# ==================== CONSTANTES ====================

# Ventanas de tiempo para recordatorios (horas antes)
RECORDATORIO_24H = 24
RECORDATORIO_2H = 2

# Mensajes de recordatorio
TEMPLATE_24H = """🔔 Recordatorio de cita médica

📅 Fecha: {fecha}
🕐 Hora: {hora}
👨‍⚕️ Doctor: Dr. {doctor_nombre}
📍 Consultorio: {ubicacion}

Te esperamos mañana. Si necesitas cancelar o reprogramar, responde a este mensaje."""

TEMPLATE_2H = """⏰ Tu cita es en 2 horas

📅 Hoy a las {hora}
👨‍⚕️ Dr. {doctor_nombre}

Por favor confirma tu asistencia respondiendo "Confirmo" """


# ==================== FUNCIÓN PRINCIPAL ====================

def nodo_recordatorios(state: Dict[str, Any]) -> Command:
    """
    Nodo 9: Procesa y envía recordatorios de citas próximas
    
    IMPLEMENTACIÓN MODERNA:
    ✅ Command pattern desde inicio
    ✅ psycopg3
    ✅ Logging estructurado
    
    Flujo:
    1. Consulta citas próximas (24h y 2h)
    2. Filtra las que no han recibido recordatorio
    3. Envía mensaje WhatsApp
    4. Actualiza flag recordatorio_enviado
    
    Returns:
        Command con update y goto
    """
    log_separator(logger, "NODO_9_RECORDATORIOS", "INICIO")
    
    tipo_ejecucion = state.get('tipo_ejecucion', 'scheduler')
    
    # Log de input
    input_data = f"tipo: {tipo_ejecucion}"
    log_node_io(logger, "INPUT", "NODO_9_RECORD", input_data)
    
    logger.info(f"    ⏰ Tipo de ejecución: {tipo_ejecucion}")
    
    try:
        # 1. Obtener citas que requieren recordatorios
        logger.info("    🔍 Buscando citas próximas...")
        
        ahora = get_current_time()
        ventana_24h = ahora.add(hours=RECORDATORIO_24H)
        ventana_2h = ahora.add(hours=RECORDATORIO_2H)
        
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                # Citas para recordatorio 24h
                cur.execute("""
                    SELECT 
                        c.id,
                        c.fecha_hora_inicio as fecha_hora,
                        c.recordatorio_24h_enviado,
                        c.recordatorio_2h_enviado,
                        p.telefono as paciente_phone,
                        p.nombre_completo as paciente_nombre,
                        d.nombre_completo as doctor_nombre,
                        d.direccion_consultorio as ubicacion_consultorio
                    FROM citas_medicas c
                    JOIN pacientes p ON c.paciente_id = p.id
                    JOIN doctores d ON c.doctor_id = d.id
                    WHERE c.estado = 'confirmada'
                    AND c.fecha_hora_inicio BETWEEN %s AND %s
                    AND c.recordatorio_24h_enviado = FALSE
                """, (ahora.to_datetime_string(), ventana_24h.to_datetime_string()))
                
                citas_24h = cur.fetchall()
                
                # Citas para recordatorio 2h
                cur.execute("""
                    SELECT 
                        c.id,
                        c.fecha_hora_inicio as fecha_hora,
                        c.recordatorio_24h_enviado,
                        c.recordatorio_2h_enviado,
                        p.telefono as paciente_phone,
                        p.nombre_completo as paciente_nombre,
                        d.nombre_completo as doctor_nombre,
                        d.direccion_consultorio as ubicacion_consultorio
                    FROM citas_medicas c
                    JOIN pacientes p ON c.paciente_id = p.id
                    JOIN doctores d ON c.doctor_id = d.id
                    WHERE c.estado = 'confirmada'
                    AND c.fecha_hora_inicio BETWEEN %s AND %s
                    AND c.recordatorio_2h_enviado = FALSE
                """, (ahora.to_datetime_string(), ventana_2h.to_datetime_string()))
                
                citas_2h = cur.fetchall()
        
        logger.info(f"    📊 Recordatorios 24h: {len(citas_24h)}")
        logger.info(f"    📊 Recordatorios 2h: {len(citas_2h)}")
        
        # 2. Enviar recordatorios
        enviados_24h = 0
        enviados_2h = 0
        
        # Procesar recordatorios 24h
        for cita in citas_24h:
            try:
                mensaje = TEMPLATE_24H.format(
                    fecha=cita['fecha_hora'].strftime('%d/%m/%Y'),
                    hora=cita['fecha_hora'].strftime('%H:%M'),
                    doctor_nombre=cita['doctor_nombre'],
                    ubicacion=cita['ubicacion_consultorio'] or 'Consultorio principal'
                )
                
                # Enviar WhatsApp (implementar función)
                exito = enviar_whatsapp(cita['paciente_phone'], mensaje)
                
                if exito:
                    # Actualizar flag
                    with psycopg.connect(DATABASE_URL) as conn:
                        with conn.cursor() as cur:
                            cur.execute("""
                                UPDATE citas_medicas
                                SET recordatorio_24h_enviado = TRUE,
                                    recordatorio_24h_fecha = NOW()
                                WHERE id = %s
                            """, (cita['id'],))
                            conn.commit()
                    
                    enviados_24h += 1
                    logger.info(f"       ✅ Recordatorio 24h enviado a {cita['paciente_nombre']}")
                
            except Exception as e:
                logger.error(f"       ❌ Error enviando a {cita['paciente_phone']}: {e}")
        
        # Procesar recordatorios 2h
        for cita in citas_2h:
            try:
                mensaje = TEMPLATE_2H.format(
                    hora=cita['fecha_hora'].strftime('%H:%M'),
                    doctor_nombre=cita['doctor_nombre']
                )
                
                exito = enviar_whatsapp(cita['paciente_phone'], mensaje)
                
                if exito:
                    with psycopg.connect(DATABASE_URL) as conn:
                        with conn.cursor() as cur:
                            cur.execute("""
                                UPDATE citas_medicas
                                SET recordatorio_2h_enviado = TRUE,
                                    recordatorio_2h_fecha = NOW()
                                WHERE id = %s
                            """, (cita['id'],))
                            conn.commit()
                    
                    enviados_2h += 1
                    logger.info(f"       ✅ Recordatorio 2h enviado a {cita['paciente_nombre']}")
                
            except Exception as e:
                logger.error(f"       ❌ Error enviando: {e}")
        
        logger.info(f"    ✅ Total enviados: {enviados_24h + enviados_2h}")
        
        # Log de output
        output_data = f"24h: {enviados_24h}, 2h: {enviados_2h}"
        log_node_io(logger, "OUTPUT", "NODO_9_RECORD", output_data)
        log_separator(logger, "NODO_9_RECORDATORIOS", "FIN")
        
        # ✅ Retornar Command
        return Command(
            update={
                'recordatorios_enviados': enviados_24h + enviados_2h,
                'recordatorios_24h': enviados_24h,
                'recordatorios_2h': enviados_2h
            },
            goto="END"
        )
        
    except Exception as e:
        logger.error(f"    ❌ Error en recordatorios: {e}")
        log_separator(logger, "NODO_9_RECORDATORIOS", "FIN")
        
        return Command(
            update={
                'recordatorios_enviados': 0,
                'error_recordatorios': str(e)
            },
            goto="END"
        )


# ==================== FUNCIÓN AUXILIAR ====================

def enviar_whatsapp(telefono: str, mensaje: str) -> bool:
    """
    Envía mensaje WhatsApp usando la API configurada.
    
    TODO: Implementar integración real con WhatsApp Business API
    Por ahora retorna True para testing.
    """
    try:
        # PLACEHOLDER: Implementar con tu proveedor WhatsApp
        # Ejemplo con Twilio:
        # from twilio.rest import Client
        # client = Client(account_sid, auth_token)
        # message = client.messages.create(
        #     from_='whatsapp:+14155238886',
        #     body=mensaje,
        #     to=f'whatsapp:{telefono}'
        # )
        
        logger.info(f"    📱 WhatsApp simulado enviado a {telefono}")
        return True
        
    except Exception as e:
        logger.error(f"    ❌ Error enviando WhatsApp: {e}")
        return False


# ==================== WRAPPER ====================

def nodo_recordatorios_wrapper(state: Dict[str, Any]) -> Command:
    """Wrapper para LangGraph - retorna Command directamente."""
    return nodo_recordatorios(state)
