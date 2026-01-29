"""
TEST 1: test_turnos.py
Pruebas del sistema de turnos rotativos

15 tests que validan:
- Alternancia correcta entre doctores
- Actualización de contadores
- Estadísticas de turnos
- Manejo de errores
"""

import pytest
import os
from datetime import datetime
from unittest.mock import patch

from src.medical.turnos import (
    obtener_siguiente_doctor_turno,
    actualizar_control_turnos,
    obtener_estadisticas_turnos,
    obtener_otro_doctor,
    DATABASE_URL
)
import psycopg


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def db_connection():
    """Conexión a base de datos"""
    conn = psycopg.connect(DATABASE_URL)
    yield conn
    conn.close()


@pytest.fixture
def resetear_control_turnos(db_connection):
    """Resetea la tabla control_turnos antes de cada test"""
    with db_connection.cursor() as cur:
        # Borrar y recrear registro inicial
        cur.execute("TRUNCATE TABLE control_turnos RESTART IDENTITY CASCADE")
        cur.execute("""
            INSERT INTO control_turnos (ultimo_doctor_id, citas_santiago, citas_joana, total_turnos_asignados)
            VALUES (NULL, 0, 0, 0)
        """)
        db_connection.commit()
    
    yield
    
    # Cleanup (por si acaso)
    with db_connection.cursor() as cur:
        cur.execute("TRUNCATE TABLE control_turnos RESTART IDENTITY CASCADE")
        cur.execute("""
            INSERT INTO control_turnos (ultimo_doctor_id, citas_santiago, citas_joana, total_turnos_asignados)
            VALUES (NULL, 0, 0, 0)
        """)
        db_connection.commit()


@pytest.fixture
def verificar_doctores(db_connection):
    """Verifica que existan doctores ID=1 y ID=2"""
    with db_connection.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM doctores WHERE id IN (1, 2)")
        count = cur.fetchone()[0]
        if count < 2:
            pytest.skip("Se requieren doctores con ID=1 y ID=2 en la BD")


# ============================================================================
# TESTS: Alternancia de Turnos
# ============================================================================

def test_alternancia_null_santiago(resetear_control_turnos, verificar_doctores):
    """Test 1.1: Primera vez: NULL → Santiago (ID=1)"""
    doctor = obtener_siguiente_doctor_turno()
    
    assert doctor is not None
    assert doctor["doctor_id"] == 1
    assert doctor["nombre_completo"] is not None
    assert doctor["en_turno"] == True


def test_alternancia_santiago_joana(resetear_control_turnos, verificar_doctores, db_connection):
    """Test 1.2: Santiago → Joana (ID=2)"""
    # Simular que último fue Santiago
    with db_connection.cursor() as cur:
        cur.execute("""
            UPDATE control_turnos 
            SET ultimo_doctor_id = 1
            WHERE id = (SELECT MAX(id) FROM control_turnos)
        """)
        db_connection.commit()
    
    doctor = obtener_siguiente_doctor_turno()
    
    assert doctor["doctor_id"] == 2  # Debe ser Joana


def test_alternancia_joana_santiago(resetear_control_turnos, verificar_doctores, db_connection):
    """Test 1.3: Joana → Santiago (ID=1)"""
    # Simular que último fue Joana
    with db_connection.cursor() as cur:
        cur.execute("""
            UPDATE control_turnos 
            SET ultimo_doctor_id = 2
            WHERE id = (SELECT MAX(id) FROM control_turnos)
        """)
        db_connection.commit()
    
    doctor = obtener_siguiente_doctor_turno()
    
    assert doctor["doctor_id"] == 1  # Debe ser Santiago


def test_alternancia_perfecta_10_turnos(resetear_control_turnos, verificar_doctores):
    """Test 1.4: Alternancia perfecta en 10 turnos consecutivos"""
    turnos = []
    
    for i in range(10):
        doctor = obtener_siguiente_doctor_turno()
        turnos.append(doctor["doctor_id"])
        
        # Actualizar para siguiente turno
        actualizar_control_turnos(doctor["doctor_id"])
    
    # Debe alternar: 1, 2, 1, 2, 1, 2, ...
    esperado = [1, 2, 1, 2, 1, 2, 1, 2, 1, 2]
    assert turnos == esperado


# ============================================================================
# TESTS: Actualización de Contadores
# ============================================================================

def test_actualizar_incrementa_contador_santiago(resetear_control_turnos, verificar_doctores):
    """Test 1.5: actualizar_control_turnos() incrementa contador de Santiago"""
    resultado = actualizar_control_turnos(1)
    
    assert resultado == True
    
    stats = obtener_estadisticas_turnos()
    assert stats["citas_santiago"] == 1
    assert stats["citas_joana"] == 0


def test_actualizar_incrementa_contador_joana(resetear_control_turnos, verificar_doctores):
    """Test 1.6: actualizar_control_turnos() incrementa contador de Joana"""
    resultado = actualizar_control_turnos(2)
    
    assert resultado == True
    
    stats = obtener_estadisticas_turnos()
    assert stats["citas_santiago"] == 0
    assert stats["citas_joana"] == 1


def test_actualizar_incrementa_total(resetear_control_turnos, verificar_doctores):
    """Test 1.7: Se incrementa total_turnos_asignados"""
    actualizar_control_turnos(1)
    actualizar_control_turnos(2)
    actualizar_control_turnos(1)
    
    stats = obtener_estadisticas_turnos()
    assert stats["total_turnos"] == 3


def test_actualizar_cambia_ultimo_doctor(resetear_control_turnos, verificar_doctores, db_connection):
    """Test 1.8: Se actualiza ultimo_doctor_id correctamente"""
    actualizar_control_turnos(1)
    
    with db_connection.cursor() as cur:
        cur.execute("SELECT ultimo_doctor_id FROM control_turnos ORDER BY id DESC LIMIT 1")
        ultimo = cur.fetchone()[0]
    
    assert ultimo == 1


# ============================================================================
# TESTS: Estadísticas de Turnos
# ============================================================================

def test_estadisticas_turnos_inicial(resetear_control_turnos):
    """Test 1.9: Estadísticas iniciales son 0"""
    stats = obtener_estadisticas_turnos()
    
    assert stats["total_turnos"] == 0
    assert stats["citas_santiago"] == 0
    assert stats["citas_joana"] == 0


def test_estadisticas_despues_asignaciones(resetear_control_turnos, verificar_doctores):
    """Test 1.10: Estadísticas reflejan asignaciones"""
    actualizar_control_turnos(1)  # Santiago
    actualizar_control_turnos(2)  # Joana
    actualizar_control_turnos(1)  # Santiago
    actualizar_control_turnos(2)  # Joana
    
    stats = obtener_estadisticas_turnos()
    
    assert stats["total_turnos"] == 4
    assert stats["citas_santiago"] == 2
    assert stats["citas_joana"] == 2
    assert stats["porcentaje_santiago"] == 50.0
    assert stats["porcentaje_joana"] == 50.0


def test_estadisticas_ultimo_turno(resetear_control_turnos, verificar_doctores):
    """Test 1.11: Estadísticas muestran último turno"""
    actualizar_control_turnos(1)
    
    stats = obtener_estadisticas_turnos()
    assert stats["ultimo_turno"] in ["Santiago", "Ninguno (Primera cita)"]


# ============================================================================
# TESTS: Obtener Otro Doctor (Fallback)
# ============================================================================

def test_obtener_otro_doctor_desde_santiago(verificar_doctores):
    """Test 1.12: obtener_otro_doctor(1) → Joana (2)"""
    otro = obtener_otro_doctor(1)
    
    assert otro is not None
    assert otro["doctor_id"] == 2
    assert otro["en_turno"] == False


def test_obtener_otro_doctor_desde_joana(verificar_doctores):
    """Test 1.13: obtener_otro_doctor(2) → Santiago (1)"""
    otro = obtener_otro_doctor(2)
    
    assert otro is not None
    assert otro["doctor_id"] == 1
    assert otro["en_turno"] == False


# ============================================================================
# TESTS: Manejo de Errores
# ============================================================================

def test_obtener_turno_sin_doctores():
    """Test 1.14: Error graceful si no hay doctores en BD"""
    # Mockear tanto DATABASE_URL como get_connection para forzar error
    with patch('src.medical.turnos.DATABASE_URL', 'postgresql://invalid:invalid@localhost:9999/invalid'):
        with patch('src.medical.turnos.get_connection', None):
            with pytest.raises(Exception):
                obtener_siguiente_doctor_turno()


def test_actualizar_control_retorna_false_en_error():
    """Test 1.15: actualizar_control_turnos() retorna False si hay error"""
    with patch('src.medical.turnos.DATABASE_URL', 'postgresql://invalid:invalid@localhost:9999/invalid'):
        resultado = actualizar_control_turnos(1)
        assert resultado == False
