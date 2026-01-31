"""
Modelos Pydantic para validación de herramientas.

Estos modelos aseguran que el LLM pase datos en formato correcto
ANTES de ejecutar las tools, reduciendo reintentos y errores.
"""

from .fecha_models import FechaCita, HoraCita, FechaRango
from .paciente_models import DatosPaciente, TelefonoPaciente

__all__ = [
    'FechaCita',
    'HoraCita', 
    'FechaRango',
    'DatosPaciente',
    'TelefonoPaciente'
]
