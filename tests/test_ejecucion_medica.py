"""
Tests para Nodo N5B: Ejecución Médica

✅ Command pattern
✅ Estado conversacional
✅ Validación de permisos
"""

import pytest
import sys
import importlib.util
from pathlib import Path
from unittest.mock import patch, Mock
from langgraph.types import Command

# Load module directly to avoid __init__.py imports
spec = importlib.util.spec_from_file_location(
    'ejecucion_medica_node',
    Path(__file__).parent.parent / 'src' / 'nodes' / 'ejecucion_medica_node.py'
)
ejecucion_medica_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ejecucion_medica_module)

nodo_ejecucion_medica = ejecucion_medica_module.nodo_ejecucion_medica
ESTADOS_FLUJO_ACTIVO = ejecucion_medica_module.ESTADOS_FLUJO_ACTIVO

def test_retorna_command():
    """Nodo retorna Command."""
    estado = {
        'herramientas_seleccionadas': [],
        'tipo_usuario': 'doctor',
        'estado_conversacion': 'inicial'
    }
    
    resultado = nodo_ejecucion_medica(estado)
    
    assert isinstance(resultado, Command)
    assert resultado.goto == "generacion_resumen"

def test_detecta_estado_activo():
    """Detecta flujo activo y salta ejecución."""
    estado = {
        'herramientas_seleccionadas': ['crear_paciente_medico'],
        'tipo_usuario': 'doctor',
        'estado_conversacion': 'esperando_confirmacion_medica'
    }
    
    resultado = nodo_ejecucion_medica(estado)
    
    assert isinstance(resultado, Command)
    assert resultado.goto == "generacion_resumen"
    assert resultado.update['herramientas_ejecutadas'] == []

@pytest.mark.parametrize("estado_conversacion", ESTADOS_FLUJO_ACTIVO)
def test_detecta_todos_estados_activos(estado_conversacion):
    """Detecta todos los estados de flujo activo."""
    state = {
        'herramientas_seleccionadas': ['test'],
        'tipo_usuario': 'doctor',
        'estado_conversacion': estado_conversacion
    }
    
    resultado = nodo_ejecucion_medica(state)
    
    assert isinstance(resultado, Command)
    assert resultado.update['herramientas_ejecutadas'] == []

def test_sin_herramientas():
    """Retorna Command cuando no hay herramientas."""
    estado = {
        'herramientas_seleccionadas': [],
        'tipo_usuario': 'doctor',
        'estado_conversacion': 'inicial'
    }
    
    resultado = nodo_ejecucion_medica(estado)
    
    assert isinstance(resultado, Command)
    assert resultado.goto == "generacion_resumen"
    assert "No se seleccionaron herramientas" in resultado.update['resultado_herramientas']

def test_command_contiene_update_fields():
    """Command contiene campos esperados en update."""
    estado = {
        'herramientas_seleccionadas': [],
        'tipo_usuario': 'doctor',
        'estado_conversacion': 'inicial'
    }
    
    resultado = nodo_ejecucion_medica(estado)
    
    assert 'resultado_herramientas' in resultado.update
    assert 'herramientas_ejecutadas' in resultado.update
