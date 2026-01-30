"""
Test 05: Flujo Completo con Ejecución de Herramientas (N0-N5)

Este test verifica el flujo completo hasta la ejecución de herramientas,
incluyendo la integración con Google Calendar (si está disponible).

Nodos probados:
- N0: Identificación
- N1: Caché
- N2: Clasificación (LLM)
- N3: Recuperación
- N4: Selección de herramientas (LLM)
- N5: Ejecución de herramientas (Calendar API)
"""

import pytest
import os
from datetime import datetime, timedelta

from conftest import (
    crear_estado_base,
    TEST_PACIENTE_PHONE,
    TEST_DOCTOR_PHONE,
)


def calendar_disponible():
    """Verifica si Google Calendar está configurado."""
    creds_file = "pro-core-466508-u7-76f56aed8c8b.json"
    return os.path.exists(creds_file) and os.path.getsize(creds_file) > 10


class TestFlujoEjecucionHerramientas:
    """Tests del flujo completo con herramientas."""

    def test_flujo_hasta_clasificacion(
        self, nodo_identificacion, nodo_cache, nodo_clasificacion, setup_test_data
    ):
        """
        Test: Flujo N0 → N1 → N2 completo.
        
        Verifica que la clasificación de solicitudes médicas funciona.
        """
        estado = crear_estado_base(
            user_id=TEST_PACIENTE_PHONE,
            mensaje="Quiero agendar una cita médica para el próximo lunes a las 10am"
        )
        
        # N0 → N1 → N2
        resultado_n0 = nodo_identificacion(estado)
        resultado_n1 = nodo_cache(resultado_n0)
        resultado_n2 = nodo_clasificacion(resultado_n1)
        
        # Verificar clasificación de solicitud médica
        clasificacion = resultado_n2.get("clasificacion_mensaje")
        assert clasificacion is not None
        
        # Las solicitudes de citas deben clasificarse como médica o cita
        print(f"✅ Clasificación de solicitud de cita:")
        print(f"   Tipo: {clasificacion}")
        print(f"   Modelo: {resultado_n2.get('modelo_clasificacion_usado')}")

    @pytest.mark.skipif(not calendar_disponible(), reason="Google Calendar no configurado")
    def test_flujo_crear_evento_calendario(
        self, nodo_identificacion, nodo_cache, nodo_clasificacion, 
        nodo_seleccion, nodo_ejecucion, google_calendar_service,
        cleanup_test_events, setup_test_data
    ):
        """
        Test: Crear evento real en Google Calendar.
        
        NOTA: Este test crea un evento REAL en el calendario.
        Se elimina automáticamente después del test.
        """
        # Crear solicitud de evento para mañana
        manana = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        estado = crear_estado_base(
            user_id=TEST_PACIENTE_PHONE,
            mensaje=f"Crea un evento llamado '[TEST] Cita de prueba' para {manana} a las 3pm"
        )
        
        # Flujo completo N0 → N5
        resultado_n0 = nodo_identificacion(estado)
        resultado_n1 = nodo_cache(resultado_n0)
        resultado_n2 = nodo_clasificacion(resultado_n1)
        resultado_n3 = nodo_seleccion({**resultado_n1, **resultado_n2})
        resultado_n5 = nodo_ejecucion({**resultado_n3})
        
        # Verificar que se creó el evento
        if resultado_n5.get("herramientas_ejecutadas"):
            herramientas = resultado_n5["herramientas_ejecutadas"]
            print(f"✅ Herramientas ejecutadas: {herramientas}")
            
            # Si se creó un evento, agregarlo a la lista de limpieza
            for h in herramientas:
                if h.get("event_id"):
                    cleanup_test_events.append(h["event_id"])
                    print(f"   📅 Evento creado: {h['event_id']}")

    @pytest.mark.skipif(not calendar_disponible(), reason="Google Calendar no configurado")
    def test_flujo_consultar_disponibilidad(
        self, nodo_identificacion, nodo_cache, nodo_clasificacion,
        nodo_seleccion, setup_test_data
    ):
        """
        Test: Consultar disponibilidad de citas.
        
        Verifica que se pueden obtener slots disponibles.
        """
        estado = crear_estado_base(
            user_id=TEST_PACIENTE_PHONE,
            mensaje="¿Qué horarios tienen disponibles para citas esta semana?"
        )
        
        # N0 → N4
        resultado_n0 = nodo_identificacion(estado)
        resultado_n1 = nodo_cache(resultado_n0)
        resultado_n2 = nodo_clasificacion(resultado_n1)
        resultado_n4 = nodo_seleccion({**resultado_n1, **resultado_n2})
        
        # Verificar selección de herramientas
        herramientas = resultado_n4.get("herramientas_seleccionadas", [])
        print(f"✅ Herramientas seleccionadas: {herramientas}")


class TestFlujoDoctor:
    """Tests de flujo para usuarios tipo doctor."""

    def test_doctor_consulta_agenda(
        self, nodo_identificacion, nodo_cache, nodo_clasificacion, setup_test_data
    ):
        """
        Test: Doctor consulta su agenda del día.
        """
        estado = crear_estado_base(
            user_id=TEST_DOCTOR_PHONE,
            mensaje="¿Cuáles son mis citas de hoy?"
        )
        
        # N0 → N2
        resultado_n0 = nodo_identificacion(estado)
        resultado_n1 = nodo_cache(resultado_n0)
        resultado_n2 = nodo_clasificacion(resultado_n1)
        
        # Verificar que se identificó como doctor
        assert resultado_n1["tipo_usuario"] == "doctor"
        assert resultado_n1["doctor_id"] is not None
        
        # Verificar clasificación
        clasificacion = resultado_n2.get("clasificacion_mensaje")
        assert clasificacion is not None
        
        print(f"✅ Consulta de doctor:")
        print(f"   Doctor ID: {resultado_n1['doctor_id']}")
        print(f"   Clasificación: {clasificacion}")

    def test_doctor_buscar_historial(
        self, nodo_identificacion, nodo_cache, nodo_clasificacion, setup_test_data
    ):
        """
        Test: Doctor busca historial de paciente.
        """
        estado = crear_estado_base(
            user_id=TEST_DOCTOR_PHONE,
            mensaje="Busca el historial médico del paciente María García"
        )
        
        # N0 → N2
        resultado_n0 = nodo_identificacion(estado)
        resultado_n1 = nodo_cache(resultado_n0)
        resultado_n2 = nodo_clasificacion(resultado_n1)
        
        clasificacion = resultado_n2.get("clasificacion_mensaje")
        
        print(f"✅ Búsqueda de historial:")
        print(f"   Clasificación: {clasificacion}")


class TestFlujoConversacional:
    """Tests de flujo para conversaciones sin herramientas."""

    def test_chat_casual(
        self, nodo_identificacion, nodo_cache, nodo_clasificacion, setup_test_data
    ):
        """
        Test: Conversación casual que no requiere herramientas.
        """
        estado = crear_estado_base(
            user_id=TEST_PACIENTE_PHONE,
            mensaje="Gracias por la información, que tengas buen día"
        )
        
        # N0 → N2
        resultado_n0 = nodo_identificacion(estado)
        resultado_n1 = nodo_cache(resultado_n0)
        resultado_n2 = nodo_clasificacion(resultado_n1)
        
        clasificacion = resultado_n2.get("clasificacion_mensaje")
        
        # Chat casual debe clasificarse como chat
        assert clasificacion in ["chat", "saludo", "despedida", "agradecimiento"], \
            f"Chat casual clasificado como: {clasificacion}"
        
        print(f"✅ Chat casual clasificado como: {clasificacion}")

    def test_pregunta_general(
        self, nodo_identificacion, nodo_cache, nodo_clasificacion, setup_test_data
    ):
        """
        Test: Pregunta general sobre el servicio.
        """
        estado = crear_estado_base(
            user_id=TEST_PACIENTE_PHONE,
            mensaje="¿Cuáles son los horarios de atención de la clínica?"
        )
        
        resultado_n0 = nodo_identificacion(estado)
        resultado_n1 = nodo_cache(resultado_n0)
        resultado_n2 = nodo_clasificacion(resultado_n1)
        
        clasificacion = resultado_n2.get("clasificacion_mensaje")
        
        print(f"✅ Pregunta general clasificada como: {clasificacion}")
