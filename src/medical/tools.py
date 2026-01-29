# Medical Tools for LangGraph Integration
# 6 herramientas médicas básicas para el sistema híbrido

from typing import Dict, List, Optional
from datetime import datetime, date, timedelta
import json
import re
from langchain_core.tools import tool

from .crud import (
    get_doctor_by_phone, create_patient, search_patients,
    schedule_appointment, check_doctor_availability, get_available_slots,
    update_appointment, cancel_appointment, get_patient_by_id
)

# ===== HERRAMIENTA 1: CREAR PACIENTE =====

@tool
def crear_paciente_medico(
    doctor_phone: str,
    nombre_completo: str,
    telefono: str,
    email: str = None,
    fecha_nacimiento: str = None,
    genero: str = None,
    direccion: str = None,
    seguro_medico: str = None,
    alergias: str = None
) -> str:
    """
    Registra un nuevo paciente en el sistema médico.
    
    Args:
        doctor_phone: Número de teléfono del doctor (obligatorio)
        nombre_completo: Nombre completo del paciente (obligatorio)
        telefono: Teléfono del paciente, debe ser único (obligatorio)
        email: Email del paciente (opcional)
        fecha_nacimiento: Fecha en formato YYYY-MM-DD (opcional)
        genero: masculino, femenino, otro (opcional)
        direccion: Dirección completa del paciente (opcional)
        seguro_medico: Nombre del seguro médico (opcional)
        alergias: Alergias conocidas del paciente (opcional)
        
    Returns:
        Mensaje de confirmación con ID del paciente creado o error
    """
    try:
        # Validar que el doctor existe
        doctor = get_doctor_by_phone(doctor_phone)
        if not doctor:
            return f"❌ Error: Doctor con teléfono {doctor_phone} no está registrado en el sistema"
        
        # Validar teléfono del paciente
        if not telefono or len(telefono) < 10:
            return "❌ Error: El teléfono del paciente es obligatorio y debe tener al menos 10 dígitos"
        
        # Preparar datos del paciente
        patient_data = {
            "doctor_id": doctor.id,
            "nombre_completo": nombre_completo.strip(),
            "telefono": telefono.strip(),
            "email": email.strip() if email else None,
            "genero": genero.lower() if genero else None,
            "direccion": direccion.strip() if direccion else None,
            "seguro_medico": seguro_medico.strip() if seguro_medico else None,
            "alergias": alergias.strip() if alergias else None
        }
        
        # Convertir fecha de nacimiento si se proporciona
        if fecha_nacimiento:
            try:
                fecha_obj = datetime.strptime(fecha_nacimiento, "%Y-%m-%d").date()
                # Validar que la fecha no sea futura
                if fecha_obj > date.today():
                    return "❌ Error: La fecha de nacimiento no puede ser futura"
                patient_data["fecha_nacimiento"] = fecha_obj
            except ValueError:
                return "❌ Error: Fecha de nacimiento debe estar en formato YYYY-MM-DD"
        
        # Crear el paciente
        paciente = create_patient(patient_data)
        
        return f"""✅ **Paciente registrado exitosamente**

👤 **{paciente.nombre_completo}** (ID: {paciente.id})
📱 Teléfono: {paciente.telefono}
📧 Email: {paciente.email or 'No registrado'}
🎂 Fecha nacimiento: {paciente.fecha_nacimiento.strftime('%d/%m/%Y') if paciente.fecha_nacimiento else 'No registrada'}
🏥 Seguro: {paciente.seguro_medico or 'No especificado'}
⚠️ Alergias: {paciente.alergias or 'Ninguna registrada'}

El paciente ha sido asignado al Dr. {doctor.phone_number}"""
        
    except Exception as e:
        error_msg = str(e)
        if "duplicate key value" in error_msg.lower():
            return "❌ Error: Ya existe un paciente registrado con este número de teléfono"
        return f"❌ Error al registrar paciente: {error_msg}"

# ===== HERRAMIENTA 2: BUSCAR PACIENTES =====

@tool
def buscar_pacientes_doctor(
    doctor_phone: str,
    busqueda: str
) -> str:
    """
    Busca pacientes del doctor por nombre, teléfono o ID.
    
    Args:
        doctor_phone: Número de teléfono del doctor
        busqueda: Término de búsqueda (nombre, teléfono, o ID del paciente)
        
    Returns:
        Lista de pacientes encontrados con información básica
    """
    try:
        # Validar que el doctor existe
        doctor = get_doctor_by_phone(doctor_phone)
        if not doctor:
            return f"❌ Error: Doctor con teléfono {doctor_phone} no está registrado en el sistema"
        
        # Realizar búsqueda
        pacientes = search_patients(doctor.id, busqueda.strip())
        
        if not pacientes:
            return f"""🔍 **No se encontraron pacientes**

Búsqueda: "{busqueda}"
Doctor: {doctor_phone}

No hay pacientes que coincidan con el término de búsqueda."""
        
        resultado = f"""🔍 **Pacientes encontrados ({len(pacientes)}):**
Búsqueda: "{busqueda}"

"""
        
        for i, p in enumerate(pacientes, 1):
            ultima_cita_str = "Sin citas previas"
            if p.ultima_cita:
                ultima_cita_str = p.ultima_cita.strftime('%d/%m/%Y')
            
            resultado += f"""**{i}. {p.nombre_completo}** (ID: {p.id})
📱 Teléfono: {p.telefono}
📧 Email: {p.email or 'No registrado'}
📅 Última cita: {ultima_cita_str}
⚠️ Alergias: {p.alergias or 'Ninguna'}

---

"""
        
        return resultado.strip()
        
    except Exception as e:
        return f"❌ Error en búsqueda: {str(e)}"

# ===== HERRAMIENTA 3: CONSULTAR DISPONIBILIDAD =====

@tool
def consultar_slots_disponibles(
    doctor_phone: str,
    fecha: str,
    duracion_minutos: int = 30
) -> str:
    """
    Consulta los horarios disponibles del doctor para una fecha específica.
    
    Args:
        doctor_phone: Número de teléfono del doctor
        fecha: Fecha en formato YYYY-MM-DD
        duracion_minutos: Duración de la cita en minutos (default: 30)
        
    Returns:
        Lista de horarios disponibles para agendar citas
    """
    try:
        # Validar que el doctor existe
        doctor = get_doctor_by_phone(doctor_phone)
        if not doctor:
            return f"❌ Error: Doctor con teléfono {doctor_phone} no está registrado en el sistema"
        
        # Validar y parsear fecha
        try:
            fecha_obj = datetime.strptime(fecha, "%Y-%m-%d").date()
        except ValueError:
            return "❌ Error: Fecha debe estar en formato YYYY-MM-DD"
        
        # Validar que no sea fecha pasada
        if fecha_obj < date.today():
            return "❌ Error: No se pueden consultar fechas pasadas"
        
        # Validar duración
        if duracion_minutos < 15 or duracion_minutos > 240:
            return "❌ Error: La duración debe estar entre 15 y 240 minutos"
        
        # Obtener slots disponibles
        slots = get_available_slots(doctor.id, fecha_obj, duracion_minutos)
        
        # Nombre del día en español
        dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        nombre_dia = dias_semana[fecha_obj.weekday()]
        
        if not slots:
            return f"""📅 **Sin horarios disponibles**

**{nombre_dia} {fecha_obj.strftime('%d/%m/%Y')}**
Duración solicitada: {duracion_minutos} minutos

No hay horarios disponibles para esta fecha.
Puede revisar otros días o consultar la disponibilidad general del doctor."""
        
        resultado = f"""📅 **Horarios disponibles - {nombre_dia} {fecha_obj.strftime('%d/%m/%Y')}**
Duración por cita: {duracion_minutos} minutos

"""
        
        # Agrupar slots por intervalos de tiempo
        for i, slot in enumerate(slots, 1):
            inicio = datetime.fromisoformat(slot['inicio']).time()
            fin = datetime.fromisoformat(slot['fin']).time()
            resultado += f"🕐 **{i}.** {inicio.strftime('%H:%M')} - {fin.strftime('%H:%M')}\n"
        
        resultado += f"\n✅ **Total: {len(slots)} horarios disponibles**"
        
        return resultado
        
    except Exception as e:
        return f"❌ Error al consultar disponibilidad: {str(e)}"

# ===== HERRAMIENTA 4: AGENDAR CITA MÉDICA =====

@tool
def agendar_cita_medica_completa(
    doctor_phone: str,
    paciente_id: int,
    fecha_hora: str,  # "YYYY-MM-DD HH:MM"
    tipo_consulta: str = "seguimiento",
    motivo_consulta: str = None,
    duracion_minutos: int = 30
) -> str:
    """
    Agenda una nueva cita médica con validaciones completas.
    
    Args:
        doctor_phone: Número de teléfono del doctor
        paciente_id: ID del paciente (obtenido de buscar_pacientes_doctor)
        fecha_hora: Fecha y hora en formato "YYYY-MM-DD HH:MM"
        tipo_consulta: primera_vez, seguimiento, urgencia, revision (default: seguimiento)
        motivo_consulta: Motivo de la consulta (opcional)
        duracion_minutos: Duración en minutos (default: 30)
        
    Returns:
        Confirmación de la cita agendada o mensaje de error
    """
    try:
        # Validar que el doctor existe
        doctor = get_doctor_by_phone(doctor_phone)
        if not doctor:
            return f"❌ Error: Doctor con teléfono {doctor_phone} no está registrado en el sistema"
        
        # Validar que el paciente existe y pertenece al doctor
        paciente = get_patient_by_id(paciente_id)
        if not paciente:
            return f"❌ Error: No se encontró paciente con ID {paciente_id}"
        
        if paciente.doctor_id != doctor.id:
            return f"❌ Error: El paciente {paciente.nombre_completo} no pertenece a este doctor"
        
        # Validar y parsear fecha y hora
        try:
            inicio = datetime.strptime(fecha_hora, "%Y-%m-%d %H:%M")
        except ValueError:
            return "❌ Error: Fecha debe estar en formato 'YYYY-MM-DD HH:MM' (ejemplo: '2024-01-15 14:30')"
        
        fin = inicio + timedelta(minutes=duracion_minutos)
        
        # Validar que no sea fecha/hora pasada
        if inicio <= datetime.now():
            return "❌ Error: No se pueden agendar citas en fechas y horas pasadas"
        
        # Validar tipo de consulta
        tipos_validos = ['primera_vez', 'seguimiento', 'urgencia', 'revision']
        if tipo_consulta not in tipos_validos:
            return f"❌ Error: Tipo de consulta debe ser uno de: {', '.join(tipos_validos)}"
        
        # Verificar disponibilidad del doctor
        if not check_doctor_availability(doctor.id, inicio, fin):
            return f"❌ Error: Doctor no disponible en horario {inicio.strftime('%d/%m/%Y %H:%M')}"
        
        # Preparar datos de la cita
        cita_data = {
            "doctor_id": doctor.id,
            "paciente_id": paciente_id,
            "fecha_hora_inicio": inicio,
            "fecha_hora_fin": fin,
            "tipo_consulta": tipo_consulta,
            "motivo_consulta": motivo_consulta.strip() if motivo_consulta else None,
            "estado": "programada"
        }
        
        # Crear la cita
        cita = schedule_appointment(cita_data)
        
        # TODO: Sincronizar con Google Calendar en background
        # sync_to_google_calendar.delay(cita.id)
        
        dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        nombre_dia = dias_semana[inicio.weekday()]
        
        return f"""✅ **Cita agendada exitosamente**

📋 **Detalles de la cita:**
🆔 ID Cita: {cita.id}
👤 Paciente: {paciente.nombre_completo}
📱 Teléfono paciente: {paciente.telefono}
📅 Fecha: {nombre_dia} {inicio.strftime('%d/%m/%Y')}
🕐 Hora: {inicio.strftime('%H:%M')} - {fin.strftime('%H:%M')}
⏱️ Duración: {duracion_minutos} minutos
🏥 Tipo: {tipo_consulta.replace('_', ' ').title()}
📝 Motivo: {motivo_consulta or 'No especificado'}
📊 Estado: Programada

La cita se sincronizará automáticamente con Google Calendar."""
        
    except ValueError as ve:
        return f"❌ Error de validación: {str(ve)}"
    except Exception as e:
        return f"❌ Error al agendar cita: {str(e)}"

# ===== HERRAMIENTA 5: MODIFICAR CITA MÉDICA =====

@tool
def modificar_cita_medica(
    doctor_phone: str,
    cita_id: int,
    nueva_fecha_hora: str = None,
    nuevo_estado: str = None,
    nuevas_notas: str = None,
    nuevo_motivo: str = None
) -> str:
    """
    Modifica una cita médica existente.
    
    Args:
        doctor_phone: Número de teléfono del doctor
        cita_id: ID de la cita a modificar
        nueva_fecha_hora: Nueva fecha y hora en formato "YYYY-MM-DD HH:MM" (opcional)
        nuevo_estado: Nuevo estado de la cita (programada, confirmada, completada, cancelada) (opcional)
        nuevas_notas: Notas adicionales sobre la cita (opcional)
        nuevo_motivo: Nuevo motivo de consulta (opcional)
        
    Returns:
        Confirmación de los cambios realizados o mensaje de error
    """
    try:
        # Validar que el doctor existe
        doctor = get_doctor_by_phone(doctor_phone)
        if not doctor:
            return f"❌ Error: Doctor con teléfono {doctor_phone} no está registrado en el sistema"
        
        # Preparar actualizaciones
        updates = {}
        cambios_realizados = []
        
        # Validar y procesar nueva fecha/hora
        if nueva_fecha_hora:
            try:
                nuevo_inicio = datetime.strptime(nueva_fecha_hora, "%Y-%m-%d %H:%M")
                if nuevo_inicio <= datetime.now():
                    return "❌ Error: La nueva fecha y hora no puede ser en el pasado"
                
                # Asumir duración de 30 minutos si no se especifica
                nuevo_fin = nuevo_inicio + timedelta(minutes=30)
                
                updates['fecha_hora_inicio'] = nuevo_inicio
                updates['fecha_hora_fin'] = nuevo_fin
                cambios_realizados.append(f"Fecha y hora: {nuevo_inicio.strftime('%d/%m/%Y %H:%M')}")
                
            except ValueError:
                return "❌ Error: Nueva fecha debe estar en formato 'YYYY-MM-DD HH:MM'"
        
        # Validar y procesar nuevo estado
        if nuevo_estado:
            estados_validos = ['programada', 'confirmada', 'en_curso', 'completada', 'cancelada', 'no_asistio']
            if nuevo_estado not in estados_validos:
                return f"❌ Error: Estado debe ser uno de: {', '.join(estados_validos)}"
            
            updates['estado'] = nuevo_estado
            cambios_realizados.append(f"Estado: {nuevo_estado.replace('_', ' ').title()}")
        
        # Procesar notas
        if nuevas_notas:
            updates['notas_privadas'] = nuevas_notas.strip()
            cambios_realizados.append("Notas actualizadas")
        
        # Procesar motivo
        if nuevo_motivo:
            updates['motivo_consulta'] = nuevo_motivo.strip()
            cambios_realizados.append("Motivo actualizado")
        
        if not updates:
            return "❌ Error: No se proporcionaron cambios para realizar"
        
        # Actualizar la cita
        cita_actualizada = update_appointment(cita_id, updates)
        
        if not cita_actualizada:
            return f"❌ Error: No se encontró la cita con ID {cita_id}"
        
        # Verificar que la cita pertenece al doctor
        if cita_actualizada.doctor_id != doctor.id:
            return f"❌ Error: La cita {cita_id} no pertenece a este doctor"
        
        # Obtener información del paciente
        paciente = get_patient_by_id(cita_actualizada.paciente_id)
        
        return f"""✅ **Cita modificada exitosamente**

📋 **Cita ID: {cita_actualizada.id}**
👤 Paciente: {paciente.nombre_completo if paciente else 'Paciente no encontrado'}
📅 Fecha actual: {cita_actualizada.fecha_hora_inicio.strftime('%d/%m/%Y %H:%M')}
📊 Estado actual: {cita_actualizada.estado.replace('_', ' ').title()}

🔄 **Cambios realizados:**
{chr(10).join(f'• {cambio}' for cambio in cambios_realizados)}

La sincronización con Google Calendar se actualizará automáticamente."""
        
    except ValueError as ve:
        return f"❌ Error de validación: {str(ve)}"
    except Exception as e:
        return f"❌ Error al modificar cita: {str(e)}"

# ===== HERRAMIENTA 6: CANCELAR CITA MÉDICA =====

@tool
def cancelar_cita_medica(
    doctor_phone: str,
    cita_id: int,
    motivo_cancelacion: str
) -> str:
    """
    Cancela una cita médica y libera el slot de tiempo.
    
    Args:
        doctor_phone: Número de teléfono del doctor
        cita_id: ID de la cita a cancelar
        motivo_cancelacion: Razón por la cual se cancela la cita
        
    Returns:
        Confirmación de la cancelación o mensaje de error
    """
    try:
        # Validar que el doctor existe
        doctor = get_doctor_by_phone(doctor_phone)
        if not doctor:
            return f"❌ Error: Doctor con teléfono {doctor_phone} no está registrado en el sistema"
        
        # Validar motivo
        if not motivo_cancelacion or len(motivo_cancelacion.strip()) < 3:
            return "❌ Error: Debe proporcionar un motivo de cancelación de al menos 3 caracteres"
        
        # Cancelar la cita
        cita_cancelada = cancel_appointment(cita_id, motivo_cancelacion.strip())
        
        if not cita_cancelada:
            return f"❌ Error: No se encontró la cita con ID {cita_id}"
        
        # Verificar que la cita pertenece al doctor
        if cita_cancelada.doctor_id != doctor.id:
            return f"❌ Error: La cita {cita_id} no pertenece a este doctor"
        
        # Obtener información del paciente
        paciente = get_patient_by_id(cita_cancelada.paciente_id)
        
        dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        nombre_dia = dias_semana[cita_cancelada.fecha_hora_inicio.weekday()]
        
        return f"""✅ **Cita cancelada exitosamente**

📋 **Detalles de la cita cancelada:**
🆔 ID Cita: {cita_cancelada.id}
👤 Paciente: {paciente.nombre_completo if paciente else 'Paciente no encontrado'}
📱 Teléfono: {paciente.telefono if paciente else 'N/A'}
📅 Fecha: {nombre_dia} {cita_cancelada.fecha_hora_inicio.strftime('%d/%m/%Y')}
🕐 Hora: {cita_cancelada.fecha_hora_inicio.strftime('%H:%M')} - {cita_cancelada.fecha_hora_fin.strftime('%H:%M')}
📊 Estado: Cancelada

🔄 **Motivo de cancelación:**
{motivo_cancelacion}

El horario ha sido liberado y está disponible para nuevas citas.
El evento se eliminará automáticamente de Google Calendar."""
        
    except Exception as e:
        return f"❌ Error al cancelar cita: {str(e)}"

# ===== HERRAMIENTA 7: CONFIRMAR CITA =====

@tool
def confirmar_cita_medica(
    doctor_phone: str,
    cita_id: int,
    notas_confirmacion: str = None
) -> str:
    """
    Confirma una cita médica programada.
    
    Args:
        doctor_phone: Número de teléfono del doctor
        cita_id: ID de la cita a confirmar
        notas_confirmacion: Notas adicionales de confirmación (opcional)
        
    Returns:
        Confirmación de la cita confirmada o mensaje de error
    """
    try:
        doctor = get_doctor_by_phone(doctor_phone)
        if not doctor:
            return f"❌ Error: Doctor con teléfono {doctor_phone} no está registrado"
        
        updates = {"estado": "confirmada"}
        if notas_confirmacion:
            updates["notas_privadas"] = notas_confirmacion.strip()
        
        cita = update_appointment(cita_id, updates)
        
        if not cita or cita.doctor_id != doctor.id:
            return f"❌ Error: Cita {cita_id} no encontrada o no pertenece a este doctor"
        
        paciente = get_patient_by_id(cita.paciente_id)
        
        return f"""✅ **Cita confirmada**

🆔 ID Cita: {cita.id}
👤 Paciente: {paciente.nombre_completo if paciente else 'N/A'}
📅 Fecha: {cita.fecha_hora_inicio.strftime('%d/%m/%Y %H:%M')}
📊 Estado: Confirmada
{f'📝 Notas: {notas_confirmacion}' if notas_confirmacion else ''}"""
        
    except Exception as e:
        return f"❌ Error al confirmar cita: {str(e)}"


# ===== HERRAMIENTA 8: REPROGRAMAR CITA =====

@tool
def reprogramar_cita_medica(
    doctor_phone: str,
    cita_id: int,
    nueva_fecha_hora: str,
    motivo_reprogramacion: str
) -> str:
    """
    Reprograma una cita médica a nueva fecha y hora.
    
    Args:
        doctor_phone: Número de teléfono del doctor
        cita_id: ID de la cita a reprogramar
        nueva_fecha_hora: Nueva fecha y hora "YYYY-MM-DD HH:MM"
        motivo_reprogramacion: Razón de la reprogramación
        
    Returns:
        Confirmación de reprogramación o mensaje de error
    """
    try:
        doctor = get_doctor_by_phone(doctor_phone)
        if not doctor:
            return f"❌ Error: Doctor no registrado"
        
        nuevo_inicio = datetime.strptime(nueva_fecha_hora, "%Y-%m-%d %H:%M")
        if nuevo_inicio <= datetime.now():
            return "❌ Error: La nueva fecha no puede ser en el pasado"
        
        nuevo_fin = nuevo_inicio + timedelta(minutes=30)
        
        if not check_doctor_availability(doctor.id, nuevo_inicio, nuevo_fin):
            return f"❌ Error: Doctor no disponible en {nueva_fecha_hora}"
        
        updates = {
            "fecha_hora_inicio": nuevo_inicio,
            "fecha_hora_fin": nuevo_fin,
            "notas_privadas": f"Reprogramada: {motivo_reprogramacion}"
        }
        
        cita = update_appointment(cita_id, updates)
        
        if not cita or cita.doctor_id != doctor.id:
            return f"❌ Error: Cita no encontrada"
        
        paciente = get_patient_by_id(cita.paciente_id)
        
        return f"""✅ **Cita reprogramada**

🆔 ID: {cita.id}
👤 Paciente: {paciente.nombre_completo if paciente else 'N/A'}
📅 Nueva fecha: {nuevo_inicio.strftime('%d/%m/%Y %H:%M')}
🔄 Motivo: {motivo_reprogramacion}"""
        
    except ValueError:
        return "❌ Error: Fecha en formato incorrecto"
    except Exception as e:
        return f"❌ Error: {str(e)}"


# ===== HERRAMIENTA 9: CONSULTAR HISTORIAL PACIENTE =====

@tool
def consultar_historial_paciente(
    doctor_phone: str,
    paciente_id: int,
    ultimas_n_notas: int = 10
) -> str:
    """
    Consulta el historial médico de un paciente.
    
    Args:
        doctor_phone: Número de teléfono del doctor
        paciente_id: ID del paciente
        ultimas_n_notas: Número de notas recientes a mostrar (default: 10)
        
    Returns:
        Historial médico del paciente
    """
    try:
        doctor = get_doctor_by_phone(doctor_phone)
        if not doctor:
            return "❌ Error: Doctor no registrado"
        
        paciente = get_patient_by_id(paciente_id)
        if not paciente or paciente.doctor_id != doctor.id:
            return "❌ Error: Paciente no encontrado o no pertenece a este doctor"
        
        # Importar aquí para evitar circular import
        from .crud import get_patient_history
        
        historiales = get_patient_history(paciente_id, limit=ultimas_n_notas)
        
        resultado = f"""📋 **Historial Médico - {paciente.nombre_completo}**
👤 ID Paciente: {paciente_id}
📱 Teléfono: {paciente.telefono}
⚠️ Alergias: {paciente.alergias or 'Ninguna'}

📝 **Últimas {len(historiales)} notas:**

"""
        
        if not historiales:
            resultado += "• Sin historial médico registrado\n"
        else:
            for i, hist in enumerate(historiales, 1):
                fecha = hist.fecha.strftime('%d/%m/%Y %H:%M') if hist.fecha else 'N/A'
                resultado += f"""**{i}. {fecha}**
{hist.nota}

---

"""
        
        return resultado.strip()
        
    except Exception as e:
        return f"❌ Error: {str(e)}"


# ===== HERRAMIENTA 10: AGREGAR NOTA A HISTORIAL =====

@tool
def agregar_nota_historial(
    doctor_phone: str,
    paciente_id: int,
    nota: str
) -> str:
    """
    Agrega una nota al historial médico del paciente.
    
    Args:
        doctor_phone: Número de teléfono del doctor
        paciente_id: ID del paciente
        nota: Nota médica a registrar
        
    Returns:
        Confirmación de nota agregada
    """
    try:
        doctor = get_doctor_by_phone(doctor_phone)
        if not doctor:
            return "❌ Error: Doctor no registrado"
        
        paciente = get_patient_by_id(paciente_id)
        if not paciente or paciente.doctor_id != doctor.id:
            return "❌ Error: Paciente no encontrado"
        
        if not nota or len(nota.strip()) < 5:
            return "❌ Error: La nota debe tener al menos 5 caracteres"
        
        # Importar aquí para evitar circular import
        from .crud import add_patient_history_note
        
        historial = add_patient_history_note(
            paciente_id=paciente_id,
            doctor_id=doctor.id,
            nota=nota.strip()
        )
        
        return f"""✅ **Nota agregada al historial**

👤 Paciente: {paciente.nombre_completo}
📅 Fecha: {historial.fecha.strftime('%d/%m/%Y %H:%M')}
📝 Nota registrada exitosamente

La nota ha sido guardada en el historial médico del paciente."""
        
    except Exception as e:
        return f"❌ Error: {str(e)}"


# ===== HERRAMIENTA 11: OBTENER CITAS DEL DOCTOR =====

@tool
def obtener_citas_doctor(
    doctor_phone: str,
    fecha_inicio: str = None,
    fecha_fin: str = None,
    estado: str = None
) -> str:
    """
    Obtiene las citas del doctor filtradas por fecha y/o estado.
    
    Args:
        doctor_phone: Número de teléfono del doctor
        fecha_inicio: Fecha inicio en formato "YYYY-MM-DD" (opcional, default: hoy)
        fecha_fin: Fecha fin en formato "YYYY-MM-DD" (opcional, default: 7 días)
        estado: Estado de citas a filtrar (opcional: programada, confirmada, etc.)
        
    Returns:
        Lista de citas del doctor
    """
    try:
        doctor = get_doctor_by_phone(doctor_phone)
        if not doctor:
            return "❌ Error: Doctor no registrado"
        
        # Defaults
        inicio = datetime.now().date()
        if fecha_inicio:
            try:
                inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
            except ValueError:
                return "❌ Error: fecha_inicio debe ser YYYY-MM-DD"
        
        fin = inicio + timedelta(days=7)
        if fecha_fin:
            try:
                fin = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
            except ValueError:
                return "❌ Error: fecha_fin debe ser YYYY-MM-DD"
        
        # Importar aquí
        from .crud import get_doctor_appointments
        
        citas = get_doctor_appointments(
            doctor_id=doctor.id,
            fecha_inicio=inicio,
            fecha_fin=fin,
            estado=estado
        )
        
        resultado = f"""📅 **Citas del Doctor**
📆 Periodo: {inicio.strftime('%d/%m/%Y')} - {fin.strftime('%d/%m/%Y')}
{f'📊 Estado: {estado}' if estado else ''}

"""
        
        if not citas:
            resultado += "• Sin citas en este periodo\n"
        else:
            for i, cita in enumerate(citas, 1):
                paciente = get_patient_by_id(cita.paciente_id)
                fecha = cita.fecha_hora_inicio.strftime('%d/%m/%Y %H:%M')
                resultado += f"""**{i}. {fecha}** - {cita.estado.title()}
👤 Paciente: {paciente.nombre_completo if paciente else 'N/A'}
📝 Motivo: {cita.motivo_consulta or 'No especificado'}

"""
        
        resultado += f"\n✅ Total: {len(citas)} citas"
        
        return resultado.strip()
        
    except Exception as e:
        return f"❌ Error: {str(e)}"


# ===== HERRAMIENTA 12: BUSCAR PACIENTE POR NOMBRE =====

@tool
def buscar_paciente_por_nombre(
    doctor_phone: str,
    nombre: str,
    incluir_inactivos: bool = False
) -> str:
    """
    Busca pacientes por nombre (búsqueda parcial).
    
    Args:
        doctor_phone: Número de teléfono del doctor
        nombre: Nombre o parte del nombre del paciente
        incluir_inactivos: Si incluir pacientes inactivos (default: False)
        
    Returns:
        Lista de pacientes que coinciden con el nombre
    """
    try:
        doctor = get_doctor_by_phone(doctor_phone)
        if not doctor:
            return "❌ Error: Doctor no registrado"
        
        if not nombre or len(nombre.strip()) < 2:
            return "❌ Error: El nombre debe tener al menos 2 caracteres"
        
        pacientes = search_patients(doctor.id, nombre.strip())
        
        if not pacientes:
            return f"""🔍 **No se encontraron pacientes**

Búsqueda: "{nombre}"
No hay pacientes que coincidan."""
        
        resultado = f"""🔍 **Pacientes encontrados ({len(pacientes)})**
Búsqueda: "{nombre}"

"""
        
        for i, p in enumerate(pacientes, 1):
            ultima_cita = "Sin citas" if not p.ultima_cita else p.ultima_cita.strftime('%d/%m/%Y')
            resultado += f"""**{i}. {p.nombre_completo}** (ID: {p.id})
📱 {p.telefono}
📧 {p.email or 'Sin email'}
📅 Última cita: {ultima_cita}
⚠️ Alergias: {p.alergias or 'Ninguna'}

---

"""
        
        return resultado.strip()
        
    except Exception as e:
        return f"❌ Error: {str(e)}"


# ===== LISTA DE HERRAMIENTAS PARA REGISTRO =====

MEDICAL_TOOLS = [
    crear_paciente_medico,
    buscar_pacientes_doctor, 
    consultar_slots_disponibles,
    agendar_cita_medica_completa,
    modificar_cita_medica,
    cancelar_cita_medica,
    confirmar_cita_medica,
    reprogramar_cita_medica,
    consultar_historial_paciente,
    agregar_nota_historial,
    obtener_citas_doctor,
    buscar_paciente_por_nombre
]

def get_medical_tools():
    """Retorna la lista de herramientas médicas para registro en LangGraph"""
    return MEDICAL_TOOLS