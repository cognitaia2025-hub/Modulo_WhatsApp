"""
Tests para Nodo N3A: Recuperación Episódica

✅ Command pattern
✅ psycopg3
✅ Estado conversacional
✅ Búsqueda semántica
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from langchain_core.messages import HumanMessage
from langgraph.types import Command

# Import directly from module file to avoid __init__.py circular imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.nodes.recuperacion_episodica_node import (
    nodo_recuperacion_episodica,
    buscar_episodios_similares,
    formatear_contexto_episodico,
    extraer_ultimo_mensaje_usuario,
    SIMILARITY_THRESHOLD,
    ESTADOS_FLUJO_ACTIVO
)

# ==================== FIXTURES ====================

@pytest.fixture
def estado_base():
    """Estado base con mensaje y user_id."""
    return {
        'user_id': '+526641234567',
        'messages': [HumanMessage(content="¿Qué eventos tengo?")],
        'estado_conversacion': 'inicial'
    }

@pytest.fixture
def episodios_mock():
    """Episodios de ejemplo para tests."""
    return [
        {
            'resumen': 'Usuario creó evento "Reunión equipo" para mañana',
            'timestamp': datetime(2026, 1, 30, 10, 0),
            'similarity': 0.85,
            'metadata': {'tipo': 'crear_evento'}
        },
        {
            'resumen': 'Usuario consultó calendario de la semana',
            'timestamp': datetime(2026, 1, 29, 15, 30),
            'similarity': 0.72,
            'metadata': {'tipo': 'consulta'}
        }
    ]

# ==================== TESTS BÁSICOS ====================

@patch('src.nodes.recuperacion_episodica_node.generate_embedding')
@patch('src.nodes.recuperacion_episodica_node.buscar_episodios_similares')
def test_recuperacion_episodica_basica(mock_buscar, mock_embed, estado_base, episodios_mock):
    """Test básico: Recupera episodios correctamente."""
    mock_embed.return_value = [0.1] * 384
    mock_buscar.return_value = episodios_mock
    
    resultado = nodo_recuperacion_episodica(estado_base)
    
    assert isinstance(resultado, Command)
    assert resultado.goto == "seleccion_herramientas"
    assert 'contexto_episodico' in resultado.update
    assert resultado.update['contexto_episodico']['episodios_recuperados'] == 2


def test_sin_user_id():
    """Sin user_id → retorna Command con error."""
    estado = {
        'messages': [HumanMessage(content="Test")],
        'estado_conversacion': 'inicial'
    }
    
    resultado = nodo_recuperacion_episodica(estado)
    
    assert isinstance(resultado, Command)
    assert resultado.goto == "seleccion_herramientas"
    assert resultado.update['contexto_episodico']['error'] == 'missing_user_id'


def test_detecta_estado_activo():
    """Detecta flujo activo y salta recuperación."""
    estado = {
        'user_id': '+526641234567',
        'messages': [HumanMessage(content="Test")],
        'estado_conversacion': 'ejecutando_herramienta'
    }
    
    resultado = nodo_recuperacion_episodica(estado)
    
    assert isinstance(resultado, Command)
    assert resultado.goto == "seleccion_herramientas"
    assert resultado.update['contexto_episodico'] is None


@pytest.mark.parametrize("estado", ESTADOS_FLUJO_ACTIVO)
def test_detecta_todos_estados_activos(estado):
    """Detecta todos los estados de flujo activo."""
    state = {
        'user_id': '+526641234567',
        'messages': [HumanMessage(content="Test")],
        'estado_conversacion': estado
    }
    
    resultado = nodo_recuperacion_episodica(state)
    
    assert isinstance(resultado, Command)
    assert resultado.update['contexto_episodico'] is None


def test_mensaje_vacio():
    """Mensaje vacío → retorna Command sin episodios."""
    estado = {
        'user_id': '+526641234567',
        'messages': [],
        'estado_conversacion': 'inicial'
    }
    
    resultado = nodo_recuperacion_episodica(estado)
    
    assert isinstance(resultado, Command)
    assert resultado.update['contexto_episodico']['episodios_recuperados'] == 0


# ==================== TESTS BÚSQUEDA SEMÁNTICA ====================

@patch('src.nodes.recuperacion_episodica_node.psycopg.connect')
def test_buscar_episodios_con_resultados(mock_connect, episodios_mock):
    """Búsqueda semántica retorna episodios correctamente."""
    mock_cursor = Mock()
    mock_cursor.fetchall.return_value = episodios_mock
    mock_connect.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
    
    embedding = [0.1] * 384
    episodios = buscar_episodios_similares('+526641234567', embedding)
    
    assert len(episodios) == 2
    assert episodios[0]['similarity'] == 0.85


@patch('src.nodes.recuperacion_episodica_node.psycopg.connect')
def test_buscar_episodios_sin_resultados(mock_connect):
    """Sin episodios sobre threshold → lista vacía."""
    mock_cursor = Mock()
    mock_cursor.fetchall.return_value = []
    mock_connect.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
    
    embedding = [0.1] * 384
    episodios = buscar_episodios_similares('+526641234567', embedding)
    
    assert episodios == []


@patch('src.nodes.recuperacion_episodica_node.psycopg.connect')
def test_query_usa_threshold_en_sql(mock_connect):
    """Query SQL incluye filtro threshold."""
    mock_cursor = Mock()
    mock_cursor.fetchall.return_value = []
    mock_connect.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
    
    embedding = [0.1] * 384
    buscar_episodios_similares('+526641234567', embedding, threshold=0.7)
    
    # Verificar que se llamó execute con threshold
    call_args = mock_cursor.execute.call_args
    assert call_args is not None
    query = call_args[0][0]
    assert ">=" in query  # Filtro threshold en SQL


# ==================== TESTS FORMATEO ====================

def test_formatear_contexto_con_episodios(episodios_mock):
    """Formatea episodios correctamente."""
    texto = formatear_contexto_episodico(episodios_mock)
    
    assert "CONVERSACIONES PREVIAS RELEVANTES" in texto
    assert "Reunión equipo" in texto
    assert "0.85" in texto
    assert "30/01/2026" in texto


def test_formatear_contexto_vacio():
    """Sin episodios → mensaje por defecto."""
    texto = formatear_contexto_episodico([])
    
    assert "No hay conversaciones previas" in texto


def test_formatear_contexto_trunca_largos():
    """Resúmenes largos se truncan."""
    episodio_largo = {
        'resumen': 'A' * 300,  # 300 caracteres
        'timestamp': datetime(2026, 1, 30),
        'similarity': 0.8,
        'metadata': {}
    }
    
    texto = formatear_contexto_episodico([episodio_largo])
    
    # Debe truncarse a ~200 chars
    assert "..." in texto
    assert len(texto) < 400


# ==================== TESTS AUXILIARES ====================

def test_extraer_ultimo_mensaje_humano():
    """Extrae último mensaje de tipo human."""
    estado = {
        'messages': [
            HumanMessage(content="Primero"),
            HumanMessage(content="Segundo")
        ]
    }
    
    mensaje = extraer_ultimo_mensaje_usuario(estado)
    assert mensaje == "Segundo"


def test_extraer_ultimo_mensaje_dict():
    """Extrae último mensaje formato dict."""
    estado = {
        'messages': [
            {'role': 'user', 'content': 'Test mensaje'}
        ]
    }
    
    mensaje = extraer_ultimo_mensaje_usuario(estado)
    assert mensaje == "Test mensaje"


# ==================== TESTS ERROR HANDLING ====================

@patch('src.nodes.recuperacion_episodica_node.generate_embedding')
def test_error_embedding_no_rompe_flujo(mock_embed, estado_base):
    """Error al generar embedding no bloquea flujo."""
    mock_embed.side_effect = Exception("Embedding error")
    
    resultado = nodo_recuperacion_episodica(estado_base)
    
    assert isinstance(resultado, Command)
    assert resultado.goto == "seleccion_herramientas"
    assert 'error' in resultado.update['contexto_episodico']


@patch('src.nodes.recuperacion_episodica_node.generate_embedding')
@patch('src.nodes.recuperacion_episodica_node.buscar_episodios_similares')
def test_error_busqueda_no_rompe_flujo(mock_buscar, mock_embed, estado_base):
    """Error en búsqueda no bloquea flujo."""
    mock_embed.return_value = [0.1] * 384
    mock_buscar.side_effect = Exception("DB error")
    
    resultado = nodo_recuperacion_episodica(estado_base)
    
    assert isinstance(resultado, Command)
    assert resultado.goto == "seleccion_herramientas"
