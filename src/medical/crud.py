# Medical CRUD Operations
# Operaciones básicas de base de datos para el sistema médico

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, text
from datetime import datetime, date, timedelta, time
from typing import List, Dict, Optional, Union, Any
import json

from .models import (
    Doctores, Pacientes, DisponibilidadMedica, CitasMedicas, 
    HistorialesMedicos, SincronizacionCalendar,
    TipoConsulta, EstadoCita, Genero, MetodoPago, EstadoSincronizacion
)
from ..database.db_config import get_db_session

# ===== OPERACIONES DE DOCTORES =====

def get_doctor_by_phone(phone_number: str) -> Optional[Dict[str, Any]]:
    """
    Obtiene doctor por número de teléfono.
    
    Returns:
        Dict con datos del doctor o None si no existe.
        Retorna dict para evitar DetachedInstanceError fuera de sesión.
    """
    with get_db_session() as db:
        doctor = db.query(Doctores).filter(Doctores.phone_number == phone_number).first()
        if doctor:
            return {
                "id": doctor.id,
                "nombre_completo": doctor.nombre_completo,
                "phone_number": doctor.phone_number,
                "especialidad": doctor.especialidad,
                "num_licencia": doctor.num_licencia,
                "orden_turno": doctor.orden_turno,
                "total_citas_asignadas": doctor.total_citas_asignadas
            }
        return None

def get_doctor_by_id(doctor_id: int) -> Optional[Dict[str, Any]]:
    """
    Obtiene doctor por ID.
    
    Returns:
        Dict con datos del doctor o None si no existe.
        Retorna dict para evitar DetachedInstanceError fuera de sesión.
    """
    with get_db_session() as db:
        doctor = db.query(Doctores).filter(Doctores.id == doctor_id).first()
        if doctor:
            return {
                "id": doctor.id,
                "nombre_completo": doctor.nombre_completo,
                "phone_number": doctor.phone_number,
                "especialidad": doctor.especialidad,
                "num_licencia": doctor.num_licencia,
                "orden_turno": doctor.orden_turno,
                "total_citas_asignadas": doctor.total_citas_asignadas
            }
        return None

def create_doctor(doctor_data: dict) -> Doctores:
    """Crea un nuevo doctor"""
    with get_db_session() as db:
        doctor = Doctores(**doctor_data)
        db.add(doctor)
        db.commit()
        db.refresh(doctor)
        return doctor

def update_doctor(doctor_id: int, updates: dict) -> Optional[Doctores]:
    """Actualiza información de doctor"""
    with get_db_session() as db:
        doctor = db.query(Doctores).filter(Doctores.id == doctor_id).first()
        if doctor:
            for key, value in updates.items():
                setattr(doctor, key, value)
            db.commit()
            db.refresh(doctor)
        return doctor

# ===== OPERACIONES DE PACIENTES =====

def create_patient(patient_data: dict) -> Pacientes:
    """Crea un nuevo paciente"""
    with get_db_session() as db:
        # Convertir fecha de nacimiento si viene como string
        if isinstance(patient_data.get('fecha_nacimiento'), str):
            patient_data['fecha_nacimiento'] = datetime.strptime(
                patient_data['fecha_nacimiento'], "%Y-%m-%d"
            ).date()
        
        paciente = Pacientes(**patient_data)
        db.add(paciente)
        db.commit()
        db.refresh(paciente)
        return paciente

def search_patients(doctor_id: int, search_term: str, limit: int = 10) -> List[Pacientes]:
    """Busca pacientes por nombre, teléfono o ID"""
    with get_db_session() as db:
        query = db.query(Pacientes).filter(Pacientes.doctor_id == doctor_id)
        
        # Búsqueda por ID si es numérico
        if search_term.isdigit():
            query = query.filter(Pacientes.id == int(search_term))
        else:
            # Búsqueda por nombre o teléfono
            query = query.filter(
                or_(
                    Pacientes.nombre_completo.ilike(f"%{search_term}%"),
                    Pacientes.telefono.ilike(f"%{search_term}%"),
                    Pacientes.email.ilike(f"%{search_term}%")
                )
            )
        
        return query.order_by(Pacientes.ultima_cita.desc().nullslast()).limit(limit).all()

def get_patient_by_id(patient_id: int) -> Optional[Dict[str, Any]]:
    """Obtiene paciente por ID. Retorna dict para evitar problemas de sesión."""
    with get_db_session() as db:
        paciente = db.query(Pacientes).filter(Pacientes.id == patient_id).first()
        if paciente:
            return {
                "id": paciente.id,
                "doctor_id": paciente.doctor_id,
                "nombre_completo": paciente.nombre_completo,
                "telefono": paciente.telefono,
                "email": paciente.email
            }
        return None

def get_paciente_by_phone(phone_number: str) -> Optional[Dict[str, Any]]:
    """Obtiene paciente por número de teléfono. Retorna dict para evitar problemas de sesión."""
    with get_db_session() as db:
        paciente = db.query(Pacientes).filter(Pacientes.telefono == phone_number).first()
        if paciente:
            return {
                "id": paciente.id,
                "doctor_id": paciente.doctor_id,
                "nombre_completo": paciente.nombre_completo,
                "telefono": paciente.telefono,
                "email": paciente.email
            }
        return None

def registrar_paciente_externo(phone_number: str, nombre: str) -> Dict[str, Any]:
    """
    Registra un paciente externo en el sistema.
    
    Args:
        phone_number: Número de teléfono del paciente
        nombre: Nombre completo del paciente
        
    Returns:
        Dict con paciente_id y es_nuevo
    """
    with get_db_session() as db:
        # Verificar si ya existe
        paciente_existente = db.query(Pacientes).filter(
            Pacientes.telefono == phone_number
        ).first()
        
        if paciente_existente:
            # Actualizar timestamp de última interacción
            paciente_existente.ultima_cita = datetime.now()
            db.commit()
            return {
                "paciente_id": paciente_existente.id,
                "es_nuevo": False,
                "nombre": paciente_existente.nombre_completo
            }
        
        # Crear nuevo paciente externo
        # Por defecto asignar al doctor 1 (Santiago) - se puede cambiar después al agendar
        patient_data = {
            "doctor_id": 1,  # Default: Santiago
            "nombre_completo": nombre.strip(),
            "telefono": phone_number.strip(),
            "created_at": datetime.now(),
            "ultima_cita": None
        }
        
        nuevo_paciente = Pacientes(**patient_data)
        db.add(nuevo_paciente)
        db.commit()
        db.refresh(nuevo_paciente)
        
        return {
            "paciente_id": nuevo_paciente.id,
            "es_nuevo": True,
            "nombre": nuevo_paciente.nombre_completo
        }

def get_patients_by_doctor(doctor_id: int, limit: int = 50) -> List[Pacientes]:
    """Obtiene todos los pacientes de un doctor"""
    with get_db_session() as db:
        return db.query(Pacientes).filter(
            Pacientes.doctor_id == doctor_id
        ).order_by(Pacientes.ultima_cita.desc().nullslast()).limit(limit).all()

def update_patient(patient_id: int, updates: dict) -> Optional[Pacientes]:
    """Actualiza información de paciente"""
    with get_db_session() as db:
        paciente = db.query(Pacientes).filter(Pacientes.id == patient_id).first()
        if paciente:
            # Manejar fecha de nacimiento si viene como string
            if 'fecha_nacimiento' in updates and isinstance(updates['fecha_nacimiento'], str):
                updates['fecha_nacimiento'] = datetime.strptime(
                    updates['fecha_nacimiento'], "%Y-%m-%d"
                ).date()
            
            for key, value in updates.items():
                setattr(paciente, key, value)
            db.commit()
            db.refresh(paciente)
        return paciente

# ===== OPERACIONES DE DISPONIBILIDAD =====

def get_doctor_availability(doctor_id: int) -> List[DisponibilidadMedica]:
    """Obtiene la disponibilidad semanal del doctor"""
    with get_db_session() as db:
        return db.query(DisponibilidadMedica).filter(
            DisponibilidadMedica.doctor_id == doctor_id,
            DisponibilidadMedica.disponible == True
        ).order_by(DisponibilidadMedica.dia_semana, DisponibilidadMedica.hora_inicio).all()

def set_doctor_availability(doctor_id: int, availability_data: List[dict]) -> List[DisponibilidadMedica]:
    """Configura la disponibilidad del doctor"""
    with get_db_session() as db:
        # Eliminar disponibilidad existente
        db.query(DisponibilidadMedica).filter(
            DisponibilidadMedica.doctor_id == doctor_id
        ).delete()
        
        # Agregar nueva disponibilidad
        availabilities = []
        for avail_data in availability_data:
            availability = DisponibilidadMedica(doctor_id=doctor_id, **avail_data)
            db.add(availability)
            availabilities.append(availability)
        
        db.commit()
        for avail in availabilities:
            db.refresh(avail)
        
        return availabilities

def check_doctor_availability(doctor_id: int, start_time: datetime, end_time: datetime) -> bool:
    """Verifica si el doctor está disponible en el horario solicitado"""
    with get_db_session() as db:
        day_of_week = start_time.weekday()
        
        availability = db.query(DisponibilidadMedica).filter(
            DisponibilidadMedica.doctor_id == doctor_id,
            DisponibilidadMedica.dia_semana == day_of_week,
            DisponibilidadMedica.disponible == True,
            DisponibilidadMedica.hora_inicio <= start_time.time(),
            DisponibilidadMedica.hora_fin >= end_time.time()
        ).first()
        
        return availability is not None

# ===== OPERACIONES DE CITAS =====

def schedule_appointment(appointment_data: dict) -> CitasMedicas:
    """Agenda una nueva cita médica"""
    with get_db_session() as db:
        # Validar disponibilidad antes de crear
        if not check_doctor_availability(
            appointment_data['doctor_id'],
            appointment_data['fecha_hora_inicio'],
            appointment_data['fecha_hora_fin']
        ):
            raise ValueError("Doctor no disponible en el horario solicitado")
        
        # Verificar conflictos
        if check_appointment_conflicts(
            appointment_data['doctor_id'],
            appointment_data['fecha_hora_inicio'],
            appointment_data['fecha_hora_fin']
        ):
            raise ValueError("Ya existe una cita en este horario")
        
        cita = CitasMedicas(**appointment_data)
        db.add(cita)
        db.commit()
        db.refresh(cita)
        
        # Actualizar última cita del paciente
        paciente = db.query(Pacientes).filter(Pacientes.id == cita.paciente_id).first()
        if paciente:
            paciente.ultima_cita = cita.fecha_hora_inicio
            db.commit()
        
        return cita

def check_appointment_conflicts(
    doctor_id: int, 
    start_time: datetime, 
    end_time: datetime, 
    exclude_cita_id: int = None
) -> bool:
    """Detecta conflictos con citas existentes"""
    with get_db_session() as db:
        query = db.query(CitasMedicas).filter(
            CitasMedicas.doctor_id == doctor_id,
            CitasMedicas.estado.in_(['programada', 'confirmada', 'en_curso']),
            or_(
                # Nueva cita inicia durante cita existente
                and_(
                    CitasMedicas.fecha_hora_inicio <= start_time,
                    CitasMedicas.fecha_hora_fin > start_time
                ),
                # Nueva cita termina durante cita existente  
                and_(
                    CitasMedicas.fecha_hora_inicio < end_time,
                    CitasMedicas.fecha_hora_fin >= end_time
                ),
                # Nueva cita envuelve cita existente
                and_(
                    CitasMedicas.fecha_hora_inicio >= start_time,
                    CitasMedicas.fecha_hora_fin <= end_time
                )
            )
        )
        
        if exclude_cita_id:
            query = query.filter(CitasMedicas.id != exclude_cita_id)
            
        return query.count() > 0


def agendar_cita_simple(
    doctor_id: int,
    paciente_id: int,
    fecha_inicio: datetime,
    fecha_fin: datetime,
    motivo: str = "Consulta general"
) -> Optional[int]:
    """
    Función simplificada para agendar citas desde el recepcionista.
    
    Args:
        doctor_id: ID del doctor
        paciente_id: ID del paciente
        fecha_inicio: Fecha y hora de inicio
        fecha_fin: Fecha y hora de fin
        motivo: Motivo de la consulta
        
    Returns:
        ID de la cita creada o None si falla
    """
    with get_db_session() as db:
        try:
            # Crear la cita
            cita = CitasMedicas(
                doctor_id=doctor_id,
                paciente_id=paciente_id,
                fecha_hora_inicio=fecha_inicio,
                fecha_hora_fin=fecha_fin,
                tipo_consulta=TipoConsulta.primera_vez,
                estado=EstadoCita.programada,
                motivo_consulta=motivo,
                created_at=datetime.now()
            )
            db.add(cita)
            db.commit()
            db.refresh(cita)
            
            # Actualizar última cita del paciente
            paciente = db.query(Pacientes).filter(Pacientes.id == paciente_id).first()
            if paciente:
                paciente.ultima_cita = fecha_inicio
                db.commit()
            
            return cita.id
            
        except Exception as e:
            db.rollback()
            import logging
            logging.getLogger(__name__).error(f"Error agendando cita: {e}")
            return None


def get_available_slots(doctor_id: int, fecha: date, duracion_minutos: int = 30) -> List[Dict]:
    """Genera slots disponibles basado en horarios y citas existentes"""
    with get_db_session() as db:
        day_of_week = fecha.weekday()
        
        # Obtener disponibilidad del doctor
        disponibilidades = db.query(DisponibilidadMedica).filter(
            DisponibilidadMedica.doctor_id == doctor_id,
            DisponibilidadMedica.dia_semana == day_of_week,
            DisponibilidadMedica.disponible == True
        ).all()
        
        if not disponibilidades:
            return []
        
        # Obtener citas existentes del día
        start_of_day = datetime.combine(fecha, time.min)
        end_of_day = datetime.combine(fecha, time.max)
        
        citas_existentes = db.query(CitasMedicas).filter(
            CitasMedicas.doctor_id == doctor_id,
            CitasMedicas.fecha_hora_inicio >= start_of_day,
            CitasMedicas.fecha_hora_fin <= end_of_day,
            CitasMedicas.estado != 'cancelada'
        ).all()
        
        slots_disponibles = []
        
        for disponibilidad in disponibilidades:
            current_time = datetime.combine(fecha, disponibilidad.hora_inicio)
            end_time = datetime.combine(fecha, disponibilidad.hora_fin)
            
            while current_time + timedelta(minutes=duracion_minutos) <= end_time:
                slot_end = current_time + timedelta(minutes=duracion_minutos)
                
                # Verificar si el slot no tiene conflictos
                tiene_conflicto = False
                for cita in citas_existentes:
                    if (current_time < cita.fecha_hora_fin and slot_end > cita.fecha_hora_inicio):
                        tiene_conflicto = True
                        break
                
                if not tiene_conflicto:
                    slots_disponibles.append({
                        "inicio": current_time.isoformat(),
                        "fin": slot_end.isoformat(),
                        "disponible": True,
                        "duracion_minutos": duracion_minutos
                    })
                
                current_time = slot_end
        
        return slots_disponibles

def get_appointments_by_doctor(
    doctor_id: int, 
    fecha_inicio: date = None,
    fecha_fin: date = None,
    estado: str = None,
    limit: int = 50
) -> List[CitasMedicas]:
    """Obtiene citas del doctor con filtros opcionales"""
    with get_db_session() as db:
        query = db.query(CitasMedicas).filter(CitasMedicas.doctor_id == doctor_id)
        
        if fecha_inicio:
            query = query.filter(func.date(CitasMedicas.fecha_hora_inicio) >= fecha_inicio)
        
        if fecha_fin:
            query = query.filter(func.date(CitasMedicas.fecha_hora_inicio) <= fecha_fin)
        
        if estado:
            query = query.filter(CitasMedicas.estado == estado)
        
        return query.order_by(CitasMedicas.fecha_hora_inicio.desc()).limit(limit).all()

def update_appointment(cita_id: int, updates: dict) -> Optional[CitasMedicas]:
    """Actualiza una cita médica"""
    with get_db_session() as db:
        cita = db.query(CitasMedicas).filter(CitasMedicas.id == cita_id).first()
        if cita:
            # Validar cambios de fecha/hora
            if 'fecha_hora_inicio' in updates or 'fecha_hora_fin' in updates:
                nuevo_inicio = updates.get('fecha_hora_inicio', cita.fecha_hora_inicio)
                nuevo_fin = updates.get('fecha_hora_fin', cita.fecha_hora_fin)
                
                if isinstance(nuevo_inicio, str):
                    nuevo_inicio = datetime.fromisoformat(nuevo_inicio)
                if isinstance(nuevo_fin, str):
                    nuevo_fin = datetime.fromisoformat(nuevo_fin)
                
                # Verificar disponibilidad y conflictos
                if not check_doctor_availability(cita.doctor_id, nuevo_inicio, nuevo_fin):
                    raise ValueError("Doctor no disponible en el nuevo horario")
                
                if check_appointment_conflicts(cita.doctor_id, nuevo_inicio, nuevo_fin, cita.id):
                    raise ValueError("Conflicto con otra cita en el nuevo horario")
            
            for key, value in updates.items():
                setattr(cita, key, value)
            
            cita.updated_at = datetime.now()
            db.commit()
            db.refresh(cita)
        
        return cita

def cancel_appointment(cita_id: int, motivo: str = None) -> Optional[CitasMedicas]:
    """Cancela una cita médica"""
    with get_db_session() as db:
        cita = db.query(CitasMedicas).filter(CitasMedicas.id == cita_id).first()
        if cita:
            cita.estado = EstadoCita.cancelada
            if motivo and cita.notas_privadas:
                cita.notas_privadas += f"\n\nCancelada: {motivo}"
            elif motivo:
                cita.notas_privadas = f"Cancelada: {motivo}"
            
            cita.updated_at = datetime.now()
            db.commit()
            db.refresh(cita)
        
        return cita

# ===== OPERACIONES DE HISTORIAL MÉDICO =====

def create_medical_history(history_data: dict) -> HistorialesMedicos:
    """Crea un registro de historial médico"""
    with get_db_session() as db:
        historial = HistorialesMedicos(**history_data)
        db.add(historial)
        db.commit()
        db.refresh(historial)
        return historial

def get_patient_history(patient_id: int, limit: int = 20) -> List[HistorialesMedicos]:
    """Obtiene el historial médico completo de un paciente"""
    with get_db_session() as db:
        return db.query(HistorialesMedicos).filter(
            HistorialesMedicos.paciente_id == patient_id
        ).order_by(HistorialesMedicos.fecha_consulta.desc()).limit(limit).all()

# ===== OPERACIONES DE SINCRONIZACIÓN =====

def create_sync_record(sync_data: dict) -> SincronizacionCalendar:
    """Crea un registro de sincronización"""
    with get_db_session() as db:
        sync = SincronizacionCalendar(**sync_data)
        db.add(sync)
        db.commit()
        db.refresh(sync)
        return sync

def update_sync_record(cita_id: int, updates: dict) -> Optional[SincronizacionCalendar]:
    """Actualiza el estado de sincronización"""
    with get_db_session() as db:
        sync = db.query(SincronizacionCalendar).filter(
            SincronizacionCalendar.cita_id == cita_id
        ).first()
        
        if sync:
            for key, value in updates.items():
                setattr(sync, key, value)
            sync.updated_at = datetime.now()
            db.commit()
            db.refresh(sync)
        else:
            # Crear nuevo registro si no existe
            updates['cita_id'] = cita_id
            sync = create_sync_record(updates)
        
        return sync

def get_pending_syncs(limit: int = 100) -> List[SincronizacionCalendar]:
    """Obtiene sincronizaciones pendientes o con error"""
    with get_db_session() as db:
        return db.query(SincronizacionCalendar).filter(
            or_(
                SincronizacionCalendar.estado == EstadoSincronizacion.pendiente,
                and_(
                    SincronizacionCalendar.estado == EstadoSincronizacion.error,
                    SincronizacionCalendar.siguiente_reintento <= datetime.now()
                )
            )
        ).limit(limit).all()

# ===== UTILIDADES Y ESTADÍSTICAS =====

def get_doctor_stats(doctor_id: int, periodo: str = "mes") -> Dict:
    """Obtiene estadísticas del doctor"""
    with get_db_session() as db:
        # Definir rango de fechas según periodo
        hoy = date.today()
        if periodo == "dia":
            fecha_inicio = hoy
            fecha_fin = hoy
        elif periodo == "semana":
            fecha_inicio = hoy - timedelta(days=hoy.weekday())
            fecha_fin = fecha_inicio + timedelta(days=6)
        elif periodo == "mes":
            fecha_inicio = hoy.replace(day=1)
            fecha_fin = (fecha_inicio + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        else:
            fecha_inicio = hoy - timedelta(days=30)
            fecha_fin = hoy
        
        # Consultas básicas
        total_pacientes = db.query(Pacientes).filter(Pacientes.doctor_id == doctor_id).count()
        
        citas_periodo = db.query(CitasMedicas).filter(
            CitasMedicas.doctor_id == doctor_id,
            func.date(CitasMedicas.fecha_hora_inicio).between(fecha_inicio, fecha_fin)
        )
        
        total_citas = citas_periodo.count()
        citas_completadas = citas_periodo.filter(CitasMedicas.estado == 'completada').count()
        citas_canceladas = citas_periodo.filter(CitasMedicas.estado == 'cancelada').count()
        
        # Ingresos del periodo
        ingresos = db.query(func.sum(CitasMedicas.costo_consulta)).filter(
            CitasMedicas.doctor_id == doctor_id,
            CitasMedicas.estado == 'completada',
            func.date(CitasMedicas.fecha_hora_inicio).between(fecha_inicio, fecha_fin)
        ).scalar() or 0
        
        return {
            "total_pacientes": total_pacientes,
            "citas_periodo": total_citas,
            "citas_completadas": citas_completadas,
            "citas_canceladas": citas_canceladas,
            "tasa_asistencia": round((citas_completadas / total_citas * 100) if total_citas > 0 else 0, 2),
            "ingresos_periodo": float(ingresos),
            "periodo": periodo,
            "fecha_inicio": fecha_inicio.isoformat(),
            "fecha_fin": fecha_fin.isoformat()
        }