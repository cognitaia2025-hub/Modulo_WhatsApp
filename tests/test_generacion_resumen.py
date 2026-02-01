"""
Tests para Nodo N6: Generación de Resumen

✅ Command pattern
✅ Estado conversacional
✅ Timeout reducido
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, Mock
from langgraph.types import Command

# Import directly from module file to avoid __init__.py circular imports
sys.path.insert(0, str(Path(__file__).parent.parent))

@patch('src.nodes.generacion_resumen_node.llm_auditor')
def test_retorna_command(mock_llm):
    """Nodo retorna Command."""
    from src.nodes.generacion_resumen_node import nodo_generacion_resumen
    
    mock_llm.invoke.return_value.content = "Test resumen"
    mock_store = Mock()
    
    estado = {
        'messages': [
            {'role': 'user', 'content': 'Test mensaje'},
            {'role': 'ai', 'content': 'Respuesta test'}
        ],
        'user_id': 'test_user',
        'estado_conversacion': 'inicial'
    }
    
    resultado = nodo_generacion_resumen(estado, mock_store)
    
    assert isinstance(resultado, Command)
    assert resultado.goto == "persistencia_episodica"
    assert 'resumen_actual' in resultado.update

def test_detecta_estado_sin_resumen():
    """Salta generación si estado no requiere resumen."""
    from src.nodes.generacion_resumen_node import nodo_generacion_resumen
    
    mock_store = Mock()
    
    estado = {
        'messages': [
            {'role': 'user', 'content': 'Test'},
            {'role': 'ai', 'content': 'Test'}
        ],
        'user_id': 'test_user',
        'estado_conversacion': 'esperando_confirmacion'
    }
    
    resultado = nodo_generacion_resumen(estado, mock_store)
    
    assert isinstance(resultado, Command)
    assert resultado.goto == "persistencia_episodica"
    assert resultado.update['resumen_actual'] == "Conversación en progreso"

@pytest.mark.parametrize("estado", [
    'esperando_confirmacion',
    'recolectando_datos',
    'procesando_pago'
])
def test_detecta_todos_estados_sin_resumen(estado):
    """Detecta todos los estados que no requieren resumen."""
    from src.nodes.generacion_resumen_node import nodo_generacion_resumen
    
    mock_store = Mock()
    
    state = {
        'messages': [
            {'role': 'user', 'content': 'Test'},
            {'role': 'ai', 'content': 'Test'}
        ],
        'user_id': 'test_user',
        'estado_conversacion': estado
    }
    
    resultado = nodo_generacion_resumen(state, mock_store)
    
    assert isinstance(resultado, Command)
    assert resultado.update['resumen_actual'] == "Conversación en progreso"

def test_timeout_reducido():
    """Timeout de LLMs es 10s."""
    from src.nodes.generacion_resumen_node import llm_primary, llm_fallback
    
    assert llm_primary.request_timeout == 10.0
    assert llm_fallback.default_request_timeout == 10.0
