"""
Tests para registrar_consulta y consultar_historial_paciente
"""
import pytest
from datetime import datetime, date
from unittest.mock import patch, MagicMock

from src.medical.herramientas_medicas import (
    registrar_consulta,
    consultar_historial_paciente
)


# Mocks para las pruebas
class MockCita:
    def __init__(self, id, paciente_id, doctor_id):
        self.id = id
        self.paciente_id = paciente_id
        self.doctor_id = doctor_id
        self.fecha_hora_inicio = datetime(2026, 1, 29, 14, 30)
        self.fecha_hora_fin = datetime(2026, 1, 29, 15, 30)
        self.diagnostico = None
        self.tratamiento_prescrito = {}
        self.sintomas_principales = None
        self.medicamentos = []
        self.notas_privadas = None
        self.estado = None
        self.updated_at = None


class MockHistorial:
    def __init__(self, id, paciente_id, cita_id):
        self.id = id
        self.paciente_id = paciente_id
        self.cita_id = cita_id
        self.fecha_consulta = date(2026, 1, 29)
        self.diagnostico_principal = "Gripe común"
        self.tratamiento_prescrito = "Reposo y líquidos"
        self.medicamentos = []
        self.peso = 70.5
        self.altura = 1.75
        self.presion_arterial = "120/80"
        self.indicaciones_generales = None
        self.sintomas = "Fiebre y dolor de cabeza"


class MockPaciente:
    def __init__(self, id, nombre):
        self.id = id
        self.nombre_completo = nombre


@patch('src.medical.herramientas_medicas.get_db_session')
def test_registrar_consulta_exitoso(mock_db_session):
    """Test: Registrar consulta exitosamente"""
    # Preparar mocks
    mock_db = MagicMock()
    cita = MockCita(1, 10, 5)
    
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_filter.first.return_value = cita
    mock_query.filter.return_value = mock_filter
    mock_db.query.return_value = mock_query
    
    mock_db_session.return_value.__enter__.return_value = mock_db
    
    # Ejecutar
    resultado = registrar_consulta(
        cita_id=1,
        diagnostico="Hipertensión arterial",
        tratamiento="Modificar dieta, reducir sal",
        sintomas="Dolor de cabeza, mareos",
        medicamentos=[
            {"nombre": "Losartán", "dosis": "50mg", "frecuencia": "1 vez al día"}
        ],
        notas_privadas="Paciente con antecedentes familiares"
    )
    
    # Verificar
    assert resultado['exito'] == True
    assert resultado['cita_id'] == 1
    assert resultado['paciente_id'] == 10
    assert 'fecha' in resultado


@patch('src.medical.herramientas_medicas.get_db_session')
def test_registrar_consulta_cita_no_existe(mock_db_session):
    """Test: Error cuando cita no existe"""
    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_filter.first.return_value = None
    mock_query.filter.return_value = mock_filter
    mock_db.query.return_value = mock_query
    
    mock_db_session.return_value.__enter__.return_value = mock_db
    
    resultado = registrar_consulta(
        cita_id=999,
        diagnostico="Test",
        tratamiento="Test",
        sintomas="Test"
    )
    
    assert resultado['exito'] == False
    assert 'no encontrada' in resultado['error']


@patch('src.medical.herramientas_medicas.get_db_session')
def test_registrar_consulta_actualiza_estado(mock_db_session):
    """Test: Actualiza estado de cita a completada"""
    from src.medical.models import EstadoCita
    
    mock_db = MagicMock()
    cita = MockCita(1, 10, 5)
    
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_filter.first.return_value = cita
    mock_query.filter.return_value = mock_filter
    mock_db.query.return_value = mock_query
    
    mock_db_session.return_value.__enter__.return_value = mock_db
    
    resultado = registrar_consulta(
        cita_id=1,
        diagnostico="Test",
        tratamiento="Test",
        sintomas="Test"
    )
    
    assert resultado['exito'] == True
    assert cita.estado == EstadoCita.completada
    assert cita.diagnostico == "Test"


@patch('src.medical.herramientas_medicas.get_db_session')
def test_registrar_consulta_con_medicamentos(mock_db_session):
    """Test: Registrar consulta con lista de medicamentos"""
    mock_db = MagicMock()
    cita = MockCita(1, 10, 5)
    
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_filter.first.return_value = cita
    mock_query.filter.return_value = mock_filter
    mock_db.query.return_value = mock_query
    
    mock_db_session.return_value.__enter__.return_value = mock_db
    
    medicamentos = [
        {"nombre": "Ibuprofeno", "dosis": "400mg"},
        {"nombre": "Paracetamol", "dosis": "500mg"}
    ]
    
    resultado = registrar_consulta(
        cita_id=1,
        diagnostico="Test",
        tratamiento="Test",
        sintomas="Test",
        medicamentos=medicamentos
    )
    
    assert resultado['exito'] == True
    assert cita.medicamentos == medicamentos


@patch('src.medical.herramientas_medicas.get_db_session')
def test_consultar_historial_paciente_exitoso(mock_db_session):
    """Test: Consultar historial de paciente exitosamente"""
    mock_db = MagicMock()
    paciente = MockPaciente(10, "Juan Pérez")
    
    # Mock para get paciente
    mock_db.query.return_value.get.return_value = paciente
    
    # Mock para query historiales
    historial1 = MockHistorial(1, 10, 1)
    historial2 = MockHistorial(2, 10, 2)
    
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_order = MagicMock()
    mock_limit = MagicMock()
    
    mock_limit.all.return_value = [historial1, historial2]
    mock_order.limit.return_value = mock_limit
    mock_filter.order_by.return_value = mock_order
    mock_query.filter.return_value = mock_filter
    
    # Configurar para que primera llamada sea get, segunda sea query de historiales
    mock_db.query.side_effect = [
        MagicMock(get=MagicMock(return_value=paciente)),
        mock_query
    ]
    
    mock_db_session.return_value.__enter__.return_value = mock_db
    
    resultado = consultar_historial_paciente(paciente_id=10)
    
    assert resultado['exito'] == True
    assert resultado['paciente_id'] == 10
    assert resultado['total_registros'] == 2
    assert len(resultado['historiales']) == 2


@patch('src.medical.herramientas_medicas.get_db_session')
def test_consultar_historial_paciente_no_existe(mock_db_session):
    """Test: Error cuando paciente no existe"""
    mock_db = MagicMock()
    mock_db.query.return_value.get.return_value = None
    mock_db_session.return_value.__enter__.return_value = mock_db
    
    resultado = consultar_historial_paciente(paciente_id=999)
    
    assert resultado['exito'] == False
    assert 'no encontrado' in resultado['error']


@patch('src.medical.herramientas_medicas.get_db_session')
def test_consultar_historial_con_busqueda(mock_db_session):
    """Test: Buscar en historial con término"""
    mock_db = MagicMock()
    paciente = MockPaciente(10, "Juan Pérez")
    historial1 = MockHistorial(1, 10, 1)
    historial1.diagnostico_principal = "Diabetes tipo 2"
    
    mock_db.query.return_value.get.return_value = paciente
    
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_order = MagicMock()
    mock_limit = MagicMock()
    
    mock_limit.all.return_value = [historial1]
    mock_order.limit.return_value = mock_limit
    mock_filter.order_by.return_value = mock_order
    # Encadenar el filter correctamente
    mock_filter.filter.return_value = mock_filter
    mock_query.filter.return_value = mock_filter
    
    mock_db.query.side_effect = [
        MagicMock(get=MagicMock(return_value=paciente)),
        mock_query
    ]
    
    mock_db_session.return_value.__enter__.return_value = mock_db
    
    resultado = consultar_historial_paciente(
        paciente_id=10,
        termino_busqueda="diabetes"
    )
    
    assert resultado['exito'] == True
    assert resultado['total_registros'] == 1


@patch('src.medical.herramientas_medicas.get_db_session')
def test_consultar_historial_con_limite(mock_db_session):
    """Test: Respetar límite de resultados"""
    mock_db = MagicMock()
    paciente = MockPaciente(10, "Juan Pérez")
    
    historiales = [MockHistorial(i, 10, i) for i in range(20)]
    
    mock_db.query.return_value.get.return_value = paciente
    
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_order = MagicMock()
    mock_limit = MagicMock()
    
    mock_limit.all.return_value = historiales[:5]
    mock_order.limit.return_value = mock_limit
    mock_filter.order_by.return_value = mock_order
    mock_query.filter.return_value = mock_filter
    
    mock_db.query.side_effect = [
        MagicMock(get=MagicMock(return_value=paciente)),
        mock_query
    ]
    
    mock_db_session.return_value.__enter__.return_value = mock_db
    
    resultado = consultar_historial_paciente(paciente_id=10, limite=5)
    
    assert resultado['exito'] == True
    assert resultado['total_registros'] == 5


@patch('src.medical.herramientas_medicas.get_db_session')
def test_consultar_historial_formatea_datos(mock_db_session):
    """Test: Formatea correctamente los datos del historial"""
    mock_db = MagicMock()
    paciente = MockPaciente(10, "Juan Pérez")
    historial = MockHistorial(1, 10, 1)
    historial.peso = 75.5
    historial.altura = 1.80
    
    mock_db.query.return_value.get.return_value = paciente
    
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_order = MagicMock()
    mock_limit = MagicMock()
    
    mock_limit.all.return_value = [historial]
    mock_order.limit.return_value = mock_limit
    mock_filter.order_by.return_value = mock_order
    mock_query.filter.return_value = mock_filter
    
    mock_db.query.side_effect = [
        MagicMock(get=MagicMock(return_value=paciente)),
        mock_query
    ]
    
    mock_db_session.return_value.__enter__.return_value = mock_db
    
    resultado = consultar_historial_paciente(paciente_id=10)
    
    assert resultado['exito'] == True
    registro = resultado['historiales'][0]
    assert registro['peso'] == 75.5
    assert registro['altura'] == 1.80
    assert registro['diagnostico'] == "Gripe común"
