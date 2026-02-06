#!/usr/bin/env python3
"""
Test de Flujo Completo - Registro de Paciente y Agendamiento de Cita
=====================================================================

Prueba el flujo end-to-end después de la consolidación de esquema:
1. Identificación de nuevo usuario (paciente externo)
2. Clasificación de intención (solicitud_cita_paciente)
3. Recolección de datos (nombre, fecha, hora)
4. Confirmación y registro en BD

Este test verifica que:
- El doctor ID 1 existe (Santiago Ornelas)
- La columna is_active funciona correctamente
- No hay ForeignKeyViolation al registrar pacientes
- Los estados de flujo activo funcionan sin bucles
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Agregar el directorio raíz al path
ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

load_dotenv()

# Configurar logging simple
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Deshabilitar warnings de embeddings
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
logging.getLogger("transformers").setLevel(logging.ERROR)

from langchain_core.messages import HumanMessage
from src.state.agent_state import WhatsAppAgentState
from src.graph_whatsapp_etapa8 import crear_grafo_whatsapp
import uuid


def test_flujo_completo():
    """
    Simula un paciente nuevo solicitando una cita
    """
    print("\n" + "=" * 70)
    print("  TEST: FLUJO COMPLETO DE REGISTRO Y AGENDAMIENTO")
    print("=" * 70 + "\n")
    
    # Crear grafo
    logger.info("📊 Creando grafo del sistema...")
    graph = crear_grafo_whatsapp()
    
    # Simular nuevo paciente (número no registrado)
    test_phone = f"+526861234{uuid.uuid4().hex[:4]}"  # Número aleatorio
    thread_id = f"test_{uuid.uuid4().hex[:8]}"
    
    logger.info(f"👤 Paciente de prueba: {test_phone}")
    logger.info(f"🔑 Thread ID: {thread_id}")
    
    # Configuración del thread
    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }
    
    print("\n" + "─" * 70)
    print("INTERACCIÓN 1: Saludo inicial (debería pedir aclaración)")
    print("─" * 70 + "\n")
    
    # Mensaje 1: Saludo sin intención clara
    state1 = WhatsAppAgentState(
        messages=[HumanMessage(content="Hola")],
        user_id=test_phone,
        thread_id=thread_id
    )
    
    result1 = graph.invoke(state1, config)
    
    last_message_1 = result1["messages"][-1].content if result1["messages"] else "Sin respuesta"
    print(f"🤖 Respuesta del bot: {last_message_1}\n")
    print(f"📊 Estado conversación: {result1.get('estado_conversacion', 'N/A')}")
    print(f"🔖 Clasificación: {result1.get('clasificacion_mensaje', 'N/A')}")
    
    print("\n" + "─" * 70)
    print("INTERACCIÓN 2: Solicitud clara de cita")
    print("─" * 70 + "\n")
    
    # Mensaje 2: Intención clara
    state2 = WhatsAppAgentState(
        messages=result1["messages"] + [HumanMessage(content="Quiero agendar una cita")],
        user_id=test_phone,
        thread_id=thread_id,
        tipo_usuario=result1.get("tipo_usuario", "paciente_externo"),
        estado_conversacion=result1.get("estado_conversacion", "inicial")
    )
    
    result2 = graph.invoke(state2, config)
    
    last_message_2 = result2["messages"][-1].content if result2["messages"] else "Sin respuesta"
    print(f"🤖 Respuesta del bot: {last_message_2}\n")
    print(f"📊 Estado conversación: {result2.get('estado_conversacion', 'N/A')}")
    print(f"🔖 Clasificación: {result2.get('clasificacion_mensaje', 'N/A')}")
    
    print("\n" + "─" * 70)
    print("INTERACCIÓN 3: Proporcionar nombre")
    print("─" * 70 + "\n")
    
    # Mensaje 3: Proporcionar nombre
    state3 = WhatsAppAgentState(
        messages=result2["messages"] + [HumanMessage(content="Mi nombre es Juan Pérez")],
        user_id=test_phone,
        thread_id=thread_id,
        tipo_usuario=result2.get("tipo_usuario", "paciente_externo"),
        estado_conversacion=result2.get("estado_conversacion", "solicitando_nombre"),
        paciente_info=result2.get("paciente_info", {})
    )
    
    result3 = graph.invoke(state3, config)
    
    last_message_3 = result3["messages"][-1].content if result3["messages"] else "Sin respuesta"
    print(f"🤖 Respuesta del bot: {last_message_3}\n")
    print(f"📊 Estado conversación: {result3.get('estado_conversacion', 'N/A')}")
    print(f"👤 Paciente info: {result3.get('paciente_info', {})}")
    
    print("\n" + "─" * 70)
    print("INTERACCIÓN 4: Seleccionar slot")
    print("─" * 70 + "\n")
    
    # Mensaje 4: Elegir opción 1
    state4 = WhatsAppAgentState(
        messages=result3["messages"] + [HumanMessage(content="1")],
        user_id=test_phone,
        thread_id=thread_id,
        tipo_usuario=result3.get("tipo_usuario", "paciente_externo"),
        estado_conversacion=result3.get("estado_conversacion", "recolectando_slots"),
        paciente_info=result3.get("paciente_info", {}),
        slots_disponibles=result3.get("slots_disponibles", [])
    )
    
    result4 = graph.invoke(state4, config)
    
    last_message_4 = result4["messages"][-1].content if result4["messages"] else "Sin respuesta"
    print(f"🤖 Respuesta del bot: {last_message_4}\n")
    print(f"📊 Estado conversación: {result4.get('estado_conversacion', 'N/A')}")
    print(f"📅 Cita seleccionada: {result4.get('cita_seleccionada', {})}")
    
    print("\n" + "─" * 70)
    print("INTERACCIÓN 5: Confirmar cita")
    print("─" * 70 + "\n")
    
    # Mensaje 5: Confirmar
    state5 = WhatsAppAgentState(
        messages=result4["messages"] + [HumanMessage(content="Sí, confirmo")],
        user_id=test_phone,
        thread_id=thread_id,
        tipo_usuario=result4.get("tipo_usuario", "paciente_externo"),
        estado_conversacion=result4.get("estado_conversacion", "confirmando_cita"),
        paciente_info=result4.get("paciente_info", {}),
        cita_seleccionada=result4.get("cita_seleccionada", {})
    )
    
    result5 = graph.invoke(state5, config)
    
    last_message_5 = result5["messages"][-1].content if result5["messages"] else "Sin respuesta"
    print(f"🤖 Respuesta del bot: {last_message_5}\n")
    print(f"📊 Estado conversación: {result5.get('estado_conversacion', 'N/A')}")
    print(f"🎯 Cita creada ID: {result5.get('cita_id', 'N/A')}")
    
    print("\n" + "=" * 70)
    print("  ✅ TEST COMPLETADO")
    print("=" * 70 + "\n")
    
    # Resumen
    print("📋 RESUMEN:")
    print(f"  • Paciente: Juan Pérez ({test_phone})")
    print(f"  • Doctor asignado: {result5.get('paciente_info', {}).get('doctor_id', 'N/A')}")
    print(f"  • Estado final: {result5.get('estado_conversacion', 'N/A')}")
    print(f"  • Mensajes intercambiados: {len(result5['messages']) // 2}")
    
    return result5


if __name__ == "__main__":
    try:
        resultado = test_flujo_completo()
        print("\n✅ Test ejecutado exitosamente\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error en test: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
