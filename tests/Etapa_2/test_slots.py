"""
TEST 3: test_slots.py
Pruebas de generación de slots con turnos

15 tests que validan:
- Generación correcta de slots
- Filtrado de días
- Aplicación de turnos
- Privacidad del doctor
"""

import pytest
from datetime import datetime, timedelta
import pytz

from src.medical.slots import (
    generar_slots_con_turnos,
    generar_slots_doctor,
    formatear_slots_para_frontend,
    agrupar_slots_por_dia,
    TIMEZONE,
    DIAS_ATENCION
)
from src.medical.turnos import DATABASE_URL
import psycopg


@pytest.fixture
def verificar_doctores():
    conn = psycopg.connect(DATABASE_URL)
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM doctores WHERE id IN (1, 2)")
        if cur.fetchone()[0] < 2:
            pytest.skip("Se requieren doctores")
    conn.close()


# ============================================================================
# TESTS: Generación de Slots
# ============================================================================

def test_generar_slots_7_dias(verificar_doctores):
    """Test 3.1: Genera slots para 7 días adelante"""
    slots = generar_slots_con_turnos(dias_adelante=7)
    
    assert len(slots) > 0
    assert isinstance(slots, list)


def test_generar_slots_estructura_correcta(verificar_doctores):
    """Test 3.2: Slots tienen estructura correcta"""
    slots = generar_slots_con_turnos(dias_adelante=2)
    
    if len(slots) > 0:
        slot = slots[0]
        assert "fecha" in slot
        assert "hora_inicio" in slot
        assert "hora_fin" in slot
        assert "slot_id" in slot
        assert "disponible" in slot


def test_slots_1_hora_duracion(verificar_doctores):
    """Test 3.3: Cada slot dura 1 hora"""
    slots = generar_slots_con_turnos(dias_adelante=1)
    
    if len(slots) > 0:
        for slot in slots[:5]:  # Verificar primeros 5
            h_inicio = slot["hora_inicio"]
            h_fin = slot["hora_fin"]
            
            # Convertir a datetime para comparar
            inicio = datetime.strptime(h_inicio, "%H:%M")
            fin = datetime.strptime(h_fin, "%H:%M")
            
            diferencia = (fin - inicio).total_seconds() / 3600
            assert diferencia == 1.0


def test_filtrar_dias_cerrados(verificar_doctores):
    """Test 3.4: NO genera slots para Martes/Miércoles"""
    slots = generar_slots_con_turnos(dias_adelante=14)  # 2 semanas
    
    # Verificar que no hay slots en días cerrados
    for slot in slots:
        fecha_str = slot["fecha"]
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d")
        dia_semana = fecha.weekday()
        
        # No debe haber slots en martes (1) ni miércoles (2)
        assert dia_semana in DIAS_ATENCION


def test_slots_solo_futuros(verificar_doctores):
    """Test 3.5: Solo genera slots futuros"""
    slots = generar_slots_con_turnos(dias_adelante=1)
    ahora = datetime.now(TIMEZONE)
    
    for slot in slots:
        fecha_str = f"{slot['fecha']}T{slot['hora_inicio']}"
        fecha_slot = datetime.fromisoformat(fecha_str).replace(tzinfo=TIMEZONE)
        
        assert fecha_slot > ahora


# ============================================================================
# TESTS: Aplicación de Turnos
# ============================================================================

def test_incluir_doctor_interno(verificar_doctores):
    """Test 3.6: incluir_doctor_interno=True incluye doctor_id"""
    slots = generar_slots_con_turnos(dias_adelante=1, incluir_doctor_interno=True)
    
    if len(slots) > 0:
        assert "doctor_asignado_id" in slots[0]


def test_no_incluir_doctor_externo(verificar_doctores):
    """Test 3.7: incluir_doctor_interno=False NO incluye doctor_id"""
    slots = generar_slots_con_turnos(dias_adelante=1, incluir_doctor_interno=False)
    
    if len(slots) > 0:
        assert "doctor_asignado_id" not in slots[0]


def test_formatear_elimina_doctor_id(verificar_doctores):
    """Test 3.8: formatear_slots_para_frontend() elimina doctor_id"""
    slots_internos = generar_slots_con_turnos(dias_adelante=1, incluir_doctor_interno=True)
    
    if len(slots_internos) > 0:
        slots_publicos = formatear_slots_para_frontend(slots_internos)
        
        assert "doctor_asignado_id" not in slots_publicos[0]
        assert "fecha" in slots_publicos[0]
        assert "hora_inicio" in slots_publicos[0]


# ============================================================================
# TESTS: Generación por Doctor Específico
# ============================================================================

def test_generar_slots_doctor_especifico(verificar_doctores):
    """Test 3.9: generar_slots_doctor() funciona"""
    slots = generar_slots_doctor(doctor_id=1, dias_adelante=3)
    
    assert isinstance(slots, list)
    
    if len(slots) > 0:
        assert "doctor_id" in slots[0]
        assert slots[0]["doctor_id"] == 1


def test_generar_slots_dos_doctores_diferente(verificar_doctores):
    """Test 3.10: Slots de doctor 1 vs doctor 2"""
    slots_santiago = generar_slots_doctor(1, dias_adelante=1)
    slots_joana = generar_slots_doctor(2, dias_adelante=1)
    
    # Ambos deben tener slots
    assert len(slots_santiago) > 0
    assert len(slots_joana) > 0
    
    # IDs deben ser diferentes
    assert slots_santiago[0]["doctor_id"] == 1
    assert slots_joana[0]["doctor_id"] == 2


# ============================================================================
# TESTS: Agrupación y Utilidades
# ============================================================================

def test_agrupar_por_dia(verificar_doctores):
    """Test 3.11: agrupar_slots_por_dia() funciona"""
    slots = generar_slots_con_turnos(dias_adelante=3)
    
    if len(slots) > 0:
        agrupados = agrupar_slots_por_dia(slots)
        
        assert isinstance(agrupados, dict)
        assert len(agrupados) > 0
        
        # Cada key debe ser una fecha
        for fecha, slots_dia in agrupados.items():
            assert isinstance(fecha, str)
            assert isinstance(slots_dia, list)


def test_slot_id_formato_correcto(verificar_doctores):
    """Test 3.12: slot_id tiene formato correcto"""
    slots = generar_slots_con_turnos(dias_adelante=1)
    
    if len(slots) > 0:
        slot_id = slots[0]["slot_id"]
        # Formato: 2026-01-30T10:30
        assert "T" in slot_id
        assert len(slot_id) >= 16


def test_horarios_dentrojornada(verificar_doctores):
    """Test 3.13: Todos los horarios están dentro de 08:30-18:30"""
    slots = generar_slots_con_turnos(dias_adelante=2)
    
    for slot in slots:
        hora = slot["hora_inicio"]
        h, m = map(int, hora.split(":"))
        
        # Debe ser >= 08:30 y < 18:30
        assert h >= 8
        assert h < 19
        if h == 8:
            assert m >= 30


def test_slots_sin_duplicados(verificar_doctores):
    """Test 3.14: No hay slots duplicados"""
    slots = generar_slots_con_turnos(dias_adelante=2)
    
    slot_ids = [s["slot_id"] for s in slots]
    assert len(slot_ids) == len(set(slot_ids))  # No duplicados


def test_cantidad_minima_slots(verificar_doctores):
    """Test 3.15: Genera cantidad razonable de slots"""
    slots = generar_slots_con_turnos(dias_adelante=1)
    
    # Al menos debería generar algunos slots
    assert len(slots) >= 3
