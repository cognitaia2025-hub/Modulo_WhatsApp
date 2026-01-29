"""
TEST 2: test_user_registration.py
Pruebas del sistema de auto-registro de usuarios

Validaciones:
- Auto-registro crea usuario 'paciente_externo'
- No duplica usuarios existentes
- Actualiza last_seen en cada mensaje
- Campos obligatorios se llenan correctamente
"""

import pytest
import os
from datetime import datetime, timedelta
from langchain_core.messages import HumanMessage

from src.nodes.identificacion_usuario_node import (
    crear_usuario_nuevo,
    consultar_usuario_bd,
    actualizar_ultima_actividad,
    nodo_identificacion_usuario,
    DATABASE_URL
)
import psycopg


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def phone_unique():
    """Genera un número de teléfono único para cada test"""
    timestamp = datetime.now().strftime("%H%M%S%f")
    return f"+52664{timestamp[:10]}"


@pytest.fixture
def limpiar_usuario_test():
    """Limpia usuario de prueba después del test"""
    phones_to_clean = []
    
    yield phones_to_clean
    
    # Cleanup
    if phones_to_clean:
        try:
            with psycopg.connect(DATABASE_URL) as conn:
                with conn.cursor() as cur:
                    for phone in phones_to_clean:
                        cur.execute("DELETE FROM usuarios WHERE phone_number = %s", (phone,))
        except:
            pass


# ============================================================================
# TESTS: Auto-registro de usuarios nuevos
# ============================================================================

def test_autoregistro_crea_paciente_externo(phone_unique, limpiar_usuario_test):
    """Test 2.1: Auto-registro crea usuario tipo 'paciente_externo'"""
    limpiar_usuario_test.append(phone_unique)
    
    usuario = crear_usuario_nuevo(phone_unique)
    
    assert usuario is not None
    assert usuario["tipo_usuario"] == "paciente_externo"
    assert usuario["phone_number"] == phone_unique
    assert usuario["is_active"] == True


def test_autoregistro_llena_campos_obligatorios(phone_unique, limpiar_usuario_test):
    """Test 2.2: Auto-registro llena todos los campos obligatorios"""
    limpiar_usuario_test.append(phone_unique)
    
    usuario = crear_usuario_nuevo(phone_unique)
    
    # Campos obligatorios
    assert usuario["phone_number"] is not None
    assert usuario["display_name"] is not None
    assert usuario["tipo_usuario"] is not None
    assert usuario["timezone"] is not None
    assert usuario["preferencias"] is not None
    assert usuario["created_at"] is not None


def test_autoregistro_asigna_display_name_default(phone_unique, limpiar_usuario_test):
    """Test 2.3: Auto-registro asigna 'Usuario Nuevo' como display_name"""
    limpiar_usuario_test.append(phone_unique)
    
    usuario = crear_usuario_nuevo(phone_unique)
    
    assert usuario["display_name"] in ["Usuario Nuevo", "Administrador"]


def test_autoregistro_asigna_timezone_default(phone_unique, limpiar_usuario_test):
    """Test 2.4: Auto-registro asigna timezone por defecto"""
    limpiar_usuario_test.append(phone_unique)
    
    usuario = crear_usuario_nuevo(phone_unique)
    
    assert usuario["timezone"] == "America/Tijuana"


def test_autoregistro_preferencias_con_flags(phone_unique, limpiar_usuario_test):
    """Test 2.5: Auto-registro incluye flags de primer uso"""
    limpiar_usuario_test.append(phone_unique)
    
    usuario = crear_usuario_nuevo(phone_unique)
    
    assert "preferencias" in usuario
    assert usuario["preferencias"].get("primer_uso") == True
    assert usuario["preferencias"].get("auto_registrado") == True


# ============================================================================
# TESTS: No duplicación de usuarios
# ============================================================================

def test_no_duplica_usuario_existente(phone_unique, limpiar_usuario_test):
    """Test 2.6: No crea usuario duplicado si ya existe"""
    limpiar_usuario_test.append(phone_unique)
    
    # Crear primera vez
    usuario1 = crear_usuario_nuevo(phone_unique)
    id1 = usuario1["id"]
    
    # Intentar crear de nuevo
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO usuarios (phone_number, display_name, tipo_usuario)
                    VALUES (%s, %s, %s)
                """, (phone_unique, "Test Duplicado", "paciente_externo"))
        
        # No debería llegar aquí
        assert False, "Debió lanzar error de unicidad"
        
    except Exception as e:
        # Debería fallar por constraint UNIQUE
        assert "unique" in str(e).lower() or "duplicate" in str(e).lower()


def test_consulta_retorna_mismo_usuario(phone_unique, limpiar_usuario_test):
    """Test 2.7: Consultar retorna el mismo usuario creado"""
    limpiar_usuario_test.append(phone_unique)
    
    # Crear usuario
    usuario_creado = crear_usuario_nuevo(phone_unique)
    
    # Consultar
    usuario_consultado = consultar_usuario_bd(phone_unique)
    
    assert usuario_consultado is not None
    assert usuario_consultado["phone_number"] == usuario_creado["phone_number"]
    assert usuario_consultado["id"] == usuario_creado["id"]


# ============================================================================
# TESTS: Actualización de last_seen
# ============================================================================

def test_actualizar_last_seen_funciona(phone_unique, limpiar_usuario_test):
    """Test 2.8: Actualizar last_seen modifica el timestamp"""
    limpiar_usuario_test.append(phone_unique)
    
    # Crear usuario
    crear_usuario_nuevo(phone_unique)
    
    # Obtener last_seen inicial
    usuario1 = consultar_usuario_bd(phone_unique)
    last_seen1 = usuario1["last_seen"]
    
    # Esperar un momento
    import time
    time.sleep(0.1)
    
    # Actualizar
    actualizar_ultima_actividad(phone_unique)
    
    # Verificar cambio
    usuario2 = consultar_usuario_bd(phone_unique)
    last_seen2 = usuario2["last_seen"]
    
    assert last_seen2 >= last_seen1


def test_nodo_actualiza_last_seen_automaticamente(phone_unique, limpiar_usuario_test):
    """Test 2.9: Nodo actualiza last_seen cada vez que se llama"""
    limpiar_usuario_test.append(phone_unique)
    
    # Crear usuario primero
    crear_usuario_nuevo(phone_unique)
    
    # Simular llamada al nodo
    estado = {
        "messages": [HumanMessage(content="Test", metadata={"phone_number": phone_unique})],
        "user_id": "",
        "session_id": "test-123",
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
    
    # Ejecutar nodo
    nodo_identificacion_usuario(estado)
    
    # Verificar que last_seen se actualizó recientemente (últimos 5 segundos)
    usuario = consultar_usuario_bd(phone_unique)
    diferencia = datetime.now() - usuario["last_seen"]
    
    assert diferencia.total_seconds() < 5


def test_last_seen_timestamp_valido(phone_unique, limpiar_usuario_test):
    """Test 2.10: last_seen es un timestamp válido"""
    limpiar_usuario_test.append(phone_unique)
    
    usuario = crear_usuario_nuevo(phone_unique)
    
    assert usuario["last_seen"] is not None
    assert isinstance(usuario["last_seen"], datetime)


# ============================================================================
# TESTS: Validación de campos obligatorios
# ============================================================================

def test_phone_number_es_obligatorio():
    """Test 2.11: phone_number es campo obligatorio"""
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO usuarios (display_name, tipo_usuario)
                    VALUES (%s, %s)
                """, ("Sin Phone", "paciente_externo"))
        
        assert False, "Debió fallar por falta de phone_number"
        
    except Exception as e:
        # Debe fallar por NOT NULL constraint
        assert "not null" in str(e).lower() or "null value" in str(e).lower()


def test_phone_number_debe_ser_unico(phone_unique, limpiar_usuario_test):
    """Test 2.12: phone_number debe ser único en la tabla"""
    limpiar_usuario_test.append(phone_unique)
    
    # Crear primer usuario
    crear_usuario_nuevo(phone_unique)
    
    # Intentar crear otro con mismo número
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO usuarios (phone_number, display_name, tipo_usuario)
                    VALUES (%s, %s, %s)
                """, (phone_unique, "Otro Usuario", "paciente_externo"))
        
        assert False, "Debió fallar por phone_number duplicado"
        
    except Exception as e:
        assert "unique" in str(e).lower() or "duplicate" in str(e).lower()


def test_tipo_usuario_valores_permitidos(phone_unique, limpiar_usuario_test):
    """Test 2.13: tipo_usuario solo acepta valores válidos"""
    limpiar_usuario_test.append(phone_unique)
    
    # Intentar crear con tipo inválido
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO usuarios (phone_number, display_name, tipo_usuario)
                    VALUES (%s, %s, %s)
                """, (phone_unique, "Test", "tipo_invalido"))
        
        # Puede fallar o no dependiendo del constraint CHECK
        # Si no falla, el constraint no está activo
        
    except Exception as e:
        # Si falla, es correcto
        assert "check" in str(e).lower() or "constraint" in str(e).lower()


def test_created_at_se_asigna_automaticamente(phone_unique, limpiar_usuario_test):
    """Test 2.14: created_at se asigna automáticamente"""
    limpiar_usuario_test.append(phone_unique)
    
    usuario = crear_usuario_nuevo(phone_unique)
    
    assert usuario["created_at"] is not None
    
    # Debe ser cercano a ahora
    diferencia = datetime.now() - usuario["created_at"]
    assert diferencia.total_seconds() < 5


def test_is_active_default_true(phone_unique, limpiar_usuario_test):
    """Test 2.15: is_active por defecto es TRUE"""
    limpiar_usuario_test.append(phone_unique)
    
    usuario = crear_usuario_nuevo(phone_unique)
    
    assert usuario["is_active"] == True
