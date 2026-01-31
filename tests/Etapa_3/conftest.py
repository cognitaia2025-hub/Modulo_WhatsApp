"""
Fixtures compartidos para tests de ETAPA 3
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from langchain_core.messages import HumanMessage, AIMessage
from datetime import datetime
import pytz

TIMEZONE = pytz.timezone("America/Tijuana")


@pytest.fixture
def mock_deepseek_response():
    """Mock de respuesta de DeepSeek para clasificación"""
    return {
        "clasificacion": "medica",
        "confianza": 0.95,
        "razonamiento": "Solicitud médica"
    }


@pytest.fixture
def mock_llm_clasificacion(mocker):
    """Mock del LLM para clasificación - retorna ClasificacionResponse"""
    from src.nodes.filtrado_inteligente_node import ClasificacionResponse
    
    mock = mocker.patch('src.nodes.filtrado_inteligente_node.llm_primary')
    
    # Crear ClasificacionResponse de prueba
    response = ClasificacionResponse(
        clasificacion="medica",
        confianza=0.95,
        razonamiento="Test"
    )
    mock.invoke.return_value = response
    return mock


@pytest.fixture
def estado_con_doctor():
    """Estado del grafo con usuario tipo doctor"""
    return {
        "messages": [HumanMessage(content="mi paciente Juan necesita cita")],
        "tipo_usuario": "doctor",
        "doctor_id": 1,
        "user_id": "+526641234567",
        "session_id": "test-session",
        "es_admin": False,
        "usuario_registrado": True
    }


@pytest.fixture
def estado_con_paciente():
    """Estado del grafo con paciente externo"""
    return {
        "messages": [HumanMessage(content="quiero una cita")],
        "tipo_usuario": "paciente_externo",
        "doctor_id": None,
        "paciente_id": None,
        "user_id": "+526649876543",
        "session_id": "test-session",
        "es_admin": False,
        "usuario_registrado": False
    }


@pytest.fixture
def estado_con_mensaje_chat():
    """Estado con mensaje de chat casual"""
    return {
        "messages": [HumanMessage(content="Hola, buenos días")],
        "tipo_usuario": "paciente_externo",
        "user_id": "+526641111111",
        "session_id": "test-session"
    }


@pytest.fixture
def mock_db_connection(mocker):
    """Mock de conexión a base de datos"""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    
    # Configurar cursor para retornar resultados vacíos por defecto
    mock_cursor.fetchone.return_value = None
    mock_cursor.fetchall.return_value = []
    
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_conn.__enter__.return_value = mock_conn
    
    mocker.patch('psycopg.connect', return_value=mock_conn)
    
    return mock_conn


@pytest.fixture
def mock_registrar_clasificacion(mocker):
    """Mock para función de registro en BD"""
    return mocker.patch('src.nodes.filtrado_inteligente_node.registrar_clasificacion_bd')


@pytest.fixture
def pacientes_mock():
    """Datos de pacientes de prueba"""
    return [
        {
            "id": 1,
            "nombre": "Juan Pérez",
            "telefono": "+526641111111",
            "email": "juan@example.com",
            "ultima_cita": datetime(2026, 1, 20, tzinfo=TIMEZONE),
            "total_citas": 3,
            "alergias": "Penicilina"
        },
        {
            "id": 2,
            "nombre": "María González",
            "telefono": "+526642222222",
            "email": None,
            "ultima_cita": None,
            "total_citas": 0,
            "alergias": None
        }
    ]


@pytest.fixture
def citas_del_dia_mock():
    """Citas del día de prueba"""
    return [
        {
            "id": 1,
            "paciente_id": 1,
            "paciente_nombre": "Juan Pérez",
            "fecha_hora_inicio": datetime(2026, 1, 28, 10, 30, tzinfo=TIMEZONE).isoformat(),
            "fecha_hora_fin": datetime(2026, 1, 28, 11, 0, tzinfo=TIMEZONE).isoformat(),
            "estado": "programada",
            "motivo": "Seguimiento",
            "fue_asignacion_automatica": True
        }
    ]


@pytest.fixture
def estadisticas_doctor_mock():
    """Estadísticas de doctor de prueba"""
    return {
        "doctor_id": 1,
        "citas_hoy": 3,
        "citas_semana": 12,
        "pacientes_totales": 25,
        "proxima_cita": None
    }


@pytest.fixture
def mock_herramientas_medicas(mocker):
    """Mock de herramientas médicas"""
    mock_tool = Mock()
    mock_tool.name = "crear_paciente_medico"
    mock_tool.description = "Crea un nuevo paciente"
    mock_tool.invoke.return_value = "✅ Paciente creado"
    
    return mocker.patch('src.nodes.ejecucion_medica_node.MEDICAL_TOOLS', [mock_tool])


@pytest.fixture
def mock_actualizar_turnos(mocker):
    """Mock para actualización de turnos"""
    return mocker.patch('src.nodes.ejecucion_medica_node.actualizar_control_turnos', return_value=True)


@pytest.fixture
def herramientas_disponibles_mock():
    """Herramientas disponibles de prueba"""
    return [
        {"id_tool": "consultar_slots_disponibles", "description": "Consulta horarios disponibles"},
        {"id_tool": "agendar_cita_medica_completa", "description": "Agenda una cita médica"},
        {"id_tool": "crear_paciente_medico", "description": "Crea un nuevo paciente"}
    ]


@pytest.fixture
def mock_obtener_herramientas(mocker, herramientas_disponibles_mock):
    """Mock para obtener herramientas según clasificación"""
    return mocker.patch(
        'src.nodes.seleccion_herramientas_node.obtener_herramientas_segun_clasificacion',
        return_value=herramientas_disponibles_mock
    )


@pytest.fixture
def limpiar_clasificaciones(mock_db_connection):
    """Limpia clasificaciones de prueba después del test"""
    yield
    # Cleanup se hace automáticamente con el mock
    pass


@pytest.fixture
def verificar_doctores(mock_db_connection):
    """Verifica que existan doctores de prueba"""
    # Configurar mock para simular que existen doctores
    mock_db_connection.cursor.return_value.__enter__.return_value.fetchone.return_value = (1,)
    return mock_db_connection
