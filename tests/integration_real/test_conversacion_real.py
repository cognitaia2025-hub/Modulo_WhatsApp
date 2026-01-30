"""
Tests de Conversación REAL con el Sistema

Estos tests ejecutan el flujo COMPLETO del grafo y muestran
las respuestas generadas por el LLM (DeepSeek).

Escenarios:
1. Paciente agenda una cita
2. Paciente pregunta por disponibilidad
3. Doctor consulta sus citas
4. Paciente reagenda cita
5. Conversación casual
"""

import pytest
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Agregar raíz al path
ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Constantes de teléfonos de prueba
TEST_PACIENTE_PHONE = "+526649876543"
TEST_DOCTOR_PHONE = "+526641111111"
TEST_ADMIN_PHONE = "+526641234567"


def ejecutar_conversacion(user_id: str, mensaje: str, nombre: str = "Usuario"):
    """
    Ejecuta una conversación completa a través del grafo.
    
    Retorna la respuesta del sistema.
    """
    from src.graph_whatsapp_etapa8 import crear_grafo_whatsapp
    from langchain_core.messages import HumanMessage
    
    # Crear grafo
    grafo = crear_grafo_whatsapp()
    
    # Estado inicial
    estado_inicial = {
        "messages": [HumanMessage(content=mensaje)],
        "user_id": user_id,
        "session_id": f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
    }
    
    # Configuración del thread
    config = {
        "configurable": {
            "thread_id": f"test_thread_{user_id}_{datetime.now().timestamp()}"
        }
    }
    
    print(f"\n{'='*70}")
    print(f"👤 {nombre} ({user_id})")
    print(f"💬 Mensaje: \"{mensaje}\"")
    print(f"{'='*70}")
    
    # Ejecutar grafo
    resultado = grafo.invoke(estado_inicial, config)
    
    # Extraer respuesta
    mensajes = resultado.get("messages", [])
    respuesta = None
    
    for msg in reversed(mensajes):
        if hasattr(msg, 'content') and msg.content:
            # Buscar mensaje de respuesta (no el del usuario)
            if msg.content != mensaje:
                respuesta = msg.content
                break
    
    # Mostrar información del procesamiento
    print(f"\n📊 PROCESAMIENTO:")
    print(f"   • Tipo usuario: {resultado.get('tipo_usuario', 'N/A')}")
    print(f"   • Clasificación: {resultado.get('clasificacion_mensaje', 'N/A')}")
    print(f"   • Confianza: {resultado.get('confianza_clasificacion', 'N/A')}")
    print(f"   • Modelo: {resultado.get('modelo_clasificacion_usado', 'N/A')}")
    
    if resultado.get('herramientas_seleccionadas'):
        print(f"   • Herramientas: {resultado.get('herramientas_seleccionadas')}")
    
    print(f"\n🤖 RESPUESTA DEL SISTEMA:")
    print(f"{'─'*70}")
    if respuesta:
        # Formatear respuesta para mejor lectura
        for linea in respuesta.split('\n'):
            print(f"   {linea}")
    else:
        print("   [Sin respuesta generada]")
    print(f"{'─'*70}")
    
    return resultado, respuesta


class TestConversacionPaciente:
    """Tests de conversación real como paciente."""

    def test_paciente_saluda(self):
        """
        Test: Paciente saluda al sistema.
        
        Esperado: Respuesta amigable de bienvenida.
        """
        resultado, respuesta = ejecutar_conversacion(
            user_id=TEST_PACIENTE_PHONE,
            mensaje="Hola, buenos días",
            nombre="Juan Pérez (Paciente)"
        )
        
        assert resultado.get("clasificacion_mensaje") in ["chat", "saludo"]
        assert respuesta is not None
        print(f"\n✅ Test pasado: Saludo procesado correctamente")

    def test_paciente_pregunta_disponibilidad(self):
        """
        Test: Paciente pregunta por horarios disponibles.
        
        Esperado: Información sobre disponibilidad de citas.
        """
        resultado, respuesta = ejecutar_conversacion(
            user_id=TEST_PACIENTE_PHONE,
            mensaje="¿Qué horarios tienen disponibles para una cita esta semana?",
            nombre="Juan Pérez (Paciente)"
        )
        
        assert resultado.get("clasificacion_mensaje") is not None
        print(f"\n✅ Test pasado: Consulta de disponibilidad procesada")

    def test_paciente_agenda_cita(self):
        """
        Test: Paciente quiere agendar una cita.
        
        Esperado: El sistema inicia proceso de agendamiento.
        """
        # Calcular fecha del próximo lunes
        hoy = datetime.now()
        dias_hasta_lunes = (7 - hoy.weekday()) % 7
        if dias_hasta_lunes == 0:
            dias_hasta_lunes = 7
        proximo_lunes = hoy + timedelta(days=dias_hasta_lunes)
        fecha = proximo_lunes.strftime("%d de %B")
        
        resultado, respuesta = ejecutar_conversacion(
            user_id=TEST_PACIENTE_PHONE,
            mensaje=f"Quiero agendar una cita médica para el {fecha} a las 10 de la mañana",
            nombre="Juan Pérez (Paciente)"
        )
        
        # Debe clasificarse como médica o cita
        clasificacion = resultado.get("clasificacion_mensaje", "")
        assert clasificacion in ["medica", "cita", "solicitud_cita_paciente", "agendar"]
        print(f"\n✅ Test pasado: Solicitud de cita procesada")

    def test_paciente_consulta_sus_citas(self):
        """
        Test: Paciente pregunta por sus citas programadas.
        """
        resultado, respuesta = ejecutar_conversacion(
            user_id=TEST_PACIENTE_PHONE,
            mensaje="¿Tengo alguna cita programada?",
            nombre="Juan Pérez (Paciente)"
        )
        
        assert resultado.get("clasificacion_mensaje") is not None
        print(f"\n✅ Test pasado: Consulta de citas procesada")

    def test_paciente_cancela_cita(self):
        """
        Test: Paciente quiere cancelar una cita.
        """
        resultado, respuesta = ejecutar_conversacion(
            user_id=TEST_PACIENTE_PHONE,
            mensaje="Necesito cancelar mi cita de mañana, surgió un imprevisto",
            nombre="Juan Pérez (Paciente)"
        )
        
        assert resultado.get("clasificacion_mensaje") is not None
        print(f"\n✅ Test pasado: Solicitud de cancelación procesada")

    def test_paciente_reagenda_cita(self):
        """
        Test: Paciente quiere reagendar su cita.
        """
        resultado, respuesta = ejecutar_conversacion(
            user_id=TEST_PACIENTE_PHONE,
            mensaje="¿Puedo cambiar mi cita del lunes para el miércoles a la misma hora?",
            nombre="Juan Pérez (Paciente)"
        )
        
        assert resultado.get("clasificacion_mensaje") is not None
        print(f"\n✅ Test pasado: Solicitud de reagendamiento procesada")


class TestConversacionDoctor:
    """Tests de conversación real como doctor."""

    def test_doctor_consulta_agenda_hoy(self):
        """
        Test: Doctor pregunta por sus citas del día.
        """
        resultado, respuesta = ejecutar_conversacion(
            user_id=TEST_DOCTOR_PHONE,
            mensaje="¿Cuántos pacientes tengo hoy?",
            nombre="Dr. Santiago Ornelas"
        )
        
        # Verificar que se identificó como doctor
        assert resultado.get("tipo_usuario") == "doctor"
        assert resultado.get("doctor_id") is not None
        print(f"\n✅ Test pasado: Doctor identificado y agenda consultada")

    def test_doctor_consulta_agenda_semana(self):
        """
        Test: Doctor pregunta por su agenda de la semana.
        """
        resultado, respuesta = ejecutar_conversacion(
            user_id=TEST_DOCTOR_PHONE,
            mensaje="Dame mi agenda completa de esta semana",
            nombre="Dr. Santiago Ornelas"
        )
        
        assert resultado.get("tipo_usuario") == "doctor"
        print(f"\n✅ Test pasado: Agenda semanal consultada")

    def test_doctor_busca_paciente(self):
        """
        Test: Doctor busca información de un paciente.
        """
        resultado, respuesta = ejecutar_conversacion(
            user_id=TEST_DOCTOR_PHONE,
            mensaje="Busca el historial del paciente María García",
            nombre="Dr. Santiago Ornelas"
        )
        
        assert resultado.get("tipo_usuario") == "doctor"
        print(f"\n✅ Test pasado: Búsqueda de paciente procesada")

    def test_doctor_bloquea_horario(self):
        """
        Test: Doctor quiere bloquear un horario.
        """
        resultado, respuesta = ejecutar_conversacion(
            user_id=TEST_DOCTOR_PHONE,
            mensaje="Bloquea mi agenda del viernes en la tarde, tengo una conferencia",
            nombre="Dr. Santiago Ornelas"
        )
        
        assert resultado.get("tipo_usuario") == "doctor"
        print(f"\n✅ Test pasado: Solicitud de bloqueo procesada")


class TestConversacionAdmin:
    """Tests de conversación real como administrador."""

    def test_admin_solicita_reporte(self):
        """
        Test: Admin solicita reporte de citas.
        """
        resultado, respuesta = ejecutar_conversacion(
            user_id=TEST_ADMIN_PHONE,
            mensaje="Dame un reporte de las citas de la última semana",
            nombre="Administrador"
        )
        
        assert resultado.get("es_admin") == True
        print(f"\n✅ Test pasado: Admin identificado y reporte solicitado")

    def test_admin_consulta_estadisticas(self):
        """
        Test: Admin consulta estadísticas.
        """
        resultado, respuesta = ejecutar_conversacion(
            user_id=TEST_ADMIN_PHONE,
            mensaje="¿Cuántas citas se cancelaron este mes?",
            nombre="Administrador"
        )
        
        assert resultado.get("es_admin") == True
        print(f"\n✅ Test pasado: Consulta de estadísticas procesada")


class TestConversacionCompleja:
    """Tests de conversaciones más complejas y casos especiales."""

    def test_paciente_urgencia(self):
        """
        Test: Paciente tiene una urgencia médica.
        """
        resultado, respuesta = ejecutar_conversacion(
            user_id=TEST_PACIENTE_PHONE,
            mensaje="Tengo un dolor muy fuerte, necesito ver al doctor lo antes posible",
            nombre="Juan Pérez (Urgencia)"
        )
        
        print(f"\n✅ Test pasado: Urgencia procesada")

    def test_paciente_pregunta_costos(self):
        """
        Test: Paciente pregunta por costos.
        """
        resultado, respuesta = ejecutar_conversacion(
            user_id=TEST_PACIENTE_PHONE,
            mensaje="¿Cuánto cuesta una consulta médica?",
            nombre="Juan Pérez (Paciente)"
        )
        
        print(f"\n✅ Test pasado: Consulta de costos procesada")

    def test_paciente_ubicacion(self):
        """
        Test: Paciente pregunta por ubicación.
        """
        resultado, respuesta = ejecutar_conversacion(
            user_id=TEST_PACIENTE_PHONE,
            mensaje="¿Cuál es la dirección del consultorio?",
            nombre="Juan Pérez (Paciente)"
        )
        
        print(f"\n✅ Test pasado: Consulta de ubicación procesada")

    def test_despedida(self):
        """
        Test: Usuario se despide.
        """
        resultado, respuesta = ejecutar_conversacion(
            user_id=TEST_PACIENTE_PHONE,
            mensaje="Muchas gracias por la ayuda, hasta luego",
            nombre="Juan Pérez (Paciente)"
        )
        
        clasificacion = resultado.get("clasificacion_mensaje", "")
        assert clasificacion in ["chat", "despedida", "agradecimiento"]
        print(f"\n✅ Test pasado: Despedida procesada")


if __name__ == "__main__":
    """Ejecutar tests directamente para ver la salida completa."""
    print("\n" + "="*70)
    print("🏥 TESTS DE CONVERSACIÓN REAL - SISTEMA DE CITAS MÉDICAS")
    print("="*70)
    
    # Instanciar clases de test
    test_paciente = TestConversacionPaciente()
    test_doctor = TestConversacionDoctor()
    test_admin = TestConversacionAdmin()
    test_complejo = TestConversacionCompleja()
    
    print("\n\n📱 === CONVERSACIONES DE PACIENTE ===")
    test_paciente.test_paciente_saluda()
    test_paciente.test_paciente_pregunta_disponibilidad()
    test_paciente.test_paciente_agenda_cita()
    
    print("\n\n👨‍⚕️ === CONVERSACIONES DE DOCTOR ===")
    test_doctor.test_doctor_consulta_agenda_hoy()
    test_doctor.test_doctor_consulta_agenda_semana()
    
    print("\n\n👑 === CONVERSACIONES DE ADMIN ===")
    test_admin.test_admin_solicita_reporte()
    
    print("\n\n🔄 === CONVERSACIONES COMPLEJAS ===")
    test_complejo.test_paciente_urgencia()
    test_complejo.test_despedida()
    
    print("\n" + "="*70)
    print("✅ TODOS LOS TESTS DE CONVERSACIÓN COMPLETADOS")
    print("="*70 + "\n")
