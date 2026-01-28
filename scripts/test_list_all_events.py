"""
Script de verificacion: Listar todos los eventos del calendario.

Este script lista todos los eventos en el rango de fechas donde
se crearon las citas de prueba, para verificar que existen.
"""

import sys
import io
from pathlib import Path

# Configurar encoding UTF-8 para Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Agregar el directorio raiz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utilities import ListGoogleCalendarEvents, SearchGoogleCalendarEvents, api_resource, CALENDAR_ID


def main():
    print("\n" + "="*70)
    print("VERIFICACION DE CITAS EN GOOGLE CALENDAR")
    print("="*70)
    print(f"\nCalendar ID: {CALENDAR_ID}")

    # 1. Listar TODOS los eventos del 29 enero al 10 febrero 2026
    print("\n" + "-"*70)
    print("1. LISTANDO TODOS LOS EVENTOS (29 ene - 10 feb 2026)")
    print("-"*70)

    tool_list = ListGoogleCalendarEvents(api_resource)
    events = tool_list._run(
        start_datetime="2026-01-29T00:00:00",
        end_datetime="2026-02-10T23:59:59",
        timezone="America/Tijuana"
    )

    print(f"\nEventos encontrados: {len(events)}")
    for i, event in enumerate(events, 1):
        print(f"\n  [{i}] {event.get('summary', 'Sin titulo')}")
        print(f"      Inicio: {event.get('start')}")
        print(f"      Fin: {event.get('end')}")
        print(f"      Ubicacion: {event.get('location', 'N/A')}")
        print(f"      Descripcion: {event.get('description', 'N/A')[:50]}...")

    # 2. Probar busqueda CON acento
    print("\n" + "-"*70)
    print("2. BUSCANDO 'Garcia' (con acento)")
    print("-"*70)

    tool_search = SearchGoogleCalendarEvents(api_resource)
    results = tool_search._run(
        start_datetime="2026-01-01T00:00:00",
        end_datetime="2026-03-01T23:59:59",
        query="García",  # Con acento
        max_results=10,
        timezone="America/Tijuana"
    )

    print(f"\nEventos encontrados: {len(results)}")
    for event in results:
        print(f"  - {event.get('summary')}: {event.get('start')}")

    # 3. Probar busqueda SIN acento
    print("\n" + "-"*70)
    print("3. BUSCANDO 'Garcia' (sin acento)")
    print("-"*70)

    results2 = tool_search._run(
        start_datetime="2026-01-01T00:00:00",
        end_datetime="2026-03-01T23:59:59",
        query="Garcia",  # Sin acento
        max_results=10,
        timezone="America/Tijuana"
    )

    print(f"\nEventos encontrados: {len(results2)}")
    for event in results2:
        print(f"  - {event.get('summary')}: {event.get('start')}")

    # 4. Probar busqueda por "Juan"
    print("\n" + "-"*70)
    print("4. BUSCANDO 'Juan' (nombre)")
    print("-"*70)

    results3 = tool_search._run(
        start_datetime="2026-01-01T00:00:00",
        end_datetime="2026-03-01T23:59:59",
        query="Juan",
        max_results=10,
        timezone="America/Tijuana"
    )

    print(f"\nEventos encontrados: {len(results3)}")
    for event in results3:
        print(f"  - {event.get('summary')}: {event.get('start')}")

    # 5. Probar busqueda por "Consulta"
    print("\n" + "-"*70)
    print("5. BUSCANDO 'Consulta' (tipo)")
    print("-"*70)

    results4 = tool_search._run(
        start_datetime="2026-01-01T00:00:00",
        end_datetime="2026-03-01T23:59:59",
        query="Consulta",
        max_results=10,
        timezone="America/Tijuana"
    )

    print(f"\nEventos encontrados: {len(results4)}")
    for event in results4:
        print(f"  - {event.get('summary')}: {event.get('start')}")

    print("\n" + "="*70)
    print("VERIFICACION COMPLETADA")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
