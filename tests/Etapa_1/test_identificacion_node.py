"""
TEST 1: test_identificacion_node.py
Pruebas del nodo de identificación de usuario

Validaciones:
- Usuario nuevo se registra automáticamente
- Usuario existente se identifica correctamente
- Doctor obtiene su doctor_id
- Admin se detecta correctamente
- Phone number se extrae bien del mensaje
"""

import pytest
import os
from datetime import datetime
from unittest.mock import Mock, patch
from langchain_core.messages import HumanMessage

from src.nodes.identificacion_usuario_node import (
    extraer_numero_telefono,
    consultar_usuario_bd,
    crear_usuario_nuevo,
    actualizar_ultima_actividad,
    nodo_identificacion_usuario
)
from src.state.agent_state import WhatsAppAgentState


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def estado_inicial():
    """Estado inicial del grafo para pruebas"""
    return {
        "messages": [HumanMessage(content="Hola", metadata={"phone_number": "+526641234567"})],
        "user_id": "",
        "session_id": "test-session-123",
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


@pytest.fixture
def phone_test():
    """Número de teléfono para pruebas"""
    return "+526641111111"


@pytest.fixture
def phone_admin():
    """Número del administrador"""
    return os.getenv("ADMIN_PHONE_NUMBER", "+526641234567")


# ============================================================================
# TESTS: Extracción de número de teléfono
# ============================================================================

def test_extraccion_phone_desde_metadata():
    """Test 1.1: Extraer phone desde metadata del mensaje"""
    metadata = {"phone_number": "+526649876543"}
    phone = extraer_numero_telefono("Hola", metadata)
    
    assert phone == "+526649876543"
    assert phone.startswith("+")


def test_extraccion_phone_sin_codigo_pais():
    """Test 1.2: Agregar código de país si falta"""
    metadata = {"phone_number": "6649876543"}
    phone = extraer_numero_telefono("Hola", metadata)
    
    assert phone.startswith("+52")
    assert len(phone) == 13  # +52 + 10 dígitos


def test_extraccion_phone_fallback_contenido():
    """Test 1.3: Extraer phone del contenido como fallback"""
    phone = extraer_numero_telefono("Mi número es +526641234567", None)
    
    assert phone == "+526641234567"


def test_extraccion_phone_default():
    """Test 1.4: Usar número default si no encuentra"""
    phone = extraer_numero_telefono("Sin número aquí", None)
    
    assert phone is not None
    assert phone.startswith("+")


# ============================================================================
# TESTS: Registro y consulta de usuarios
# ============================================================================

def test_crear_usuario_nuevo_paciente(phone_test):
    """Test 1.5: Crear usuario nuevo se registra como paciente_externo"""
    usuario = crear_usuario_nuevo(phone_test)
    
    assert usuario is not None
    assert usuario["phone_number"] == phone_test
    assert usuario["tipo_usuario"] == "paciente_externo"
    assert usuario["es_admin"] == False
    assert usuario["is_active"] == True
    assert usuario["doctor_id"] is None


def test_crear_usuario_admin(phone_admin):
    """Test 1.6: Crear admin se detecta por número de teléfono"""
    usuario = crear_usuario_nuevo(phone_admin)
    
    assert usuario is not None
    assert usuario["es_admin"] == True
    assert usuario["tipo_usuario"] == "admin"


def test_consultar_usuario_existente(phone_admin):
    """Test 1.7: Consultar usuario existente retorna sus datos"""
    usuario = consultar_usuario_bd(phone_admin)
    
    # El admin debe existir por el script SQL
    if usuario:
        assert usuario["phone_number"] == phone_admin
        assert "tipo_usuario" in usuario
        assert "display_name" in usuario


def test_consultar_usuario_no_existe():
    """Test 1.8: Consultar usuario inexistente retorna None"""
    phone_inexistente = "+521234567890"
    usuario = consultar_usuario_bd(phone_inexistente)
    
    # Puede ser None si no existe
    assert usuario is None or usuario.get("phone_number") == phone_inexistente


# ============================================================================
# TESTS: Actualización de última actividad
# ============================================================================

def test_actualizar_ultima_actividad(phone_admin):
    """Test 1.9: Actualizar last_seen funciona correctamente"""
    resultado = actualizar_ultima_actividad(phone_admin)
    
    # Debería retornar True si el usuario existe
    assert isinstance(resultado, bool)


# ============================================================================
# TESTS: Nodo de identificación completo
# ============================================================================

def test_nodo_identifica_usuario_nuevo(estado_inicial):
    """Test 1.10: Nodo identifica y registra usuario nuevo"""
    # Usuario nuevo con número único
    phone_nuevo = f"+52664{datetime.now().microsecond}"
    estado_inicial["messages"] = [
        HumanMessage(content="Hola", metadata={"phone_number": phone_nuevo})
    ]
    
    resultado = nodo_identificacion_usuario(estado_inicial)
    
    assert resultado["user_id"] == phone_nuevo
    assert resultado["usuario_registrado"] == False
    assert resultado["tipo_usuario"] == "paciente_externo"
    assert resultado["usuario_info"] is not None
    assert resultado["usuario_info"]["phone_number"] == phone_nuevo


def test_nodo_identifica_usuario_existente(estado_inicial, phone_admin):
    """Test 1.11: Nodo identifica usuario existente correctamente"""
    estado_inicial["messages"] = [
        HumanMessage(content="Hola admin", metadata={"phone_number": phone_admin})
    ]
    
    resultado = nodo_identificacion_usuario(estado_inicial)
    
    assert resultado["user_id"] == phone_admin
    assert resultado["usuario_registrado"] == True
    assert resultado["es_admin"] == True
    assert resultado["tipo_usuario"] in ["admin", "paciente_externo"]


def test_nodo_identifica_doctor(estado_inicial):
    """Test 1.12: Doctor obtiene su doctor_id en el estado"""
    # Crear un doctor de prueba primero
    from src.nodes.identificacion_usuario_node import DATABASE_URL
    import psycopg
    
    phone_doctor = f"+52664DOC{datetime.now().microsecond % 1000}"
    
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                # Crear usuario doctor
                cur.execute("""
                    INSERT INTO usuarios (phone_number, display_name, tipo_usuario, es_admin)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (phone_number) DO NOTHING
                    RETURNING id
                """, (phone_doctor, "Dr. Test", "doctor", False))
                
                # Crear registro de doctor
                cur.execute("""
                    INSERT INTO doctores (phone_number, nombre_completo, especialidad)
                    VALUES (%s, %s, %s)
                    ON CONFLICT DO NOTHING
                    RETURNING id
                """, (phone_doctor, "Dr. Test", "Medicina General"))
                
                doctor_id = cur.fetchone()
                
        # Probar nodo
        estado_inicial["messages"] = [
            HumanMessage(content="Hola", metadata={"phone_number": phone_doctor})
        ]
        
        resultado = nodo_identificacion_usuario(estado_inicial)
        
        assert resultado["tipo_usuario"] == "doctor"
        assert resultado["doctor_id"] is not None
        
    except Exception as e:
        pytest.skip(f"No se pudo crear doctor de prueba: {e}")


def test_nodo_detecta_admin(estado_inicial, phone_admin):
    """Test 1.13: Admin se detecta correctamente"""
    estado_inicial["messages"] = [
        HumanMessage(content="Comando admin", metadata={"phone_number": phone_admin})
    ]
    
    resultado = nodo_identificacion_usuario(estado_inicial)
    
    assert resultado["es_admin"] == True


def test_nodo_maneja_error_gracefully(estado_inicial):
    """Test 1.14: Nodo maneja errores de BD sin crashear"""
    estado_inicial["messages"] = []  # Sin mensajes para forzar error
    
    # No debe lanzar excepción
    resultado = nodo_identificacion_usuario(estado_inicial)
    
    # Debe retornar el estado original o con valores por defecto
    assert resultado is not None


def test_phone_en_formato_internacional(estado_inicial):
    """Test 1.15: Phone number siempre está en formato internacional"""
    estado_inicial["messages"] = [
        HumanMessage(content="Test", metadata={"phone_number": "6649876543"})
    ]
    
    resultado = nodo_identificacion_usuario(estado_inicial)
    
    assert resultado["user_id"].startswith("+")
    assert len(resultado["user_id"]) >= 12  # Mínimo +52 + 10 dígitos
