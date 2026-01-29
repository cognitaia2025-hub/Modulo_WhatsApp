"""
TEST 4: test_integration_identificacion.py
Pruebas de integración del nodo en el grafo

Validaciones:
- Nodo se integra correctamente en el grafo
- Estado se actualiza con user_info
- Flujo continúa después de identificación
- Maneja errores de BD gracefully
"""

import pytest
import os
from datetime import datetime
from unittest.mock import Mock, patch
from langchain_core.messages import HumanMessage

from src.nodes.identificacion_usuario_node import (
    nodo_identificacion_usuario,
    nodo_identificacion_usuario_wrapper,
    consultar_usuario_bd,
    DATABASE_URL,
    ADMIN_PHONE_NUMBER
)
import psycopg


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def estado_completo():
    """Estado completo del grafo para pruebas de integración"""
    return {
        "messages": [HumanMessage(content="Hola", metadata={"phone_number": ADMIN_PHONE_NUMBER})],
        "user_id": "",
        "session_id": "integration-test-123",
        "es_admin": False,
        "usuario_info": {},
        "usuario_registrado": False,
        "tipo_usuario": "",
        "doctor_id": None,
        "paciente_id": None,
        "contexto_episodico": None,
        "herramientas_seleccionadas": [],
        "requiere_herramientas": False,
        "resumen_actual": None,
        "sesion_expirada": False,
        "ultimo_listado": None,
        "timestamp": datetime.now().isoformat()
    }


# ============================================================================
# TESTS: Integración en el grafo
# ============================================================================

def test_nodo_retorna_estado_actualizado(estado_completo):
    """Test 4.1: Nodo retorna estado actualizado correctamente"""
    resultado = nodo_identificacion_usuario(estado_completo)
    
    # Debe retornar un diccionario tipo estado
    assert isinstance(resultado, dict)
    
    # Debe contener todos los campos del estado
    assert "user_id" in resultado
    assert "usuario_info" in resultado
    assert "es_admin" in resultado
    assert "tipo_usuario" in resultado
    assert "doctor_id" in resultado


def test_estado_user_id_se_actualiza(estado_completo):
    """Test 4.2: Estado user_id se actualiza con el phone_number"""
    resultado = nodo_identificacion_usuario(estado_completo)
    
    assert resultado["user_id"] != ""
    assert resultado["user_id"] == ADMIN_PHONE_NUMBER


def test_estado_usuario_info_se_llena(estado_completo):
    """Test 4.3: Estado usuario_info se llena con datos de BD"""
    resultado = nodo_identificacion_usuario(estado_completo)
    
    assert resultado["usuario_info"] != {}
    assert "phone_number" in resultado["usuario_info"]
    assert "display_name" in resultado["usuario_info"]
    assert "tipo_usuario" in resultado["usuario_info"]


def test_estado_tipo_usuario_se_asigna(estado_completo):
    """Test 4.4: Estado tipo_usuario se asigna correctamente"""
    resultado = nodo_identificacion_usuario(estado_completo)
    
    assert resultado["tipo_usuario"] != ""
    assert resultado["tipo_usuario"] in ["admin", "doctor", "paciente_externo", "personal"]


def test_estado_es_admin_booleano(estado_completo):
    """Test 4.5: Estado es_admin es booleano"""
    resultado = nodo_identificacion_usuario(estado_completo)
    
    assert isinstance(resultado["es_admin"], bool)


def test_estado_doctor_id_opcional(estado_completo):
    """Test 4.6: Estado doctor_id es opcional (puede ser None)"""
    resultado = nodo_identificacion_usuario(estado_completo)
    
    # Puede ser None o int
    assert resultado["doctor_id"] is None or isinstance(resultado["doctor_id"], int)


def test_estado_preserva_mensajes(estado_completo):
    """Test 4.7: Nodo preserva los mensajes existentes"""
    mensajes_originales = estado_completo["messages"]
    
    resultado = nodo_identificacion_usuario(estado_completo)
    
    assert resultado["messages"] == mensajes_originales


def test_estado_preserva_session_id(estado_completo):
    """Test 4.8: Nodo preserva session_id"""
    session_original = estado_completo["session_id"]
    
    resultado = nodo_identificacion_usuario(estado_completo)
    
    assert resultado["session_id"] == session_original


# ============================================================================
# TESTS: Flujo de ejecución
# ============================================================================

def test_flujo_continua_despues_identificacion(estado_completo):
    """Test 4.9: Flujo puede continuar después de identificación"""
    resultado = nodo_identificacion_usuario(estado_completo)
    
    # El estado debe estar listo para el siguiente nodo
    assert resultado["user_id"] != ""
    assert resultado["usuario_info"] != {}
    
    # Otros campos deben estar presentes para siguientes nodos
    assert "herramientas_seleccionadas" in resultado
    assert "requiere_herramientas" in resultado


def test_nodo_no_modifica_otros_campos(estado_completo):
    """Test 4.10: Nodo NO modifica campos que no le corresponden"""
    # Establecer valores en campos de otros nodos
    estado_completo["contexto_episodico"] = {"test": "data"}
    estado_completo["herramientas_seleccionadas"] = ["tool1"]
    estado_completo["resumen_actual"] = "Resumen previo"
    
    resultado = nodo_identificacion_usuario(estado_completo)
    
    # Estos campos deben permanecer intactos
    assert resultado["contexto_episodico"] == {"test": "data"}
    assert resultado["herramientas_seleccionadas"] == ["tool1"]
    assert resultado["resumen_actual"] == "Resumen previo"


def test_multiples_llamadas_mismo_usuario(estado_completo):
    """Test 4.11: Múltiples llamadas con mismo usuario son consistentes"""
    resultado1 = nodo_identificacion_usuario(estado_completo.copy())
    resultado2 = nodo_identificacion_usuario(estado_completo.copy())
    
    assert resultado1["user_id"] == resultado2["user_id"]
    assert resultado1["es_admin"] == resultado2["es_admin"]
    assert resultado1["tipo_usuario"] == resultado2["tipo_usuario"]


# ============================================================================
# TESTS: Manejo de errores
# ============================================================================

def test_nodo_maneja_error_bd_gracefully():
    """Test 4.12: Nodo maneja error de BD sin crashear"""
    # Simular error de conexión con URL inválida
    with patch('src.nodes.identificacion_usuario_node.DATABASE_URL', 'postgresql://invalid:invalid@localhost:9999/invalid'):
        estado = {
            "messages": [HumanMessage(content="Test", metadata={"phone_number": "+526649999999"})],
            "user_id": "",
            "session_id": "error-test",
            "es_admin": False,
            "usuario_info": {},
            "usuario_registrado": False,
            "tipo_usuario": "",
            "doctor_id": None,
            "paciente_id": None,
            "contexto_episodico": None,
            "herramientas_seleccionadas": [],
            "requiere_herramientas": False,
            "resumen_actual": None,
            "sesion_expirada": False,
            "ultimo_listado": None,
            "timestamp": datetime.now().isoformat()
        }
        
        # No debe lanzar excepción
        resultado = nodo_identificacion_usuario(estado)
        
        # Debe retornar estado con valores por defecto
        assert resultado is not None
        assert "user_id" in resultado


def test_wrapper_maneja_excepciones():
    """Test 4.13: Wrapper maneja excepciones del nodo"""
    estado_invalido = {
        "messages": [],  # Sin mensajes para forzar error
        "user_id": "",
        "session_id": "wrapper-test",
        "es_admin": False,
        "usuario_info": {},
        "usuario_registrado": False,
        "tipo_usuario": "",
        "doctor_id": None,
        "paciente_id": None,
        "contexto_episodico": None,
        "herramientas_seleccionadas": [],
        "requiere_herramientas": False,
        "resumen_actual": None,
        "sesion_expirada": False,
        "ultimo_listado": None,
        "timestamp": datetime.now().isoformat()
    }
    
    # Wrapper no debe lanzar excepción
    resultado = nodo_identificacion_usuario_wrapper(estado_invalido)
    
    assert resultado is not None
    assert "user_id" in resultado


def test_nodo_maneja_mensaje_sin_metadata(estado_completo):
    """Test 4.14: Nodo maneja mensaje sin metadata"""
    # Mensaje sin metadata de WhatsApp
    estado_completo["messages"] = [HumanMessage(content="Test sin metadata")]
    
    # No debe crashear
    resultado = nodo_identificacion_usuario(estado_completo)
    
    assert resultado is not None
    assert resultado["user_id"] != ""  # Debe usar fallback


def test_conexion_bd_disponible():
    """Test 4.15: Conexión a BD está disponible"""
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                result = cur.fetchone()
                
        assert result[0] == 1
        
    except Exception as e:
        pytest.fail(f"Base de datos no disponible: {e}")


# ============================================================================
# TESTS: Validación de campos del estado
# ============================================================================

def test_todos_campos_estado_presentes(estado_completo):
    """Test 4.16: Todos los campos del estado están presentes después del nodo"""
    resultado = nodo_identificacion_usuario(estado_completo)
    
    campos_requeridos = [
        "messages", "user_id", "session_id", "es_admin",
        "usuario_info", "usuario_registrado", "tipo_usuario",
        "doctor_id", "paciente_id", "contexto_episodico",
        "herramientas_seleccionadas", "requiere_herramientas",
        "resumen_actual", "sesion_expirada", "ultimo_listado",
        "timestamp"
    ]
    
    for campo in campos_requeridos:
        assert campo in resultado, f"Campo {campo} falta en el estado"


def test_tipos_datos_estado_correctos(estado_completo):
    """Test 4.17: Los tipos de datos del estado son correctos"""
    resultado = nodo_identificacion_usuario(estado_completo)
    
    assert isinstance(resultado["user_id"], str)
    assert isinstance(resultado["es_admin"], bool)
    assert isinstance(resultado["usuario_info"], dict)
    assert isinstance(resultado["usuario_registrado"], bool)
    assert isinstance(resultado["tipo_usuario"], str)
    assert isinstance(resultado["herramientas_seleccionadas"], list)
    assert isinstance(resultado["requiere_herramientas"], bool)


def test_estado_listo_para_siguiente_nodo(estado_completo):
    """Test 4.18: Estado está listo para el siguiente nodo del grafo"""
    resultado = nodo_identificacion_usuario(estado_completo)
    
    # Campos críticos deben estar llenos
    assert resultado["user_id"] != ""
    assert resultado["usuario_info"] != {}
    assert resultado["tipo_usuario"] != ""
    
    # Usuario identificado correctamente
    assert resultado["usuario_registrado"] in [True, False]
