"""
Tests para actualizar_disponibilidad_doctor y generar_reporte_doctor
"""
import pytest
from datetime import datetime, date, time
from unittest.mock import patch, MagicMock
from decimal import Decimal

from src.medical.herramientas_medicas import (
    actualizar_disponibilidad_doctor,
    generar_reporte_doctor
)


class MockDoctor:
    def __init__(self, id, nombre, especialidad="Cardiología"):
        self.id = id
        self.nombre_completo = nombre
        self.especialidad = especialidad


class MockDisponibilidad:
    def __init__(self, id, doctor_id, dia_semana):
        self.id = id
        self.doctor_id = doctor_id
        self.dia_semana = dia_semana
        self.hora_inicio = None
        self.hora_fin = None
        self.disponible = True
        self.duracion_cita = 30


class MockCitaReporte:
    def __init__(self, id, doctor_id, paciente_id, fecha, estado, costo=None):
        self.id = id
        self.doctor_id = doctor_id
        self.paciente_id = paciente_id
        self.fecha_hora_inicio = fecha
        self.fecha_hora_fin = fecha
        self.estado = estado
        self.costo_consulta = Decimal(str(costo)) if costo else None
        self.tipo_consulta = None


@patch('src.medical.herramientas_medicas.get_db_session')
def test_actualizar_disponibilidad_crear_nueva(mock_db_session):
    """Test: Crear nueva disponibilidad"""
    mock_db = MagicMock()
    doctor = MockDoctor(1, "Dr. García")
    
    # Mock para obtener doctor
    mock_db.query.return_value.get.return_value = doctor
    
    # Mock para buscar disponibilidad existente
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_filter.first.return_value = None  # No existe
    mock_query.filter.return_value = mock_filter
    
    # Configurar side_effect para múltiples llamadas a query
    mock_db.query.side_effect = [
        MagicMock(get=MagicMock(return_value=doctor)),
        mock_query
    ]
    
    mock_db_session.return_value.__enter__.return_value = mock_db
    
    resultado = actualizar_disponibilidad_doctor(
        doctor_id=1,
        dia_semana=1,  # Martes
        hora_inicio="09:00",
        hora_fin="17:00",
        disponible=True,
        duracion_cita=30
    )
    
    assert resultado['exito'] == True
    assert resultado['accion'] == 'creada'
    assert resultado['dia_nombre'] == 'Martes'


@patch('src.medical.herramientas_medicas.get_db_session')
def test_actualizar_disponibilidad_actualizar_existente(mock_db_session):
    """Test: Actualizar disponibilidad existente"""
    mock_db = MagicMock()
    doctor = MockDoctor(1, "Dr. García")
    disponibilidad = MockDisponibilidad(1, 1, 1)
    
    mock_db.query.return_value.get.return_value = doctor
    
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_filter.first.return_value = disponibilidad
    mock_query.filter.return_value = mock_filter
    
    mock_db.query.side_effect = [
        MagicMock(get=MagicMock(return_value=doctor)),
        mock_query
    ]
    
    mock_db_session.return_value.__enter__.return_value = mock_db
    
    resultado = actualizar_disponibilidad_doctor(
        doctor_id=1,
        dia_semana=1,
        hora_inicio="10:00",
        hora_fin="18:00"
    )
    
    assert resultado['exito'] == True
    assert resultado['accion'] == 'actualizada'


@patch('src.medical.herramientas_medicas.get_db_session')
def test_actualizar_disponibilidad_doctor_no_existe(mock_db_session):
    """Test: Error cuando doctor no existe"""
    mock_db = MagicMock()
    mock_db.query.return_value.get.return_value = None
    mock_db_session.return_value.__enter__.return_value = mock_db
    
    resultado = actualizar_disponibilidad_doctor(
        doctor_id=999,
        dia_semana=1,
        hora_inicio="09:00",
        hora_fin="17:00"
    )
    
    assert resultado['exito'] == False
    assert 'no encontrado' in resultado['error']


@patch('src.medical.herramientas_medicas.get_db_session')
def test_actualizar_disponibilidad_dia_invalido(mock_db_session):
    """Test: Error con día de semana inválido"""
    mock_db = MagicMock()
    doctor = MockDoctor(1, "Dr. García")
    mock_db.query.return_value.get.return_value = doctor
    mock_db_session.return_value.__enter__.return_value = mock_db
    
    resultado = actualizar_disponibilidad_doctor(
        doctor_id=1,
        dia_semana=7,  # Inválido (0-6)
        hora_inicio="09:00",
        hora_fin="17:00"
    )
    
    assert resultado['exito'] == False
    assert 'Día de semana' in resultado['error']


@patch('src.medical.herramientas_medicas.get_db_session')
def test_actualizar_disponibilidad_hora_invalida(mock_db_session):
    """Test: Error cuando hora_fin <= hora_inicio"""
    mock_db = MagicMock()
    doctor = MockDoctor(1, "Dr. García")
    mock_db.query.return_value.get.return_value = doctor
    
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_filter.first.return_value = None
    mock_query.filter.return_value = mock_filter
    
    mock_db.query.side_effect = [
        MagicMock(get=MagicMock(return_value=doctor)),
        mock_query
    ]
    
    mock_db_session.return_value.__enter__.return_value = mock_db
    
    resultado = actualizar_disponibilidad_doctor(
        doctor_id=1,
        dia_semana=1,
        hora_inicio="17:00",
        hora_fin="09:00"  # Antes del inicio
    )
    
    assert resultado['exito'] == False
    assert 'posterior' in resultado['error']


@patch('src.medical.herramientas_medicas.get_db_session')
def test_actualizar_disponibilidad_formato_hora_invalido(mock_db_session):
    """Test: Error con formato de hora inválido"""
    mock_db = MagicMock()
    doctor = MockDoctor(1, "Dr. García")
    mock_db.query.return_value.get.return_value = doctor
    mock_db_session.return_value.__enter__.return_value = mock_db
    
    resultado = actualizar_disponibilidad_doctor(
        doctor_id=1,
        dia_semana=1,
        hora_inicio="9:00 AM",  # Formato incorrecto
        hora_fin="17:00"
    )
    
    assert resultado['exito'] == False
    assert 'Formato de hora' in resultado['error']


@patch('src.medical.herramientas_medicas.get_db_session')
def test_generar_reporte_doctor_exitoso(mock_db_session):
    """Test: Generar reporte exitosamente"""
    from src.medical.models import EstadoCita
    
    mock_db = MagicMock()
    doctor = MockDoctor(1, "Dr. García", "Cardiología")
    
    # Crear citas de prueba
    fecha = datetime(2026, 1, 29, 10, 0)
    citas = [
        MockCitaReporte(1, 1, 10, fecha, EstadoCita.completada, 500),
        MockCitaReporte(2, 1, 11, fecha, EstadoCita.completada, 600),
        MockCitaReporte(3, 1, 12, fecha, EstadoCita.cancelada),
    ]
    
    mock_db.query.return_value.get.return_value = doctor
    
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_filter.all.return_value = citas
    mock_query.filter.return_value = mock_filter
    
    mock_db.query.side_effect = [
        MagicMock(get=MagicMock(return_value=doctor)),
        mock_query
    ]
    
    mock_db_session.return_value.__enter__.return_value = mock_db
    
    resultado = generar_reporte_doctor(
        doctor_id=1,
        fecha_inicio=date(2026, 1, 29),
        fecha_fin=date(2026, 1, 29)
    )
    
    assert resultado['exito'] == True
    assert resultado['doctor_id'] == 1
    assert resultado['metricas']['total_citas'] == 3
    assert resultado['metricas']['completadas'] == 2
    assert resultado['metricas']['canceladas'] == 1


@patch('src.medical.herramientas_medicas.get_db_session')
def test_generar_reporte_calcula_ingresos(mock_db_session):
    """Test: Calcular ingresos correctamente"""
    from src.medical.models import EstadoCita
    
    mock_db = MagicMock()
    doctor = MockDoctor(1, "Dr. García")
    
    fecha = datetime(2026, 1, 29, 10, 0)
    citas = [
        MockCitaReporte(1, 1, 10, fecha, EstadoCita.completada, 500),
        MockCitaReporte(2, 1, 11, fecha, EstadoCita.completada, 700),
    ]
    
    mock_db.query.return_value.get.return_value = doctor
    
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_filter.all.return_value = citas
    mock_query.filter.return_value = mock_filter
    
    mock_db.query.side_effect = [
        MagicMock(get=MagicMock(return_value=doctor)),
        mock_query
    ]
    
    mock_db_session.return_value.__enter__.return_value = mock_db
    
    resultado = generar_reporte_doctor(
        doctor_id=1,
        fecha_inicio=date(2026, 1, 29),
        fecha_fin=date(2026, 1, 29)
    )
    
    assert resultado['ingresos']['total'] == 1200.0
    assert resultado['ingresos']['promedio_por_consulta'] == 600.0


@patch('src.medical.herramientas_medicas.get_db_session')
def test_generar_reporte_doctor_no_existe(mock_db_session):
    """Test: Error cuando doctor no existe"""
    mock_db = MagicMock()
    mock_db.query.return_value.get.return_value = None
    mock_db_session.return_value.__enter__.return_value = mock_db
    
    resultado = generar_reporte_doctor(
        doctor_id=999,
        fecha_inicio=date(2026, 1, 29),
        fecha_fin=date(2026, 1, 29)
    )
    
    assert resultado['exito'] == False
    assert 'no encontrado' in resultado['error']


@patch('src.medical.herramientas_medicas.get_db_session')
def test_generar_reporte_calcula_tasa_completadas(mock_db_session):
    """Test: Calcular tasa de citas completadas"""
    from src.medical.models import EstadoCita
    
    mock_db = MagicMock()
    doctor = MockDoctor(1, "Dr. García")
    
    fecha = datetime(2026, 1, 29, 10, 0)
    citas = [
        MockCitaReporte(1, 1, 10, fecha, EstadoCita.completada, 500),
        MockCitaReporte(2, 1, 11, fecha, EstadoCita.completada, 600),
        MockCitaReporte(3, 1, 12, fecha, EstadoCita.cancelada),
        MockCitaReporte(4, 1, 13, fecha, EstadoCita.no_asistio),
    ]
    
    mock_db.query.return_value.get.return_value = doctor
    
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_filter.all.return_value = citas
    mock_query.filter.return_value = mock_filter
    
    mock_db.query.side_effect = [
        MagicMock(get=MagicMock(return_value=doctor)),
        mock_query
    ]
    
    mock_db_session.return_value.__enter__.return_value = mock_db
    
    resultado = generar_reporte_doctor(
        doctor_id=1,
        fecha_inicio=date(2026, 1, 29),
        fecha_fin=date(2026, 1, 29)
    )
    
    # 2 completadas de 4 total = 50%
    assert resultado['metricas']['tasa_completadas'] == 50.0


@patch('src.medical.herramientas_medicas.get_db_session')
def test_generar_reporte_pacientes_unicos(mock_db_session):
    """Test: Contar pacientes únicos correctamente"""
    from src.medical.models import EstadoCita
    
    mock_db = MagicMock()
    doctor = MockDoctor(1, "Dr. García")
    
    fecha = datetime(2026, 1, 29, 10, 0)
    citas = [
        MockCitaReporte(1, 1, 10, fecha, EstadoCita.completada, 500),
        MockCitaReporte(2, 1, 10, fecha, EstadoCita.completada, 600),  # Mismo paciente
        MockCitaReporte(3, 1, 11, fecha, EstadoCita.completada, 700),  # Diferente
    ]
    
    mock_db.query.return_value.get.return_value = doctor
    
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_filter.all.return_value = citas
    mock_query.filter.return_value = mock_filter
    
    mock_db.query.side_effect = [
        MagicMock(get=MagicMock(return_value=doctor)),
        mock_query
    ]
    
    mock_db_session.return_value.__enter__.return_value = mock_db
    
    resultado = generar_reporte_doctor(
        doctor_id=1,
        fecha_inicio=date(2026, 1, 29),
        fecha_fin=date(2026, 1, 29)
    )
    
    assert resultado['metricas']['pacientes_unicos'] == 2


@patch('src.medical.herramientas_medicas.get_db_session')
def test_generar_reporte_incluye_desglose_por_dia(mock_db_session):
    """Test: Incluir desglose por día en período corto"""
    from src.medical.models import EstadoCita
    
    mock_db = MagicMock()
    doctor = MockDoctor(1, "Dr. García")
    
    fecha1 = datetime(2026, 1, 29, 10, 0)
    fecha2 = datetime(2026, 1, 30, 10, 0)
    citas = [
        MockCitaReporte(1, 1, 10, fecha1, EstadoCita.completada, 500),
        MockCitaReporte(2, 1, 11, fecha2, EstadoCita.completada, 600),
    ]
    
    mock_db.query.return_value.get.return_value = doctor
    
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_filter.all.return_value = citas
    mock_query.filter.return_value = mock_filter
    
    mock_db.query.side_effect = [
        MagicMock(get=MagicMock(return_value=doctor)),
        mock_query
    ]
    
    mock_db_session.return_value.__enter__.return_value = mock_db
    
    resultado = generar_reporte_doctor(
        doctor_id=1,
        fecha_inicio=date(2026, 1, 29),
        fecha_fin=date(2026, 1, 30)
    )
    
    assert 'por_dia' in resultado
    assert '2026-01-29' in resultado['por_dia']
    assert '2026-01-30' in resultado['por_dia']
