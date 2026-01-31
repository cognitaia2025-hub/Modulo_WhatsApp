"""
Herramientas (tools) para los agentes.

Todas las tools usan Pydantic validation para asegurar formato correcto
antes de ejecutar, reduciendo errores del LLM.
"""

from .agendamiento_tools import (
    agendar_cita_paciente,
    reagendar_cita,
    cancelar_cita
)

from .models import (
    FechaCita,
    HoraCita,
    DatosPaciente,
    TelefonoPaciente
)

__all__ = [
    'agendar_cita_paciente',
    'reagendar_cita',
    'cancelar_cita',
    'FechaCita',
    'HoraCita',
    'DatosPaciente',
    'TelefonoPaciente'
]
