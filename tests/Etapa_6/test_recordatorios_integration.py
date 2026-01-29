"""Tests de Integración - Recordatorios"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, Mock, MagicMock
import time

from src.background.recordatorios_scheduler import enviar_recordatorios, run_scheduler


# Mock classes simples para los tests
class MockPaciente:
    def __init__(self, id, nombre_completo, telefono):
        self.id = id
        self.nombre_completo = nombre_completo
        self.telefono = telefono

class MockDoctor:
    def __init__(self, id, nombre_completo):
        self.id = id
        self.nombre_completo = nombre_completo

class MockCita:
    def __init__(self, id, paciente_id, doctor_id, fecha_hora_inicio, fecha_hora_fin, estado, 
                 recordatorio_enviado=False, recordatorio_intentos=0):
        self.id = id
        self.paciente_id = paciente_id
        self.doctor_id = doctor_id
        self.fecha_hora_inicio = fecha_hora_inicio
        self.fecha_hora_fin = fecha_hora_fin
        self.estado = estado
        self.recordatorio_enviado = recordatorio_enviado
        self.recordatorio_intentos = recordatorio_intentos
        self.recordatorio_fecha_envio = None


@patch('src.background.recordatorios_scheduler.enviar_whatsapp')
@patch('src.background.recordatorios_scheduler.get_db_session')
def test_flujo_completo_recordatorio(mock_db_session, mock_enviar_whatsapp):
    """Test: Flujo completo de envío de recordatorio"""
    ahora = datetime.now()
    
    # Crear objetos mock
    paciente = MockPaciente(1, "Juan Pérez", "+525512345678")
    doctor = MockDoctor(1, "Dr. Santiago Ornelas")
    cita = MockCita(
        id=1,
        paciente_id=1,
        doctor_id=1,
        fecha_hora_inicio=ahora + timedelta(hours=23.5),
        fecha_hora_fin=ahora + timedelta(hours=24.5),
        estado='programada',
        recordatorio_enviado=False,
        recordatorio_intentos=0
    )
    
    # Mock de la sesión de base de datos
    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_filter = MagicMock()
    
    # Configurar la cadena de llamadas
    mock_db.query.return_value = mock_query
    mock_query.filter.return_value = mock_filter
    mock_filter.all.return_value = [cita]
    mock_db.query.return_value.get.side_effect = lambda id: paciente if id == 1 else doctor
    
    mock_db_session.return_value.__enter__.return_value = mock_db
    mock_enviar_whatsapp.return_value = {'exito': True}
    
    # Ejecutar
    resultado = enviar_recordatorios()
    
    # Verificar resultado
    assert resultado['enviados'] == 1
    assert resultado['errores'] == 0
    
    # Verificar cita actualizada
    assert cita.recordatorio_enviado == True
    assert cita.recordatorio_intentos == 1
    assert cita.recordatorio_fecha_envio is not None
    
    # Verificar que se llamó a enviar_whatsapp
    mock_enviar_whatsapp.assert_called_once()
    call_args = mock_enviar_whatsapp.call_args[0]
    assert call_args[0] == '+525512345678'
    assert 'Juan Pérez' in call_args[1]


@patch('src.background.recordatorios_scheduler.enviar_whatsapp')
@patch('src.background.recordatorios_scheduler.get_db_session')
def test_no_duplica_recordatorios(mock_db_session, mock_enviar_whatsapp):
    """Test: No duplica recordatorios enviados"""
    ahora = datetime.now()
    
    # Crear objetos mock
    paciente = MockPaciente(1, "Juan Pérez", "+525512345678")
    doctor = MockDoctor(1, "Dr. Santiago Ornelas")
    cita = MockCita(
        id=1,
        paciente_id=1,
        doctor_id=1,
        fecha_hora_inicio=ahora + timedelta(hours=23.5),
        fecha_hora_fin=ahora + timedelta(hours=24.5),
        estado='programada',
        recordatorio_enviado=False,
        recordatorio_intentos=0
    )
    
    # Mock de la sesión de base de datos
    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_filter = MagicMock()
    
    # Primera ejecución: retorna la cita
    mock_db.query.return_value = mock_query
    mock_query.filter.return_value = mock_filter
    mock_filter.all.return_value = [cita]
    mock_db.query.return_value.get.side_effect = lambda id: paciente if id == 1 else doctor
    
    mock_db_session.return_value.__enter__.return_value = mock_db
    mock_enviar_whatsapp.return_value = {'exito': True}
    
    # Primera ejecución
    resultado1 = enviar_recordatorios()
    assert resultado1['enviados'] == 1
    
    # Segunda ejecución: ya no retorna la cita (porque está marcada como enviada)
    mock_filter.all.return_value = []
    
    resultado2 = enviar_recordatorios()
    assert resultado2['enviados'] == 0
    
    # Verificar que solo se llamó una vez en total
    assert mock_enviar_whatsapp.call_count == 1


@patch('schedule.run_pending')
@patch('time.sleep')
def test_scheduler_corre_en_background(mock_sleep, mock_run_pending):
    """Test: Scheduler puede correr en background"""
    # Configurar mock para que solo corra una iteración
    mock_sleep.side_effect = KeyboardInterrupt("Test complete")
    
    # Intentar ejecutar scheduler
    try:
        run_scheduler()
    except KeyboardInterrupt:
        pass
    
    # Verificar que se llamó a run_pending
    assert mock_run_pending.called
    
    # Verificar que intenta dormir (loop infinito)
    assert mock_sleep.called
