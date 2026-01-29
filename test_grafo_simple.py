"""
Script de prueba simple del grafo LangGraph
"""
from langchain_core.messages import HumanMessage
from src.graph_whatsapp import crear_grafo_whatsapp
from src.utils.session_manager import get_or_create_session
import pendulum

print("=" * 80)
print("PRUEBA SIMPLE DEL GRAFO LANGGRAPH")
print("=" * 80)

# Crear grafo
print("\n1. Creando grafo...")
grafo = crear_grafo_whatsapp()
print("   ✅ Grafo creado")

# Simular sesión
print("\n2. Creando sesión de prueba...")
phone_number = "+521234567890"
user_id, session_id, config = get_or_create_session(phone_number, None)
print(f"   ✅ Session ID: {session_id}")
print(f"   ✅ Thread ID: {config.get('configurable', {}).get('thread_id', 'N/A')}")

# Crear estado inicial
print("\n3. Creando estado inicial...")
mensaje_prueba = "Hola, necesito agendar una cita"
estado = {
    "messages": [HumanMessage(content=mensaje_prueba)],
    "user_id": user_id,
    "session_id": session_id,
    "cambio_de_tema": False,
    "sesion_expirada": False,
    "herramientas_seleccionadas": [],
    "resumen_actual": None,
    "timestamp": pendulum.now('America/Tijuana').to_iso8601_string()
}
print(f"   ✅ Mensaje: '{mensaje_prueba}'")

# Invocar grafo
print("\n4. Invocando grafo...")
print("   (Esto puede tardar unos segundos...)")
try:
    result = grafo.invoke(estado, config)
    print("   ✅ Grafo ejecutado correctamente")

    # Analizar resultado
    print("\n" + "=" * 80)
    print("RESULTADO DEL GRAFO")
    print("=" * 80)

    print(f"\n📊 Claves en resultado: {list(result.keys())}")

    if "messages" in result:
        print(f"\n💬 Total de mensajes: {len(result['messages'])}")

        for i, msg in enumerate(result["messages"]):
            msg_type = getattr(msg, "type", None) or (msg.get("type") if isinstance(msg, dict) else "unknown")
            msg_content = getattr(msg, "content", None) or (msg.get("content") if isinstance(msg, dict) else str(msg))

            print(f"\n  [{i+1}] Tipo: {msg_type}")
            print(f"      Contenido: {msg_content[:200]}...")

    # Verificar último mensaje
    if "messages" in result and len(result["messages"]) > 0:
        last_message = result["messages"][-1]
        last_type = getattr(last_message, "type", None) or (last_message.get("type") if isinstance(last_message, dict) else "unknown")

        print("\n" + "=" * 80)
        print("ÚLTIMO MENSAJE (RESPUESTA AL USUARIO)")
        print("=" * 80)
        print(f"\nTipo: {last_type}")

        if hasattr(last_message, "content"):
            response_text = last_message.content
        elif isinstance(last_message, dict) and "content" in last_message:
            response_text = last_message["content"]
        else:
            response_text = str(last_message)

        print(f"Contenido:\n{response_text}")

        # Verificar si es el mismo mensaje que enviamos
        if response_text == mensaje_prueba:
            print("\n⚠️  WARNING: La respuesta es idéntica al mensaje enviado!")
            print("   Esto indica que el grafo no está generando respuestas.")
        else:
            print("\n✅ El grafo generó una respuesta diferente al mensaje enviado")

    print("\n" + "=" * 80)

except Exception as e:
    print(f"\n❌ ERROR al invocar grafo: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("PRUEBA COMPLETADA")
print("=" * 80)
