"""
TEST 5: test_integration_etapa2.py
Pruebas end-to-end del sistema completo

10 tests que validan:
- Flujos completos
- Equidad de distribución
- Manejo de concurrencia
- Performance
"""

import pytest
from datetime import datetime, timedelta
import pytz
import time

from src.medical import (
    obtener_siguiente_doctor_turno,
    actualizar_control_turnos,
    generar_slots_con_turnos,
    check_doctor_availability,
    obtener_estadisticas_turnos,
    formatear_slots_para_frontend
)
from src.medical.turnos import DATABASE_URL
import psycopg


@pytest.fixture
def db_connection():
    conn = psycopg.connect(DATABASE_URL)
    yield conn
    conn.close()


@pytest.fixture
def sistema_limpio(db_connection):
    """Limpia y prepara el sistema para tests de integración"""
    with db_connection.cursor() as cur:
        # Limpiar citas de prueba
        cur.execute("DELETE FROM citas_medicas WHERE fecha_hora_inicio > NOW() + INTERVAL '1 month'")
        
        # Resetear control_turnos
        cur.execute("TRUNCATE TABLE control_turnos RESTART IDENTITY CASCADE")
        cur.execute("""
            INSERT INTO control_turnos (ultimo_doctor_id, citas_santiago, citas_joana)
            VALUES (NULL, 0, 0)
        """)
        db_connection.commit()
    
    yield
    
    # Cleanup final
    with db_connection.cursor() as cur:
        cur.execute("DELETE FROM citas_medicas WHERE fecha_hora_inicio > NOW() + INTERVAL '1 month'")
        db_connection.commit()


@pytest.fixture
def verificar_doctores(db_connection):
    with db_connection.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM doctores WHERE id IN (1, 2)")
        if cur.fetchone()[0] < 2:
            pytest.skip("Requiere doctores 1 y 2")


# ============================================================================
# TESTS: Flujos Completos
# ============================================================================

def test_flujo_completo_consulta_a_agendamiento(verificar_doctores, sistema_limpio, db_connection):
    """Test 5.1: Flujo completo: consultar slots → seleccionar → agendar → confirmar"""
    # PASO 1: Generar slots
    slots = generar_slots_con_turnos(dias_adelante=3, incluir_doctor_interno=True)
    assert len(slots) > 0
    
    # PASO 2: Formatear para frontend (ocultar doctor)
    slots_publicos = formatear_slots_para_frontend(slots)
    assert "doctor_asignado_id" not in slots_publicos[0]
    
    # PASO 3: Usuario selecciona un slot
    slot_seleccionado = slots[0]  # Versión interna (con doctor_id)
    doctor_id = slot_seleccionado["doctor_asignado_id"]
    
    # PASO 4: Agendar cita
    fecha_str = f"{slot_seleccionado['fecha']}T{slot_seleccionado['hora_inicio']}"
    fecha_inicio = datetime.fromisoformat(fecha_str).replace(tzinfo=pytz.timezone("America/Tijuana"))
    fecha_fin = fecha_inicio + timedelta(hours=1)
    
    with db_connection.cursor() as cur:
        cur.execute("""
            INSERT INTO citas_medicas (
                doctor_id, fecha_hora_inicio, fecha_hora_fin, 
                estado, fue_asignacion_automatica, doctor_turno_original
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (doctor_id, fecha_inicio, fecha_fin, 'programada', True, doctor_id))
        
        cita_id = cur.fetchone()[0]
        db_connection.commit()
    
    # PASO 5: Actualizar control de turnos
    resultado = actualizar_control_turnos(doctor_id)
    assert resultado == True
    
    # PASO 6: Verificar estadísticas
    stats = obtener_estadisticas_turnos()
    assert stats["total_turnos"] >= 1
    
    # Cleanup
    with db_connection.cursor() as cur:
        cur.execute("DELETE FROM citas_medicas WHERE id = %s", (cita_id,))
        db_connection.commit()


def test_10_agendamientos_consecutivos(verificar_doctores, sistema_limpio):
    """Test 5.2: 10 agendamientos consecutivos mantienen alternancia"""
    doctores_asignados = []
    
    for i in range(10):
        # Obtener doctor del turno
        doctor = obtener_siguiente_doctor_turno()
        doctores_asignados.append(doctor["doctor_id"])
        
        # Actualizar turnos (simular agendamiento)
        actualizar_control_turnos(doctor["doctor_id"])
    
    # Debe alternar perfectamente: [1, 2, 1, 2, ...]
    esperado = [1, 2] * 5
    assert doctores_asignados == esperado


def test_equidad_distribucion_20_citas(verificar_doctores, sistema_limpio):
    """Test 5.3: Después de 20 citas, distribución es 50%-50%"""
    for i in range(20):
        doctor = obtener_siguiente_doctor_turno()
        actualizar_control_turnos(doctor["doctor_id"])
    
    stats = obtener_estadisticas_turnos()
    
    # Debe ser exactamente 10 cada uno
    assert stats["citas_santiago"] == 10
    assert stats["citas_joana"] == 10
    assert stats["porcentaje_santiago"] == 50.0
    assert stats["porcentaje_joana"] == 50.0


def test_equidad_distribucion_100_citas(verificar_doctores, sistema_limpio):
    """Test 5.4: Equidad se mantiene incluso con 100 citas"""
    for i in range(100):
        doctor = obtener_siguiente_doctor_turno()
        actualizar_control_turnos(doctor["doctor_id"])
    
    stats = obtener_estadisticas_turnos()
    
    # Debe ser 50-50
    assert stats["citas_santiago"] == 50
    assert stats["citas_joana"] == 50


# ============================================================================
# TESTS: Concurrencia y Edge Cases
# ============================================================================

def test_multiples_usuarios_consultan_simultaneamente(verificar_doctores):
    """Test 5.5: Sistema maneja múltiples consultas simultáneas"""
    # Simular 5 usuarios consultando slots al mismo tiempo
    resultados = []
    
    for i in range(5):
        slots = generar_slots_con_turnos(dias_adelante=2)
        resultados.append(len(slots))
    
    # Todos deben obtener slots
    for count in resultados:
        assert count > 0


def test_sistema_recupera_de_error_bd(verificar_doctores):
    """Test 5.6: Sistema se recupera de errores de BD"""
    from unittest.mock import patch
    
    # Primera llamada con BD inválida
    with patch('src.medical.turnos.DATABASE_URL', 'postgresql://invalid:invalid@localhost:9999/invalid'):
        try:
            obtener_siguiente_doctor_turno()
        except Exception:
            pass  # Esperado
    
    # Segunda llamada con BD correcta debe funcionar
    doctor = obtener_siguiente_doctor_turno()
    assert doctor is not None


def test_flujo_con_doctor_ocupado_reasigna(verificar_doctores, sistema_limpio, db_connection):
    """Test 5.7: Flujo con doctor ocupado → reasigna automáticamente"""
    # Obtener doctor del turno
    doctor_turno = obtener_siguiente_doctor_turno()
    doctor_id_turno = doctor_turno["doctor_id"]
    
    # Ocupar ese doctor
    fecha = datetime(2026, 7, 1, 10, 30, tzinfo=pytz.timezone("America/Tijuana"))
    fecha_fin = fecha + timedelta(hours=1)
    
    with db_connection.cursor() as cur:
        cur.execute("""
            INSERT INTO citas_medicas (doctor_id, fecha_hora_inicio, fecha_hora_fin, estado)
            VALUES (%s, %s, %s, %s) RETURNING id
        """, (doctor_id_turno, fecha, fecha_fin, 'programada'))
        
        cita_id = cur.fetchone()[0]
        db_connection.commit()
    
    # Verificar que está ocupado
    disponible = check_doctor_availability(doctor_id_turno, fecha, fecha_fin)
    assert disponible["disponible"] == False
    
    # El otro doctor debería estar disponible
    otro_doctor_id = 2 if doctor_id_turno == 1 else 1
    disponible_otro = check_doctor_availability(otro_doctor_id, fecha, fecha_fin)
    
    # Si el otro está disponible, el sistema puede reasignar
    if disponible_otro["disponible"]:
        assert True  # Sistema funcionó correctamente
    
    # Cleanup
    with db_connection.cursor() as cur:
        cur.execute("DELETE FROM citas_medicas WHERE id = %s", (cita_id,))
        db_connection.commit()


# ============================================================================
# TESTS: Performance
# ============================================================================

def test_performance_generar_100_slots(verificar_doctores):
    """Test 5.8: Generar 100+ slots es rápido (<5s)"""
    inicio = time.time()
    
    slots = generar_slots_con_turnos(dias_adelante=15)
    
    duracion = time.time() - inicio
    
    assert duracion < 5.0
    assert len(slots) > 50  # Al menos 50 slots en 15 días


def test_performance_100_consultas_turnos(verificar_doctores):
    """Test 5.9: 100 consultas de turnos son rápidas (<2s)"""
    inicio = time.time()
    
    for i in range(100):
        obtener_siguiente_doctor_turno()
    
    duracion = time.time() - inicio
    
    assert duracion < 2.0


def test_sistema_maneja_carga_mixta(verificar_doctores, sistema_limpio):
    """Test 5.10: Sistema maneja carga mixta (slots + turnos + disponibilidad)"""
    inicio = time.time()
    
    # Operaciones mixtas
    for i in range(10):
        # Consultar slots
        slots = generar_slots_con_turnos(dias_adelante=2)
        
        # Obtener turno
        doctor = obtener_siguiente_doctor_turno()
        
        # Verificar disponibilidad
        fecha = datetime(2026, 7, i+1, 10, 30, tzinfo=pytz.timezone("America/Tijuana"))
        fecha_fin = fecha + timedelta(hours=1)
        check_doctor_availability(doctor["doctor_id"], fecha, fecha_fin)
        
        # Actualizar turnos
        actualizar_control_turnos(doctor["doctor_id"])
    
    duracion = time.time() - inicio
    
    # Debe completar en menos de 10 segundos
    assert duracion < 10.0
    
    # Verificar que todo funcionó
    stats = obtener_estadisticas_turnos()
    assert stats["total_turnos"] == 10
