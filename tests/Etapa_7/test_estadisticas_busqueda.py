"""
Tests para obtener_estadisticas_consultas y buscar_citas_por_periodo
"""
import pytest
from datetime import datetime, date
from unittest.mock import patch, MagicMock
from decimal import Decimal

from src.medical.herramientas_medicas import (
    obtener_estadisticas_consultas,
    buscar_citas_por_periodo
)


class MockCitaStats:
    def __init__(self, id, doctor_id, paciente_id, fecha, estado, tipo, costo=None):
        self.id = id
        self.doctor_id = doctor_id
        self.paciente_id = paciente_id
        self.fecha_hora_inicio = fecha
        self.fecha_hora_fin = fecha
        self.estado = estado
        self.tipo_consulta = tipo
        self.costo_consulta = Decimal(str(costo)) if costo else None
        self.motivo_consulta = "Consulta general"


class MockDoctor:
    def __init__(self, id, nombre):
        self.id = id
        self.nombre_completo = nombre


class MockPaciente:
    def __init__(self, id, nombre):
        self.id = id
        self.nombre_completo = nombre


@patch('src.medical.herramientas_medicas.get_db_session')
def test_obtener_estadisticas_todas_citas(mock_db_session):
    """Test: Obtener estadísticas de todas las citas"""
    from src.medical.models import EstadoCita, TipoConsulta
    
    mock_db = MagicMock()
    
    fecha = datetime(2026, 1, 29, 10, 0)
    citas = [
        MockCitaStats(1, 1, 10, fecha, EstadoCita.completada, TipoConsulta.primera_vez, 500),
        MockCitaStats(2, 1, 11, fecha, EstadoCita.completada, TipoConsulta.seguimiento, 400),
        MockCitaStats(3, 2, 12, fecha, EstadoCita.cancelada, TipoConsulta.primera_vez),
    ]
    
    mock_query = MagicMock()
    mock_query.all.return_value = citas
    mock_db.query.return_value = mock_query
    
    # Mock para obtener doctores
    mock_db.query.return_value.get.side_effect = lambda id: MockDoctor(id, f"Dr. {id}")
    
    mock_db_session.return_value.__enter__.return_value = mock_db
    
    resultado = obtener_estadisticas_consultas()
    
    assert resultado['exito'] == True
    assert resultado['total_citas'] == 3
    assert 'completada' in resultado['por_estado']
    assert 'cancelada' in resultado['por_estado']


@patch('src.medical.herramientas_medicas.get_db_session')
def test_obtener_estadisticas_por_doctor(mock_db_session):
    """Test: Estadísticas filtradas por doctor"""
    from src.medical.models import EstadoCita, TipoConsulta
    
    mock_db = MagicMock()
    
    fecha = datetime(2026, 1, 29, 10, 0)
    citas = [
        MockCitaStats(1, 1, 10, fecha, EstadoCita.completada, TipoConsulta.primera_vez, 500),
        MockCitaStats(2, 1, 11, fecha, EstadoCita.completada, TipoConsulta.seguimiento, 600),
    ]
    
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_filter.all.return_value = citas
    mock_query.filter.return_value = mock_filter
    mock_db.query.return_value = mock_query
    
    mock_db_session.return_value.__enter__.return_value = mock_db
    
    resultado = obtener_estadisticas_consultas(doctor_id=1)
    
    assert resultado['exito'] == True
    assert resultado['total_citas'] == 2


@patch('src.medical.herramientas_medicas.get_db_session')
def test_obtener_estadisticas_calcula_porcentajes(mock_db_session):
    """Test: Calcular porcentajes por estado"""
    from src.medical.models import EstadoCita, TipoConsulta
    
    mock_db = MagicMock()
    
    fecha = datetime(2026, 1, 29, 10, 0)
    citas = [
        MockCitaStats(1, 1, 10, fecha, EstadoCita.completada, TipoConsulta.primera_vez, 500),
        MockCitaStats(2, 1, 11, fecha, EstadoCita.completada, TipoConsulta.primera_vez, 600),
        MockCitaStats(3, 1, 12, fecha, EstadoCita.cancelada, TipoConsulta.primera_vez),
        MockCitaStats(4, 1, 13, fecha, EstadoCita.cancelada, TipoConsulta.primera_vez),
    ]
    
    mock_query = MagicMock()
    mock_query.all.return_value = citas
    mock_db.query.return_value = mock_query
    mock_db.query.return_value.get.return_value = MockDoctor(1, "Dr. Test")
    
    mock_db_session.return_value.__enter__.return_value = mock_db
    
    resultado = obtener_estadisticas_consultas()
    
    assert resultado['por_estado']['completada']['porcentaje'] == 50.0
    assert resultado['por_estado']['cancelada']['porcentaje'] == 50.0


@patch('src.medical.herramientas_medicas.get_db_session')
def test_obtener_estadisticas_calcula_ingresos(mock_db_session):
    """Test: Calcular ingresos totales"""
    from src.medical.models import EstadoCita, TipoConsulta
    
    mock_db = MagicMock()
    
    fecha = datetime(2026, 1, 29, 10, 0)
    citas = [
        MockCitaStats(1, 1, 10, fecha, EstadoCita.completada, TipoConsulta.primera_vez, 500),
        MockCitaStats(2, 1, 11, fecha, EstadoCita.completada, TipoConsulta.primera_vez, 700),
        MockCitaStats(3, 1, 12, fecha, EstadoCita.cancelada, TipoConsulta.primera_vez, 300),  # No cuenta
    ]
    
    mock_query = MagicMock()
    mock_query.all.return_value = citas
    mock_db.query.return_value = mock_query
    mock_db.query.return_value.get.return_value = MockDoctor(1, "Dr. Test")
    
    mock_db_session.return_value.__enter__.return_value = mock_db
    
    resultado = obtener_estadisticas_consultas()
    
    assert resultado['ingresos']['total'] == 1200.0
    assert resultado['ingresos']['citas_con_costo'] == 2


@patch('src.medical.herramientas_medicas.get_db_session')
def test_obtener_estadisticas_sin_datos(mock_db_session):
    """Test: Manejo cuando no hay datos"""
    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_query.all.return_value = []
    mock_db.query.return_value = mock_query
    
    mock_db_session.return_value.__enter__.return_value = mock_db
    
    resultado = obtener_estadisticas_consultas()
    
    assert resultado['exito'] == True
    assert resultado['total_citas'] == 0
    assert 'No hay datos' in resultado['mensaje']


@patch('src.medical.herramientas_medicas.get_db_session')
def test_obtener_estadisticas_top_doctores(mock_db_session):
    """Test: Listar top doctores cuando no se filtra por doctor_id"""
    from src.medical.models import EstadoCita, TipoConsulta
    
    mock_db = MagicMock()
    
    fecha = datetime(2026, 1, 29, 10, 0)
    citas = [
        MockCitaStats(1, 1, 10, fecha, EstadoCita.completada, TipoConsulta.primera_vez, 500),
        MockCitaStats(2, 1, 11, fecha, EstadoCita.completada, TipoConsulta.primera_vez, 500),
        MockCitaStats(3, 2, 12, fecha, EstadoCita.completada, TipoConsulta.primera_vez, 500),
    ]
    
    mock_query = MagicMock()
    mock_query.all.return_value = citas
    mock_db.query.return_value = mock_query
    
    # Mock para get doctor
    def get_doctor(id):
        return MockDoctor(id, f"Dr. García {id}")
    
    mock_db.query.return_value.get.side_effect = get_doctor
    
    mock_db_session.return_value.__enter__.return_value = mock_db
    
    resultado = obtener_estadisticas_consultas()
    
    assert 'top_doctores' in resultado
    assert len(resultado['top_doctores']) == 2


@patch('src.medical.herramientas_medicas.get_db_session')
def test_buscar_citas_sin_filtros(mock_db_session):
    """Test: Buscar citas sin filtros retorna todas"""
    from src.medical.models import EstadoCita, TipoConsulta
    
    mock_db = MagicMock()
    
    fecha = datetime(2026, 1, 29, 10, 0)
    citas = [
        MockCitaStats(1, 1, 10, fecha, EstadoCita.completada, TipoConsulta.primera_vez, 500),
        MockCitaStats(2, 2, 11, fecha, EstadoCita.programada, TipoConsulta.seguimiento, 400),
    ]
    
    mock_query = MagicMock()
    mock_order = MagicMock()
    mock_limit = MagicMock()
    mock_limit.all.return_value = citas
    mock_order.limit.return_value = mock_limit
    mock_query.order_by.return_value = mock_order
    mock_db.query.return_value = mock_query
    
    # Mock para get doctor/paciente
    mock_db.query.return_value.get.side_effect = lambda id: (
        MockDoctor(id, f"Dr. {id}") if id <= 2 
        else MockPaciente(id, f"Paciente {id}")
    )
    
    mock_db_session.return_value.__enter__.return_value = mock_db
    
    resultado = buscar_citas_por_periodo()
    
    assert resultado['exito'] == True
    assert resultado['total_resultados'] == 2


@patch('src.medical.herramientas_medicas.get_db_session')
def test_buscar_citas_por_doctor(mock_db_session):
    """Test: Filtrar citas por doctor"""
    from src.medical.models import EstadoCita, TipoConsulta
    
    mock_db = MagicMock()
    
    fecha = datetime(2026, 1, 29, 10, 0)
    citas = [
        MockCitaStats(1, 1, 10, fecha, EstadoCita.completada, TipoConsulta.primera_vez, 500),
    ]
    
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_order = MagicMock()
    mock_limit = MagicMock()
    mock_limit.all.return_value = citas
    mock_order.limit.return_value = mock_limit
    mock_filter.order_by.return_value = mock_order
    mock_query.filter.return_value = mock_filter
    mock_db.query.return_value = mock_query
    
    mock_db.query.return_value.get.side_effect = lambda id: (
        MockDoctor(id, f"Dr. {id}") if id == 1 
        else MockPaciente(id, f"Paciente {id}")
    )
    
    mock_db_session.return_value.__enter__.return_value = mock_db
    
    resultado = buscar_citas_por_periodo(doctor_id=1)
    
    assert resultado['exito'] == True
    assert resultado['total_resultados'] == 1


@patch('src.medical.herramientas_medicas.get_db_session')
def test_buscar_citas_por_estado(mock_db_session):
    """Test: Filtrar citas por estado"""
    from src.medical.models import EstadoCita, TipoConsulta
    
    mock_db = MagicMock()
    
    fecha = datetime(2026, 1, 29, 10, 0)
    citas = [
        MockCitaStats(1, 1, 10, fecha, EstadoCita.completada, TipoConsulta.primera_vez, 500),
    ]
    
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_order = MagicMock()
    mock_limit = MagicMock()
    mock_limit.all.return_value = citas
    mock_order.limit.return_value = mock_limit
    mock_filter.order_by.return_value = mock_order
    mock_query.filter.return_value = mock_filter
    mock_db.query.return_value = mock_query
    
    mock_db.query.return_value.get.side_effect = lambda id: (
        MockDoctor(id, f"Dr. {id}") if id == 1 
        else MockPaciente(id, f"Paciente {id}")
    )
    
    mock_db_session.return_value.__enter__.return_value = mock_db
    
    resultado = buscar_citas_por_periodo(estado='completada')
    
    assert resultado['exito'] == True


@patch('src.medical.herramientas_medicas.get_db_session')
def test_buscar_citas_estado_invalido(mock_db_session):
    """Test: Error con estado inválido"""
    mock_db = MagicMock()
    mock_db_session.return_value.__enter__.return_value = mock_db
    
    resultado = buscar_citas_por_periodo(estado='estado_invalido')
    
    assert resultado['exito'] == False
    assert 'inválido' in resultado['error']


@patch('src.medical.herramientas_medicas.get_db_session')
def test_buscar_citas_por_fecha(mock_db_session):
    """Test: Filtrar citas por rango de fechas"""
    from src.medical.models import EstadoCita, TipoConsulta
    
    mock_db = MagicMock()
    
    fecha = datetime(2026, 1, 29, 10, 0)
    citas = [
        MockCitaStats(1, 1, 10, fecha, EstadoCita.completada, TipoConsulta.primera_vez, 500),
    ]
    
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_order = MagicMock()
    mock_limit = MagicMock()
    mock_limit.all.return_value = citas
    mock_order.limit.return_value = mock_limit
    mock_filter.order_by.return_value = mock_order
    mock_query.filter.return_value = mock_filter
    mock_db.query.return_value = mock_query
    
    mock_db.query.return_value.get.side_effect = lambda id: (
        MockDoctor(id, f"Dr. {id}") if id == 1 
        else MockPaciente(id, f"Paciente {id}")
    )
    
    mock_db_session.return_value.__enter__.return_value = mock_db
    
    resultado = buscar_citas_por_periodo(
        fecha_inicio=date(2026, 1, 29),
        fecha_fin=date(2026, 1, 29)
    )
    
    assert resultado['exito'] == True


@patch('src.medical.herramientas_medicas.get_db_session')
def test_buscar_citas_respeta_limite(mock_db_session):
    """Test: Respetar límite de resultados"""
    from src.medical.models import EstadoCita, TipoConsulta
    
    mock_db = MagicMock()
    
    fecha = datetime(2026, 1, 29, 10, 0)
    citas = [
        MockCitaStats(i, 1, 10+i, fecha, EstadoCita.completada, TipoConsulta.primera_vez, 500)
        for i in range(5)
    ]
    
    mock_query = MagicMock()
    mock_order = MagicMock()
    mock_limit = MagicMock()
    mock_limit.all.return_value = citas[:5]
    mock_order.limit.return_value = mock_limit
    mock_query.order_by.return_value = mock_order
    mock_db.query.return_value = mock_query
    
    mock_db.query.return_value.get.side_effect = lambda id: (
        MockDoctor(id, f"Dr. {id}") if id == 1 
        else MockPaciente(id, f"Paciente {id}")
    )
    
    mock_db_session.return_value.__enter__.return_value = mock_db
    
    resultado = buscar_citas_por_periodo(limite=5)
    
    assert resultado['exito'] == True
    assert resultado['total_resultados'] == 5
    assert resultado['limite_aplicado'] == 5


@patch('src.medical.herramientas_medicas.get_db_session')
def test_buscar_citas_formatea_resultado(mock_db_session):
    """Test: Formatear resultado correctamente"""
    from src.medical.models import EstadoCita, TipoConsulta
    
    mock_db = MagicMock()
    
    fecha = datetime(2026, 1, 29, 10, 30)
    cita = MockCitaStats(1, 5, 10, fecha, EstadoCita.completada, TipoConsulta.primera_vez, 500.50)
    
    mock_query = MagicMock()
    mock_order = MagicMock()
    mock_limit = MagicMock()
    mock_limit.all.return_value = [cita]
    mock_order.limit.return_value = mock_limit
    mock_query.order_by.return_value = mock_order
    mock_db.query.return_value = mock_query
    
    mock_db.query.return_value.get.side_effect = lambda id: (
        MockDoctor(id, "Dr. García") if id == 5 
        else MockPaciente(id, "Juan Pérez")
    )
    
    mock_db_session.return_value.__enter__.return_value = mock_db
    
    resultado = buscar_citas_por_periodo()
    
    assert resultado['exito'] == True
    cita_resultado = resultado['citas'][0]
    assert cita_resultado['id'] == 1
    assert cita_resultado['doctor']['nombre'] == "Dr. García"
    assert cita_resultado['paciente']['nombre'] == "Juan Pérez"
    assert cita_resultado['estado'] == 'completada'
    assert cita_resultado['costo'] == 500.50
