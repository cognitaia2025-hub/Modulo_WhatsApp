"""
Tests para Nodo N1: Cache de Sesión
"""

import pytest
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from langchain_core.messages import HumanMessage, AIMessage

# Añadir path del proyecto
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.nodes.cache_sesion_node import (
    nodo_cache_sesion,
    buscar_sesion_activa,
    crear_nueva_sesion,
    actualizar_actividad_sesion,
    limpiar_sesiones_antiguas
)


# ==================== FIXTURES ====================

@pytest.fixture
def estado_base():
    """Estado base para tests"""
    return {
        'user_id': '+526641234567',
        'messages': [HumanMessage(content="Hola, necesito una cita")],
        'timestamp': datetime.now().isoformat()
    }


@pytest.fixture
def limpiar_sesiones_test():
    """Limpia sesiones de prueba después del test"""
    yield
    # Cleanup después del test
    import psycopg
    DATABASE_URL = os.getenv("DATABASE_URL")
    if DATABASE_URL:
        try:
            with psycopg.connect(DATABASE_URL) as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM user_sessions WHERE user_id LIKE '+5266412%'")
                    conn.commit()
        except:
            pass


# ==================== TESTS DE FUNCIONES AUXILIARES ====================

def test_crear_nueva_sesion(limpiar_sesiones_test):
    """Crea una nueva sesión en BD correctamente"""
    user_id = '+526641234567'
    phone_number = user_id
    
    thread_id = crear_nueva_sesion(user_id, phone_number)
    
    # Verificar formato del thread_id
    assert thread_id.startswith('thread_')
    assert len(thread_id) > 20  # thread_xxx_xxxxxxxx


def test_buscar_sesion_inexistente():
    """Retorna None si no hay sesión para el usuario"""
    user_id = '+526641111111'  # Usuario que no existe
    
    sesion = buscar_sesion_activa(user_id)
    
    assert sesion is None


def test_buscar_sesion_activa(limpiar_sesiones_test):
    """Encuentra sesión activa creada recientemente"""
    user_id = '+526641234568'
    
    # Crear sesión
    thread_id = crear_nueva_sesion(user_id, user_id)
    
    # Buscar sesión
    sesion = buscar_sesion_activa(user_id)
    
    assert sesion is not None
    assert sesion['thread_id'] == thread_id
    assert sesion['hours_inactive'] < 1  # Menos de 1 hora de inactividad


def test_actualizar_actividad_sesion(limpiar_sesiones_test):
    """Actualiza el timestamp de última actividad"""
    user_id = '+526641234569'
    
    # Crear sesión
    thread_id = crear_nueva_sesion(user_id, user_id)
    
    # Actualizar actividad
    resultado = actualizar_actividad_sesion(thread_id, user_id)
    
    assert resultado == True


def test_limpiar_sesiones_antiguas():
    """Limpia sesiones con más de 30 días"""
    # Este test solo verifica que la función se ejecuta sin error
    # No crea sesiones antiguas reales (requeriría manipular timestamps)
    
    count = limpiar_sesiones_antiguas()
    
    # Debería ejecutarse sin error
    assert count >= 0


# ==================== TESTS DEL NODO COMPLETO ====================

def test_nodo_cache_sesion_nueva(estado_base, limpiar_sesiones_test):
    """Crea nueva sesión si no existe"""
    state = estado_base.copy()
    
    resultado = nodo_cache_sesion(state)
    
    # Verificar que se creó sesión
    assert 'session_id' in resultado
    assert resultado['session_id'].startswith('thread_')
    assert resultado['sesion_expirada'] == True  # Nueva sesión
    assert 'timestamp' in resultado


def test_nodo_cache_sesion_activa(estado_base, limpiar_sesiones_test):
    """Recupera sesión activa existente"""
    state = estado_base.copy()
    
    # Primera llamada: crear sesión
    resultado1 = nodo_cache_sesion(state)
    thread_id = resultado1['session_id']
    
    # Segunda llamada: recuperar sesión activa
    state2 = estado_base.copy()
    resultado2 = nodo_cache_sesion(state2)
    
    # Verificar que recuperó la misma sesión
    assert resultado2['session_id'] == thread_id
    assert resultado2['sesion_expirada'] == False  # Sesión activa


def test_nodo_cache_preserva_mensajes(estado_base, limpiar_sesiones_test):
    """Los mensajes originales se preservan"""
    state = estado_base.copy()
    mensaje_original = "Hola, necesito una cita"
    
    resultado = nodo_cache_sesion(state)
    
    # Verificar que el mensaje original está
    mensajes = resultado['messages']
    assert len(mensajes) > 0
    assert any(mensaje_original in str(msg.content) for msg in mensajes)


def test_nodo_cache_sin_user_id():
    """Maneja gracefully cuando no hay user_id"""
    state = {
        'messages': [HumanMessage(content="test")]
    }
    
    resultado = nodo_cache_sesion(state)
    
    # Debería marcar como expirada pero no crashear
    assert resultado['sesion_expirada'] == True
    assert 'timestamp' in resultado


# ==================== TESTS DE INTEGRACIÓN ====================

def test_flujo_completo_conversacion(limpiar_sesiones_test):
    """Simula flujo completo de conversación con cache"""
    user_id = '+526641234570'
    
    # Mensaje 1: Usuario inicia conversación
    state1 = {
        'user_id': user_id,
        'messages': [HumanMessage(content="Hola")],
        'timestamp': datetime.now().isoformat()
    }
    resultado1 = nodo_cache_sesion(state1)
    
    # Verificar nueva sesión
    assert resultado1['sesion_expirada'] == True
    thread_id = resultado1['session_id']
    
    # Mensaje 2: Usuario continúa conversación (5 min después)
    state2 = {
        'user_id': user_id,
        'messages': [HumanMessage(content="Necesito una cita")],
        'timestamp': datetime.now().isoformat()
    }
    resultado2 = nodo_cache_sesion(state2)
    
    # Verificar que recuperó la misma sesión
    assert resultado2['session_id'] == thread_id
    assert resultado2['sesion_expirada'] == False
    
    # Mensaje 3: Usuario regresa después de 1 hora
    state3 = {
        'user_id': user_id,
        'messages': [HumanMessage(content="¿Para mañana?")],
        'timestamp': datetime.now().isoformat()
    }
    resultado3 = nodo_cache_sesion(state3)
    
    # Debería mantener la misma sesión (< 24h)
    assert resultado3['session_id'] == thread_id
    assert resultado3['sesion_expirada'] == False


def test_recuperacion_mensajes_con_checkpointer_mock(estado_base):
    """Test recuperación de mensajes con checkpointer mockeado"""
    # Mock del checkpointer
    mock_checkpointer = Mock()
    mock_checkpointer.get.return_value = {
        'channel_values': {
            'messages': [
                HumanMessage(content="Mensaje anterior 1"),
                AIMessage(content="Respuesta anterior 1"),
                HumanMessage(content="Mensaje anterior 2")
            ]
        }
    }
    
    state = estado_base.copy()
    state['session_id'] = 'thread_test_12345678'
    
    # Ejecutar nodo con checkpointer mock
    # Nota: Este test verifica la lógica aunque el wrapper real no pasa checkpointer
    from src.nodes.cache_sesion_node import recuperar_mensajes_checkpointer
    mensajes, estado_conversacion = recuperar_mensajes_checkpointer('thread_test_12345678', mock_checkpointer)
    
    # Verificar que recuperó mensajes
    assert len(mensajes) == 3
    assert mensajes[0].content == "Mensaje anterior 1"
    # Verificar que retorna estado por defecto si no existe
    assert estado_conversacion == 'inicial'


def test_cache_preserva_estado_conversacion(limpiar_sesiones_test):
    """Verifica que el cache preserve estado_conversacion entre mensajes."""
    # Mock del checkpointer con estado_conversacion
    mock_checkpointer = Mock()
    mock_checkpointer.get.return_value = {
        'channel_values': {
            'messages': [
                HumanMessage(content="Quiero cita"),
                AIMessage(content="¿Qué tipo de cita necesitas?")
            ],
            'estado_conversacion': 'mostrando_opciones'
        }
    }
    
    user_id = '+526641234571'
    thread_id = 'thread_526641234571_test123'
    
    # Mock buscar_sesion_activa para simular que hay una sesión activa
    with patch('src.nodes.cache_sesion_node.buscar_sesion_activa') as mock_buscar:
        mock_buscar.return_value = {
            'thread_id': thread_id,
            'last_activity': datetime.now(),
            'messages_count': 2,
            'hours_inactive': 0.5
        }
        
        # Mock actualizar_actividad_sesion
        with patch('src.nodes.cache_sesion_node.actualizar_actividad_sesion') as mock_actualizar:
            mock_actualizar.return_value = True
            
            # Mensaje: Recuperar sesión con estado conversacional
            state = {
                'user_id': user_id,
                'messages': [HumanMessage(content="La opción B")],
                'timestamp': datetime.now().isoformat()
            }
            
            # Ejecutar nodo con checkpointer mock
            resultado = nodo_cache_sesion(state, checkpointer=mock_checkpointer)
            
            # Verificar que recuperó el estado conversacional
            assert resultado['estado_conversacion'] == 'mostrando_opciones'
            assert resultado['sesion_expirada'] == False
            assert resultado['session_id'] == thread_id
            
            # Verificar que recuperó mensajes previos
            assert len(resultado['messages']) == 3  # 2 previos + 1 nuevo


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
