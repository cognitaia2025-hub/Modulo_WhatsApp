"""
Script de prueba: Busqueda mejorada con normalizacion de acentos.

Verifica que la funcion search_calendar_events_tool encuentre
eventos con o sin acentos en la busqueda.
"""

import sys
import io
from pathlib import Path

# Configurar encoding UTF-8 para Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Agregar el directorio raiz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.tool import search_calendar_events_tool


def test_search(query: str, expected_count: int):
    """Ejecuta una busqueda y muestra los resultados."""
    print(f"\n{'='*60}")
    print(f"BUSQUEDA: '{query}'")
    print(f"Esperado: {expected_count} citas")
    print(f"{'='*60}")

    # Invocar la herramienta
    result = search_calendar_events_tool.invoke({
        "start_datetime": "2026-01-01T00:00:00",
        "end_datetime": "2026-03-01T23:59:59",
        "query": query,
        "max_results": 10
    })

    print(f"\nResultado: {len(result)} citas encontradas")

    for i, event in enumerate(result, 1):
        print(f"  [{i}] {event.get('summary')}")
        print(f"      {event.get('start')}")

    if len(result) == expected_count:
        print(f"\n  [OK] Encontro las {expected_count} citas esperadas")
    else:
        print(f"\n  [!!] Esperaba {expected_count}, encontro {len(result)}")

    return len(result) == expected_count


def main():
    print("\n" + "="*60)
    print("TEST DE BUSQUEDA MEJORADA (con normalizacion de acentos)")
    print("="*60)

    resultados = []

    # Test 1: Garcia SIN acento (debe encontrar 3 gracias a la normalizacion)
    resultados.append(("Garcia (sin acento)", test_search("Garcia", 3)))

    # Test 2: Garcia CON acento (debe encontrar 3)
    resultados.append(("Garcia (con acento)", test_search("García", 3)))

    # Test 3: Juan Garcia SIN acentos (debe encontrar 3)
    resultados.append(("Juan Garcia", test_search("Juan Garcia", 3)))

    # Test 4: Maria Lopez SIN acentos (debe encontrar 2)
    resultados.append(("Maria Lopez", test_search("Maria Lopez", 2)))

    # Test 5: Pedro Martinez SIN acentos (debe encontrar 1)
    resultados.append(("Pedro Martinez", test_search("Pedro Martinez", 1)))

    # Resumen
    print("\n" + "="*60)
    print("RESUMEN DE TESTS")
    print("="*60)

    passed = sum(1 for _, ok in resultados if ok)
    total = len(resultados)

    for name, ok in resultados:
        status = "[OK]" if ok else "[FAIL]"
        print(f"  {status} {name}")

    print(f"\nResultado: {passed}/{total} tests pasados")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
