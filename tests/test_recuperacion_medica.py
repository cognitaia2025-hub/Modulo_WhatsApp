"""
Tests para Nodo N3B: Recuperación Médica

✅ Usa CSV fixtures para tests rápidos
✅ Tests de búsqueda semántica con embeddings
✅ Tests de Command pattern
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from langchain_core.messages import HumanMessage
from langgraph.types import Command

from src.nodes.recuperacion_medica_node import (
    nodo_recuperacion_medica,
    obtener_pacientes_recientes,
    obtener_citas_del_dia,
    obtener_estadisticas_doctor,
    buscar_historiales_semantica,
    generar_embedding
)

# ==================== FIXTURES ====================

@pytest.fixture
def estado_base_doctor():
    """Estado base para tests de doctor."""
    return {
        'doctor_id': 1,
        'tipo_usuario': 'doctor',
        'messages': [HumanMessage(content="Busca a Juan Pérez")],
        'estado_conversacion': 'inicial'
    }

@pytest.fixture
def estado_no_doctor():
    """Estado de usuario que NO es doctor."""
    return {
        'tipo_usuario': 'paciente_externo',
        'messages': [HumanMessage(content="Hola")],
        'estado_conversacion': 'inicial'
    }

# ==================== TESTS BÁSICOS ====================

@patch('src.nodes.recuperacion_medica_node.obtener_estadisticas_doctor')
@patch('src.nodes.recuperacion_medica_node.obtener_pacientes_recientes')
@patch('src.nodes.recuperacion_medica_node.obtener_citas_del_dia')
@patch('src.nodes.recuperacion_medica_node.buscar_historiales_semantica')
@patch('src.nodes.recuperacion_medica_node.generar_embedding')
def test_recuperacion_medica_basica(mock_embed, mock_hist, mock_citas, mock_pac, mock_stats, estado_base_doctor):
    """Test básico: Recupera contexto médico correctamente."""
    mock_stats.return_value = {'citas_hoy': 5, 'citas_semana': 20}
    mock_pac.return_value = [{'id': 1, 'nombre': 'Juan Pérez'}]
    mock_citas.return_value = [{'id': 1, 'paciente_nombre': 'María'}]
    mock_hist.return_value = [{'id': 1, 'nota': 'Consulta general'}]
    mock_embed.return_value = [0.1] * 384
    
    resultado = nodo_recuperacion_medica(estado_base_doctor)
    
    assert isinstance(resultado, Command)
    assert resultado.goto == "seleccion_herramientas"
    assert 'contexto_medico' in resultado.update
    assert resultado.update['contexto_medico']['doctor_id'] == 1


def test_no_doctor_salta_recuperacion(estado_no_doctor):
    """Usuario que NO es doctor → salta recuperación."""
    resultado = nodo_recuperacion_medica(estado_no_doctor)
    
    assert isinstance(resultado, Command)
    assert resultado.goto == "generacion_resumen"
    assert resultado.update['contexto_medico'] is None


def test_detecta_estado_activo():
    """Detecta flujo activo y salta recuperación."""
    estado = {
        'doctor_id': 1,
        'tipo_usuario': 'doctor',
        'messages': [HumanMessage(content="Test")],
        'estado_conversacion': 'ejecutando_herramienta'
    }
    
    resultado = nodo_recuperacion_medica(estado)
    
    assert isinstance(resultado, Command)
    assert resultado.goto == "seleccion_herramientas"
    assert resultado.update['contexto_medico'] is None


# ==================== TESTS BÚSQUEDA SEMÁNTICA ====================

@patch('src.nodes.recuperacion_medica_node.psycopg.connect')
def test_busqueda_semantica_con_embedding(mock_connect):
    """Búsqueda semántica funciona con embedding."""
    mock_cursor = Mock()
    mock_cursor.fetchall.return_value = [
        (1, 101, 'Juan Pérez', 'Consulta general', '2026-01-15', 0.85)
    ]
    mock_connect.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
    
    embedding = [0.1] * 384
    historiales = buscar_historiales_semantica(1, query_embedding=embedding, limit=5)
    
    assert len(historiales) == 1
    assert historiales[0]['similitud'] == 0.85
    assert historiales[0]['paciente_nombre'] == 'Juan Pérez'


def test_busqueda_semantica_sin_embedding():
    """Sin embedding → retorna lista vacía."""
    historiales = buscar_historiales_semantica(1, query_embedding=None, limit=5)
    
    assert historiales == []


@patch('src.nodes.recuperacion_medica_node.get_embedding_model')
def test_generar_embedding_funciona(mock_model):
    """Genera embedding de 384 dimensiones."""
    mock_model.return_value.encode.return_value = Mock(tolist=lambda: [0.1] * 384)
    
    embedding = generar_embedding("Busca paciente Juan")
    
    assert embedding is not None
    assert len(embedding) == 384


@patch('src.nodes.recuperacion_medica_node.get_embedding_model')
def test_generar_embedding_maneja_error(mock_model):
    """Maneja error al generar embedding."""
    mock_model.side_effect = Exception("Model error")
    
    embedding = generar_embedding("Test")
    
    assert embedding is None


# ==================== TESTS FUNCIONES AUXILIARES ====================

@patch('src.nodes.recuperacion_medica_node.psycopg.connect')
def test_obtener_pacientes_recientes(mock_connect):
    """Obtiene últimos pacientes correctamente."""
    mock_cursor = Mock()
    mock_cursor.fetchall.return_value = [
        (1, 'Juan Pérez', '+526641234567', 'juan@test.com', '2026-01-31', 5)
    ]
    mock_connect.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
    
    pacientes = obtener_pacientes_recientes(1, limit=10)
    
    assert len(pacientes) == 1
    assert pacientes[0]['nombre'] == 'Juan Pérez'
    assert pacientes[0]['total_citas'] == 5


@patch('src.nodes.recuperacion_medica_node.psycopg.connect')
def test_obtener_citas_del_dia(mock_connect):
    """Obtiene citas del día correctamente."""
    mock_cursor = Mock()
    mock_cursor.fetchall.return_value = [
        (1, 'María García', '2026-01-31 09:00:00', 'agendada', 'Consulta')
    ]
    mock_connect.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
    
    citas = obtener_citas_del_dia(1)
    
    assert len(citas) == 1
    assert citas[0]['paciente_nombre'] == 'María García'


@patch('src.nodes.recuperacion_medica_node.psycopg.connect')
def test_obtener_estadisticas_doctor(mock_connect):
    """Obtiene estadísticas correctamente."""
    mock_cursor = Mock()
    mock_cursor.fetchone.side_effect = [
        ({'citas_hoy': 5, 'citas_semana': 20, 'pacientes_totales': 100},)
    ]
    mock_connect.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
    
    stats = obtener_estadisticas_doctor(1)
    
    assert stats['citas_hoy'] == 5
    assert stats['citas_semana'] == 20


# ==================== TESTS EDGE CASES ====================

def test_doctor_id_none():
    """doctor_id None → salta recuperación."""
    estado = {
        'doctor_id': None,
        'tipo_usuario': 'doctor',
        'messages': [HumanMessage(content="Test")]
    }
    
    resultado = nodo_recuperacion_medica(estado)
    
    assert isinstance(resultado, Command)
    assert resultado.update['contexto_medico'] is None


@patch('src.nodes.recuperacion_medica_node.obtener_estadisticas_doctor')
def test_error_en_query_no_rompe_flujo(mock_stats, estado_base_doctor):
    """Error en query no rompe el flujo."""
    mock_stats.side_effect = Exception("DB error")
    
    # Patch otras funciones para que funcionen
    with patch('src.nodes.recuperacion_medica_node.obtener_pacientes_recientes', return_value=[]):
        with patch('src.nodes.recuperacion_medica_node.obtener_citas_del_dia', return_value=[]):
            with patch('src.nodes.recuperacion_medica_node.buscar_historiales_semantica', return_value=[]):
                with patch('src.nodes.recuperacion_medica_node.generar_embedding', return_value=None):
                    resultado = nodo_recuperacion_medica(estado_base_doctor)
    
    assert isinstance(resultado, Command)
    assert resultado.goto == "seleccion_herramientas"


def test_mensaje_vacio_funciona():
    """Mensaje vacío no rompe generación de embedding."""
    estado = {
        'doctor_id': 1,
        'tipo_usuario': 'doctor',
        'messages': [],
        'estado_conversacion': 'inicial'
    }
    
    with patch('src.nodes.recuperacion_medica_node.obtener_estadisticas_doctor', return_value={}):
        with patch('src.nodes.recuperacion_medica_node.obtener_pacientes_recientes', return_value=[]):
            with patch('src.nodes.recuperacion_medica_node.obtener_citas_del_dia', return_value=[]):
                with patch('src.nodes.recuperacion_medica_node.buscar_historiales_semantica', return_value=[]):
                    resultado = nodo_recuperacion_medica(estado)
    
    assert isinstance(resultado, Command)
