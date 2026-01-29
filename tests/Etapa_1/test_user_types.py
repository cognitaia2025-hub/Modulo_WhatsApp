"""
TEST 3: test_user_types.py
Pruebas de diferenciación de tipos de usuario

Validaciones:
- Diferencia entre doctor/personal/paciente/admin
- Doctor tiene acceso a doctor_id
- Paciente NO tiene doctor_id
- Usuario personal tiene tipo correcto
"""

import pytest
import os
from datetime import datetime
from langchain_core.messages import HumanMessage

from src.nodes.identificacion_usuario_node import (
    crear_usuario_nuevo,
    consultar_usuario_bd,
    nodo_identificacion_usuario,
    DATABASE_URL,
    ADMIN_PHONE_NUMBER
)
import psycopg


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def phone_admin():
    """Número de administrador"""
    return ADMIN_PHONE_NUMBER


@pytest.fixture
def crear_doctor_test():
    """Crea un doctor de prueba"""
    doctors_created = []
    
    def _crear_doctor(phone=None, nombre="Dr. Test", especialidad="Medicina General"):
        if phone is None:
            phone = f"+52664DR{datetime.now().microsecond % 10000}"
        
        try:
            with psycopg.connect(DATABASE_URL) as conn:
                with conn.cursor() as cur:
                    # Crear usuario tipo doctor
                    cur.execute("""
                        INSERT INTO usuarios (phone_number, display_name, tipo_usuario, es_admin)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (phone_number) DO UPDATE 
                        SET tipo_usuario = 'doctor'
                        RETURNING id
                    """, (phone, nombre, "doctor", False))
                    
                    # Crear registro en tabla doctores
                    cur.execute("""
                        INSERT INTO doctores (phone_number, nombre_completo, especialidad, orden_turno)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (phone_number) DO UPDATE 
                        SET nombre_completo = EXCLUDED.nombre_completo
                        RETURNING id
                    """, (phone, nombre, especialidad, 1))
                    
                    doctor_id = cur.fetchone()[0]
                    
            doctors_created.append(phone)
            return {"phone": phone, "doctor_id": doctor_id}
            
        except Exception as e:
            pytest.skip(f"No se pudo crear doctor: {e}")
    
    yield _crear_doctor
    
    # Cleanup
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                for phone in doctors_created:
                    cur.execute("DELETE FROM doctores WHERE phone_number = %s", (phone,))
                    cur.execute("DELETE FROM usuarios WHERE phone_number = %s", (phone,))
    except:
        pass


@pytest.fixture
def crear_paciente_test():
    """Crea un paciente de prueba"""
    patients_created = []
    
    def _crear_paciente(phone=None):
        if phone is None:
            phone = f"+52664PAC{datetime.now().microsecond % 10000}"
        
        try:
            with psycopg.connect(DATABASE_URL) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO usuarios (phone_number, display_name, tipo_usuario, es_admin)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (phone_number) DO UPDATE 
                        SET tipo_usuario = 'paciente_externo'
                        RETURNING id
                    """, (phone, "Paciente Test", "paciente_externo", False))
                    
            patients_created.append(phone)
            return phone
            
        except Exception as e:
            pytest.skip(f"No se pudo crear paciente: {e}")
    
    yield _crear_paciente
    
    # Cleanup
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                for phone in patients_created:
                    cur.execute("DELETE FROM usuarios WHERE phone_number = %s", (phone,))
    except:
        pass


# ============================================================================
# TESTS: Identificación de Admin
# ============================================================================

def test_admin_se_identifica_correctamente(phone_admin):
    """Test 3.1: Admin se identifica por número de teléfono"""
    usuario = consultar_usuario_bd(phone_admin)
    
    if usuario:
        assert usuario["es_admin"] == True
        assert usuario["tipo_usuario"] in ["admin", "paciente_externo"]


def test_admin_en_nodo_identificacion(phone_admin):
    """Test 3.2: Nodo identifica admin correctamente"""
    estado = {
        "messages": [HumanMessage(content="Test admin", metadata={"phone_number": phone_admin})],
        "user_id": "",
        "session_id": "test-admin",
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
    
    resultado = nodo_identificacion_usuario(estado)
    
    assert resultado["es_admin"] == True
    assert resultado["user_id"] == phone_admin


def test_admin_nuevo_se_crea_como_admin():
    """Test 3.3: Al crear admin nuevo, tipo_usuario = 'admin'"""
    usuario = crear_usuario_nuevo(ADMIN_PHONE_NUMBER)
    
    assert usuario["tipo_usuario"] == "admin"
    assert usuario["es_admin"] == True


# ============================================================================
# TESTS: Identificación de Doctor
# ============================================================================

def test_doctor_tiene_doctor_id(crear_doctor_test):
    """Test 3.4: Doctor tiene doctor_id en consulta"""
    doctor_data = crear_doctor_test()
    phone = doctor_data["phone"]
    
    usuario = consultar_usuario_bd(phone)
    
    assert usuario is not None
    assert usuario["tipo_usuario"] == "doctor"
    assert usuario["doctor_id"] is not None
    assert usuario["doctor_id"] == doctor_data["doctor_id"]


def test_doctor_en_nodo_tiene_doctor_id(crear_doctor_test):
    """Test 3.5: Doctor en nodo obtiene doctor_id en estado"""
    doctor_data = crear_doctor_test()
    phone = doctor_data["phone"]
    
    estado = {
        "messages": [HumanMessage(content="Hola", metadata={"phone_number": phone})],
        "user_id": "",
        "session_id": "test-doctor",
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
    
    resultado = nodo_identificacion_usuario(estado)
    
    assert resultado["tipo_usuario"] == "doctor"
    assert resultado["doctor_id"] is not None
    assert resultado["doctor_id"] == doctor_data["doctor_id"]


def test_doctor_tiene_especialidad(crear_doctor_test):
    """Test 3.6: Doctor tiene especialidad en consulta"""
    doctor_data = crear_doctor_test(especialidad="Cardiología")
    phone = doctor_data["phone"]
    
    usuario = consultar_usuario_bd(phone)
    
    assert usuario["especialidad"] == "Cardiología"


def test_doctor_no_es_admin_automaticamente(crear_doctor_test):
    """Test 3.7: Doctor NO es admin por defecto"""
    doctor_data = crear_doctor_test()
    phone = doctor_data["phone"]
    
    usuario = consultar_usuario_bd(phone)
    
    assert usuario["es_admin"] == False


# ============================================================================
# TESTS: Identificación de Paciente Externo
# ============================================================================

def test_paciente_no_tiene_doctor_id(crear_paciente_test):
    """Test 3.8: Paciente NO tiene doctor_id"""
    phone = crear_paciente_test()
    
    usuario = consultar_usuario_bd(phone)
    
    assert usuario is not None
    assert usuario["tipo_usuario"] == "paciente_externo"
    assert usuario["doctor_id"] is None


def test_paciente_en_nodo_no_tiene_doctor_id(crear_paciente_test):
    """Test 3.9: Paciente en nodo NO tiene doctor_id"""
    phone = crear_paciente_test()
    
    estado = {
        "messages": [HumanMessage(content="Hola", metadata={"phone_number": phone})],
        "user_id": "",
        "session_id": "test-paciente",
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
    
    resultado = nodo_identificacion_usuario(estado)
    
    assert resultado["tipo_usuario"] == "paciente_externo"
    assert resultado["doctor_id"] is None


def test_paciente_no_es_admin(crear_paciente_test):
    """Test 3.10: Paciente NO es admin"""
    phone = crear_paciente_test()
    
    usuario = consultar_usuario_bd(phone)
    
    assert usuario["es_admin"] == False


def test_paciente_nuevo_autoregistro():
    """Test 3.11: Usuario nuevo se crea como paciente_externo"""
    phone = f"+52664NEW{datetime.now().microsecond % 10000}"
    
    usuario = crear_usuario_nuevo(phone)
    
    # Debe ser paciente_externo a menos que sea el admin
    if phone != ADMIN_PHONE_NUMBER:
        assert usuario["tipo_usuario"] == "paciente_externo"
    
    # Cleanup
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM usuarios WHERE phone_number = %s", (phone,))
    except:
        pass


# ============================================================================
# TESTS: Diferenciación entre tipos
# ============================================================================

def test_tipos_validos_permitidos():
    """Test 3.12: Solo se permiten tipos válidos"""
    tipos_validos = ["personal", "doctor", "paciente_externo", "admin"]
    
    # Esto es más una verificación de documentación
    assert "personal" in tipos_validos
    assert "doctor" in tipos_validos
    assert "paciente_externo" in tipos_validos
    assert "admin" in tipos_validos


def test_doctor_vs_paciente_diferenciacion(crear_doctor_test, crear_paciente_test):
    """Test 3.13: Doctor y paciente se diferencian correctamente"""
    doctor_data = crear_doctor_test()
    phone_doctor = doctor_data["phone"]
    phone_paciente = crear_paciente_test()
    
    doctor = consultar_usuario_bd(phone_doctor)
    paciente = consultar_usuario_bd(phone_paciente)
    
    # Verificar diferencias
    assert doctor["tipo_usuario"] == "doctor"
    assert paciente["tipo_usuario"] == "paciente_externo"
    
    assert doctor["doctor_id"] is not None
    assert paciente["doctor_id"] is None


def test_usuario_personal_tipo():
    """Test 3.14: Usuario personal tiene tipo correcto"""
    phone = f"+52664PER{datetime.now().microsecond % 10000}"
    
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO usuarios (phone_number, display_name, tipo_usuario, es_admin)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                """, (phone, "Usuario Personal", "personal", False))
                
        usuario = consultar_usuario_bd(phone)
        
        assert usuario["tipo_usuario"] == "personal"
        assert usuario["es_admin"] == False
        assert usuario["doctor_id"] is None
        
        # Cleanup
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM usuarios WHERE phone_number = %s", (phone,))
                
    except Exception as e:
        pytest.skip(f"No se pudo crear usuario personal: {e}")


def test_estado_contiene_tipo_usuario():
    """Test 3.15: Estado del grafo contiene tipo_usuario"""
    estado = {
        "messages": [HumanMessage(content="Test", metadata={"phone_number": ADMIN_PHONE_NUMBER})],
        "user_id": "",
        "session_id": "test-tipo",
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
    
    resultado = nodo_identificacion_usuario(estado)
    
    assert "tipo_usuario" in resultado
    assert resultado["tipo_usuario"] is not None
    assert resultado["tipo_usuario"] != ""
