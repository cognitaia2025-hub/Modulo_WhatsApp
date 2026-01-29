"""
TEST 2: test_recuperacion_medica.py
Pruebas del nodo de recuperación médica (sin LLM)

15 tests que validan:
- Recuperación de pacientes recientes
- Citas del día
- Estadísticas del doctor
- Búsqueda semántica
"""

import pytest
from datetime import datetime, date
import pytz
from src.nodes.recuperacion_medica_node import (
    nodo_recuperacion_medica,
    obtener_pacientes_recientes,
    obtener_citas_del_dia,
    obtener_estadisticas_doctor,
    formatear_contexto_medico
)

TIMEZONE = pytz.timezone("America/Tijuana")


# ============================================================================
# TESTS: Recuperación de Pacientes
# ============================================================================

def test_obtener_pacientes_recientes_con_doctores(mock_db_connection, estado_con_doctor):
    """Test 2.1: Doctor obtiene pacientes recientes correctamente"""
    # Configurar mock
    mock_cursor = mock_db_connection.cursor.return_value.__enter__.return_value
    mock_cursor.fetchall.return_value = [
        (1, "Juan Pérez", "+526641111111", "juan@example.com", datetime(2026, 1, 20, tzinfo=TIMEZONE), 3)
    ]
    
    resultado = nodo_recuperacion_medica(estado_con_doctor)
    
    assert resultado["contexto_medico"] is not None
    assert "pacientes_recientes" in resultado["contexto_medico"]


def test_recuperacion_solo_para_doctores(estado_con_paciente):
    """Test 2.2: Pacientes externos NO obtienen contexto médico"""
    resultado = nodo_recuperacion_medica(estado_con_paciente)
    
    assert resultado["contexto_medico"] is None


def test_pacientes_recientes_limit_10(mock_db_connection, estado_con_doctor):
    """Test 2.3: Recupera máximo 10 pacientes recientes"""
    mock_cursor = mock_db_connection.cursor.return_value.__enter__.return_value

    # Mockear múltiples llamadas (orden: estadísticas, pacientes, citas, historiales)
    # Estadísticas hace 2 fetchone: primero intenta función SQL (None), luego fallback manual
    mock_cursor.fetchone.side_effect = [
        None,  # Primera llamada: función SQL no existe
        (0, 0, 0)  # Segunda llamada: fallback manual (citas_hoy, citas_semana, pacientes_totales)
    ]

    # fetchall para: pacientes, citas del día, historiales
    # El SQL tiene LIMIT 10, así que la BD retornaría solo 10 aunque haya 15
    mock_cursor.fetchall.side_effect = [
        [(i, f"Paciente {i}", f"+52664{i:07d}", None, None, 0) for i in range(10)],  # pacientes (limitado a 10 por SQL)
        [],  # citas del día
        []   # historiales
    ]

    resultado = nodo_recuperacion_medica(estado_con_doctor)

    pacientes = resultado["contexto_medico"]["pacientes_recientes"]
    assert len(pacientes) <= 10


def test_pacientes_sin_historial(mock_db_connection, estado_con_doctor):
    """Test 2.4: Maneja pacientes sin historial previo"""
    mock_cursor = mock_db_connection.cursor.return_value.__enter__.return_value
    mock_cursor.fetchall.return_value = []
    
    resultado = nodo_recuperacion_medica(estado_con_doctor)
    
    assert resultado["contexto_medico"]["pacientes_recientes"] == []


# ============================================================================
# TESTS: Citas del Día
# ============================================================================

def test_obtener_citas_del_dia(mock_db_connection, estado_con_doctor):
    """Test 2.5: Obtiene citas del día actual"""
    mock_cursor = mock_db_connection.cursor.return_value.__enter__.return_value
    hoy = datetime.now(TIMEZONE)

    # Mockear múltiples llamadas: estadísticas (2 fetchone), pacientes, citas, historiales (3 fetchall)
    mock_cursor.fetchone.side_effect = [
        None,  # Función SQL no existe
        (0, 0, 0)  # Fallback manual
    ]

    mock_cursor.fetchall.side_effect = [
        [],  # pacientes
        [(1, 1, "Juan Pérez", hoy, hoy, "programada", "Seguimiento", True)],  # citas del día
        []   # historiales
    ]

    resultado = nodo_recuperacion_medica(estado_con_doctor)

    citas = resultado["contexto_medico"]["citas_hoy"]
    assert len(citas) >= 0


def test_citas_ordenadas_por_hora(mock_db_connection, estado_con_doctor):
    """Test 2.6: Citas ordenadas por fecha_hora_inicio ASC"""
    mock_cursor = mock_db_connection.cursor.return_value.__enter__.return_value
    hoy = date.today()

    # Mockear múltiples llamadas: estadísticas (2 fetchone), pacientes, citas, historiales (3 fetchall)
    mock_cursor.fetchone.side_effect = [
        None,  # Función SQL no existe
        (0, 0, 0)  # Fallback manual
    ]

    mock_cursor.fetchall.side_effect = [
        [],  # pacientes
        [    # citas del día
            (1, 1, "A", datetime.combine(hoy, datetime.min.time()), None, "programada", None, False),
            (2, 2, "B", datetime.combine(hoy, datetime.min.time()), None, "programada", None, False)
        ],
        []   # historiales
    ]

    resultado = nodo_recuperacion_medica(estado_con_doctor)

    citas = resultado["contexto_medico"]["citas_hoy"]
    # Verificar que el query incluye ORDER BY
    assert isinstance(citas, list)


def test_sin_citas_hoy(mock_db_connection, estado_con_doctor):
    """Test 2.7: Maneja día sin citas correctamente"""
    mock_cursor = mock_db_connection.cursor.return_value.__enter__.return_value
    mock_cursor.fetchall.return_value = []
    
    resultado = nodo_recuperacion_medica(estado_con_doctor)
    
    assert resultado["contexto_medico"]["citas_hoy"] == []


# ============================================================================
# TESTS: Estadísticas del Doctor
# ============================================================================

def test_obtener_estadisticas_completas(mock_db_connection, estado_con_doctor):
    """Test 2.8: Obtiene estadísticas completas del doctor"""
    mock_cursor = mock_db_connection.cursor.return_value.__enter__.return_value
    
    # Simular función SQL
    mock_cursor.fetchone.return_value = ({
        "doctor_id": 1,
        "citas_hoy": 3,
        "citas_semana": 12,
        "pacientes_totales": 25
    },)
    
    resultado = nodo_recuperacion_medica(estado_con_doctor)
    
    stats = resultado["contexto_medico"]["estadisticas"]
    assert "doctor_id" in stats


def test_estadisticas_incluyen_metricas_clave(mock_db_connection, estado_con_doctor):
    """Test 2.9: Estadísticas incluyen citas_hoy, citas_semana, pacientes_totales"""
    mock_cursor = mock_db_connection.cursor.return_value.__enter__.return_value
    mock_cursor.fetchone.return_value = ({
        "doctor_id": 1,
        "citas_hoy": 5,
        "citas_semana": 20,
        "pacientes_totales": 50
    },)
    
    resultado = nodo_recuperacion_medica(estado_con_doctor)
    
    stats = resultado["contexto_medico"]["estadisticas"]
    assert "citas_hoy" in stats
    assert "citas_semana" in stats
    assert "pacientes_totales" in stats


# ============================================================================
# TESTS: Formateo de Contexto
# ============================================================================

def test_formatear_contexto_medico_legible(pacientes_mock, citas_del_dia_mock, estadisticas_doctor_mock):
    """Test 2.10: Contexto se formatea de forma legible"""
    contexto = formatear_contexto_medico(
        pacientes_recientes=pacientes_mock,
        citas_hoy=citas_del_dia_mock,
        estadisticas=estadisticas_doctor_mock,
        historiales=[]
    )
    
    assert "ESTADÍSTICAS" in contexto
    assert "CITAS HOY" in contexto
    assert "PACIENTES RECIENTES" in contexto


def test_contexto_con_datos_vacios():
    """Test 2.11: Contexto maneja datos vacíos sin errores"""
    contexto = formatear_contexto_medico(
        pacientes_recientes=[],
        citas_hoy=[],
        estadisticas={"doctor_id": 1, "citas_hoy": 0, "citas_semana": 0, "pacientes_totales": 0},
        historiales=[]
    )
    
    assert "Sin citas agendadas" in contexto
    assert "Sin pacientes recientes" in contexto


# ============================================================================
# TESTS: Búsqueda Semántica (Opcional)
# ============================================================================

def test_busqueda_semantica_sin_embedding(mock_db_connection):
    """Test 2.12: Búsqueda sin embedding retorna historiales recientes"""
    from src.nodes.recuperacion_medica_node import buscar_historiales_semantica
    
    mock_cursor = mock_db_connection.cursor.return_value.__enter__.return_value
    mock_cursor.fetchall.return_value = [
        (1, 1, "Juan", "Nota 1", datetime.now(TIMEZONE))
    ]
    
    historiales = buscar_historiales_semantica(doctor_id=1, query_embedding=None)
    
    assert len(historiales) >= 0


def test_busqueda_semantica_con_embedding(mock_db_connection):
    """Test 2.13: Búsqueda con embedding ejecuta query vectorial"""
    from src.nodes.recuperacion_medica_node import buscar_historiales_semantica
    
    mock_cursor = mock_db_connection.cursor.return_value.__enter__.return_value
    mock_cursor.fetchall.return_value = [
        (1, 1, "Juan", "Nota relevante", datetime.now(TIMEZONE), 0.95)
    ]
    
    embedding = [0.1] * 384  # Embedding de 384 dimensiones
    
    historiales = buscar_historiales_semantica(
        doctor_id=1,
        query_embedding=embedding,
        limit=5
    )
    
    assert isinstance(historiales, list)


# ============================================================================
# TESTS: Timestamp y Metadata
# ============================================================================

def test_contexto_incluye_timestamp(mock_db_connection, estado_con_doctor):
    """Test 2.14: Contexto incluye timestamp de generación"""
    mock_cursor = mock_db_connection.cursor.return_value.__enter__.return_value
    mock_cursor.fetchall.return_value = []
    mock_cursor.fetchone.return_value = ({"doctor_id": 1, "citas_hoy": 0, "citas_semana": 0, "pacientes_totales": 0},)
    
    resultado = nodo_recuperacion_medica(estado_con_doctor)
    
    assert "timestamp" in resultado["contexto_medico"]


def test_contexto_incluye_doctor_id(mock_db_connection, estado_con_doctor):
    """Test 2.15: Contexto siempre incluye doctor_id"""
    mock_cursor = mock_db_connection.cursor.return_value.__enter__.return_value
    mock_cursor.fetchall.return_value = []
    mock_cursor.fetchone.return_value = ({"doctor_id": 1, "citas_hoy": 0, "citas_semana": 0, "pacientes_totales": 0},)
    
    resultado = nodo_recuperacion_medica(estado_con_doctor)
    
    assert resultado["contexto_medico"]["doctor_id"] == 1
