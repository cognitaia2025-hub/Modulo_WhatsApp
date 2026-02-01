"""
Tests para Nodo N9: Recordatorios

✅ Command pattern
✅ Detección de citas próximas
✅ Envío de mensajes
"""

import pytest
from unittest.mock import patch, Mock, MagicMock
from datetime import datetime, timedelta
import sys
import os
import importlib.util

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import Command directly
from langgraph.types import Command

# Load recordatorios_node directly to avoid __init__.py chain
spec = importlib.util.spec_from_file_location(
    'recordatorios_node',
    os.path.join(project_root, 'src/nodes/recordatorios_node.py')
)
recordatorios_node = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recordatorios_node)

# Extract functions
nodo_recordatorios = recordatorios_node.nodo_recordatorios
nodo_recordatorios_wrapper = recordatorios_node.nodo_recordatorios_wrapper
enviar_whatsapp = recordatorios_node.enviar_whatsapp


# ==================== FIXTURES ====================

@pytest.fixture
def mock_cursor():
    """Mock cursor for psycopg3"""
    cursor = Mock()
    cursor.fetchall.return_value = []
    cursor.execute = Mock()
    cursor.__enter__ = Mock(return_value=cursor)
    cursor.__exit__ = Mock(return_value=False)
    return cursor


@pytest.fixture
def mock_connection(mock_cursor):
    """Mock database connection"""
    conn = Mock()
    conn.cursor.return_value = mock_cursor
    conn.commit = Mock()
    conn.__enter__ = Mock(return_value=conn)
    conn.__exit__ = Mock(return_value=False)
    return conn


@pytest.fixture
def mock_pendulum_now():
    """Mock get_current_time to return a fixed datetime"""
    mock_time = Mock()
    mock_time.add = Mock(side_effect=lambda hours: mock_time)
    mock_time.to_datetime_string = Mock(return_value='2026-02-01 10:00:00')
    return mock_time


# ==================== TESTS ====================

@patch.object(recordatorios_node, 'psycopg')
@patch.object(recordatorios_node, 'enviar_whatsapp')
@patch.object(recordatorios_node, 'get_current_time')
def test_retorna_command(mock_time, mock_whatsapp, mock_psycopg, mock_connection, mock_cursor, mock_pendulum_now):
    """Nodo retorna Command."""
    # Setup mocks
    mock_time.return_value = mock_pendulum_now
    mock_whatsapp.return_value = True
    mock_cursor.fetchall.return_value = []
    mock_psycopg.connect.return_value = mock_connection
    
    estado = {
        'tipo_ejecucion': 'scheduler'
    }
    
    resultado = nodo_recordatorios(estado)
    
    assert isinstance(resultado, Command)
    assert resultado.goto == "END"
    assert 'recordatorios_enviados' in resultado.update
    assert 'recordatorios_24h' in resultado.update
    assert 'recordatorios_2h' in resultado.update


@patch.object(recordatorios_node, 'psycopg')
@patch.object(recordatorios_node, 'enviar_whatsapp')
@patch.object(recordatorios_node, 'get_current_time')
def test_envia_recordatorio_24h(mock_time, mock_whatsapp, mock_psycopg, mock_connection, mock_cursor, mock_pendulum_now):
    """Envía recordatorio 24h antes."""
    # Setup mocks
    mock_time.return_value = mock_pendulum_now
    mock_whatsapp.return_value = True
    
    # Simular cita en 24h
    fecha_cita = datetime.now() + timedelta(hours=24)
    
    cita_mock = {
        'id': 1,
        'fecha_hora': fecha_cita,
        'paciente_phone': '+526641234567',
        'paciente_nombre': 'Test Paciente',
        'doctor_nombre': 'García',
        'ubicacion_consultorio': 'Consultorio 1',
        'recordatorio_24h_enviado': False,
        'recordatorio_2h_enviado': False
    }
    
    # First call returns 24h citas, second call returns empty for 2h
    mock_cursor.fetchall.side_effect = [
        [cita_mock],  # Citas 24h
        []  # Citas 2h
    ]
    mock_psycopg.connect.return_value = mock_connection
    
    resultado = nodo_recordatorios({'tipo_ejecucion': 'scheduler'})
    
    assert resultado.update['recordatorios_24h'] >= 1
    assert mock_whatsapp.called


@patch.object(recordatorios_node, 'psycopg')
@patch.object(recordatorios_node, 'get_current_time')
def test_sin_citas_proximas(mock_time, mock_psycopg, mock_connection, mock_cursor, mock_pendulum_now):
    """Retorna correctamente cuando no hay citas próximas."""
    # Setup mocks
    mock_time.return_value = mock_pendulum_now
    mock_cursor.fetchall.return_value = []
    mock_psycopg.connect.return_value = mock_connection
    
    resultado = nodo_recordatorios({'tipo_ejecucion': 'scheduler'})
    
    assert isinstance(resultado, Command)
    assert resultado.update['recordatorios_enviados'] == 0
    assert resultado.update['recordatorios_24h'] == 0
    assert resultado.update['recordatorios_2h'] == 0


def test_wrapper_retorna_command():
    """Wrapper retorna Command directamente."""
    with patch.object(recordatorios_node, 'nodo_recordatorios') as mock_nodo:
        mock_command = Command(update={}, goto="END")
        mock_nodo.return_value = mock_command
        
        resultado = nodo_recordatorios_wrapper({'tipo_ejecucion': 'scheduler'})
        
        assert isinstance(resultado, Command)
        assert mock_nodo.called


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
