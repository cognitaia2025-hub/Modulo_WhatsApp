"""
Worker de Reintentos - Sincronización Google Calendar
=====================================================

Worker que ejecuta cada 15 minutos para reintentar
sincronizaciones fallidas con Google Calendar.

REGLA: BD médica es source of truth.
Si falla Google después de max_intentos, registrar error permanente
pero cita sigue válida en BD.
"""

import os
import sys
import time
import logging
import schedule
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# Ajustar path para importaciones
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_root)

from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker
from src.medical.models import CitasMedicas, Doctores, Pacientes, SincronizacionCalendar, EstadoSincronizacion
from src.auth.google_calendar_auth import get_calendar_service

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Variables de entorno
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:password@localhost:5432/medical_calendar')
GOOGLE_CALENDAR_ID = os.getenv('GOOGLE_CALENDAR_ID', 'primary')
RETRY_INTERVAL_MINUTES = 15
MAX_INTENTOS_DEFAULT = 5

# Configuración de base de datos
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_calendar_service_safe() -> Optional[any]:
    """
    Obtener servicio de Google Calendar de forma segura
    
    Returns:
        Servicio de Google Calendar o None si falla
    """
    try:
        return get_calendar_service()
    except Exception as e:
        logger.error(f"Error obteniendo servicio Google Calendar: {e}")
        return None

def crear_evento_google_calendar_retry(cita: CitasMedicas, doctor: Doctores, paciente: Pacientes) -> Dict:
    """
    Crear evento en Google Calendar (versión retry)
    
    Args:
        cita: Instancia de CitasMedicas
        doctor: Instancia de Doctores  
        paciente: Instancia de Pacientes
    
    Returns:
        Dict con resultado de la operación
    """
    try:
        calendar_service = get_calendar_service_safe()
        if not calendar_service:
            return {
                'exito': False,
                'error': 'No se pudo obtener servicio Google Calendar'
            }

        # Crear evento
        evento = {
            'summary': f'Consulta - {paciente.nombre_completo}',
            'description': f'''Paciente: {paciente.nombre_completo}
Tel: {paciente.telefono}
Tipo: {cita.tipo_consulta.value}

ID Cita: {cita.id}
Sistema: WhatsApp Agent''',
            'start': {
                'dateTime': cita.fecha_hora_inicio.isoformat(),
                'timeZone': 'America/Tijuana'
            },
            'end': {
                'dateTime': cita.fecha_hora_fin.isoformat(),
                'timeZone': 'America/Tijuana'
            },
            'extendedProperties': {
                'private': {
                    'cita_id': str(cita.id),
                    'sistema': 'whatsapp_agent'
                }
            },
            'colorId': '11'  # Rojo para citas médicas
        }

        # Insertar en Google Calendar
        result = calendar_service.events().insert(
            calendarId=GOOGLE_CALENDAR_ID,
            body=evento
        ).execute()

        logger.info(f"Evento creado en retry: {result['id']}")
        
        return {
            'exito': True,
            'event_id': result['id']
        }

    except Exception as e:
        logger.error(f"Error en retry Google Calendar: {e}")
        return {
            'exito': False,
            'error': str(e)
        }

def obtener_sincronizaciones_pendientes() -> List[SincronizacionCalendar]:
    """
    Obtener sincronizaciones pendientes de reintento
    
    Returns:
        Lista de sincronizaciones para reintentar
    """
    db = SessionLocal()
    
    try:
        ahora = datetime.now()
        
        # Buscar sincronizaciones pendientes
        pendientes = db.query(SincronizacionCalendar).filter(
            and_(
                SincronizacionCalendar.estado.in_([
                    EstadoSincronizacion.error, 
                    EstadoSincronizacion.pendiente,
                    EstadoSincronizacion.reintentando
                ]),
                SincronizacionCalendar.siguiente_reintento <= ahora,
                SincronizacionCalendar.intentos < SincronizacionCalendar.max_intentos
            )
        ).all()
        
        logger.info(f"Encontradas {len(pendientes)} sincronizaciones pendientes")
        return pendientes
        
    except Exception as e:
        logger.error(f"Error obteniendo sincronizaciones pendientes: {e}")
        return []
    
    finally:
        db.close()

def sincronizar_cita_retry(cita_id: int) -> Dict:
    """
    Reintentar sincronización de una cita específica
    
    Args:
        cita_id: ID de la cita a sincronizar
    
    Returns:
        Dict con resultado de la operación
    """
    db = SessionLocal()
    
    try:
        # Obtener cita de BD
        cita = db.query(CitasMedicas).filter(CitasMedicas.id == cita_id).first()
        if not cita:
            return {'exito': False, 'error': f'Cita {cita_id} no encontrada'}

        # Obtener doctor y paciente
        doctor = db.query(Doctores).filter(Doctores.id == cita.doctor_id).first()
        paciente = db.query(Pacientes).filter(Pacientes.id == cita.paciente_id).first()

        if not doctor or not paciente:
            return {'exito': False, 'error': 'Doctor o paciente no encontrado'}

        # Crear evento en Google Calendar
        resultado = crear_evento_google_calendar_retry(cita, doctor, paciente)
        
        if resultado['exito']:
            # Actualizar cita con ID de Google
            cita.google_event_id = resultado['event_id']
            cita.sincronizada_google = True
            db.commit()
            
            logger.info(f"Cita {cita_id} sincronizada en retry")
        
        return resultado

    except Exception as e:
        logger.error(f"Error en retry cita {cita_id}: {e}")
        db.rollback()
        return {'exito': False, 'error': str(e)}
    
    finally:
        db.close()

def procesar_reintento_sincronizacion(sincronizacion: SincronizacionCalendar) -> bool:
    """
    Procesar un reintento de sincronización individual
    
    Args:
        sincronizacion: Instancia de SincronizacionCalendar
    
    Returns:
        bool: True si fue exitoso, False si falló
    """
    db = SessionLocal()
    
    try:
        logger.info(f"Reintentando sincronización cita {sincronizacion.cita_id} (intento {sincronizacion.intentos + 1})")
        
        # Cambiar estado a reintentando
        sincronizacion.estado = EstadoSincronizacion.reintentando
        sincronizacion.ultimo_intento = datetime.now()
        sincronizacion.intentos += 1
        db.commit()
        
        # Intentar sincronización
        resultado = sincronizar_cita_retry(sincronizacion.cita_id)
        
        if resultado['exito']:
            # Sincronización exitosa
            sincronizacion.estado = EstadoSincronizacion.sincronizada
            sincronizacion.google_event_id = resultado['event_id']
            sincronizacion.error_message = None
            sincronizacion.siguiente_reintento = None
            
            logger.info(f"✅ Cita {sincronizacion.cita_id} sincronizada exitosamente en reintento")
            
        else:
            # Error en reintento
            sincronizacion.error_message = resultado['error']
            
            if sincronizacion.intentos >= sincronizacion.max_intentos:
                # Máximo de intentos alcanzado
                sincronizacion.estado = EstadoSincronizacion.error_permanente
                sincronizacion.siguiente_reintento = None
                
                logger.warning(f"❌ Cita {sincronizacion.cita_id} alcanzó máximo de intentos ({sincronizacion.max_intentos})")
                logger.info(f"🏥 CITA SIGUE VÁLIDA EN BD")
                
            else:
                # Programar siguiente reintento
                sincronizacion.estado = EstadoSincronizacion.error
                sincronizacion.siguiente_reintento = datetime.now() + timedelta(minutes=RETRY_INTERVAL_MINUTES)
                
                logger.info(f"⏰ Próximo reintento para cita {sincronizacion.cita_id}: {sincronizacion.siguiente_reintento}")
        
        db.commit()
        return resultado['exito']
        
    except Exception as e:
        logger.error(f"Error procesando reintento para cita {sincronizacion.cita_id}: {e}")
        db.rollback()
        return False
    
    finally:
        db.close()

def retry_failed_syncs():
    """
    Función principal que reintenta sincronizaciones fallidas
    Ejecutar cada 15 minutos
    """
    logger.info("\n" + "="*60)
    logger.info("🔄 INICIANDO WORKER DE REINTENTOS")
    logger.info("="*60)
    
    try:
        # Obtener sincronizaciones pendientes
        sincronizaciones_pendientes = obtener_sincronizaciones_pendientes()
        
        if not sincronizaciones_pendientes:
            logger.info("✅ No hay sincronizaciones pendientes")
            return
        
        # Procesar cada sincronización
        exitos = 0
        errores = 0
        
        for sincronizacion in sincronizaciones_pendientes:
            try:
                if procesar_reintento_sincronizacion(sincronizacion):
                    exitos += 1
                else:
                    errores += 1
                    
                # Pausa pequeña entre reintentos
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error procesando sincronización {sincronizacion.id}: {e}")
                errores += 1
        
        # Reporte final
        logger.info(f"\n📊 REPORTE REINTENTOS:")
        logger.info(f"   Exitosos: {exitos}")
        logger.info(f"   Errores: {errores}")
        logger.info(f"   Total procesados: {len(sincronizaciones_pendientes)}")
        
    except Exception as e:
        logger.error(f"Error crítico en worker de reintentos: {e}")
    
    logger.info("="*60)

def iniciar_worker_reintentos():
    """
    Iniciar el worker de reintentos como proceso de fondo
    """
    logger.info("🚀 Iniciando worker de reintentos de sincronización")
    logger.info(f"⏰ Intervalo: cada {RETRY_INTERVAL_MINUTES} minutos")
    
    # Programar ejecución cada 15 minutos
    schedule.every(RETRY_INTERVAL_MINUTES).minutes.do(retry_failed_syncs)
    
    # Ejecutar inmediatamente una vez
    retry_failed_syncs()
    
    # Loop principal
    while True:
        try:
            schedule.run_pending()
            time.sleep(30)  # Check cada 30 segundos
            
        except KeyboardInterrupt:
            logger.info("🛑 Worker detenido por usuario")
            break
        except Exception as e:
            logger.error(f"Error en loop principal del worker: {e}")
            time.sleep(60)  # Pausa más larga en caso de error

if __name__ == "__main__":
    # Ejecutar worker
    iniciar_worker_reintentos()