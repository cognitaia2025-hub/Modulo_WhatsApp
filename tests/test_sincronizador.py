"""
Tests para Nodo N8: Sincronizador Híbrido

✅ Command pattern
✅ Detección de cambios
✅ Sincronización bidireccional
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock
from langgraph.types import Command

# Import directly from module file to avoid __init__.py circular imports
sys.path.insert(0, str(Path(__file__).parent.parent))


@patch('src.nodes.sincronizador_hibrido_node.list_events_tool')
@patch('src.nodes.sincronizador_hibrido_node.psycopg.connect')
def test_retorna_command(mock_conn, mock_calendar):
    """Nodo retorna Command."""
    from src.nodes.sincronizador_hibrido_node import nodo_sincronizador_hibrido
    
    # Mock calendar events
    mock_calendar.invoke.return_value = []
    
    # Mock database connection
    mock_cursor = Mock()
    mock_cursor.fetchall.return_value = []
    mock_cursor.__enter__ = Mock(return_value=mock_cursor)
    mock_cursor.__exit__ = Mock(return_value=False)
    
    mock_conn_instance = Mock()
    mock_conn_instance.cursor.return_value = mock_cursor
    mock_conn_instance.__enter__ = Mock(return_value=mock_conn_instance)
    mock_conn_instance.__exit__ = Mock(return_value=False)
    mock_conn.return_value = mock_conn_instance
    
    estado = {
        'user_id': 'test_user',
        'tipo_sincronizacion': 'post_agendamiento'
    }
    
    resultado = nodo_sincronizador_hibrido(estado)
    
    assert isinstance(resultado, Command)
    assert resultado.goto == "generacion_resumen"
    assert 'sincronizacion_exitosa' in resultado.update


def test_detectar_cambios_encuentra_nuevas():
    """Detecta eventos nuevos en Calendar."""
    from src.nodes.sincronizador_hibrido_node import detectar_cambios_sincronizacion
    
    eventos = [{'id': 'ev1', 'start': '2025-02-10T10:00:00'}]
    citas = []
    
    cambios = detectar_cambios_sincronizacion(eventos, citas)
    
    assert len(cambios['nuevas']) == 1
    assert cambios['nuevas'][0]['id'] == 'ev1'


def test_detectar_cambios_encuentra_modificadas():
    """Detecta eventos modificados."""
    from src.nodes.sincronizador_hibrido_node import detectar_cambios_sincronizacion
    from datetime import datetime
    
    eventos = [{'id': 'ev1', 'start': '2025-02-10T11:00:00'}]
    
    # Mock fecha_hora como datetime
    mock_fecha = Mock()
    mock_fecha.isoformat.return_value = '2025-02-10T10:00:00'
    
    citas = [{
        'id': 1,
        'event_id_calendar': 'ev1',
        'fecha_hora': mock_fecha
    }]
    
    cambios = detectar_cambios_sincronizacion(eventos, citas)
    
    assert len(cambios['modificadas']) == 1
    assert cambios['modificadas'][0]['id'] == 'ev1'


def test_detectar_cambios_encuentra_eliminadas():
    """Detecta eventos eliminados de Calendar."""
    from src.nodes.sincronizador_hibrido_node import detectar_cambios_sincronizacion
    from datetime import datetime
    
    eventos = []
    
    mock_fecha = Mock()
    mock_fecha.isoformat.return_value = '2025-02-10T10:00:00'
    
    citas = [{
        'id': 1,
        'event_id_calendar': 'ev1',
        'fecha_hora': mock_fecha
    }]
    
    cambios = detectar_cambios_sincronizacion(eventos, citas)
    
    assert len(cambios['eliminadas']) == 1
    assert cambios['eliminadas'][0] == 1


@patch('src.nodes.sincronizador_hibrido_node.list_events_tool')
@patch('src.nodes.sincronizador_hibrido_node.psycopg.connect')
def test_maneja_errores_con_command(mock_conn, mock_calendar):
    """Maneja errores y retorna Command con error."""
    from src.nodes.sincronizador_hibrido_node import nodo_sincronizador_hibrido
    
    # Simular error en calendar
    mock_calendar.invoke.side_effect = Exception("Calendar API Error")
    
    estado = {
        'user_id': 'test_user',
        'tipo_sincronizacion': 'post_agendamiento'
    }
    
    resultado = nodo_sincronizador_hibrido(estado)
    
    assert isinstance(resultado, Command)
    assert resultado.goto == "generacion_resumen"
    assert 'sincronizacion_exitosa' in resultado.update
    assert resultado.update['sincronizacion_exitosa'] == False
    assert 'error_sincronizacion' in resultado.update


def test_wrapper_retorna_command():
    """Wrapper retorna Command directamente."""
    from src.nodes.sincronizador_hibrido_node import nodo_sincronizador_hibrido_wrapper
    
    with patch('src.nodes.sincronizador_hibrido_node.nodo_sincronizador_hibrido') as mock_nodo:
        mock_command = Command(
            update={'sincronizacion_exitosa': True},
            goto="generacion_resumen"
        )
        mock_nodo.return_value = mock_command
        
        estado = {'user_id': 'test'}
        resultado = nodo_sincronizador_hibrido_wrapper(estado)
        
        assert isinstance(resultado, Command)
        assert resultado.goto == "generacion_resumen"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
