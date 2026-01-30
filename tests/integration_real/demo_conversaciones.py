"""
Tests de Conversación REAL con Respuestas del LLM

Este script ejecuta conversaciones REALES y muestra las respuestas
generadas por el sistema, tanto de clasificación como del recepcionista.
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

# Agregar raíz al path
ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Teléfonos de prueba
TEST_PACIENTE_PHONE = "+526649876543"
TEST_DOCTOR_PHONE = "+526641111111"
TEST_ADMIN_PHONE = "+526641234567"


def ejecutar_mensaje(user_id: str, mensaje: str, nombre: str = "Usuario"):
    """
    Ejecuta un mensaje a través del grafo completo y muestra TODO el proceso.
    """
    from src.graph_whatsapp_etapa8 import crear_grafo_whatsapp
    from langchain_core.messages import HumanMessage, AIMessage
    
    # Crear grafo
    grafo = crear_grafo_whatsapp()
    
    # Estado inicial
    estado_inicial = {
        "messages": [HumanMessage(content=mensaje)],
        "user_id": user_id,
        "session_id": f"demo_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "estado_conversacion": "inicial",
    }
    
    config = {
        "configurable": {
            "thread_id": f"demo_{user_id}_{datetime.now().timestamp()}"
        }
    }
    
    print(f"\n{'='*70}")
    print(f"👤 {nombre}")
    print(f"📱 Teléfono: {user_id}")
    print(f"💬 Dice: \"{mensaje}\"")
    print(f"{'='*70}")
    
    # Ejecutar
    resultado = grafo.invoke(estado_inicial, config)
    
    # Mostrar clasificación
    print(f"\n📊 ANÁLISIS DEL MENSAJE:")
    print(f"   • Tipo usuario: {resultado.get('tipo_usuario', 'N/A')}")
    print(f"   • Clasificación LLM: {resultado.get('clasificacion_mensaje', 'N/A')}")
    print(f"   • Confianza: {resultado.get('confianza_clasificacion', 'N/A')}")
    print(f"   • Modelo: {resultado.get('modelo_clasificacion_usado', 'N/A')}")
    print(f"   • Estado conversación: {resultado.get('estado_conversacion', 'N/A')}")
    
    # Buscar respuesta del sistema
    mensajes = resultado.get("messages", [])
    respuestas = []
    
    for msg in mensajes:
        if isinstance(msg, AIMessage) or (hasattr(msg, 'type') and msg.type == 'ai'):
            if hasattr(msg, 'content') and msg.content:
                respuestas.append(msg.content)
    
    # Mostrar respuestas del sistema
    print(f"\n🤖 RESPUESTA DEL SISTEMA:")
    print(f"{'─'*70}")
    
    if respuestas:
        for i, resp in enumerate(respuestas, 1):
            if len(respuestas) > 1:
                print(f"\n   [{i}] ", end="")
            else:
                print("   ", end="")
            # Formatear respuesta
            for linea in resp.split('\n'):
                print(f"{linea}")
                if linea != resp.split('\n')[-1]:
                    print("   ", end="")
    else:
        # Buscar respuesta_recepcionista
        resp_recep = resultado.get('respuesta_recepcionista')
        if resp_recep:
            for linea in resp_recep.split('\n'):
                print(f"   {linea}")
        else:
            print("   [El sistema procesó la solicitud]")
    
    print(f"{'─'*70}")
    
    # Mostrar slots disponibles si los hay
    slots = resultado.get('slots_disponibles', [])
    if slots:
        print(f"\n📅 SLOTS DISPONIBLES:")
        for slot in slots[:5]:
            print(f"   • {slot}")
    
    return resultado


def demo_paciente_agenda_cita():
    """Demo: Paciente quiere agendar una cita."""
    print("\n" + "="*70)
    print("🏥 ESCENARIO: PACIENTE AGENDA CITA MÉDICA")
    print("="*70)
    
    # Paso 1: Paciente pide cita
    resultado = ejecutar_mensaje(
        TEST_PACIENTE_PHONE,
        "Hola, quiero agendar una cita médica",
        "Juan Pérez (Paciente)"
    )
    
    return resultado


def demo_paciente_pregunta_horarios():
    """Demo: Paciente pregunta por horarios."""
    print("\n" + "="*70)
    print("🏥 ESCENARIO: PACIENTE CONSULTA DISPONIBILIDAD")
    print("="*70)
    
    resultado = ejecutar_mensaje(
        TEST_PACIENTE_PHONE,
        "¿Qué horarios tienen disponibles para esta semana?",
        "Juan Pérez (Paciente)"
    )
    
    return resultado


def demo_doctor_consulta_agenda():
    """Demo: Doctor consulta su agenda."""
    print("\n" + "="*70)
    print("👨‍⚕️ ESCENARIO: DOCTOR CONSULTA SU AGENDA")
    print("="*70)
    
    resultado = ejecutar_mensaje(
        TEST_DOCTOR_PHONE,
        "¿Cuántos pacientes tengo agendados para hoy?",
        "Dr. Santiago Ornelas"
    )
    
    return resultado


def demo_paciente_reagenda():
    """Demo: Paciente quiere reagendar."""
    print("\n" + "="*70)
    print("🔄 ESCENARIO: PACIENTE REAGENDA CITA")
    print("="*70)
    
    resultado = ejecutar_mensaje(
        TEST_PACIENTE_PHONE,
        "Necesito cambiar mi cita del lunes para otro día",
        "Juan Pérez (Paciente)"
    )
    
    return resultado


def demo_paciente_cancela():
    """Demo: Paciente cancela cita."""
    print("\n" + "="*70)
    print("❌ ESCENARIO: PACIENTE CANCELA CITA")
    print("="*70)
    
    resultado = ejecutar_mensaje(
        TEST_PACIENTE_PHONE,
        "Necesito cancelar mi cita de mañana por favor",
        "Juan Pérez (Paciente)"
    )
    
    return resultado


def demo_admin_reporte():
    """Demo: Admin solicita reporte."""
    print("\n" + "="*70)
    print("👑 ESCENARIO: ADMIN SOLICITA REPORTE")
    print("="*70)
    
    resultado = ejecutar_mensaje(
        TEST_ADMIN_PHONE,
        "Dame un reporte de las citas de esta semana",
        "Administrador"
    )
    
    return resultado


if __name__ == "__main__":
    print("\n" + "🏥"*35)
    print("\n      DEMO: SISTEMA DE CITAS MÉDICAS VÍA WHATSAPP")
    print("      Conversaciones REALES con LLM (DeepSeek)")
    print("\n" + "🏥"*35)
    
    # Ejecutar demos
    demo_paciente_agenda_cita()
    
    print("\n\n")
    demo_paciente_pregunta_horarios()
    
    print("\n\n")  
    demo_doctor_consulta_agenda()
    
    print("\n\n")
    demo_paciente_reagenda()
    
    print("\n\n")
    demo_admin_reporte()
    
    print("\n\n" + "="*70)
    print("✅ DEMO COMPLETADA - Todas las conversaciones procesadas")
    print("="*70 + "\n")
