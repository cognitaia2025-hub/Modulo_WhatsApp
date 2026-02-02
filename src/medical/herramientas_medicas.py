"""
Herramientas Médicas Avanzadas
Sistema completo de analytics, reportes y búsqueda semántica
"""
import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Any
from decimal import Decimal

from sqlalchemy import func, and_, or_, extract, text
from sqlalchemy.orm import Session

from src.database.db_config import get_db_session
from src.medical.models import (
    CitasMedicas, Doctores, Pacientes, HistorialesMedicos,
    DisponibilidadMedica, EstadoCita, TipoConsulta
)

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def registrar_consulta(
    cita_id: int,
    diagnostico: str,
    tratamiento: str,
    sintomas: str,
    medicamentos: List[Dict[str, Any]] = None,
    notas_privadas: str = None
) -> Dict[str, Any]:
    """
    Registra una consulta médica completa con todos sus detalles.
    
    Args:
        cita_id: ID de la cita médica
        diagnostico: Diagnóstico del médico
        tratamiento: Tratamiento prescrito
        sintomas: Síntomas reportados por el paciente
        medicamentos: Lista de medicamentos prescritos
        notas_privadas: Notas privadas del doctor
    
    Returns:
        Dict con el resultado de la operación
    """
    try:
        with get_db_session() as db:
            # Buscar la cita
            cita = db.query(CitasMedicas).filter(CitasMedicas.id == cita_id).first()
            
            if not cita:
                return {
                    'exito': False,
                    'error': f'Cita {cita_id} no encontrada'
                }
            
            # Actualizar información de la cita
            cita.diagnostico = diagnostico
            cita.tratamiento_prescrito = {'descripcion': tratamiento}
            cita.sintomas_principales = sintomas
            cita.medicamentos = medicamentos or []
            if notas_privadas:
                cita.notas_privadas = notas_privadas
            
            # Marcar como completada
            cita.estado = EstadoCita.completada
            cita.updated_at = datetime.now()
            
            # Crear o actualizar historial médico
            historial = db.query(HistorialesMedicos).filter(
                HistorialesMedicos.cita_id == cita_id
            ).first()
            
            if not historial:
                historial = HistorialesMedicos(
                    paciente_id=cita.paciente_id,
                    cita_id=cita_id,
                    fecha_consulta=cita.fecha_hora_inicio.date(),
                    diagnostico=diagnostico,
                    tratamiento=tratamiento,
                    medicamentos_prescritos=medicamentos or []
                )
                db.add(historial)
            else:
                historial.diagnostico = diagnostico
                historial.tratamiento = tratamiento
                historial.medicamentos_prescritos = medicamentos or []
            
            db.commit()
            
            logger.info(f"✅ Consulta registrada: cita {cita_id}")
            
            return {
                'exito': True,
                'cita_id': cita_id,
                'paciente_id': cita.paciente_id,
                'fecha': cita.fecha_hora_inicio.isoformat()
            }
            
    except Exception as e:
        logger.error(f"❌ Error registrando consulta: {e}")
        return {
            'exito': False,
            'error': str(e)
        }


def consultar_historial_paciente(
    paciente_id: int,
    limite: int = 10,
    termino_busqueda: str = None
) -> Dict[str, Any]:
    """
    Consulta el historial médico de un paciente con búsqueda opcional.
    
    Args:
        paciente_id: ID del paciente
        limite: Número máximo de registros a retornar
        termino_busqueda: Término para búsqueda en diagnóstico/síntomas
    
    Returns:
        Dict con el historial del paciente
    """
    try:
        with get_db_session() as db:
            # Verificar que el paciente existe
            paciente = db.query(Pacientes).get(paciente_id)
            if not paciente:
                return {
                    'exito': False,
                    'error': f'Paciente {paciente_id} no encontrado'
                }
            
            # Construir query base
            query = db.query(HistorialesMedicos).filter(
                HistorialesMedicos.paciente_id == paciente_id
            )
            
            # Búsqueda por término si se proporciona
            if termino_busqueda:
                busqueda = f'%{termino_busqueda}%'
                query = query.filter(
                    or_(
                        HistorialesMedicos.diagnostico_principal.ilike(busqueda),
                        HistorialesMedicos.tratamiento_prescrito.ilike(busqueda),
                        HistorialesMedicos.indicaciones_generales.ilike(busqueda),
                        HistorialesMedicos.sintomas.ilike(busqueda)
                    )
                )
            
            # Ordenar por fecha más reciente
            historiales = query.order_by(
                HistorialesMedicos.fecha_consulta.desc()
            ).limit(limite).all()
            
            # Formatear resultados
            resultados = []
            for h in historiales:
                resultados.append({
                    'id': h.id,
                    'fecha': h.fecha_consulta.isoformat(),
                    'diagnostico': h.diagnostico_principal,
                    'tratamiento': h.tratamiento_prescrito,
                    'medicamentos': h.medicamentos or [],
                    'peso': float(h.peso) if h.peso else None,
                    'altura': float(h.altura) if h.altura else None,
                    'presion_arterial': h.presion_arterial
                })
            
            logger.info(f"✅ Historial consultado: paciente {paciente_id}, {len(resultados)} registros")
            
            return {
                'exito': True,
                'paciente_id': paciente_id,
                'paciente_nombre': paciente.nombre_completo,
                'total_registros': len(resultados),
                'historiales': resultados
            }
            
    except Exception as e:
        logger.error(f"❌ Error consultando historial: {e}")
        return {
            'exito': False,
            'error': str(e)
        }


def actualizar_disponibilidad_doctor(
    doctor_id: int,
    dia_semana: int,
    hora_inicio: str,
    hora_fin: str,
    disponible: bool = True,
    duracion_cita: int = 30
) -> Dict[str, Any]:
    """
    Actualiza o crea disponibilidad de un doctor para un día específico.
    
    Args:
        doctor_id: ID del doctor
        dia_semana: Día de la semana (0=Lunes, 6=Domingo)
        hora_inicio: Hora de inicio (formato HH:MM)
        hora_fin: Hora de fin (formato HH:MM)
        disponible: Si está disponible o no
        duracion_cita: Duración de cada cita en minutos
    
    Returns:
        Dict con el resultado de la operación
    """
    try:
        with get_db_session() as db:
            # Verificar que el doctor existe
            doctor = db.query(Doctores).get(doctor_id)
            if not doctor:
                return {
                    'exito': False,
                    'error': f'Doctor {doctor_id} no encontrado'
                }
            
            # Validar día de la semana
            if not 0 <= dia_semana <= 6:
                return {
                    'exito': False,
                    'error': 'Día de semana debe estar entre 0 (Lunes) y 6 (Domingo)'
                }
            
            # Convertir horas a time objects
            from datetime import time
            hora_inicio_obj = datetime.strptime(hora_inicio, '%H:%M').time()
            hora_fin_obj = datetime.strptime(hora_fin, '%H:%M').time()
            
            # Verificar que hora_fin > hora_inicio
            if hora_fin_obj <= hora_inicio_obj:
                return {
                    'exito': False,
                    'error': 'Hora de fin debe ser posterior a hora de inicio'
                }
            
            # Buscar disponibilidad existente
            disponibilidad = db.query(DisponibilidadMedica).filter(
                DisponibilidadMedica.doctor_id == doctor_id,
                DisponibilidadMedica.dia_semana == dia_semana
            ).first()
            
            if disponibilidad:
                # Actualizar existente
                disponibilidad.hora_inicio = hora_inicio_obj
                disponibilidad.hora_fin = hora_fin_obj
                disponibilidad.disponible = disponible
                disponibilidad.duracion_cita = duracion_cita
                accion = 'actualizada'
            else:
                # Crear nueva
                disponibilidad = DisponibilidadMedica(
                    doctor_id=doctor_id,
                    dia_semana=dia_semana,
                    hora_inicio=hora_inicio_obj,
                    hora_fin=hora_fin_obj,
                    disponible=disponible,
                    duracion_cita=duracion_cita
                )
                db.add(disponibilidad)
                accion = 'creada'
            
            db.commit()
            
            dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
            logger.info(f"✅ Disponibilidad {accion}: {doctor.nombre_completo} - {dias[dia_semana]}")
            
            return {
                'exito': True,
                'doctor_id': doctor_id,
                'dia_semana': dia_semana,
                'dia_nombre': dias[dia_semana],
                'hora_inicio': hora_inicio,
                'hora_fin': hora_fin,
                'disponible': disponible,
                'accion': accion
            }
            
    except ValueError as e:
        return {
            'exito': False,
            'error': f'Formato de hora inválido. Use HH:MM. Error: {e}'
        }
    except Exception as e:
        logger.error(f"❌ Error actualizando disponibilidad: {e}")
        return {
            'exito': False,
            'error': str(e)
        }


def generar_reporte_doctor(
    doctor_id: int,
    fecha_inicio: date,
    fecha_fin: date,
    tipo_reporte: str = 'completo'
) -> Dict[str, Any]:
    """
    Genera reporte de consultas y ingresos para un doctor.
    
    Args:
        doctor_id: ID del doctor
        fecha_inicio: Fecha de inicio del período
        fecha_fin: Fecha de fin del período
        tipo_reporte: Tipo de reporte ('dia', 'mes', 'ingresos', 'completo')
    
    Returns:
        Dict con el reporte generado
    """
    try:
        with get_db_session() as db:
            # Verificar doctor
            doctor = db.query(Doctores).get(doctor_id)
            if not doctor:
                return {
                    'exito': False,
                    'error': f'Doctor {doctor_id} no encontrado'
                }
            
            # Consultar citas del período
            citas = db.query(CitasMedicas).filter(
                CitasMedicas.doctor_id == doctor_id,
                func.date(CitasMedicas.fecha_hora_inicio) >= fecha_inicio,
                func.date(CitasMedicas.fecha_hora_inicio) <= fecha_fin
            ).all()
            
            # Calcular métricas
            total_citas = len(citas)
            citas_completadas = sum(1 for c in citas if c.estado == EstadoCita.completada)
            citas_canceladas = sum(1 for c in citas if c.estado == EstadoCita.cancelada)
            citas_no_asistio = sum(1 for c in citas if c.estado == EstadoCita.no_asistio)
            
            ingresos_total = sum(
                c.costo_consulta for c in citas 
                if c.costo_consulta and c.estado == EstadoCita.completada
            ) or Decimal('0.00')
            
            ingreso_promedio = (
                ingresos_total / citas_completadas 
                if citas_completadas > 0 
                else Decimal('0.00')
            )
            
            # Pacientes únicos
            pacientes_unicos = len(set(c.paciente_id for c in citas))
            
            # Desglose por tipo de consulta
            por_tipo = {}
            for tipo in TipoConsulta:
                count = sum(1 for c in citas if c.tipo_consulta == tipo)
                if count > 0:
                    por_tipo[tipo.value] = count
            
            # Desglose por día (si el período es <= 31 días)
            por_dia = {}
            if (fecha_fin - fecha_inicio).days <= 31:
                for cita in citas:
                    fecha_str = cita.fecha_hora_inicio.date().isoformat()
                    if fecha_str not in por_dia:
                        por_dia[fecha_str] = {
                            'total': 0,
                            'completadas': 0,
                            'ingresos': Decimal('0.00')
                        }
                    por_dia[fecha_str]['total'] += 1
                    if cita.estado == EstadoCita.completada:
                        por_dia[fecha_str]['completadas'] += 1
                        if cita.costo_consulta:
                            por_dia[fecha_str]['ingresos'] += cita.costo_consulta
            
            reporte = {
                'exito': True,
                'doctor_id': doctor_id,
                'doctor_nombre': doctor.nombre_completo,
                'especialidad': doctor.especialidad,
                'periodo': {
                    'inicio': fecha_inicio.isoformat(),
                    'fin': fecha_fin.isoformat(),
                    'dias': (fecha_fin - fecha_inicio).days + 1
                },
                'metricas': {
                    'total_citas': total_citas,
                    'completadas': citas_completadas,
                    'canceladas': citas_canceladas,
                    'no_asistio': citas_no_asistio,
                    'tasa_completadas': round(citas_completadas / total_citas * 100, 2) if total_citas > 0 else 0,
                    'pacientes_unicos': pacientes_unicos
                },
                'ingresos': {
                    'total': float(ingresos_total),
                    'promedio_por_consulta': float(ingreso_promedio)
                },
                'por_tipo_consulta': por_tipo
            }
            
            if por_dia:
                # Convertir Decimal a float para JSON
                por_dia_serializable = {}
                for fecha, datos in por_dia.items():
                    por_dia_serializable[fecha] = {
                        'total': datos['total'],
                        'completadas': datos['completadas'],
                        'ingresos': float(datos['ingresos'])
                    }
                reporte['por_dia'] = por_dia_serializable
            
            logger.info(f"✅ Reporte generado: {doctor.nombre_completo}, {total_citas} citas")
            
            return reporte
            
    except Exception as e:
        logger.error(f"❌ Error generando reporte: {e}")
        return {
            'exito': False,
            'error': str(e)
        }


def obtener_estadisticas_consultas(
    doctor_id: Optional[int] = None,
    fecha_inicio: Optional[date] = None,
    fecha_fin: Optional[date] = None
) -> Dict[str, Any]:
    """
    Obtiene estadísticas agregadas de consultas.
    
    Args:
        doctor_id: ID del doctor (opcional, None para todos)
        fecha_inicio: Fecha de inicio (opcional)
        fecha_fin: Fecha de fin (opcional)
    
    Returns:
        Dict con estadísticas agregadas
    """
    try:
        with get_db_session() as db:
            # Construir query base
            query = db.query(CitasMedicas)
            
            # Filtros opcionales
            if doctor_id:
                query = query.filter(CitasMedicas.doctor_id == doctor_id)
            
            if fecha_inicio:
                query = query.filter(
                    func.date(CitasMedicas.fecha_hora_inicio) >= fecha_inicio
                )
            
            if fecha_fin:
                query = query.filter(
                    func.date(CitasMedicas.fecha_hora_inicio) <= fecha_fin
                )
            
            citas = query.all()
            
            if not citas:
                return {
                    'exito': True,
                    'mensaje': 'No hay datos para el período especificado',
                    'total_citas': 0
                }
            
            # Calcular estadísticas
            total_citas = len(citas)
            
            # Por estado
            por_estado = {}
            for estado in EstadoCita:
                count = sum(1 for c in citas if c.estado == estado)
                if count > 0:
                    por_estado[estado.value] = {
                        'cantidad': count,
                        'porcentaje': round(count / total_citas * 100, 2)
                    }
            
            # Por tipo de consulta
            por_tipo = {}
            for tipo in TipoConsulta:
                count = sum(1 for c in citas if c.tipo_consulta == tipo)
                if count > 0:
                    por_tipo[tipo.value] = {
                        'cantidad': count,
                        'porcentaje': round(count / total_citas * 100, 2)
                    }
            
            # Ingresos
            citas_con_costo = [c for c in citas if c.costo_consulta and c.estado == EstadoCita.completada]
            ingresos_total = sum(c.costo_consulta for c in citas_con_costo) or Decimal('0.00')
            
            # Duración promedio
            duraciones = [
                (c.fecha_hora_fin - c.fecha_hora_inicio).total_seconds() / 60
                for c in citas if c.fecha_hora_fin
            ]
            duracion_promedio = sum(duraciones) / len(duraciones) if duraciones else 0
            
            # Top doctores (si no se filtró por doctor_id)
            top_doctores = []
            if not doctor_id:
                doctores_stats = {}
                for cita in citas:
                    if cita.doctor_id not in doctores_stats:
                        doctor = db.query(Doctores).get(cita.doctor_id)
                        doctores_stats[cita.doctor_id] = {
                            'nombre': doctor.nombre_completo if doctor else 'Desconocido',
                            'total': 0,
                            'completadas': 0
                        }
                    doctores_stats[cita.doctor_id]['total'] += 1
                    if cita.estado == EstadoCita.completada:
                        doctores_stats[cita.doctor_id]['completadas'] += 1
                
                top_doctores = sorted(
                    [
                        {'doctor_id': k, **v} 
                        for k, v in doctores_stats.items()
                    ],
                    key=lambda x: x['total'],
                    reverse=True
                )[:5]
            
            resultado = {
                'exito': True,
                'periodo': {
                    'inicio': fecha_inicio.isoformat() if fecha_inicio else None,
                    'fin': fecha_fin.isoformat() if fecha_fin else None
                },
                'total_citas': total_citas,
                'por_estado': por_estado,
                'por_tipo_consulta': por_tipo,
                'ingresos': {
                    'total': float(ingresos_total),
                    'citas_con_costo': len(citas_con_costo)
                },
                'duracion_promedio_minutos': round(duracion_promedio, 2)
            }
            
            if top_doctores:
                resultado['top_doctores'] = top_doctores
            
            logger.info(f"✅ Estadísticas calculadas: {total_citas} citas")
            
            return resultado
            
    except Exception as e:
        logger.error(f"❌ Error obteniendo estadísticas: {e}")
        return {
            'exito': False,
            'error': str(e)
        }


def buscar_citas_por_periodo(
    doctor_id: Optional[int] = None,
    paciente_id: Optional[int] = None,
    fecha_inicio: Optional[date] = None,
    fecha_fin: Optional[date] = None,
    estado: Optional[str] = None,
    tipo_consulta: Optional[str] = None,
    limite: int = 100
) -> Dict[str, Any]:
    """
    Búsqueda avanzada de citas con múltiples filtros.
    
    Args:
        doctor_id: ID del doctor (opcional)
        paciente_id: ID del paciente (opcional)
        fecha_inicio: Fecha de inicio (opcional)
        fecha_fin: Fecha de fin (opcional)
        estado: Estado de la cita (opcional)
        tipo_consulta: Tipo de consulta (opcional)
        limite: Número máximo de resultados
    
    Returns:
        Dict con las citas encontradas
    """
    try:
        with get_db_session() as db:
            # Construir query
            query = db.query(CitasMedicas)
            
            # Aplicar filtros
            if doctor_id:
                query = query.filter(CitasMedicas.doctor_id == doctor_id)
            
            if paciente_id:
                query = query.filter(CitasMedicas.paciente_id == paciente_id)
            
            if fecha_inicio:
                query = query.filter(
                    func.date(CitasMedicas.fecha_hora_inicio) >= fecha_inicio
                )
            
            if fecha_fin:
                query = query.filter(
                    func.date(CitasMedicas.fecha_hora_inicio) <= fecha_fin
                )
            
            if estado:
                try:
                    estado_enum = EstadoCita[estado]
                    query = query.filter(CitasMedicas.estado == estado_enum)
                except KeyError:
                    return {
                        'exito': False,
                        'error': f'Estado inválido: {estado}'
                    }
            
            if tipo_consulta:
                try:
                    tipo_enum = TipoConsulta[tipo_consulta]
                    query = query.filter(CitasMedicas.tipo_consulta == tipo_enum)
                except KeyError:
                    return {
                        'exito': False,
                        'error': f'Tipo de consulta inválido: {tipo_consulta}'
                    }
            
            # Ordenar y limitar
            citas = query.order_by(
                CitasMedicas.fecha_hora_inicio.desc()
            ).limit(limite).all()
            
            # Formatear resultados
            resultados = []
            for cita in citas:
                doctor = db.query(Doctores).get(cita.doctor_id)
                paciente = db.query(Pacientes).get(cita.paciente_id)
                
                resultados.append({
                    'id': cita.id,
                    'doctor': {
                        'id': cita.doctor_id,
                        'nombre': doctor.nombre_completo if doctor else 'Desconocido'
                    },
                    'paciente': {
                        'id': cita.paciente_id,
                        'nombre': paciente.nombre_completo if paciente else 'Desconocido'
                    },
                    'fecha_hora_inicio': cita.fecha_hora_inicio.isoformat(),
                    'fecha_hora_fin': cita.fecha_hora_fin.isoformat() if cita.fecha_hora_fin else None,
                    'estado': cita.estado.value,
                    'tipo_consulta': cita.tipo_consulta.value if cita.tipo_consulta else None,
                    'costo': float(cita.costo_consulta) if cita.costo_consulta else None,
                    'motivo': cita.motivo_consulta
                })
            
            logger.info(f"✅ Búsqueda completada: {len(resultados)} citas encontradas")
            
            return {
                'exito': True,
                'total_resultados': len(resultados),
                'limite_aplicado': limite,
                'citas': resultados
            }
            
    except Exception as e:
        logger.error(f"❌ Error buscando citas: {e}")
        return {
            'exito': False,
            'error': str(e)
        }


# ==================== LANGCHAIN TOOLS ====================
# Herramientas para uso con ToolNode de LangGraph

from langchain_core.tools import tool

@tool
def buscar_disponibilidad_tool(
    doctor_id: Optional[int] = None,
    fecha: Optional[str] = None,
    especialidad: Optional[str] = None
) -> Dict[str, Any]:
    """
    Busca disponibilidad de doctores para agendar citas.
    
    Args:
        doctor_id: ID del doctor específico (opcional)
        fecha: Fecha a consultar en formato YYYY-MM-DD (opcional, default: hoy)
        especialidad: Filtrar por especialidad del doctor (opcional)
    
    Returns:
        Dict con horarios disponibles por doctor
    """
    try:
        with get_db_session() as db:
            # Determinar fecha
            if fecha:
                fecha_consulta = datetime.strptime(fecha, '%Y-%m-%d').date()
            else:
                fecha_consulta = date.today()
            
            dia_semana = fecha_consulta.weekday()
            
            # Query base de disponibilidad
            query = db.query(DisponibilidadMedica).filter(
                DisponibilidadMedica.dia_semana == dia_semana,
                DisponibilidadMedica.disponible == True
            )
            
            if doctor_id:
                query = query.filter(DisponibilidadMedica.doctor_id == doctor_id)
            
            disponibilidades = query.all()
            
            resultados = []
            for disp in disponibilidades:
                doctor = db.query(Doctores).get(disp.doctor_id)
                if not doctor:
                    continue
                    
                # Filtrar por especialidad si se especifica
                if especialidad and especialidad.lower() not in doctor.especialidad.lower():
                    continue
                
                # Obtener citas existentes para esa fecha
                citas_existentes = db.query(CitasMedicas).filter(
                    CitasMedicas.doctor_id == disp.doctor_id,
                    func.date(CitasMedicas.fecha_hora_inicio) == fecha_consulta,
                    CitasMedicas.estado.in_([EstadoCita.confirmada, EstadoCita.pendiente])
                ).all()
                
                # Calcular slots disponibles
                horas_ocupadas = [c.fecha_hora_inicio.time() for c in citas_existentes]
                
                slots_disponibles = []
                hora_actual = datetime.combine(fecha_consulta, disp.hora_inicio)
                hora_fin = datetime.combine(fecha_consulta, disp.hora_fin)
                
                while hora_actual < hora_fin:
                    if hora_actual.time() not in horas_ocupadas:
                        slots_disponibles.append(hora_actual.strftime('%H:%M'))
                    hora_actual += timedelta(minutes=disp.duracion_cita)
                
                if slots_disponibles:
                    resultados.append({
                        'doctor_id': doctor.id,
                        'doctor_nombre': doctor.nombre_completo,
                        'especialidad': doctor.especialidad,
                        'fecha': fecha_consulta.isoformat(),
                        'slots_disponibles': slots_disponibles,
                        'duracion_cita_min': disp.duracion_cita
                    })
            
            return {
                'exito': True,
                'fecha_consultada': fecha_consulta.isoformat(),
                'total_doctores': len(resultados),
                'disponibilidad': resultados
            }
            
    except Exception as e:
        logger.error(f"❌ Error buscando disponibilidad: {e}")
        return {
            'exito': False,
            'error': str(e)
        }


@tool
def agendar_cita_tool(
    paciente_id: int,
    doctor_id: int,
    fecha: str,
    hora: str,
    motivo: str = "Consulta general",
    tipo_consulta: str = "general"
) -> Dict[str, Any]:
    """
    Agenda una nueva cita médica.
    
    Args:
        paciente_id: ID del paciente
        doctor_id: ID del doctor
        fecha: Fecha de la cita en formato YYYY-MM-DD
        hora: Hora de la cita en formato HH:MM
        motivo: Motivo de la consulta
        tipo_consulta: Tipo de consulta (general, seguimiento, urgente, especialidad)
    
    Returns:
        Dict con los detalles de la cita creada
    """
    try:
        with get_db_session() as db:
            # Verificar que paciente existe
            paciente = db.query(Pacientes).get(paciente_id)
            if not paciente:
                return {'exito': False, 'error': f'Paciente {paciente_id} no encontrado'}
            
            # Verificar que doctor existe
            doctor = db.query(Doctores).get(doctor_id)
            if not doctor:
                return {'exito': False, 'error': f'Doctor {doctor_id} no encontrado'}
            
            # Parsear fecha y hora
            fecha_hora_inicio = datetime.strptime(f"{fecha} {hora}", '%Y-%m-%d %H:%M')
            
            # Obtener duración de cita del doctor
            disponibilidad = db.query(DisponibilidadMedica).filter(
                DisponibilidadMedica.doctor_id == doctor_id,
                DisponibilidadMedica.dia_semana == fecha_hora_inicio.weekday()
            ).first()
            
            duracion = disponibilidad.duracion_cita if disponibilidad else 30
            fecha_hora_fin = fecha_hora_inicio + timedelta(minutes=duracion)
            
            # Verificar que no hay conflicto
            cita_existente = db.query(CitasMedicas).filter(
                CitasMedicas.doctor_id == doctor_id,
                CitasMedicas.fecha_hora_inicio == fecha_hora_inicio,
                CitasMedicas.estado.in_([EstadoCita.confirmada, EstadoCita.pendiente])
            ).first()
            
            if cita_existente:
                return {
                    'exito': False,
                    'error': f'Ya existe una cita a las {hora} con este doctor'
                }
            
            # Mapear tipo de consulta
            tipo_map = {
                'general': TipoConsulta.general,
                'seguimiento': TipoConsulta.seguimiento,
                'urgente': TipoConsulta.urgente,
                'especialidad': TipoConsulta.especialidad
            }
            tipo = tipo_map.get(tipo_consulta.lower(), TipoConsulta.general)
            
            # Crear la cita
            nueva_cita = CitasMedicas(
                paciente_id=paciente_id,
                doctor_id=doctor_id,
                fecha_hora_inicio=fecha_hora_inicio,
                fecha_hora_fin=fecha_hora_fin,
                estado=EstadoCita.pendiente,
                tipo_consulta=tipo,
                motivo_consulta=motivo
            )
            
            db.add(nueva_cita)
            db.commit()
            db.refresh(nueva_cita)
            
            logger.info(f"✅ Cita agendada: {paciente.nombre_completo} con {doctor.nombre_completo} - {fecha} {hora}")
            
            return {
                'exito': True,
                'cita_id': nueva_cita.id,
                'paciente': paciente.nombre_completo,
                'doctor': doctor.nombre_completo,
                'especialidad': doctor.especialidad,
                'fecha_hora': fecha_hora_inicio.isoformat(),
                'duracion_min': duracion,
                'estado': 'pendiente'
            }
            
    except ValueError as e:
        return {'exito': False, 'error': f'Formato de fecha/hora inválido: {e}'}
    except Exception as e:
        logger.error(f"❌ Error agendando cita: {e}")
        return {'exito': False, 'error': str(e)}


@tool
def cancelar_cita_tool(
    cita_id: int,
    motivo_cancelacion: str = "Cancelado por el paciente"
) -> Dict[str, Any]:
    """
    Cancela una cita médica existente.
    
    Args:
        cita_id: ID de la cita a cancelar
        motivo_cancelacion: Razón de la cancelación
    
    Returns:
        Dict con el resultado de la operación
    """
    try:
        with get_db_session() as db:
            cita = db.query(CitasMedicas).get(cita_id)
            
            if not cita:
                return {'exito': False, 'error': f'Cita {cita_id} no encontrada'}
            
            if cita.estado == EstadoCita.cancelada:
                return {'exito': False, 'error': 'La cita ya está cancelada'}
            
            if cita.estado == EstadoCita.completada:
                return {'exito': False, 'error': 'No se puede cancelar una cita completada'}
            
            # Obtener info antes de cancelar
            doctor = db.query(Doctores).get(cita.doctor_id)
            paciente = db.query(Pacientes).get(cita.paciente_id)
            
            # Cancelar
            cita.estado = EstadoCita.cancelada
            cita.notas_privadas = f"Cancelación: {motivo_cancelacion}"
            cita.updated_at = datetime.now()
            
            db.commit()
            
            logger.info(f"✅ Cita {cita_id} cancelada: {motivo_cancelacion}")
            
            return {
                'exito': True,
                'cita_id': cita_id,
                'paciente': paciente.nombre_completo if paciente else 'Desconocido',
                'doctor': doctor.nombre_completo if doctor else 'Desconocido',
                'fecha_hora_original': cita.fecha_hora_inicio.isoformat(),
                'motivo_cancelacion': motivo_cancelacion
            }
            
    except Exception as e:
        logger.error(f"❌ Error cancelando cita: {e}")
        return {'exito': False, 'error': str(e)}


@tool
def listar_citas_tool(
    paciente_id: Optional[int] = None,
    doctor_id: Optional[int] = None,
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None,
    estado: Optional[str] = None,
    limite: int = 20
) -> Dict[str, Any]:
    """
    Lista citas médicas con filtros opcionales.
    
    Args:
        paciente_id: Filtrar por paciente específico (opcional)
        doctor_id: Filtrar por doctor específico (opcional)
        fecha_inicio: Fecha inicio del rango YYYY-MM-DD (opcional)
        fecha_fin: Fecha fin del rango YYYY-MM-DD (opcional)
        estado: Filtrar por estado: pendiente, confirmada, completada, cancelada (opcional)
        limite: Número máximo de resultados (default: 20)
    
    Returns:
        Dict con lista de citas
    """
    try:
        with get_db_session() as db:
            query = db.query(CitasMedicas)
            
            if paciente_id:
                query = query.filter(CitasMedicas.paciente_id == paciente_id)
            
            if doctor_id:
                query = query.filter(CitasMedicas.doctor_id == doctor_id)
            
            if fecha_inicio:
                fecha_ini = datetime.strptime(fecha_inicio, '%Y-%m-%d')
                query = query.filter(CitasMedicas.fecha_hora_inicio >= fecha_ini)
            
            if fecha_fin:
                fecha_f = datetime.strptime(fecha_fin, '%Y-%m-%d') + timedelta(days=1)
                query = query.filter(CitasMedicas.fecha_hora_inicio < fecha_f)
            
            if estado:
                estado_map = {
                    'pendiente': EstadoCita.pendiente,
                    'confirmada': EstadoCita.confirmada,
                    'completada': EstadoCita.completada,
                    'cancelada': EstadoCita.cancelada
                }
                if estado.lower() in estado_map:
                    query = query.filter(CitasMedicas.estado == estado_map[estado.lower()])
            
            citas = query.order_by(CitasMedicas.fecha_hora_inicio.desc()).limit(limite).all()
            
            resultados = []
            for cita in citas:
                doctor = db.query(Doctores).get(cita.doctor_id)
                paciente = db.query(Pacientes).get(cita.paciente_id)
                
                resultados.append({
                    'cita_id': cita.id,
                    'paciente': paciente.nombre_completo if paciente else 'Desconocido',
                    'doctor': doctor.nombre_completo if doctor else 'Desconocido',
                    'especialidad': doctor.especialidad if doctor else None,
                    'fecha_hora': cita.fecha_hora_inicio.isoformat(),
                    'estado': cita.estado.value,
                    'motivo': cita.motivo_consulta
                })
            
            return {
                'exito': True,
                'total': len(resultados),
                'citas': resultados
            }
            
    except Exception as e:
        logger.error(f"❌ Error listando citas: {e}")
        return {'exito': False, 'error': str(e)}
