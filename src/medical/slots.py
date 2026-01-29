"""
Generación de Slots de Disponibilidad con Sistema de Turnos

Genera horarios disponibles aplicando alternancia automática entre doctores.
NO revela el doctor asignado hasta la confirmación de la cita.
"""

import os
import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta, time

import pytz
from dotenv import load_dotenv

from src.medical.turnos import obtener_siguiente_doctor_turno, obtener_otro_doctor
from src.medical.disponibilidad import check_doctor_availability, validar_horario_clinica

load_dotenv()

TIMEZONE = pytz.timezone("America/Tijuana")
logger = logging.getLogger(__name__)

# Configuración de slots
DURACION_SLOT_HORAS = 1  # Slots de 1 hora
HORA_INICIO_CLINICA = time(8, 30)  # 8:30 AM
HORA_FIN_CLINICA = time(18, 30)  # 6:30 PM
DIAS_ATENCION = [0, 3, 4, 5, 6]  # Lunes, Jueves, Viernes, Sábado, Domingo


def generar_slots_con_turnos(
    dias_adelante: int = 7,
    incluir_doctor_interno: bool = True
) -> List[Dict[str, Any]]:
    """
    Genera slots de disponibilidad aplicando sistema de turnos rotativos.
    
    Algoritmo:
    1. Para cada día (hoy + dias_adelante):
       - Verificar si es día de atención
       - Generar slots de 1 hora dentro del horario
    
    2. Para cada slot:
       - Determinar doctor por turno
       - Verificar disponibilidad del doctor del turno
       - Si ocupado → intentar con el otro doctor
       - Si ambos ocupados → skip slot
    
    3. Agregar slot a resultado SIN revelar doctor (a menos que incluir_doctor_interno=True)
    
    Args:
        dias_adelante: Número de días hacia adelante a generar
        incluir_doctor_interno: Si True, incluye doctor_id (solo para backend)
    
    Returns:
        Lista de slots disponibles:
        [
            {
                "fecha": "2026-01-30",
                "hora_inicio": "08:30",
                "hora_fin": "09:30",
                "slot_id": "2026-01-30T08:30",
                "disponible": True,
                
                # Solo si incluir_doctor_interno=True:
                "doctor_asignado_id": 1,
                "turno_numero": 1
            }
        ]
    
    IMPORTANTE: El campo doctor_asignado_id NO debe exponerse al frontend.
    """
    slots_disponibles = []
    ahora = datetime.now(TIMEZONE)
    
    logger.info(f"🔍 Generando slots para próximos {dias_adelante} días...")
    
    # Contador de turnos para simular alternancia (sin modificar BD)
    turno_contador = 0
    
    # Generar slots desde hoy hasta dias_adelante (inclusivo)
    for dia_offset in range(dias_adelante + 1):
        fecha = ahora + timedelta(days=dia_offset)
        dia_semana = fecha.weekday()
        
        # Filtrar días no laborables
        if dia_semana not in DIAS_ATENCION:
            continue
        
        # Generar slots para ese día
        hora_actual = HORA_INICIO_CLINICA
        
        while hora_actual < HORA_FIN_CLINICA:
            # Crear datetime para el slot
            fecha_slot = fecha.replace(
                hour=hora_actual.hour,
                minute=hora_actual.minute,
                second=0,
                microsecond=0
            )
            
            # Solo slots futuros
            if fecha_slot <= ahora:
                hora_actual = (datetime.combine(datetime.today(), hora_actual) + 
                              timedelta(hours=DURACION_SLOT_HORAS)).time()
                continue
            
            hora_fin_slot = (datetime.combine(datetime.today(), hora_actual) + 
                           timedelta(hours=DURACION_SLOT_HORAS)).time()
            
            fecha_fin_slot = fecha_slot.replace(
                hour=hora_fin_slot.hour,
                minute=hora_fin_slot.minute
            )
            
            # Determinar doctor por turno (alternar sin consultar BD cada vez)
            try:
                # Obtener doctor del turno actual
                doctor_turno = obtener_siguiente_doctor_turno()
                doctor_id = doctor_turno["doctor_id"]
                
                # Simular alternancia para este cálculo
                if turno_contador % 2 == 0:
                    doctor_id = 1  # Santiago
                else:
                    doctor_id = 2  # Joana
                
                turno_contador += 1
                
                # Verificar disponibilidad del doctor del turno
                disponibilidad = check_doctor_availability(
                    doctor_id,
                    fecha_slot,
                    fecha_fin_slot
                )
                
                doctor_asignado = doctor_id
                
                # Si el doctor del turno está ocupado, intentar con el otro
                if not disponibilidad["disponible"]:
                    otro_doctor = obtener_otro_doctor(doctor_id)
                    
                    if otro_doctor:
                        disponibilidad_otro = check_doctor_availability(
                            otro_doctor["doctor_id"],
                            fecha_slot,
                            fecha_fin_slot
                        )
                        
                        if disponibilidad_otro["disponible"]:
                            doctor_asignado = otro_doctor["doctor_id"]
                            disponibilidad = disponibilidad_otro
                            logger.debug(f"🔄 Reasignado: Doctor {doctor_id} → {doctor_asignado}")
                
                # Si hay disponibilidad, agregar slot
                if disponibilidad["disponible"]:
                    slot = {
                        "fecha": fecha_slot.strftime("%Y-%m-%d"),
                        "hora_inicio": hora_actual.strftime("%H:%M"),
                        "hora_fin": hora_fin_slot.strftime("%H:%M"),
                        "slot_id": fecha_slot.strftime("%Y-%m-%dT%H:%M"),
                        "disponible": True
                    }
                    
                    # Solo incluir doctor_id si es para uso interno
                    if incluir_doctor_interno:
                        slot["doctor_asignado_id"] = doctor_asignado
                        slot["turno_numero"] = turno_contador
                    
                    slots_disponibles.append(slot)
                
            except Exception as e:
                logger.error(f"❌ Error procesando slot {fecha_slot}: {e}")
            
            # Avanzar a siguiente hora
            hora_actual = hora_fin_slot
    
    logger.info(f"✅ {len(slots_disponibles)} slots disponibles generados")
    return slots_disponibles


def generar_slots_doctor(
    doctor_id: int,
    dias_adelante: int = 7
) -> List[Dict[str, Any]]:
    """
    Genera slots disponibles para un doctor específico.
    
    Útil para consultas administrativas o cuando se quiere ver
    disponibilidad de un doctor particular.
    
    Args:
        doctor_id: ID del doctor
        dias_adelante: Días hacia adelante
    
    Returns:
        Lista de slots del doctor
    """
    slots = []
    ahora = datetime.now(TIMEZONE)
    
    # Generar slots desde hoy hasta dias_adelante (inclusivo)
    for dia_offset in range(dias_adelante + 1):
        fecha = ahora + timedelta(days=dia_offset)
        dia_semana = fecha.weekday()
        
        if dia_semana not in DIAS_ATENCION:
            continue
        
        hora_actual = HORA_INICIO_CLINICA
        
        while hora_actual < HORA_FIN_CLINICA:
            fecha_slot = fecha.replace(
                hour=hora_actual.hour,
                minute=hora_actual.minute,
                second=0,
                microsecond=0
            )
            
            if fecha_slot <= ahora:
                hora_actual = (datetime.combine(datetime.today(), hora_actual) + 
                              timedelta(hours=DURACION_SLOT_HORAS)).time()
                continue
            
            hora_fin_slot = (datetime.combine(datetime.today(), hora_actual) + 
                           timedelta(hours=DURACION_SLOT_HORAS)).time()
            
            fecha_fin_slot = fecha_slot.replace(
                hour=hora_fin_slot.hour,
                minute=hora_fin_slot.minute
            )
            
            # Verificar disponibilidad
            disponibilidad = check_doctor_availability(
                doctor_id,
                fecha_slot,
                fecha_fin_slot
            )
            
            if disponibilidad["disponible"]:
                slots.append({
                    "fecha": fecha_slot.strftime("%Y-%m-%d"),
                    "hora_inicio": hora_actual.strftime("%H:%M"),
                    "hora_fin": hora_fin_slot.strftime("%H:%M"),
                    "slot_id": fecha_slot.strftime("%Y-%m-%dT%H:%M"),
                    "doctor_id": doctor_id,
                    "disponible": True
                })
            
            hora_actual = hora_fin_slot
    
    return slots


def formatear_slots_para_frontend(slots: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Formatea slots para exponerlos al frontend.
    
    IMPORTANTE: Elimina información sensible como doctor_asignado_id.
    
    Args:
        slots: Lista de slots con información completa
    
    Returns:
        Lista de slots sin información del doctor
    """
    slots_publicos = []
    
    for slot in slots:
        slot_publico = {
            "fecha": slot["fecha"],
            "hora_inicio": slot["hora_inicio"],
            "hora_fin": slot["hora_fin"],
            "slot_id": slot["slot_id"],
            "disponible": slot["disponible"]
        }
        
        # NO incluir: doctor_asignado_id, turno_numero
        slots_publicos.append(slot_publico)
    
    return slots_publicos


def agrupar_slots_por_dia(slots: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Agrupa slots por día para mejor presentación.
    
    Args:
        slots: Lista de slots
    
    Returns:
        {
            "2026-01-30": [slots del día],
            "2026-01-31": [slots del día]
        }
    """
    agrupados = {}
    
    for slot in slots:
        fecha = slot["fecha"]
        if fecha not in agrupados:
            agrupados[fecha] = []
        agrupados[fecha].append(slot)
    
    return agrupados
