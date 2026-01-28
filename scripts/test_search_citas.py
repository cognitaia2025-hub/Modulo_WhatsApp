"""
Script de Test: Busqueda de citas via simulacion WhatsApp

Simula mensajes de WhatsApp y prueba que search_calendar_events
encuentre todas las citas correctamente.

Formato de entrada (WhatsApp):
{
    chat_id: "521234567890@c.us",
    message: "Busca citas con Juan Garcia",
    sender_name: "Usuario Test",
    timestamp: "2026-01-26T10:00:00",
    thread_id: "521234567890"
}

Ejecutar desde la raiz del proyecto:
    python scripts/test_search_citas.py
"""

import sys
import io
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Configurar encoding UTF-8 para Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Agregar el directorio raiz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_core.messages import HumanMessage


def simular_mensaje_whatsapp(
    chat_id: str,
    message: str,
    sender_name: str = "Usuario Test",
    timestamp: str = None
) -> Dict[str, Any]:
    """
    Simula un mensaje entrante de WhatsApp.

    Args:
        chat_id: ID del chat (ej: "521234567890@c.us")
        message: Texto del mensaje
        sender_name: Nombre del remitente
        timestamp: Timestamp ISO (opcional)

    Returns:
        Dict con formato de mensaje WhatsApp
    """
    if timestamp is None:
        timestamp = datetime.now().isoformat()

    return {
        "chat_id": chat_id,
        "message": message,
        "sender_name": sender_name,
        "timestamp": timestamp,
        "thread_id": chat_id.replace("@c.us", "")
    }


def convertir_a_estado_grafo(mensaje_whatsapp: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convierte un mensaje de WhatsApp al formato de estado del grafo.

    Args:
        mensaje_whatsapp: Dict con formato WhatsApp

    Returns:
        Dict con formato de estado del grafo LangGraph
    """
    # Generar user_id desde thread_id (simplificado para test)
    user_id = f"user_{mensaje_whatsapp['thread_id'][-12:]}"
    session_id = f"session_test_{mensaje_whatsapp['thread_id'][-8:]}"

    return {
        "messages": [
            HumanMessage(content=mensaje_whatsapp["message"])
        ],
        "user_id": user_id,
        "session_id": session_id,
        "contexto_episodico": None,
        "herramientas_seleccionadas": [],
        "requiere_herramientas": False,
        "resumen_actual": None,
        "timestamp": mensaje_whatsapp["timestamp"],
        "sesion_expirada": False
    }


def ejecutar_test_busqueda(mensaje: str, descripcion: str) -> Dict[str, Any]:
    """
    Ejecuta un test de busqueda con el grafo completo.

    Args:
        mensaje: Texto del mensaje a enviar
        descripcion: Descripcion del test

    Returns:
        Resultado del grafo
    """
    print(f"\n{'='*70}")
    print(f"TEST: {descripcion}")
    print(f"{'='*70}")

    # 1. Simular mensaje WhatsApp
    msg_whatsapp = simular_mensaje_whatsapp(
        chat_id="5213334445555@c.us",
        message=mensaje,
        sender_name="Paciente Test"
    )

    print(f"\n[ENTRADA WhatsApp]")
    print(f"  chat_id: {msg_whatsapp['chat_id']}")
    print(f"  message: {msg_whatsapp['message']}")
    print(f"  sender_name: {msg_whatsapp['sender_name']}")
    print(f"  thread_id: {msg_whatsapp['thread_id']}")

    # 2. Convertir a estado del grafo
    estado = convertir_a_estado_grafo(msg_whatsapp)

    print(f"\n[ESTADO GRAFO]")
    print(f"  user_id: {estado['user_id']}")
    print(f"  session_id: {estado['session_id']}")
    print(f"  mensaje: {estado['messages'][0].content}")

    # 3. Crear y ejecutar grafo
    print(f"\n[EJECUTANDO GRAFO...]")
    print("-"*70)

    from src.graph_whatsapp import crear_grafo

    grafo = crear_grafo()
    resultado = grafo.invoke(estado)

    print("-"*70)

    # 4. Extraer respuesta
    respuesta = ""
    if resultado.get('messages'):
        ultimo = resultado['messages'][-1]
        if hasattr(ultimo, 'content'):
            respuesta = ultimo.content
        elif isinstance(ultimo, dict):
            respuesta = ultimo.get('content', '')

    print(f"\n[RESPUESTA DEL AGENTE]")
    print(f"  {respuesta[:500]}..." if len(respuesta) > 500 else f"  {respuesta}")

    # 5. Verificar herramientas usadas
    herramientas = resultado.get('herramientas_seleccionadas', [])
    print(f"\n[HERRAMIENTAS USADAS]")
    print(f"  {herramientas if herramientas else 'Ninguna (conversacional)'}")

    return resultado


def main():
    """Ejecuta todos los tests de busqueda."""

    print("\n" + "="*70)
    print("TEST DE BUSQUEDA DE CITAS - Simulacion WhatsApp")
    print("="*70)
    print("""
Este script simula mensajes de WhatsApp y verifica que el sistema
encuentre correctamente las citas insertadas previamente:

  - Juan Garcia: 3 citas (29 ene, 2 feb, 5 feb 2026)
  - Maria Lopez: 2 citas (30 ene, 3 feb 2026)
  - Pedro Martinez: 1 cita (4 feb 2026)
""")

    # ================================================================
    # TEST 1: Buscar citas de Juan Garcia (debe encontrar 3)
    # ================================================================
    resultado1 = ejecutar_test_busqueda(
        mensaje="Busca todas las citas con Juan Garcia",
        descripcion="Buscar Juan Garcia (esperado: 3 citas)"
    )

    # ================================================================
    # TEST 2: Buscar citas de Maria Lopez (debe encontrar 2)
    # ================================================================
    resultado2 = ejecutar_test_busqueda(
        mensaje="Busca las citas de Maria Lopez",
        descripcion="Buscar Maria Lopez (esperado: 2 citas)"
    )

    # ================================================================
    # TEST 3: Buscar citas de Pedro Martinez (debe encontrar 1)
    # ================================================================
    resultado3 = ejecutar_test_busqueda(
        mensaje="Tengo citas con Pedro Martinez?",
        descripcion="Buscar Pedro Martinez (esperado: 1 cita)"
    )

    # ================================================================
    # TEST 4: Buscar consultas (debe encontrar 3)
    # ================================================================
    resultado4 = ejecutar_test_busqueda(
        mensaje="Muestrame todas las consultas que tengo",
        descripcion="Buscar 'Consulta' (esperado: 3 citas)"
    )

    # ================================================================
    # TEST 5: Buscar citas de febrero (debe encontrar 5)
    # ================================================================
    resultado5 = ejecutar_test_busqueda(
        mensaje="Que citas tengo en febrero?",
        descripcion="Buscar febrero 2026 (esperado: 5 citas)"
    )

    # ================================================================
    # RESUMEN FINAL
    # ================================================================
    print("\n" + "="*70)
    print("RESUMEN DE TESTS")
    print("="*70)
    print("""
  TEST 1: Juan Garcia    -> Esperado: 3 citas
  TEST 2: Maria Lopez    -> Esperado: 2 citas
  TEST 3: Pedro Martinez -> Esperado: 1 cita
  TEST 4: Consultas      -> Esperado: 3 citas
  TEST 5: Febrero 2026   -> Esperado: 5 citas

Verifica los resultados arriba para confirmar que la busqueda
funciona correctamente.
""")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
