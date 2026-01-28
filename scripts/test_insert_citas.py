"""
Script de prueba: Insertar citas de prueba en Google Calendar

Objetivo: Verificar que search_calendar_events encuentra TODAS las citas
de un mismo paciente cuando hay múltiples citas en diferentes fechas.

Ejecutar desde la raíz del proyecto:
    python scripts/test_insert_citas.py

Después de ejecutar, verificar en Google Calendar que las citas se crearon.
"""

import sys
import io
from pathlib import Path

# Configurar encoding UTF-8 para Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pendulum
from src.utilities import CreateGoogleCalendarEvent, api_resource, CALENDAR_ID

# Configuración de timezone
TIMEZONE = "America/Tijuana"


def crear_citas_prueba():
    """Crea citas de prueba para testing de búsqueda."""

    print("\n" + "="*70)
    print("🧪 SCRIPT DE PRUEBA: Insertar citas para test de búsqueda")
    print("="*70)
    print(f"\n📅 Calendar ID: {CALENDAR_ID[:30]}...")
    print(f"🌍 Timezone: {TIMEZONE}")

    # Definir citas de prueba
    # IMPORTANTE: Múltiples citas del MISMO paciente para probar búsqueda
    citas = [
        # ========== JUAN GARCÍA - 3 citas en diferentes fechas ==========
        {
            "summary": "Consulta - Juan García",
            "description": "Primera consulta - Evaluación inicial de uña encarnada",
            "location": "Consultorio 1",
            "fecha": "2026-01-29",
            "hora_inicio": "10:00",
            "hora_fin": "10:30",
        },
        {
            "summary": "Tratamiento - Juan García",
            "description": "Segunda cita - Tratamiento de uña encarnada",
            "location": "Consultorio 1",
            "fecha": "2026-02-02",
            "hora_inicio": "11:00",
            "hora_fin": "11:45",
        },
        {
            "summary": "Revisión - Juan García",
            "description": "Tercera cita - Revisión post-tratamiento",
            "location": "Consultorio 1",
            "fecha": "2026-02-05",
            "hora_inicio": "09:30",
            "hora_fin": "10:00",
        },

        # ========== MARÍA LÓPEZ - 2 citas ==========
        {
            "summary": "Consulta - María López",
            "description": "Evaluación de juanete",
            "location": "Consultorio 2",
            "fecha": "2026-01-30",
            "hora_inicio": "14:00",
            "hora_fin": "14:30",
        },
        {
            "summary": "Tratamiento - María López",
            "description": "Tratamiento ortopédico",
            "location": "Consultorio 2",
            "fecha": "2026-02-03",
            "hora_inicio": "15:00",
            "hora_fin": "16:00",
        },

        # ========== PEDRO MARTÍNEZ - 1 cita ==========
        {
            "summary": "Consulta - Pedro Martínez",
            "description": "Evaluación de pie diabético",
            "location": "Consultorio 1",
            "fecha": "2026-02-04",
            "hora_inicio": "16:30",
            "hora_fin": "17:00",
        },
    ]

    print("\n" + "-"*70)
    print("📝 CITAS A CREAR (para test de búsqueda):")
    print("-"*70)

    # Agrupar por paciente para mostrar
    pacientes = {}
    for cita in citas:
        nombre = cita['summary'].split(' - ')[1]
        if nombre not in pacientes:
            pacientes[nombre] = []
        pacientes[nombre].append(cita)

    for nombre, citas_paciente in pacientes.items():
        print(f"\n  👤 {nombre} ({len(citas_paciente)} citas)")
        for cita in citas_paciente:
            print(f"     📅 {cita['fecha']} | {cita['hora_inicio']}-{cita['hora_fin']} | {cita['summary'].split(' - ')[0]}")

    print("\n" + "-"*70)
    print("🚀 INSERTANDO EN GOOGLE CALENDAR...")
    print("-"*70)

    # Crear instancia de la herramienta
    tool = CreateGoogleCalendarEvent(api_resource)

    resultados = []
    total = len(citas)

    for i, cita in enumerate(citas, 1):
        try:
            # Construir datetime completo
            start_dt = f"{cita['fecha']}T{cita['hora_inicio']}:00"
            end_dt = f"{cita['fecha']}T{cita['hora_fin']}:00"

            print(f"\n  [{i}/{total}] {cita['summary']}")
            print(f"           📅 {cita['fecha']} {cita['hora_inicio']}-{cita['hora_fin']}")

            resultado = tool._run(
                start_datetime=start_dt,
                end_datetime=end_dt,
                summary=cita['summary'],
                location=cita['location'],
                description=cita['description'],
                timezone=TIMEZONE
            )

            print(f"           ✅ Creada exitosamente")
            resultados.append({"success": True, "cita": cita['summary']})

        except Exception as e:
            print(f"           ❌ Error: {e}")
            resultados.append({"success": False, "cita": cita['summary'], "error": str(e)})

    # Resumen final
    print("\n" + "="*70)
    print("📊 RESUMEN DE RESULTADOS")
    print("="*70)

    exitosos = sum(1 for r in resultados if r['success'])
    fallidos = len(resultados) - exitosos

    print(f"\n  ✅ Exitosos: {exitosos}/{total}")
    print(f"  ❌ Fallidos: {fallidos}/{total}")

    if exitosos > 0:
        print("\n" + "-"*70)
        print("🧪 TESTS DE BÚSQUEDA SUGERIDOS:")
        print("-"*70)
        print("""
  Después de verificar en Google Calendar, prueba buscar:

  1. "Busca citas con Juan García"
     → Debe encontrar 3 citas (29 ene, 2 feb, 5 feb)

  2. "Busca citas con María López"
     → Debe encontrar 2 citas (30 ene, 3 feb)

  3. "Busca citas con Pedro Martínez"
     → Debe encontrar 1 cita (4 feb)

  4. "Busca citas de febrero"
     → Debe encontrar 5 citas (todas las de febrero)

  5. "Busca consultas"
     → Debe encontrar 3 citas (las que empiezan con "Consulta")
""")

    print("="*70 + "\n")

    return resultados


if __name__ == "__main__":
    crear_citas_prueba()
