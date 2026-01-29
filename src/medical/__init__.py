"""
Módulo Médico - Sistema de Gestión de Citas y Turnos

Componentes:
- turnos: Sistema de turnos rotativos entre doctores
- disponibilidad: Validación de horarios y conflictos
- slots: Generación de horarios disponibles
"""

from src.medical.turnos import (
    obtener_siguiente_doctor_turno,
    actualizar_control_turnos,
    obtener_estadisticas_turnos,
    obtener_otro_doctor
)

from src.medical.disponibilidad import (
    check_doctor_availability,
    validar_horario_clinica,
    obtener_horarios_doctor
)

from src.medical.slots import (
    generar_slots_con_turnos,
    generar_slots_doctor,
    formatear_slots_para_frontend,
    agrupar_slots_por_dia
)

__all__ = [
    # Turnos
    "obtener_siguiente_doctor_turno",
    "actualizar_control_turnos",
    "obtener_estadisticas_turnos",
    "obtener_otro_doctor",
    
    # Disponibilidad
    "check_doctor_availability",
    "validar_horario_clinica",
    "obtener_horarios_doctor",
    
    # Slots
    "generar_slots_con_turnos",
    "generar_slots_doctor",
    "formatear_slots_para_frontend",
    "agrupar_slots_por_dia",
]
