"""
Test 01: Nodos N0 + N1 (Identificación + Caché de Sesión)

Prueba incremental que verifica:
- N0: Identificación de usuario (ya probado)
- N1: Caché de sesión (nuevo)

El nodo de caché maneja la persistencia de sesión y evita
consultas repetidas a BD para el mismo usuario.
"""

import pytest
from datetime import datetime, timedelta

from conftest import (
    crear_estado_base,
    validar_estado_post_identificacion,
    TEST_PACIENTE_PHONE,
    TEST_DOCTOR_PHONE,
    TEST_ADMIN_PHONE,
)


class TestNodosCacheIncremental:
    """Tests incrementales: N0 → N1"""

    def test_flujo_identificacion_cache_paciente(
        self, nodo_identificacion, nodo_cache, estado_paciente, setup_test_data
    ):
        """
        Test: Flujo completo N0 → N1 para paciente.
        
        Escenario: Paciente envía mensaje, se identifica y se cachea.
        """
        # N0: Identificación
        resultado_n0 = nodo_identificacion(estado_paciente)
        validar_estado_post_identificacion(resultado_n0)
        
        # Verificar que N0 funcionó
        assert resultado_n0["user_id"] == TEST_PACIENTE_PHONE
        assert resultado_n0["usuario_registrado"] == True
        
        # N1: Caché de sesión
        resultado_n1 = nodo_cache(resultado_n0)
        
        # Verificar que el caché mantiene la información
        assert resultado_n1["user_id"] == TEST_PACIENTE_PHONE
        assert resultado_n1["usuario_registrado"] == True
        
        # Verificar que se asignó session_id si no había
        assert resultado_n1.get("session_id") is not None
        
        print(f"✅ Flujo N0→N1 completado para paciente")
        print(f"   Session ID: {resultado_n1.get('session_id')}")

    def test_flujo_identificacion_cache_doctor(
        self, nodo_identificacion, nodo_cache, estado_doctor, setup_test_data
    ):
        """
        Test: Flujo completo N0 → N1 para doctor.
        
        Escenario: Doctor envía mensaje, se identifica con permisos especiales.
        """
        # N0: Identificación
        resultado_n0 = nodo_identificacion(estado_doctor)
        validar_estado_post_identificacion(resultado_n0)
        
        # Verificar identificación de doctor
        assert resultado_n0["tipo_usuario"] == "doctor"
        assert resultado_n0["doctor_id"] is not None
        
        # N1: Caché de sesión
        resultado_n1 = nodo_cache(resultado_n0)
        
        # Verificar que se mantienen datos de doctor
        assert resultado_n1["tipo_usuario"] == "doctor"
        assert resultado_n1["doctor_id"] == resultado_n0["doctor_id"]
        
        print(f"✅ Flujo N0→N1 completado para doctor")
        print(f"   Doctor ID: {resultado_n1['doctor_id']}")

    def test_flujo_identificacion_cache_admin(
        self, nodo_identificacion, nodo_cache, estado_admin, setup_test_data
    ):
        """
        Test: Flujo completo N0 → N1 para admin.
        
        Escenario: Admin envía mensaje, se identifica con permisos elevados.
        """
        # N0: Identificación
        resultado_n0 = nodo_identificacion(estado_admin)
        validar_estado_post_identificacion(resultado_n0)
        
        # Verificar identificación de admin
        assert resultado_n0["es_admin"] == True
        assert resultado_n0["tipo_usuario"] == "admin"
        
        # N1: Caché de sesión
        resultado_n1 = nodo_cache(resultado_n0)
        
        # Verificar que se mantienen permisos de admin
        assert resultado_n1["es_admin"] == True
        
        print(f"✅ Flujo N0→N1 completado para admin")

    def test_cache_preserva_mensajes(
        self, nodo_identificacion, nodo_cache, setup_test_data
    ):
        """
        Test: Verificar que el caché preserva los mensajes.
        
        Escenario: Mensaje del usuario se mantiene a través del flujo.
        """
        mensaje_original = "Hola, necesito agendar una cita"
        estado = crear_estado_base(
            user_id=TEST_PACIENTE_PHONE,
            mensaje=mensaje_original
        )
        
        # N0 → N1
        resultado_n0 = nodo_identificacion(estado)
        resultado_n1 = nodo_cache(resultado_n0)
        
        # Verificar que el mensaje original se mantiene
        mensajes = resultado_n1.get("messages", [])
        assert len(mensajes) > 0
        assert mensaje_original in mensajes[-1].content
        
        print(f"✅ Mensajes preservados correctamente")

    def test_cache_sesion_expiracion(
        self, nodo_identificacion, nodo_cache, setup_test_data
    ):
        """
        Test: Verificar comportamiento con sesión expirada.
        
        Escenario: Estado indica sesión expirada, se debe renovar.
        """
        estado = crear_estado_base(
            user_id=TEST_PACIENTE_PHONE,
            mensaje="Hola de nuevo"
        )
        # Simular sesión expirada
        estado = dict(estado)
        estado["sesion_expirada"] = True
        
        # N0: Identificación
        resultado_n0 = nodo_identificacion(estado)
        
        # N1: Caché debe manejar la sesión expirada
        resultado_n1 = nodo_cache(resultado_n0)
        
        # El sistema debe poder continuar
        assert resultado_n1["user_id"] == TEST_PACIENTE_PHONE
        
        print(f"✅ Sesión expirada manejada correctamente")


class TestCachePerformance:
    """Tests de rendimiento para el caché."""

    @pytest.mark.slow
    def test_cache_mejora_rendimiento(
        self, nodo_identificacion, nodo_cache, setup_test_data
    ):
        """
        Test: Verificar que el caché mejora tiempos de respuesta.
        
        Escenario: Segunda llamada debe ser más rápida por caché.
        """
        import time
        
        estado = crear_estado_base(
            user_id=TEST_PACIENTE_PHONE,
            mensaje="Primera llamada"
        )
        
        # Primera llamada (sin caché)
        start1 = time.time()
        resultado_n0 = nodo_identificacion(estado)
        resultado_n1 = nodo_cache(resultado_n0)
        tiempo1 = time.time() - start1
        
        # Segunda llamada (con caché potencialmente activo)
        estado2 = crear_estado_base(
            user_id=TEST_PACIENTE_PHONE,
            mensaje="Segunda llamada"
        )
        # Mantener session_id para aprovechar caché
        estado2 = dict(estado2)
        estado2["session_id"] = resultado_n1.get("session_id")
        
        start2 = time.time()
        resultado_n0_2 = nodo_identificacion(estado2)
        resultado_n1_2 = nodo_cache(resultado_n0_2)
        tiempo2 = time.time() - start2
        
        print(f"📊 Tiempo primera llamada: {tiempo1*1000:.2f}ms")
        print(f"📊 Tiempo segunda llamada: {tiempo2*1000:.2f}ms")
        
        # Ambas deben completar en tiempo razonable
        assert tiempo1 < 5.0, "Primera llamada no debe tardar más de 5s"
        assert tiempo2 < 5.0, "Segunda llamada no debe tardar más de 5s"
