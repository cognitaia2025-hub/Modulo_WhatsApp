"""
Test simple: Un solo mensaje a traves del grafo completo.

Verifica que el flujo LLM -> herramienta -> respuesta funciona.
"""

import sys
import io
from pathlib import Path
from datetime import datetime

# Configurar encoding UTF-8 para Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Agregar el directorio raiz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_core.messages import HumanMessage


def main():
    print("\n" + "="*70)
    print("TEST: Busqueda via grafo completo (con LLM)")
    print("="*70)

    # Mensaje de prueba
    mensaje = "Busca todas las citas con Juan Garcia"

    print(f"\nMensaje: '{mensaje}'")
    print(f"Esperado: 3 citas de Juan Garcia")

    # Crear estado
    estado = {
        "messages": [HumanMessage(content=mensaje)],
        "user_id": "test_user_single",
        "session_id": "session_single_test",
        "contexto_episodico": None,
        "herramientas_seleccionadas": [],
        "requiere_herramientas": False,
        "resumen_actual": None,
        "timestamp": datetime.now().isoformat(),
        "sesion_expirada": False
    }

    print("\n" + "-"*70)
    print("Ejecutando grafo...")
    print("-"*70)

    # Crear y ejecutar grafo
    from src.graph_whatsapp import crear_grafo

    grafo = crear_grafo()

    # Configuracion para el checkpointer (PostgreSQL)
    config = {
        "configurable": {
            "thread_id": estado["session_id"]
        }
    }

    resultado = grafo.invoke(estado, config)

    print("-"*70)

    # Extraer respuesta
    respuesta = ""
    if resultado.get('messages'):
        ultimo = resultado['messages'][-1]
        if hasattr(ultimo, 'content'):
            respuesta = ultimo.content
        elif isinstance(ultimo, dict):
            respuesta = ultimo.get('content', '')

    print(f"\n[RESPUESTA DEL AGENTE]")
    print(f"{respuesta}")

    # Verificar herramientas usadas
    herramientas = resultado.get('herramientas_seleccionadas', [])
    print(f"\n[HERRAMIENTAS SELECCIONADAS]")
    print(f"{herramientas}")

    print("\n" + "="*70)
    print("VERIFICACION MANUAL:")
    print("="*70)
    print("""
La respuesta deberia mencionar las 3 citas de Juan Garcia:
  1. Consulta - 29 enero 2026, 10:00
  2. Tratamiento - 2 febrero 2026, 11:00
  3. Revision - 5 febrero 2026, 09:30

Si la respuesta dice "no se encontraron citas", el flujo
LLM -> herramienta tiene un problema.
""")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
