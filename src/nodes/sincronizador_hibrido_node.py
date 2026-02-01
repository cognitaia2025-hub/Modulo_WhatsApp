"""
Nodo 8: Sincronizador Híbrido - BD ↔ Google Calendar

ARQUITECTURA CRÍTICA:
- BD médica es SOURCE OF TRUTH
- Google Calendar es solo para VISUALIZACIÓN
- Si falla Google Calendar, la cita SIGUE SIENDO VÁLIDA en BD

MEJORAS APLICADAS:
✅ Command pattern con routing directo
✅ Detección de conflictos mejorada
✅ psycopg3 con context managers
✅ Logging estructurado
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List

from dotenv import load_dotenv

# ✅ Imports modernos
from langgraph.types import Command
from src.utils.logging_config import (
    log_separator,
    log_node_io,
    setup_colored_logging
)
import psycopg
from psycopg.rows import dict_row

# Imports legacy para compatibilidad con funciones auxiliares
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.state.agent_state import WhatsAppAgentState
from src.auth.google_calendar_auth import get_calendar_service
from src.medical.models import CitasMedicas, Doctores, Pacientes, SincronizacionCalendar, EstadoSincronizacion

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logger = setup_colored_logging()

# Variables de configuración
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5434/agente_whatsapp")
GOOGLE_CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "primary")

# Configuración SQLAlchemy (legacy - para funciones auxiliares)
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ==================== CONSTANTES ====================

# Ventana de tiempo para sincronización (días hacia adelante)
SYNC_WINDOW_DAYS = 30

# Tolerancia de tiempo para considerar citas duplicadas (minutos)
DUPLICATE_TOLERANCE_MINUTES = 5


def detectar_cambios_sincronizacion(
    eventos_calendar: List[Dict],
    citas_bd: List[Dict]
) -> Dict[str, List]:
    """
    Detecta diferencias entre Google Calendar y BD.
    
    Returns:
        {
            'nuevas': [...],
            'modificadas': [...],
            'eliminadas': [...]
        }
    """
    # Crear mapas por event_id
    calendar_map = {e['id']: e for e in eventos_calendar}
    bd_map = {c['event_id_calendar']: c for c in citas_bd if c.get('event_id_calendar')}
    
    cambios = {
        'nuevas': [],
        'modificadas': [],
        'eliminadas': []
    }
    
    # Detectar nuevas (en Calendar pero no en BD)
    for event_id, evento in calendar_map.items():
        if event_id not in bd_map:
            cambios['nuevas'].append(evento)
    
    # Detectar modificadas (diferentes fecha/hora)
    for event_id, evento in calendar_map.items():
        if event_id in bd_map:
            cita = bd_map[event_id]
            
            # Comparar timestamps
            fecha_calendar = evento['start']
            fecha_bd = cita['fecha_hora'].isoformat() if hasattr(cita['fecha_hora'], 'isoformat') else str(cita['fecha_hora'])
            
            if fecha_calendar != fecha_bd:
                cambios['modificadas'].append(evento)
    
    # Detectar eliminadas (en BD pero no en Calendar)
    for event_id, cita in bd_map.items():
        if event_id not in calendar_map:
            cambios['eliminadas'].append(cita['id'])
    
    return cambios


def nodo_sincronizador_hibrido(state: Dict[str, Any]) -> Command:
    """
    Nodo 8: Sincroniza citas entre Google Calendar y PostgreSQL
    
    MEJORAS APLICADAS:
    ✅ Command pattern con routing directo
    ✅ Detección de conflictos mejorada
    ✅ psycopg3 con context managers
    ✅ Logging estructurado
    
    Flujo:
    1. Obtiene citas recientes de Google Calendar (próximos 30 días)
    2. Compara con citas_medicas en PostgreSQL
    3. Detecta: nuevas, modificadas, eliminadas
    4. Sincroniza cambios bidireccionales
    5. Actualiza control_turnos si es necesario
    
    Returns:
        Command con update y goto
    """
    log_separator(logger, "NODO_8_SINCRONIZADOR", "INICIO")
    
    user_id = state.get('user_id', 'system')
    tipo_sincronizacion = state.get('tipo_sincronizacion', 'post_agendamiento')
    
    # Log de input
    input_data = f"user_id: {user_id}\ntipo: {tipo_sincronizacion}"
    log_node_io(logger, "INPUT", "NODO_8_SYNC", input_data)
    
    logger.info(f"    🔄 Tipo de sincronización: {tipo_sincronizacion}")
    
    try:
        # 1. Obtener citas de Google Calendar
        logger.info("    📅 Obteniendo citas de Google Calendar...")
        
        from src.utils import get_current_time
        ahora = get_current_time()
        fecha_inicio = ahora.format('YYYY-MM-DDTHH:mm:ss')
        fecha_fin = ahora.add(days=SYNC_WINDOW_DAYS).format('YYYY-MM-DDTHH:mm:ss')
        
        from src.tool import list_events_tool
        eventos_calendar = list_events_tool.invoke({
            'start_datetime': fecha_inicio,
            'end_datetime': fecha_fin,
            'max_results': 100,
            'timezone': 'America/Tijuana'
        })
        
        logger.info(f"    📊 Eventos en Calendar: {len(eventos_calendar)}")
        
        # 2. Obtener citas de PostgreSQL
        logger.info("    💾 Obteniendo citas de BD...")
        
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                # Use explicit casting to avoid SQL injection risks
                cur.execute("""
                    SELECT 
                        c.id,
                        c.event_id_calendar,
                        c.fecha_hora,
                        c.paciente_id,
                        c.doctor_id,
                        c.estado
                    FROM citas_medicas c
                    WHERE c.fecha_hora >= NOW()
                    AND c.fecha_hora <= NOW() + make_interval(days => %s)
                """, (SYNC_WINDOW_DAYS,))
                
                citas_bd = cur.fetchall()
        
        logger.info(f"    📊 Citas en BD: {len(citas_bd)}")
        
        # 3. Detectar diferencias
        cambios = detectar_cambios_sincronizacion(eventos_calendar, citas_bd)
        
        logger.info(f"    📝 Cambios detectados:")
        logger.info(f"       - Nuevas: {len(cambios['nuevas'])}")
        logger.info(f"       - Modificadas: {len(cambios['modificadas'])}")
        logger.info(f"       - Eliminadas: {len(cambios['eliminadas'])}")
        
        # 4. Aplicar sincronización
        sincronizadas = 0
        
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                # Insertar nuevas
                for evento in cambios['nuevas']:
                    try:
                        cur.execute("""
                            INSERT INTO citas_medicas 
                            (event_id_calendar, fecha_hora, estado, sincronizado)
                            VALUES (%s, %s, 'confirmada', TRUE)
                            ON CONFLICT (event_id_calendar) DO NOTHING
                        """, (evento['id'], evento['start']))
                        sincronizadas += 1
                    except Exception as e:
                        logger.warning(f"       ⚠️ Error insertando evento: {e}")
                
                # Actualizar modificadas
                for evento in cambios['modificadas']:
                    try:
                        cur.execute("""
                            UPDATE citas_medicas
                            SET fecha_hora = %s,
                                sincronizado = TRUE
                            WHERE event_id_calendar = %s
                        """, (evento['start'], evento['id']))
                        sincronizadas += 1
                    except Exception as e:
                        logger.warning(f"       ⚠️ Error actualizando evento: {e}")
                
                # Marcar eliminadas
                for cita_id in cambios['eliminadas']:
                    try:
                        cur.execute("""
                            UPDATE citas_medicas
                            SET estado = 'cancelada',
                                sincronizado = TRUE
                            WHERE id = %s
                        """, (cita_id,))
                        sincronizadas += 1
                    except Exception as e:
                        logger.warning(f"       ⚠️ Error marcando eliminada: {e}")
                
                conn.commit()
        
        logger.info(f"    ✅ Sincronizadas: {sincronizadas} citas")
        
        # Log de output
        output_data = f"sincronizadas: {sincronizadas}\nnuevas: {len(cambios['nuevas'])}"
        log_node_io(logger, "OUTPUT", "NODO_8_SYNC", output_data)
        log_separator(logger, "NODO_8_SINCRONIZADOR", "FIN")
        
        # ✅ Retornar Command
        return Command(
            update={
                'sincronizacion_exitosa': True,
                'citas_sincronizadas': sincronizadas
            },
            goto="generacion_resumen"
        )
        
    except Exception as e:
        logger.error(f"    ❌ Error en sincronización: {e}")
        log_separator(logger, "NODO_8_SINCRONIZADOR", "FIN")
        
        return Command(
            update={
                'sincronizacion_exitosa': False,
                'error_sincronizacion': str(e)
            },
            goto="generacion_resumen"
        )


def sincronizador_hibrido_node(state: WhatsAppAgentState) -> Dict:
    """
    Sincroniza cita médica recién creada con Google Calendar.
    
    REGLA CRÍTICA:
    Si falla la sincronización con Google, la cita PERMANECE VÁLIDA en BD.
    Se registra el error y se reintentará después.
    
    Args:
        state: Estado del agente con 'cita_id_creada'
        
    Returns:
        Dict con state actualizado + 'sincronizado': bool
    """
    logger.info("\n" + "="*70)
    logger.info("📅 INICIANDO SINCRONIZACIÓN HÍBRIDA BD → GOOGLE CALENDAR")
    logger.info("="*70)
    
    # Verificar si hay cita para sincronizar
    cita_id = state.get('cita_id_creada')
    if not cita_id:
        logger.warning("⚠️  No hay cita_id_creada en el estado. Saltando sincronización.")
        return {**state, 'sincronizado': False, 'mensaje_sync': 'No hay cita para sincronizar'}
    
    logger.info(f"🆔 Cita ID: {cita_id}")
    
    try:
        db = SessionLocal()
        try:
            # 1. Obtener cita de BD usando SQLAlchemy
            logger.info("📖 Obteniendo datos de la cita desde BD...")
            cita = db.query(CitasMedicas).filter(CitasMedicas.id == cita_id).first()
            
            if not cita:
                logger.error(f"❌ No se encontró cita con ID {cita_id}")
                return {
                    **state, 
                    'sincronizado': False, 
                    'error_sync': f'Cita {cita_id} no encontrada'
                }
            
            # Obtener doctor y paciente
            doctor = db.query(Doctores).filter(Doctores.id == cita.doctor_id).first()
            paciente = db.query(Pacientes).filter(Pacientes.id == cita.paciente_id).first()
            
            if not doctor or not paciente:
                logger.error("❌ Doctor o paciente no encontrado")
                return {
                    **state, 
                    'sincronizado': False, 
                    'error_sync': 'Doctor o paciente no encontrado'
                }
            
            logger.info(f"   ✅ Cita encontrada: {paciente.nombre_completo}")
            logger.info(f"   📅 Horario: {cita.fecha_hora_inicio} - {cita.fecha_hora_fin}")
            
            # 2. Construir evento de Google Calendar
            logger.info("🔨 Construyendo evento de Google Calendar...")
            
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
            
            logger.info("   ✅ Evento construido correctamente")
            
            # 3. Insertar evento en Google Calendar
            logger.info("☁️  Insertando evento en Google Calendar...")
            
            calendar_service = get_calendar_service()
            result = calendar_service.events().insert(
                calendarId=GOOGLE_CALENDAR_ID,
                body=evento
            ).execute()
            
            google_event_id = result['id']
            logger.info(f"   ✅ Evento creado en Google: {google_event_id}")
            
            # 4. Actualizar BD con google_event_id
            logger.info("💾 Actualizando BD con google_event_id...")
            cita.google_event_id = google_event_id
            cita.sincronizada_google = True
            
            # 5. Registrar sincronización exitosa
            logger.info("📝 Registrando sincronización exitosa...")
            sincronizacion = SincronizacionCalendar(
                cita_id=cita.id,
                google_event_id=google_event_id,
                estado=EstadoSincronizacion.sincronizada,
                ultimo_intento=datetime.now(),
                intentos=1
            )
            db.add(sincronizacion)
            
            db.commit()
            
            logger.info("\n" + "="*70)
            logger.info("✅ SINCRONIZACIÓN COMPLETADA EXITOSAMENTE")
            logger.info("="*70 + "\n")
            
            return {
                **state, 
                'sincronizado': True, 
                'google_event_id': google_event_id,
                'mensaje_sync': 'Cita sincronizada con Google Calendar'
            }
            
        finally:
            db.close()
    
    except Exception as e:
        # CRÍTICO: Si falla Google, la cita SIGUE SIENDO VÁLIDA
        logger.error("\n" + "="*70)
        logger.error("❌ ERROR EN SINCRONIZACIÓN CON GOOGLE CALENDAR")
        logger.error(f"   Mensaje: {e}")
        logger.error("="*70)
        logger.warning("⚠️  LA CITA SIGUE SIENDO VÁLIDA EN BD")
        logger.info("🔄 Se registrará para reintento automático...")
        
        try:
            # Registrar error para reintentar después
            db = SessionLocal()
            try:
                siguiente_reintento = datetime.now() + timedelta(minutes=15)
                
                sincronizacion = SincronizacionCalendar(
                    cita_id=cita_id,
                    estado=EstadoSincronizacion.error,
                    ultimo_intento=datetime.now(),
                    siguiente_reintento=siguiente_reintento,
                    intentos=1,
                    error_message=str(e)
                )
                db.add(sincronizacion)
                db.commit()
                
                logger.info(f"   ✅ Error registrado. Reintento en 15 minutos ({siguiente_reintento})")
            finally:
                db.close()
        
        except Exception as db_error:
            logger.error(f"❌ Error al registrar fallo de sincronización: {db_error}")
        
        # Retornar estado con sincronización fallida PERO cita válida
        return {
            **state, 
            'sincronizado': False, 
            'error_sync': str(e),
            'mensaje_sync': 'Cita creada en BD. Error en Google Calendar, se reintentará automáticamente.'
        }


def sincronizar_cita_a_google(cita_id: int) -> Dict[str, Any]:
    """
    Función auxiliar para sincronizar una cita específica a Google Calendar.
    Usada por el retry worker.
    
    Args:
        cita_id: ID de la cita a sincronizar
        
    Returns:
        Dict con {'exito': bool, 'event_id': str, 'error': str}
    """
    try:
        db = SessionLocal()
        try:
            # Obtener datos de la cita
            cita = db.query(CitasMedicas).filter(CitasMedicas.id == cita_id).first()
            if not cita:
                return {'exito': False, 'error': f'Cita {cita_id} no encontrada'}
            
            # Obtener paciente
            paciente = db.query(Pacientes).filter(Pacientes.id == cita.paciente_id).first()
            if not paciente:
                return {'exito': False, 'error': f'Paciente para cita {cita_id} no encontrado'}
            
            # Construir evento
            evento = {
                'summary': f'Consulta - {paciente.nombre_completo}',
                'description': f'''Paciente: {paciente.nombre_completo}
Tel: {paciente.telefono}
Tipo: {cita.tipo_consulta.value}

ID Cita: {cita_id}
Sistema: WhatsApp Agent (Reintento)
''',
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
                        'cita_id': str(cita_id),
                        'sistema': 'whatsapp_agent'
                    }
                },
                'colorId': '11'
            }
            
            # Insertar en Google Calendar
            calendar_service = get_calendar_service()
            result = calendar_service.events().insert(
                calendarId=GOOGLE_CALENDAR_ID,
                body=evento
            ).execute()
            
            google_event_id = result['id']
            
            # Actualizar BD
            cita.google_event_id = google_event_id
            cita.sincronizada_google = True
            db.commit()
            
            return {'exito': True, 'event_id': google_event_id}
        
        finally:
            db.close()
    
    except Exception as e:
        logger.error(f"Error sincronizando cita {cita_id}: {e}")
        return {'exito': False, 'error': str(e)}


# Wrapper para compatibilidad con grafo
def nodo_sincronizador_hibrido_wrapper(state: Dict[str, Any]) -> Command:
    """Wrapper para LangGraph - retorna Command directamente."""
    return nodo_sincronizador_hibrido(state)


if __name__ == "__main__":
    # Test del nodo
    print("\n" + "="*70)
    print("🧪 TEST DEL NODO SINCRONIZADOR HÍBRIDO")
    print("="*70 + "\n")
    
    # Estado de prueba con una cita recién creada
    test_state = WhatsAppAgentState(
        messages=[],
        user_info={},
        cita_id_creada=1  # Cambiar por un ID real
    )
    
    resultado = sincronizador_hibrido_node(test_state)
    
    print("\n📊 RESULTADO:")
    print(f"   Sincronizado: {resultado.get('sincronizado')}")
    if resultado.get('google_event_id'):
        print(f"   Google Event ID: {resultado.get('google_event_id')}")
    if resultado.get('sincronizacion_error'):
        print(f"   Error: {resultado.get('sincronizacion_error')}")
