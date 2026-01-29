"""
Scheduler de Recordatorios Automáticos
Envía recordatorios por WhatsApp 24h antes de cada cita
"""
import os
import schedule
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict
import requests

from src.database.db_config import get_db_session
from src.medical.models import CitasMedicas, Pacientes, Doctores

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def enviar_recordatorios():
    """
    Ejecuta cada hora.
    Busca citas en ventana 23-24h y envía recordatorios.
    """
    ahora = datetime.now()
    ventana_inicio = ahora + timedelta(hours=23)
    ventana_fin = ahora + timedelta(hours=24)

    logger.info(f"🔍 Buscando citas entre {ventana_inicio} y {ventana_fin}")

    with get_db_session() as db:
        # Buscar citas pendientes de recordatorio
        citas = db.query(CitasMedicas).filter(
            CitasMedicas.fecha_hora_inicio >= ventana_inicio,
            CitasMedicas.fecha_hora_inicio <= ventana_fin,
            CitasMedicas.estado.in_(['programada', 'confirmada']),
            CitasMedicas.recordatorio_enviado == False
        ).all()

        logger.info(f"📱 Enviando {len(citas)} recordatorios...")

        enviados = 0
        errores = 0

        for cita in citas:
            try:
                # Obtener datos
                paciente = db.query(Pacientes).get(cita.paciente_id)
                doctor = db.query(Doctores).get(cita.doctor_id)

                if not paciente or not doctor:
                    logger.error(f"❌ Datos incompletos para cita {cita.id}")
                    continue

                # Formatear mensaje
                fecha = cita.fecha_hora_inicio
                
                # Nombres de días en español
                dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
                meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
                        'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
                
                dia_nombre = dias[fecha.weekday()]
                mes_nombre = meses[fecha.month - 1]
                
                mensaje = f"""🔔 Recordatorio de Cita

Hola {paciente.nombre_completo}!

Tienes una cita programada para:

📅 {dia_nombre} {fecha.day} de {mes_nombre}, {fecha.year}
🕐 {fecha.strftime('%H:%M')} a {cita.fecha_hora_fin.strftime('%H:%M')}
👨‍⚕️ {doctor.nombre_completo}

💬 Si necesitas cancelar, responde "cancelar cita"

¡Te esperamos!"""

                # Enviar WhatsApp
                resultado = enviar_whatsapp(paciente.telefono, mensaje)

                if resultado['exito']:
                    # Marcar como enviado
                    cita.recordatorio_enviado = True
                    cita.recordatorio_fecha_envio = datetime.now()
                    cita.recordatorio_intentos += 1
                    db.commit()

                    enviados += 1
                    logger.info(f"✅ Recordatorio enviado: cita {cita.id}")
                else:
                    raise Exception(resultado['error'])

            except Exception as e:
                errores += 1
                logger.error(f"❌ Error cita {cita.id}: {e}")

                # Incrementar intentos (max 3)
                cita.recordatorio_intentos += 1
                if cita.recordatorio_intentos >= 3:
                    cita.recordatorio_enviado = True  # Marcar como enviado para no reintentar
                    logger.warning(f"⚠️ Cita {cita.id}: máximo de intentos alcanzado")
                db.commit()

        logger.info(f"📊 Resumen: {enviados} enviados, {errores} errores")
        return {'enviados': enviados, 'errores': errores}


def enviar_whatsapp(telefono: str, mensaje: str) -> Dict:
    """
    Envía mensaje vía API de WhatsApp.

    Args:
        telefono: Número de teléfono del destinatario
        mensaje: Texto del mensaje a enviar

    Returns:
        {'exito': True/False, 'error': str}
    """
    WHATSAPP_API_URL = os.getenv('WHATSAPP_API_URL', 'http://localhost:3000')

    try:
        response = requests.post(
            f"{WHATSAPP_API_URL}/api/send-reminder",
            json={
                'destinatario': telefono,
                'mensaje': mensaje
            },
            timeout=10
        )

        if response.status_code == 200:
            return {'exito': True}
        else:
            return {'exito': False, 'error': response.text}

    except requests.exceptions.Timeout:
        return {'exito': False, 'error': 'Timeout de API'}
    except requests.exceptions.RequestException as e:
        return {'exito': False, 'error': str(e)}
    except Exception as e:
        return {'exito': False, 'error': str(e)}


def run_scheduler():
    """Ejecutar scheduler en loop infinito"""
    logger.info("🚀 Scheduler de recordatorios iniciado")
    logger.info("⏰ Ejecutando cada hora...")

    # Programar ejecución cada hora
    schedule.every(1).hours.do(enviar_recordatorios)

    # Loop infinito
    while True:
        schedule.run_pending()
        time.sleep(60)  # Revisar cada minuto


if __name__ == '__main__':
    run_scheduler()
