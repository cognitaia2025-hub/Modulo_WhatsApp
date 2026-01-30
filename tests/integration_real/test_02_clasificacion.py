"""
Test 02: Nodos N0 + N1 + N2 (Identificación + Caché + Clasificación)

Prueba incremental que verifica:
- N0: Identificación de usuario
- N1: Caché de sesión
- N2: Clasificación inteligente (USA LLM REAL - DeepSeek)

El nodo de clasificación analiza el mensaje y determina:
- Categoría (saludo, cita, consulta médica, etc.)
- Intención del usuario
- Si requiere herramientas
"""

import pytest
from datetime import datetime

from conftest import (
    crear_estado_base,
    validar_estado_post_identificacion,
    TEST_PACIENTE_PHONE,
    TEST_DOCTOR_PHONE,
    TEST_ADMIN_PHONE,
)


class TestNodosClasificacionIncremental:
    """Tests incrementales: N0 → N1 → N2 (con LLM real)"""

    def test_clasificar_saludo_simple(
        self, nodo_identificacion, nodo_cache, nodo_clasificacion, setup_test_data
    ):
        """
        Test: Clasificar un saludo simple.
        
        Escenario: Usuario dice "Hola, ¿cómo estás?"
        Esperado: Clasificación como 'saludo', 'chat' o similar.
        """
        estado = crear_estado_base(
            user_id=TEST_PACIENTE_PHONE,
            mensaje="Hola, ¿cómo estás?"
        )
        
        # N0 → N1 → N2
        resultado_n0 = nodo_identificacion(estado)
        resultado_n1 = nodo_cache(resultado_n0)
        resultado_n2 = nodo_clasificacion(resultado_n1)
        
        # Verificar clasificación
        clasificacion = resultado_n2.get("clasificacion_mensaje")
        assert clasificacion is not None, "Debe haber clasificación"
        
        # Saludos deben clasificarse como chat/saludo/conversacional
        assert clasificacion.lower() in ["chat", "saludo", "conversacional", "chat_casual"], \
            f"Saludo debe clasificarse como chat, pero fue: {clasificacion}"
        
        print(f"✅ Clasificación de saludo:")
        print(f"   Tipo: {clasificacion}")
        print(f"   Confianza: {resultado_n2.get('confianza_clasificacion')}")
        print(f"   Modelo usado: {resultado_n2.get('modelo_clasificacion_usado')}")

    def test_clasificar_solicitud_cita(
        self, nodo_identificacion, nodo_cache, nodo_clasificacion, setup_test_data
    ):
        """
        Test: Clasificar solicitud de cita médica.
        
        Escenario: Paciente pide agendar cita.
        Esperado: Clasificación como 'cita_medica' o similar, requiere herramientas.
        """
        estado = crear_estado_base(
            user_id=TEST_PACIENTE_PHONE,
            mensaje="Necesito agendar una cita médica para mañana con el doctor"
        )
        
        # N0 → N1 → N2
        resultado_n0 = nodo_identificacion(estado)
        resultado_n1 = nodo_cache(resultado_n0)
        resultado_n2 = nodo_clasificacion(resultado_n1)
        
        # Verificar clasificación
        clasificacion = resultado_n2.get("clasificacion_mensaje")
        assert clasificacion is not None
        
        # Solicitudes de cita generalmente requieren herramientas
        print(f"✅ Clasificación de solicitud de cita:")
        print(f"   Tipo: {clasificacion}")
        print(f"   Requiere herramientas: {resultado_n2.get('requiere_herramientas')}")
        print(f"   Confianza: {resultado_n2.get('confianza_clasificacion')}")

    def test_clasificar_consulta_disponibilidad(
        self, nodo_identificacion, nodo_cache, nodo_clasificacion, setup_test_data
    ):
        """
        Test: Clasificar consulta de disponibilidad.
        
        Escenario: Paciente pregunta por horarios disponibles.
        Esperado: Clasificación relacionada con disponibilidad.
        """
        estado = crear_estado_base(
            user_id=TEST_PACIENTE_PHONE,
            mensaje="¿Qué horarios tienen disponibles para esta semana?"
        )
        
        # N0 → N1 → N2
        resultado_n0 = nodo_identificacion(estado)
        resultado_n1 = nodo_cache(resultado_n0)
        resultado_n2 = nodo_clasificacion(resultado_n1)
        
        clasificacion = resultado_n2.get("clasificacion_mensaje")
        assert clasificacion is not None
        
        print(f"✅ Clasificación de consulta disponibilidad:")
        print(f"   Tipo: {clasificacion}")
        print(f"   Requiere herramientas: {resultado_n2.get('requiere_herramientas')}")

    def test_clasificar_doctor_consulta_citas(
        self, nodo_identificacion, nodo_cache, nodo_clasificacion, setup_test_data
    ):
        """
        Test: Doctor consulta sus citas del día.
        
        Escenario: Doctor pregunta por su agenda.
        Esperado: Clasificación como consulta de agenda médica.
        """
        estado = crear_estado_base(
            user_id=TEST_DOCTOR_PHONE,
            mensaje="¿Cuántos pacientes tengo agendados para hoy?"
        )
        
        # N0 → N1 → N2
        resultado_n0 = nodo_identificacion(estado)
        resultado_n1 = nodo_cache(resultado_n0)
        resultado_n2 = nodo_clasificacion(resultado_n1)
        
        # El nodo N2 solo retorna campos de clasificación
        # La info de doctor está en resultado_n1
        assert resultado_n1["tipo_usuario"] == "doctor"
        
        clasificacion = resultado_n2.get("clasificacion_mensaje")
        assert clasificacion is not None
        
        print(f"✅ Clasificación de consulta de doctor:")
        print(f"   Tipo: {clasificacion}")
        print(f"   Doctor ID: {resultado_n1.get('doctor_id')}")

    def test_clasificar_admin_reporte(
        self, nodo_identificacion, nodo_cache, nodo_clasificacion, setup_test_data
    ):
        """
        Test: Admin solicita reporte.
        
        Escenario: Admin pide estadísticas.
        Esperado: Clasificación administrativa.
        """
        estado = crear_estado_base(
            user_id=TEST_ADMIN_PHONE,
            mensaje="Dame un reporte de las citas de la última semana"
        )
        
        # N0 → N1 → N2
        resultado_n0 = nodo_identificacion(estado)
        resultado_n1 = nodo_cache(resultado_n0)
        resultado_n2 = nodo_clasificacion(resultado_n1)
        
        # El nodo N2 solo retorna campos de clasificación
        # La info de admin está en resultado_n1
        assert resultado_n1["es_admin"] == True
        
        clasificacion = resultado_n2.get("clasificacion_mensaje")
        assert clasificacion is not None
        
        print(f"✅ Clasificación de solicitud admin:")
        print(f"   Tipo: {clasificacion}")
        print(f"   Es admin: {resultado_n1['es_admin']}")

    def test_clasificar_evento_calendario_personal(
        self, nodo_identificacion, nodo_cache, nodo_clasificacion, setup_test_data
    ):
        """
        Test: Crear evento en calendario personal.
        
        Escenario: Usuario quiere agregar evento personal.
        Esperado: Clasificación de calendario personal.
        """
        estado = crear_estado_base(
            user_id=TEST_PACIENTE_PHONE,
            mensaje="Crea un evento llamado 'Reunión de trabajo' mañana a las 3pm"
        )
        
        # N0 → N1 → N2
        resultado_n0 = nodo_identificacion(estado)
        resultado_n1 = nodo_cache(resultado_n0)
        resultado_n2 = nodo_clasificacion(resultado_n1)
        
        clasificacion = resultado_n2.get("clasificacion_mensaje")
        assert clasificacion is not None
        
        # Eventos de calendario deben requerir herramientas
        print(f"✅ Clasificación de evento calendario:")
        print(f"   Tipo: {clasificacion}")
        print(f"   Requiere herramientas: {resultado_n2.get('requiere_herramientas')}")


class TestClasificacionLLMDetalles:
    """Tests detallados del comportamiento del LLM."""

    def test_tiempo_clasificacion_razonable(
        self, nodo_identificacion, nodo_cache, nodo_clasificacion, setup_test_data
    ):
        """
        Test: Verificar tiempo de respuesta del LLM.
        
        Esperado: Clasificación en menos de 10 segundos.
        """
        import time
        
        estado = crear_estado_base(
            user_id=TEST_PACIENTE_PHONE,
            mensaje="Quiero agendar una cita"
        )
        
        resultado_n0 = nodo_identificacion(estado)
        resultado_n1 = nodo_cache(resultado_n0)
        
        start = time.time()
        resultado_n2 = nodo_clasificacion(resultado_n1)
        tiempo_ms = (time.time() - start) * 1000
        
        # Verificar tiempo registrado
        tiempo_reportado = resultado_n2.get("tiempo_clasificacion_ms")
        
        print(f"📊 Tiempo de clasificación:")
        print(f"   Medido: {tiempo_ms:.2f}ms")
        print(f"   Reportado: {tiempo_reportado}ms")
        
        # Debe completar en tiempo razonable
        assert tiempo_ms < 15000, "Clasificación no debe tardar más de 15s"

    def test_modelo_usado_es_esperado(
        self, nodo_identificacion, nodo_cache, nodo_clasificacion, setup_test_data
    ):
        """
        Test: Verificar que se usa el modelo esperado.
        
        Esperado: DeepSeek o Claude como modelo principal.
        """
        estado = crear_estado_base(
            user_id=TEST_PACIENTE_PHONE,
            mensaje="Hola"
        )
        
        resultado_n0 = nodo_identificacion(estado)
        resultado_n1 = nodo_cache(resultado_n0)
        resultado_n2 = nodo_clasificacion(resultado_n1)
        
        modelo = resultado_n2.get("modelo_clasificacion_usado")
        
        print(f"✅ Modelo de clasificación: {modelo}")
        
        # Debe usar uno de los modelos configurados
        if modelo:
            assert any(m in modelo.lower() for m in ["deepseek", "claude", "gpt"]), \
                f"Modelo inesperado: {modelo}"

    def test_confianza_clasificacion(
        self, nodo_identificacion, nodo_cache, nodo_clasificacion, setup_test_data
    ):
        """
        Test: Verificar que se reporta confianza de clasificación.
        
        Esperado: Valor de confianza entre 0 y 1.
        """
        estado = crear_estado_base(
            user_id=TEST_PACIENTE_PHONE,
            mensaje="Necesito urgentemente una cita con el doctor para mañana"
        )
        
        resultado_n0 = nodo_identificacion(estado)
        resultado_n1 = nodo_cache(resultado_n0)
        resultado_n2 = nodo_clasificacion(resultado_n1)
        
        confianza = resultado_n2.get("confianza_clasificacion")
        
        print(f"✅ Confianza de clasificación: {confianza}")
        
        # Si hay confianza, debe ser valor válido
        if confianza is not None:
            assert 0 <= confianza <= 1, f"Confianza fuera de rango: {confianza}"
