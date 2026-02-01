"""
Tests para Nodo N7: Persistencia Episódica

✅ Command pattern
✅ Estado conversacional
✅ Embedding generation
✅ psycopg3 integration
"""

import pytest
import sys
import os
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock
from langgraph.types import Command

# Set dummy env vars to avoid OpenAI initialization errors and config errors
os.environ.setdefault("OPENAI_API_KEY", "sk-dummy-key-for-testing")
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-dummy-key-for-testing")
os.environ.setdefault("DEEPSEEK_API_KEY", "sk-dummy-key-for-testing")
os.environ.setdefault("POSTGRES_HOST", "localhost")
# Port 5434 matches project configuration (avoids conflicts with system PostgreSQL on 5432)
os.environ.setdefault("POSTGRES_PORT", "5434")
os.environ.setdefault("POSTGRES_DB", "test_db")
os.environ.setdefault("POSTGRES_USER", "test_user")
os.environ.setdefault("POSTGRES_PASSWORD", "test_pass")
os.environ.setdefault("GOOGLE_SERVICE_ACCOUNT_FILE", "/tmp/dummy.json")
os.environ.setdefault("GOOGLE_CALENDAR_ID", "dummy@group.calendar.google.com")
os.environ.setdefault("DEFAULT_TIMEZONE", "America/Tijuana")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5434/test_db")

# Import directly from module file to avoid __init__.py circular imports
sys.path.insert(0, str(Path(__file__).parent.parent))


@patch('src.nodes.persistencia_episodica_node.psycopg.connect')
@patch('src.nodes.persistencia_episodica_node.generar_embedding_optimizado')
def test_retorna_command(mock_embedding, mock_conn):
    """Nodo retorna Command."""
    from src.nodes.persistencia_episodica_node import nodo_persistencia_episodica
    
    # Mock embedding
    mock_embedding.return_value = [0.1] * 384
    
    # Mock database connection
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = [123]
    
    mock_context_manager = MagicMock()
    mock_context_manager.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
    mock_conn.return_value = mock_context_manager
    
    estado = {
        'resumen_actual': 'Test resumen de conversación con suficiente contenido',
        'user_id': 'test_user',
        'session_id': 'test_session',
        'estado_conversacion': 'completado'
    }
    
    resultado = nodo_persistencia_episodica(estado)
    
    assert isinstance(resultado, Command)
    assert resultado.goto == "END"
    assert resultado.update['episodio_guardado'] == True
    assert 'episodio_id' in resultado.update


def test_detecta_estado_sin_persistencia():
    """Salta persistencia si estado no lo requiere."""
    from src.nodes.persistencia_episodica_node import nodo_persistencia_episodica
    
    estado = {
        'resumen_actual': 'Test resumen con contenido',
        'user_id': 'test_user',
        'session_id': 'test_session',
        'estado_conversacion': 'inicial'
    }
    
    resultado = nodo_persistencia_episodica(estado)
    
    assert isinstance(resultado, Command)
    assert resultado.goto == "END"
    assert resultado.update['episodio_guardado'] == False


@pytest.mark.parametrize("estado", [
    'esperando_confirmacion',
    'recolectando_datos',
    'procesando_pago',
    'inicial'
])
def test_detecta_todos_estados_sin_persistencia(estado):
    """Detecta todos los estados que saltan persistencia."""
    from src.nodes.persistencia_episodica_node import nodo_persistencia_episodica
    
    state = {
        'resumen_actual': 'Test resumen con contenido',
        'user_id': 'test_user',
        'session_id': 'test_session',
        'estado_conversacion': estado
    }
    
    resultado = nodo_persistencia_episodica(state)
    
    assert isinstance(resultado, Command)
    assert resultado.update['episodio_guardado'] == False
    assert resultado.goto == "END"


def test_resumen_vacio_no_persiste():
    """No persiste si resumen está vacío."""
    from src.nodes.persistencia_episodica_node import nodo_persistencia_episodica
    
    estado = {
        'resumen_actual': '',
        'user_id': 'test_user',
        'session_id': 'test_session',
        'estado_conversacion': 'completado'
    }
    
    resultado = nodo_persistencia_episodica(estado)
    
    assert isinstance(resultado, Command)
    assert resultado.update['episodio_guardado'] == False
    assert resultado.goto == "END"


def test_resumen_muy_corto_no_persiste():
    """No persiste si resumen es muy corto (< 10 caracteres)."""
    from src.nodes.persistencia_episodica_node import nodo_persistencia_episodica
    
    estado = {
        'resumen_actual': 'Corto',
        'user_id': 'test_user',
        'session_id': 'test_session',
        'estado_conversacion': 'completado'
    }
    
    resultado = nodo_persistencia_episodica(estado)
    
    assert isinstance(resultado, Command)
    assert resultado.update['episodio_guardado'] == False
    assert resultado.goto == "END"


@patch('src.nodes.persistencia_episodica_node.generar_embedding_optimizado')
def test_error_embedding_retorna_command(mock_embedding):
    """Error en generación de embedding retorna Command con False."""
    from src.nodes.persistencia_episodica_node import nodo_persistencia_episodica
    
    # Simular error en embedding
    mock_embedding.return_value = None
    
    estado = {
        'resumen_actual': 'Test resumen de conversación válido',
        'user_id': 'test_user',
        'session_id': 'test_session',
        'estado_conversacion': 'completado'
    }
    
    resultado = nodo_persistencia_episodica(estado)
    
    assert isinstance(resultado, Command)
    assert resultado.goto == "END"
    assert resultado.update['episodio_guardado'] == False


@patch('src.nodes.persistencia_episodica_node.psycopg.connect')
@patch('src.nodes.persistencia_episodica_node.generar_embedding_optimizado')
def test_error_bd_retorna_command(mock_embedding, mock_conn):
    """Error en BD retorna Command con False."""
    from src.nodes.persistencia_episodica_node import nodo_persistencia_episodica
    
    # Mock embedding exitoso
    mock_embedding.return_value = [0.1] * 384
    
    # Simular error en BD
    mock_conn.side_effect = Exception("Database error")
    
    estado = {
        'resumen_actual': 'Test resumen de conversación válido',
        'user_id': 'test_user',
        'session_id': 'test_session',
        'estado_conversacion': 'completado'
    }
    
    resultado = nodo_persistencia_episodica(estado)
    
    assert isinstance(resultado, Command)
    assert resultado.goto == "END"
    assert resultado.update['episodio_guardado'] == False


@patch('src.nodes.persistencia_episodica_node.generate_embedding')
def test_generar_embedding_optimizado_usa_singleton(mock_generate):
    """generar_embedding_optimizado usa el singleton del modelo."""
    from src.nodes.persistencia_episodica_node import generar_embedding_optimizado
    
    mock_generate.return_value = [0.1] * 384
    
    resultado = generar_embedding_optimizado("Test texto")
    
    assert resultado is not None
    assert len(resultado) == 384
    mock_generate.assert_called_once_with("Test texto")


@patch('src.nodes.persistencia_episodica_node.generate_embedding')
def test_generar_embedding_optimizado_maneja_error(mock_generate):
    """generar_embedding_optimizado maneja errores correctamente."""
    from src.nodes.persistencia_episodica_node import generar_embedding_optimizado
    
    # Simular error
    mock_generate.side_effect = Exception("Model error")
    
    resultado = generar_embedding_optimizado("Test texto")
    
    assert resultado is None


def test_wrapper_retorna_command():
    """Wrapper retorna Command."""
    from src.nodes.persistencia_episodica_node import nodo_persistencia_episodica_wrapper
    
    estado = {
        'resumen_actual': '',
        'user_id': 'test_user',
        'session_id': 'test_session',
        'estado_conversacion': 'inicial'
    }
    
    resultado = nodo_persistencia_episodica_wrapper(estado)
    
    assert isinstance(resultado, Command)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
