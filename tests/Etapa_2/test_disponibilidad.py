"""
TEST 2: test_disponibilidad.py
Pruebas de validación de disponibilidad de doctores

15 tests que validan:
- Días de atención (Jueves-Lunes)
- Horarios válidos (8:30-18:30)
- Detección de conflictos
- Timezone awareness
"""

import pytest
import os
from datetime import datetime, time, timedelta
import pytz

from src.medical.disponibilidad import (
    check_doctor_availability,
    validar_horario_clinica,
    obtener_horarios_doctor,
    DIAS_ATENCION,
    TIMEZONE
)
from src.medical.turnos import DATABASE_URL
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
def limpiar_citas_prueba(db_connection):
    """Limpia citas de prueba después del test"""
    citas_creadas = []
    
    yield citas_creadas
    
    # Cleanup
    if citas_creadas:
        with db_connection.cursor() as cur:
            for cita_id in citas_creadas:
                cur.execute("DELETE FROM citas_medicas WHERE id = %s", (cita_id,))
            db_connection.commit()


@pytest.fixture
def verificar_doctores(db_connection):
    """Verifica que existan doctores"""
    with db_connection.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM doctores WHERE id IN (1, 2)")
        count = cur.fetchone()[0]
        if count < 2:
            pytest.skip("Se requieren doctores con ID=1 y ID=2")


# ============================================================================
# TESTS: Validación de Días
# ============================================================================

def test_dia_cerrado_martes(verificar_doctores):
    """Test 2.1: Rechaza Martes (día 1)"""
    # Crear fecha un martes
    fecha = datetime(2026, 2, 3, 10, 30, tzinfo=TIMEZONE)  # Martes
    fecha_fin = fecha + timedelta(hours=1)
    
    resultado = check_doctor_availability(1, fecha, fecha_fin)
    
    assert resultado["disponible"] == False
    assert resultado["razon"] == "dia_cerrado"


def test_dia_cerrado_miercoles(verificar_doctores):
    """Test 2.2: Rechaza Miércoles (día 2)"""
    fecha = datetime(2026, 2, 4, 10, 30, tzinfo=TIMEZONE)  # Miércoles
    fecha_fin = fecha + timedelta(hours=1)
    
    resultado = check_doctor_availability(1, fecha, fecha_fin)
    
    assert resultado["disponible"] == False
    assert resultado["razon"] == "dia_cerrado"


def test_dia_laborable_jueves(verificar_doctores):
    """Test 2.3: Acepta Jueves (día 3)"""
    fecha = datetime(2026, 1, 29, 10, 30, tzinfo=TIMEZONE)  # Jueves
    fecha_fin = fecha + timedelta(hours=1)
    
    resultado = check_doctor_availability(1, fecha, fecha_fin)
    
    # No debe rechazar por día
    if not resultado["disponible"]:
        assert resultado["razon"] != "dia_cerrado"


def test_dia_laborable_lunes(verificar_doctores):
    """Test 2.4: Acepta Lunes (día 0)"""
    fecha = datetime(2026, 2, 2, 10, 30, tzinfo=TIMEZONE)  # Lunes
    fecha_fin = fecha + timedelta(hours=1)
    
    resultado = check_doctor_availability(1, fecha, fecha_fin)
    
    if not resultado["disponible"]:
        assert resultado["razon"] != "dia_cerrado"


# ============================================================================
# TESTS: Validación de Horarios
# ============================================================================

def test_horario_valido_inicio_jornada(verificar_doctores):
    """Test 2.5: 08:30 AM es válido"""
    fecha = datetime(2026, 1, 30, 8, 30, tzinfo=TIMEZONE)  # Viernes 8:30 AM
    fecha_fin = fecha + timedelta(hours=1)
    
    resultado = check_doctor_availability(1, fecha, fecha_fin)
    
    if not resultado["disponible"]:
        assert resultado["razon"] != "fuera_de_horario"


def test_horario_valido_fin_jornada(verificar_doctores):
    """Test 2.6: 17:30-18:30 es válido"""
    fecha = datetime(2026, 1, 30, 17, 30, tzinfo=TIMEZONE)
    fecha_fin = datetime(2026, 1, 30, 18, 30, tzinfo=TIMEZONE)
    
    resultado = check_doctor_availability(1, fecha, fecha_fin)
    
    if not resultado["disponible"]:
        assert resultado["razon"] != "fuera_de_horario"


def test_horario_fuera_rango_temprano(verificar_doctores):
    """Test 2.7: 07:00 AM es inválido"""
    fecha = datetime(2026, 1, 30, 7, 0, tzinfo=TIMEZONE)
    fecha_fin = fecha + timedelta(hours=1)
    
    resultado = check_doctor_availability(1, fecha, fecha_fin)
    
    assert resultado["disponible"] == False
    assert resultado["razon"] == "fuera_de_horario"


def test_horario_fuera_rango_tarde(verificar_doctores):
    """Test 2.8: 19:00 (7 PM) es inválido"""
    fecha = datetime(2026, 1, 30, 19, 0, tzinfo=TIMEZONE)
    fecha_fin = fecha + timedelta(hours=1)
    
    resultado = check_doctor_availability(1, fecha, fecha_fin)
    
    assert resultado["disponible"] == False
    assert resultado["razon"] == "fuera_de_horario"


# ============================================================================
# TESTS: Detección de Conflictos
# ============================================================================

def test_sin_conflictos(verificar_doctores, limpiar_citas_prueba):
    """Test 2.9: Sin citas existentes, debe estar disponible"""
    fecha = datetime(2026, 6, 1, 10, 30, tzinfo=TIMEZONE)  # Fecha futura
    fecha_fin = fecha + timedelta(hours=1)
    
    resultado = check_doctor_availability(1, fecha, fecha_fin)
    
    # Puede ser True o False, pero no debe ser por conflicto
    if not resultado["disponible"]:
        assert resultado["razon"] != "ocupado"


def test_conflicto_exacto(verificar_doctores, limpiar_citas_prueba, db_connection):
    """Test 2.10: Detecta conflicto cuando horarios son exactos"""
    fecha_inicio = datetime(2026, 6, 5, 10, 30, tzinfo=TIMEZONE)  # Viernes (día laborable)
    fecha_fin = datetime(2026, 6, 5, 11, 30, tzinfo=TIMEZONE)
    
    # Crear cita existente
    with db_connection.cursor() as cur:
        cur.execute("""
            INSERT INTO citas_medicas (
                doctor_id, fecha_hora_inicio, fecha_hora_fin, estado
            )
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (1, fecha_inicio, fecha_fin, 'programada'))
        
        cita_id = cur.fetchone()[0]
        limpiar_citas_prueba.append(cita_id)
        db_connection.commit()
    
    # Intentar agendar en mismo horario
    resultado = check_doctor_availability(1, fecha_inicio, fecha_fin)
    
    assert resultado["disponible"] == False
    assert resultado["razon"] == "ocupado"
    assert resultado["conflicto_con"] is not None


def test_conflicto_parcial_inicio(verificar_doctores, limpiar_citas_prueba, db_connection):
    """Test 2.11: Detecta overlap parcial (inicio dentro de cita existente)"""
    # Cita existente: 10:00-11:00
    cita_inicio = datetime(2026, 6, 6, 10, 0, tzinfo=TIMEZONE)  # Sábado (día laborable)
    cita_fin = datetime(2026, 6, 6, 11, 0, tzinfo=TIMEZONE)
    
    with db_connection.cursor() as cur:
        cur.execute("""
            INSERT INTO citas_medicas (doctor_id, fecha_hora_inicio, fecha_hora_fin, estado)
            VALUES (%s, %s, %s, %s) RETURNING id
        """, (1, cita_inicio, cita_fin, 'programada'))
        
        cita_id = cur.fetchone()[0]
        limpiar_citas_prueba.append(cita_id)
        db_connection.commit()
    
    # Intentar agendar 10:30-11:30 (empieza durante cita existente)
    nuevo_inicio = datetime(2026, 6, 6, 10, 30, tzinfo=TIMEZONE)
    nuevo_fin = datetime(2026, 6, 6, 11, 30, tzinfo=TIMEZONE)
    
    resultado = check_doctor_availability(1, nuevo_inicio, nuevo_fin)
    
    assert resultado["disponible"] == False
    assert resultado["razon"] == "ocupado"


def test_sin_conflicto_horarios_contiguos(verificar_doctores, limpiar_citas_prueba, db_connection):
    """Test 2.12: Horarios contiguos NO generan conflicto"""
    # Cita existente: 10:00-11:00
    cita_inicio = datetime(2026, 6, 4, 10, 0, tzinfo=TIMEZONE)
    cita_fin = datetime(2026, 6, 4, 11, 0, tzinfo=TIMEZONE)
    
    with db_connection.cursor() as cur:
        cur.execute("""
            INSERT INTO citas_medicas (doctor_id, fecha_hora_inicio, fecha_hora_fin, estado)
            VALUES (%s, %s, %s, %s) RETURNING id
        """, (1, cita_inicio, cita_fin, 'programada'))
        
        cita_id = cur.fetchone()[0]
        limpiar_citas_prueba.append(cita_id)
        db_connection.commit()
    
    # Agendar 11:00-12:00 (justo después)
    nuevo_inicio = datetime(2026, 6, 4, 11, 0, tzinfo=TIMEZONE)
    nuevo_fin = datetime(2026, 6, 4, 12, 0, tzinfo=TIMEZONE)
    
    resultado = check_doctor_availability(1, nuevo_inicio, nuevo_fin)
    
    # NO debe haber conflicto
    if not resultado["disponible"]:
        assert resultado["razon"] != "ocupado"


# ============================================================================
# TESTS: Timezone y Edge Cases
# ============================================================================

def test_timezone_aware_fechas(verificar_doctores):
    """Test 2.13: Funciona con fechas timezone-aware"""
    fecha = datetime(2026, 1, 30, 10, 30, tzinfo=pytz.timezone("America/Tijuana"))
    fecha_fin = fecha + timedelta(hours=1)
    
    # No debe lanzar excepción
    resultado = check_doctor_availability(1, fecha, fecha_fin)
    assert "disponible" in resultado


def test_timezone_naive_se_convierte(verificar_doctores):
    """Test 2.14: Fechas naive se convierten a timezone-aware"""
    fecha_naive = datetime(2026, 1, 30, 10, 30)  # Sin timezone
    fecha_fin_naive = datetime(2026, 1, 30, 11, 30)
    
    # Debe funcionar sin error
    resultado = check_doctor_availability(1, fecha_naive, fecha_fin_naive)
    assert "disponible" in resultado


def test_validar_horario_clinica_helper(verificar_doctores):
    """Test 2.15: validar_horario_clinica() funciona correctamente"""
    # Horario válido
    fecha_valida = datetime(2026, 1, 30, 10, 30, tzinfo=TIMEZONE)
    resultado_valido = validar_horario_clinica(fecha_valida)
    assert resultado_valido["valido"] == True
    
    # Horario inválido (Martes)
    fecha_invalida = datetime(2026, 2, 3, 10, 30, tzinfo=TIMEZONE)
    resultado_invalido = validar_horario_clinica(fecha_invalida)
    assert resultado_invalido["valido"] == False
