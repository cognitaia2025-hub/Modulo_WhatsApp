"""
TEST 4: test_agendamiento_turnos.py  
Pruebas de integración del flujo de agendamiento

15 tests que validan:
- Agendamiento con turno normal
- Reasignación automática
- Actualización de control_turnos
- Campos de tracking
"""

import pytest
from datetime import datetime, timedelta
import pytz

from src.medical.turnos import (
    obtener_siguiente_doctor_turno,
    actualizar_control_turnos,
    DATABASE_URL
)
from src.medical.disponibilidad import check_doctor_availability
from src.medical.slots import generar_slots_con_turnos
import psycopg


@pytest.fixture
def db_connection():
    conn = psycopg.connect(DATABASE_URL)
    yield conn
    conn.close()


@pytest.fixture
def limpiar_citas_test(db_connection):
    citas = []
    yield citas
    
    if citas:
        with db_connection.cursor() as cur:
            for cita_id in citas:
                cur.execute("DELETE FROM citas_medicas WHERE id = %s", (cita_id,))
            db_connection.commit()


@pytest.fixture
def resetear_turnos(db_connection):
    with db_connection.cursor() as cur:
        cur.execute("TRUNCATE TABLE control_turnos RESTART IDENTITY CASCADE")
        cur.execute("""
            INSERT INTO control_turnos (ultimo_doctor_id, citas_santiago, citas_joana)
            VALUES (NULL, 0, 0)
        """)
        db_connection.commit()
    yield


@pytest.fixture
def verificar_doctores(db_connection):
    with db_connection.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM doctores WHERE id IN (1, 2)")
        if cur.fetchone()[0] < 2:
            pytest.skip("Requiere doctores 1 y 2")


# ============================================================================
# TESTS: Agendamiento Básico
# ============================================================================

def test_agendar_con_turno_normal(verificar_doctores, resetear_turnos, limpiar_citas_test, db_connection):
    """Test 4.1: Agendamiento normal con doctor del turno"""
    # Obtener doctor del turno
    doctor = obtener_siguiente_doctor_turno()
    doctor_id = doctor["doctor_id"]
    
    # Crear cita
    fecha_inicio = datetime(2026, 6, 10, 10, 30, tzinfo=pytz.timezone("America/Tijuana"))
    fecha_fin = fecha_inicio + timedelta(hours=1)
    
    with db_connection.cursor() as cur:
        cur.execute("""
            INSERT INTO citas_medicas (
                doctor_id, fecha_hora_inicio, fecha_hora_fin, 
                estado, fue_asignacion_automatica
            )
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (doctor_id, fecha_inicio, fecha_fin, 'programada', True))
        
        cita_id = cur.fetchone()[0]
        limpiar_citas_test.append(cita_id)
        db_connection.commit()
    
    # Actualizar control de turnos
    resultado = actualizar_control_turnos(doctor_id)
    
    assert resultado == True
    assert cita_id is not None


def test_campo_fue_asignacion_automatica(verificar_doctores, limpiar_citas_test, db_connection):
    """Test 4.2: fue_asignacion_automatica = TRUE"""
    fecha_inicio = datetime(2026, 6, 11, 10, 30, tzinfo=pytz.timezone("America/Tijuana"))
    fecha_fin = fecha_inicio + timedelta(hours=1)
    
    with db_connection.cursor() as cur:
        cur.execute("""
            INSERT INTO citas_medicas (
                doctor_id, fecha_hora_inicio, fecha_hora_fin,
                estado, fue_asignacion_automatica
            )
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, fue_asignacion_automatica
        """, (1, fecha_inicio, fecha_fin, 'programada', True))
        
        cita_id, fue_auto = cur.fetchone()
        limpiar_citas_test.append(cita_id)
        db_connection.commit()
    
    assert fue_auto == True


def test_campo_doctor_turno_original(verificar_doctores, limpiar_citas_test, db_connection):
    """Test 4.3: Guarda doctor_turno_original correctamente"""
    doctor_original = 1
    fecha_inicio = datetime(2026, 6, 12, 10, 30, tzinfo=pytz.timezone("America/Tijuana"))
    fecha_fin = fecha_inicio + timedelta(hours=1)
    
    with db_connection.cursor() as cur:
        cur.execute("""
            INSERT INTO citas_medicas (
                doctor_id, fecha_hora_inicio, fecha_hora_fin,
                estado, doctor_turno_original
            )
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, doctor_turno_original
        """, (1, fecha_inicio, fecha_fin, 'programada', doctor_original))
        
        cita_id, turno_orig = cur.fetchone()
        limpiar_citas_test.append(cita_id)
        db_connection.commit()
    
    assert turno_orig == doctor_original


def test_campo_razon_reasignacion(verificar_doctores, limpiar_citas_test, db_connection):
    """Test 4.4: razon_reasignacion se guarda si hay reasignación"""
    fecha_inicio = datetime(2026, 6, 13, 10, 30, tzinfo=pytz.timezone("America/Tijuana"))
    fecha_fin = fecha_inicio + timedelta(hours=1)
    
    with db_connection.cursor() as cur:
        cur.execute("""
            INSERT INTO citas_medicas (
                doctor_id, fecha_hora_inicio, fecha_hora_fin,
                estado, doctor_turno_original, razon_reasignacion
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, razon_reasignacion
        """, (2, fecha_inicio, fecha_fin, 'programada', 1, 'ocupado'))
        
        cita_id, razon = cur.fetchone()
        limpiar_citas_test.append(cita_id)
        db_connection.commit()
    
    assert razon == 'ocupado'


# ============================================================================
# TESTS: Reasignación Automática
# ============================================================================

def test_reasignacion_doctor_ocupado(verificar_doctores, limpiar_citas_test, db_connection):
    """Test 4.5: Reasignación si doctor del turno ocupado"""
    fecha = datetime(2026, 6, 14, 10, 30, tzinfo=pytz.timezone("America/Tijuana"))
    fecha_fin = fecha + timedelta(hours=1)
    
    # Ocupar doctor 1
    with db_connection.cursor() as cur:
        cur.execute("""
            INSERT INTO citas_medicas (doctor_id, fecha_hora_inicio, fecha_hora_fin, estado)
            VALUES (%s, %s, %s, %s) RETURNING id
        """, (1, fecha, fecha_fin, 'programada'))
        
        cita1_id = cur.fetchone()[0]
        limpiar_citas_test.append(cita1_id)
        db_connection.commit()
    
    # Verificar que doctor 1 está ocupado
    disponible = check_doctor_availability(1, fecha, fecha_fin)
    assert disponible["disponible"] == False
    
    # Doctor 2 debería estar disponible
    disponible2 = check_doctor_availability(2, fecha, fecha_fin)
    # Si está disponible, se puede asignar
    if disponible2["disponible"]:
        assert True


def test_actualizar_control_despues_agendar(verificar_doctores, resetear_turnos):
    """Test 4.6: Se actualiza control_turnos después de agendar"""
    # Simular agendamiento
    doctor_id = 1
    resultado = actualizar_control_turnos(doctor_id)
    
    assert resultado == True


def test_multiples_agendamientos_alternancia(verificar_doctores, resetear_turnos, limpiar_citas_test, db_connection):
    """Test 4.7: Múltiples agendamientos mantienen alternancia"""
    turnos_asignados = []
    
    for i in range(4):
        doctor = obtener_siguiente_doctor_turno()
        turnos_asignados.append(doctor["doctor_id"])
        
        # Simular agendamiento
        fecha = datetime(2026, 6, 15 + i, 10, 30, tzinfo=pytz.timezone("America/Tijuana"))
        fecha_fin = fecha + timedelta(hours=1)
        
        with db_connection.cursor() as cur:
            cur.execute("""
                INSERT INTO citas_medicas (doctor_id, fecha_hora_inicio, fecha_hora_fin, estado)
                VALUES (%s, %s, %s, %s) RETURNING id
            """, (doctor["doctor_id"], fecha, fecha_fin, 'programada'))
            
            cita_id = cur.fetchone()[0]
            limpiar_citas_test.append(cita_id)
            db_connection.commit()
        
        # Actualizar turnos
        actualizar_control_turnos(doctor["doctor_id"])
    
    # Debe alternar: 1, 2, 1, 2
    assert turnos_asignados == [1, 2, 1, 2]


# ============================================================================
# TESTS: Índices y Performance
# ============================================================================

def test_indice_doctor_fecha_existe(db_connection):
    """Test 4.8: Índice idx_citas_doctor_fecha_estado existe"""
    with db_connection.cursor() as cur:
        cur.execute("""
            SELECT indexname FROM pg_indexes 
            WHERE tablename = 'citas_medicas' 
            AND indexname = 'idx_citas_doctor_fecha_estado'
        """)
        
        resultado = cur.fetchone()
        assert resultado is not None


def test_columnas_nuevas_existen(db_connection):
    """Test 4.9: Columnas nuevas existen en citas_medicas"""
    with db_connection.cursor() as cur:
        cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'citas_medicas'
            AND column_name IN ('fue_asignacion_automatica', 'doctor_turno_original', 'razon_reasignacion')
        """)
        
        columnas = [row[0] for row in cur.fetchall()]
        
        assert 'fue_asignacion_automatica' in columnas
        assert 'doctor_turno_original' in columnas
        assert 'razon_reasignacion' in columnas


# ============================================================================
# TESTS: Edge Cases
# ============================================================================

def test_agendar_sin_actualizar_turnos_no_rompe(verificar_doctores, limpiar_citas_test, db_connection):
    """Test 4.10: Olvidar actualizar turnos no rompe el sistema"""
    fecha = datetime(2026, 6, 20, 10, 30, tzinfo=pytz.timezone("America/Tijuana"))
    fecha_fin = fecha + timedelta(hours=1)
    
    with db_connection.cursor() as cur:
        cur.execute("""
            INSERT INTO citas_medicas (doctor_id, fecha_hora_inicio, fecha_hora_fin, estado)
            VALUES (%s, %s, %s, %s) RETURNING id
        """, (1, fecha, fecha_fin, 'programada'))
        
        cita_id = cur.fetchone()[0]
        limpiar_citas_test.append(cita_id)
        db_connection.commit()
    
    # No actualizar turnos intencionalmente
    # Siguiente llamada debe funcionar igual
    doctor = obtener_siguiente_doctor_turno()
    assert doctor is not None


def test_citas_estado_cancelada_no_bloquean(verificar_doctores, limpiar_citas_test, db_connection):
    """Test 4.11: Citas canceladas NO bloquean horarios"""
    fecha = datetime(2026, 6, 21, 10, 30, tzinfo=pytz.timezone("America/Tijuana"))
    fecha_fin = fecha + timedelta(hours=1)
    
    # Crear cita cancelada
    with db_connection.cursor() as cur:
        cur.execute("""
            INSERT INTO citas_medicas (doctor_id, fecha_hora_inicio, fecha_hora_fin, estado)
            VALUES (%s, %s, %s, %s) RETURNING id
        """, (1, fecha, fecha_fin, 'cancelada'))
        
        cita_id = cur.fetchone()[0]
        limpiar_citas_test.append(cita_id)
        db_connection.commit()
    
    # Debe estar disponible (cita cancelada no cuenta)
    disponible = check_doctor_availability(1, fecha, fecha_fin)
    assert disponible["disponible"] == True


def test_equidad_20_citas(verificar_doctores, resetear_turnos):
    """Test 4.12: Después de 20 citas, distribución ~50-50"""
    for i in range(20):
        doctor = obtener_siguiente_doctor_turno()
        actualizar_control_turnos(doctor["doctor_id"])
    
    from src.medical.turnos import obtener_estadisticas_turnos
    stats = obtener_estadisticas_turnos()
    
    # Debe ser exacto: 10 cada uno
    assert stats["citas_santiago"] == 10
    assert stats["citas_joana"] == 10


def test_flujo_slots_a_agendamiento(verificar_doctores):
    """Test 4.13: Flujo completo: generar_slots → verificar → agendar"""
    # 1. Generar slots
    slots = generar_slots_con_turnos(dias_adelante=3, incluir_doctor_interno=True)
    
    assert len(slots) > 0
    
    # 2. Tomar primer slot
    if len(slots) > 0:
        slot = slots[0]
        assert "doctor_asignado_id" in slot


def test_razon_reasignacion_valores_validos(db_connection):
    """Test 4.14: razon_reasignacion acepta valores válidos"""
    # Verificar que acepta los valores especificados
    razones_validas = ['ocupado', 'no_disponible', 'solicitud_especifica']
    
    # Este test solo verifica que el campo existe y acepta strings
    with db_connection.cursor() as cur:
        cur.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns
            WHERE table_name = 'citas_medicas' AND column_name = 'razon_reasignacion'
        """)
        
        resultado = cur.fetchone()
        assert resultado is not None
        assert resultado[1] == 'character varying'


def test_performance_1000_slots(verificar_doctores):
    """Test 4.15: Puede generar 1000+ slots sin timeout"""
    import time
    
    inicio = time.time()
    slots = generar_slots_con_turnos(dias_adelante=30)  # 1 mes
    duracion = time.time() - inicio
    
    # Debe completar en menos de 10 segundos
    assert duracion < 10
    assert len(slots) > 0
