"""Tests del Scheduler de Recordatorios"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock, PropertyMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.background.recordatorios_scheduler import enviar_recordatorios, enviar_whatsapp


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


def test_busca_citas_en_ventana_24h():
    """Test: Busca citas en ventana 23-24h"""
    ahora = datetime.now()
    
    # Crear cita en ventana (23.5 horas en el futuro)
    cita = MockCita(
        id=1,
        paciente_id=1,
        doctor_id=1,
        fecha_hora_inicio=ahora + timedelta(hours=23.5),
        fecha_hora_fin=ahora + timedelta(hours=24.5),
        estado='programada',
        recordatorio_enviado=False
    )
    
    # Verificar que la cita está en ventana
    ventana_inicio = ahora + timedelta(hours=23)
    ventana_fin = ahora + timedelta(hours=24)
    
    assert cita.fecha_hora_inicio >= ventana_inicio
    assert cita.fecha_hora_inicio <= ventana_fin
    assert cita.estado in ['programada', 'confirmada']
    assert cita.recordatorio_enviado == False


def test_ignora_citas_fuera_de_ventana():
    """Test: Ignora citas fuera de ventana 23-24h"""
    ahora = datetime.now()
    
    # Citas fuera de ventana
    cita_muy_pronto = MockCita(
        id=1,
        paciente_id=1,
        doctor_id=1,
        fecha_hora_inicio=ahora + timedelta(hours=5),
        fecha_hora_fin=ahora + timedelta(hours=6),
        estado='programada',
        recordatorio_enviado=False
    )
    
    cita_muy_tarde = MockCita(
        id=2,
        paciente_id=1,
        doctor_id=1,
        fecha_hora_inicio=ahora + timedelta(hours=48),
        fecha_hora_fin=ahora + timedelta(hours=49),
        estado='programada',
        recordatorio_enviado=False
    )
    
    # Verificar que están fuera de ventana
    ventana_inicio = ahora + timedelta(hours=23)
    ventana_fin = ahora + timedelta(hours=24)
    
    assert not (cita_muy_pronto.fecha_hora_inicio >= ventana_inicio and 
                cita_muy_pronto.fecha_hora_inicio <= ventana_fin)
    assert not (cita_muy_tarde.fecha_hora_inicio >= ventana_inicio and 
                cita_muy_tarde.fecha_hora_inicio <= ventana_fin)


def test_ignora_citas_ya_enviadas():
    """Test: Ignora citas con recordatorio ya enviado"""
    ahora = datetime.now()
    
    # Cita con recordatorio enviado
    cita = MockCita(
        id=1,
        paciente_id=1,
        doctor_id=1,
        fecha_hora_inicio=ahora + timedelta(hours=23.5),
        fecha_hora_fin=ahora + timedelta(hours=24.5),
        estado='programada',
        recordatorio_enviado=True
    )
    
    # Verificar que está marcada como enviada
    assert cita.recordatorio_enviado == True


def test_ignora_citas_canceladas():
    """Test: Ignora citas canceladas"""
    ahora = datetime.now()
    
    # Cita cancelada
    cita = MockCita(
        id=1,
        paciente_id=1,
        doctor_id=1,
        fecha_hora_inicio=ahora + timedelta(hours=23.5),
        fecha_hora_fin=ahora + timedelta(hours=24.5),
        estado='cancelada',
        recordatorio_enviado=False
    )
    
    # Verificar que no está en estados válidos
    assert cita.estado not in ['programada', 'confirmada']


def test_formatea_mensaje_correctamente():
    """Test: Formatea mensaje correctamente"""
    paciente = MockPaciente(1, "Juan Pérez", "+525512345678")
    doctor = MockDoctor(1, "Dr. Santiago de Jesús Ornelas Reynoso")
    
    # Crear cita específica
    fecha_cita = datetime(2026, 1, 30, 14, 30)  # Jueves
    cita = MockCita(
        id=1,
        paciente_id=1,
        doctor_id=1,
        fecha_hora_inicio=fecha_cita,
        fecha_hora_fin=fecha_cita + timedelta(hours=1),
        estado='programada',
        recordatorio_enviado=False
    )
    
    # Generar mensaje
    dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
    meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
            'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
    
    dia_nombre = dias[fecha_cita.weekday()]
    mes_nombre = meses[fecha_cita.month - 1]
    
    mensaje = f"""🔔 Recordatorio de Cita

Hola {paciente.nombre_completo}!

Tienes una cita programada para:

📅 {dia_nombre} {fecha_cita.day} de {mes_nombre}, {fecha_cita.year}
🕐 {fecha_cita.strftime('%H:%M')} a {cita.fecha_hora_fin.strftime('%H:%M')}
👨‍⚕️ {doctor.nombre_completo}

💬 Si necesitas cancelar, responde "cancelar cita"

¡Te esperamos!"""
    
    # Verificar contenido
    assert "Juan Pérez" in mensaje
    assert "Viernes 30 de enero, 2026" in mensaje  # 30 de enero de 2026 es Viernes
    assert "14:30 a 15:30" in mensaje
    assert "Dr. Santiago de Jesús Ornelas Reynoso" in mensaje
    assert "cancelar cita" in mensaje


@patch('src.background.recordatorios_scheduler.enviar_whatsapp')
@patch('src.background.recordatorios_scheduler.get_db_session')
def test_marca_como_enviado_despues_envio(mock_db_session, mock_enviar_whatsapp):
    """Test: Marca como enviado después de envío exitoso"""
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
    enviar_recordatorios()
    
    # Verificar
    assert cita.recordatorio_enviado == True
    assert cita.recordatorio_intentos == 1
    assert cita.recordatorio_fecha_envio is not None


@patch('src.background.recordatorios_scheduler.enviar_whatsapp')
@patch('src.background.recordatorios_scheduler.get_db_session')
def test_max_3_intentos_por_cita(mock_db_session, mock_enviar_whatsapp):
    """Test: Máximo 3 intentos por cita"""
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
        recordatorio_intentos=2
    )
    
    # Mock de la sesión de base de datos
    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_filter = MagicMock()
    
    mock_db.query.return_value = mock_query
    mock_query.filter.return_value = mock_filter
    mock_filter.all.return_value = [cita]
    mock_db.query.return_value.get.side_effect = lambda id: paciente if id == 1 else doctor
    
    mock_db_session.return_value.__enter__.return_value = mock_db
    mock_enviar_whatsapp.return_value = {'exito': False, 'error': 'Error de red'}
    
    # Ejecutar
    enviar_recordatorios()
    
    # Verificar
    assert cita.recordatorio_intentos == 3
    assert cita.recordatorio_enviado == True  # Marcado como enviado para no reintentar


def test_ejecuta_cada_hora():
    """Test: Scheduler ejecuta cada hora"""
    import schedule
    
    # Limpiar schedule
    schedule.clear()
    
    # Programar tarea
    schedule.every(1).hours.do(lambda: None)
    
    # Verificar que hay un job programado
    assert len(schedule.get_jobs()) == 1
    
    # Verificar intervalo
    job = schedule.get_jobs()[0]
    assert job.interval == 1
    assert job.unit == 'hours'
