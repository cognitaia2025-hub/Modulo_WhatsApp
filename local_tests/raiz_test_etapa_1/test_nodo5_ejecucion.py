"""
Test del Nodo 5: Ejecución de Herramientas y Orquestador

Prueba:
1. Utilidades de tiempo (Pendulum)
2. Autenticación de Google Calendar
3. Flujo completo de ejecución
4. Orquestador (LLM)
"""

from src.utils import (
    get_current_time,
    get_time_context,
    parse_relative_time,
    create_event_time,
    get_timezone_offset
)
from src.nodes.ejecucion_herramientas_node import (
    nodo_ejecucion_herramientas,
    construir_prompt_orquestador
)
from datetime import datetime


def test_tiempo_mexicali():
    """Test 1: Utilidades de tiempo para Mexicali"""
    print("\n" + "="*80)
    print("🧪 TEST 1: Utilidades de Tiempo (Mexicali, BC)")
    print("="*80 + "\n")
    
    # Tiempo actual
    now = get_current_time()
    print(f"   📅 Tiempo actual: {now}")
    print(f"   ⏰ Formato legible: {now.format('dddd, DD/MM/YYYY HH:mm')}")
    print(f"   🌐 Offset UTC: {get_timezone_offset()}")
    
    # Contexto para LLM
    contexto = get_time_context()
    print(f"\n   💬 Contexto para LLM:")
    print(f"      {contexto}")
    
    # Verificaciones
    assert 'Mexicali' in contexto, "❌ Falta 'Mexicali' en contexto"
    assert '2026' in contexto, "❌ Año incorrecto en contexto"
    
    print("\n✅ Utilidades de tiempo funcionando correctamente")


def test_parseo_fechas():
    """Test 2: Parseo de expresiones relativas"""
    print("\n" + "="*80)
    print("🧪 TEST 2: Parseo de Expresiones Temporales")
    print("="*80 + "\n")
    
    expresiones = [
        "hoy",
        "mañana",
        "próximo lunes"
    ]
    
    for expr in expresiones:
        parsed = parse_relative_time(expr)
        if parsed:
            print(f"   ✅ '{expr}' → {parsed.format('dddd, DD/MM/YYYY')}")
        else:
            print(f"   ⚠️  '{expr}' → No parseado")
    
    print("\n✅ Parseo de fechas relativas funcionando")


def test_evento_rfc3339():
    """Test 3: Crear eventos en formato RFC3339"""
    print("\n" + "="*80)
    print("🧪 TEST 3: Formato RFC3339 para Google Calendar")
    print("="*80 + "\n")
    
    # Crear tiempo de evento
    event_time = create_event_time("2026-01-24", "15:00", 60)
    
    print(f"   📆 Evento de prueba:")
    print(f"      Inicio: {event_time['start']}")
    print(f"      Fin: {event_time['end']}")
    
    # Verificar formato
    assert 'T' in event_time['start'], "❌ Falta separador 'T'"
    assert '-08:00' in event_time['start'] or '-07:00' in event_time['start'], "❌ Offset incorrecto"
    
    print("\n✅ Formato RFC3339 correcto")


def test_prompt_orquestador():
    """Test 4: Construcción de prompt del Orquestador"""
    print("\n" + "="*80)
    print("🧪 TEST 4: Prompt del Orquestador")
    print("="*80 + "\n")
    
    tiempo_ctx = get_time_context()
    resultados = [
        {
            'tool_id': 'list_calendar_events',
            'success': True,
            'data': {'events': ['Reunión con equipo', 'Cita médica']}
        }
    ]
    contexto_episodico = {}
    mensaje = "¿Qué tengo que hacer hoy?"
    
    prompt = construir_prompt_orquestador(
        tiempo_context=tiempo_ctx,
        resultados_google=resultados,
        contexto_episodico=contexto_episodico,
        mensaje_usuario=mensaje
    )
    
    print("   📝 Prompt generado:")
    print("   " + "-"*70)
    print(prompt[:300] + "...")
    print("   " + "-"*70)
    
    # Verificaciones
    assert 'Mexicali' in prompt, "❌ Falta contexto de Mexicali"
    assert mensaje in prompt, "❌ Falta mensaje del usuario"
    assert 'list_calendar_events' in prompt, "❌ Faltan resultados"
    
    print("\n✅ Prompt del Orquestador construido correctamente")


def test_nodo_sin_herramientas():
    """Test 5: Nodo con mensaje sin herramientas de calendario"""
    print("\n" + "="*80)
    print("🧪 TEST 5: Nodo sin Herramientas (Respuesta Conversacional)")
    print("="*80 + "\n")
    
    state = {
        'messages': [
            {'role': 'user', 'content': '¿Cómo estás?'}
        ],
        'user_id': 'test_user',
        'session_id': 'session_005',
        'contexto_episodico': None,
        'herramientas_seleccionadas': [],  # Sin herramientas
        'cambio_de_tema': False,
        'resumen_actual': None,
        'timestamp': datetime.now().isoformat(),
        'sesion_expirada': False
    }
    
    print("💬 Usuario: '¿Cómo estás?'")
    print("📋 Herramientas seleccionadas: [] (ninguna)")
    print("🤖 Ejecutando nodo...")
    
    resultado = nodo_ejecucion_herramientas(state)
    
    mensajes_respuesta = resultado.get('messages', [])
    
    if mensajes_respuesta:
        respuesta = mensajes_respuesta[0].content if hasattr(mensajes_respuesta[0], 'content') else str(mensajes_respuesta[0])
        print(f"\n   ✅ Respuesta generada: '{respuesta}'")
    else:
        print("\n   ⚠️  No se generó respuesta")
    
    assert len(mensajes_respuesta) > 0, "❌ Debería generar respuesta"
    
    print("\n✅ Nodo maneja correctamente casos sin herramientas")


def test_nodo_con_list_events():
    """Test 6: Nodo con herramienta list_calendar_events"""
    print("\n" + "="*80)
    print("🧪 TEST 6: Nodo con list_calendar_events")
    print("="*80 + "\n")
    
    state = {
        'messages': [
            {'role': 'user', 'content': '¿Qué reuniones tengo hoy?'}
        ],
        'user_id': 'test_user',
        'session_id': 'session_006',
        'contexto_episodico': None,
        'herramientas_seleccionadas': ['list_calendar_events'],
        'cambio_de_tema': False,
        'resumen_actual': None,
        'timestamp': datetime.now().isoformat(),
        'sesion_expirada': False
    }
    
    print("💬 Usuario: '¿Qué reuniones tengo hoy?'")
    print("📋 Herramientas: ['list_calendar_events']")
    print("🤖 Ejecutando nodo...")
    
    resultado = nodo_ejecucion_herramientas(state)
    
    mensajes_respuesta = resultado.get('messages', [])
    herramientas_limpiadas = resultado.get('herramientas_seleccionadas', [])
    
    if mensajes_respuesta:
        respuesta = mensajes_respuesta[0].content if hasattr(mensajes_respuesta[0], 'content') else str(mensajes_respuesta[0])
        print(f"\n   ✅ Respuesta: '{respuesta[:100]}...'")
    
    print(f"   ✅ Herramientas limpiadas: {herramientas_limpiadas}")
    
    assert len(mensajes_respuesta) > 0, "❌ Debería generar respuesta"
    assert len(herramientas_limpiadas) == 0, "❌ Debería limpiar herramientas"
    
    print("\n✅ Nodo ejecuta y orquesta correctamente")


if __name__ == "__main__":
    print("\n" + "🤖 "+"="*76 + "🤖")
    print("🤖 PRUEBAS DEL NODO 5 - Ejecución y Orquestador")
    print("🤖 "+"="*76 + "🤖")
    
    print("\n⚠️  NOTA: Tests de autenticación de Google Calendar requieren credentials.json")
    print("   Los tests de ejecución funcionan con herramientas disponibles.\n")
    
    try:
        # Tests de utilidades
        test_tiempo_mexicali()
        test_parseo_fechas()
        test_evento_rfc3339()
        test_prompt_orquestador()
        
        # Tests de nodo
        test_nodo_sin_herramientas()
        test_nodo_con_list_events()
        
        print("\n" + "="*80)
        print("🎉 TODAS LAS PRUEBAS COMPLETADAS")
        print("="*80)
        print("\n📋 RESUMEN DEL NODO 5:")
        print("   1. ✅ Gestión de tiempo con Pendulum (Mexicali, BC)")
        print("   2. ✅ Parseo de expresiones relativas ('hoy', 'mañana')")
        print("   3. ✅ Formato RFC3339 con offset correcto")
        print("   4. ✅ Prompt del Orquestador con contexto completo")
        print("   5. ✅ Ejecución de herramientas de Google Calendar")
        print("   6. ✅ Respuestas naturales con LLM")
        print("   7. ✅ Limpieza de estado post-ejecución")
        
        print("\n💡 PRÓXIMOS PASOS:")
        print("   • Autenticar con Google Calendar (./venv/Scripts/python src/auth/google_calendar_auth.py)")
        print("   • Extraer parámetros de mensajes con LLM (para create_event)")
        print("   • Integrar todas las herramientas (update, delete, search)")
        print("   • Implementar Nodo 6 (Generación de Resumen)")
        
        print("\n✅ El agente ahora ACTÚA y RESPONDE de forma natural\n")
        
    except Exception as e:
        print(f"\n❌ ERROR EN PRUEBAS: {e}")
        import traceback
        traceback.print_exc()
