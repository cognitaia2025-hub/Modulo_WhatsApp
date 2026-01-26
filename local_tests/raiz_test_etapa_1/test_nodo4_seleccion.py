"""
Test del Nodo 4: Selección Inteligente de Herramientas

Prueba el sistema de selección dinámica con fallback (sin PostgreSQL)
"""

from src.nodes.seleccion_herramientas_node import (
    nodo_seleccion_herramientas,
    extraer_ultimo_mensaje_usuario,
    parsear_respuesta_llm,
    construir_prompt_seleccion
)
from datetime import datetime
import time


def test_extraccion_mensaje():
    """Test 1: Extracción de último mensaje del usuario"""
    print("\n" + "="*80)
    print("🧪 TEST 1: Extracción de Último Mensaje")
    print("="*80 + "\n")
    
    state = {
        'messages': [
            {'role': 'user', 'content': 'Hola'},
            {'role': 'assistant', 'content': '¡Hola! ¿Cómo puedo ayudarte?'},
            {'role': 'user', 'content': '¿Qué reuniones tengo hoy?'}
        ]
    }
    
    mensaje = extraer_ultimo_mensaje_usuario(state)
    
    print(f"   Mensajes en historial: {len(state['messages'])}")
    print(f"   ✓ Último mensaje extraído: '{mensaje}'")
    
    assert mensaje == '¿Qué reuniones tengo hoy?', "❌ Error: mensaje incorrecto"
    print("\n✅ Extracción correcta")


def test_parseo_respuesta():
    """Test 2: Parseo de respuestas del LLM"""
    print("\n" + "="*80)
    print("🧪 TEST 2: Parseo de Respuestas LLM")
    print("="*80 + "\n")
    
    casos = [
        ("list_calendar_events", ['list_calendar_events']),
        ("list_calendar_events, create_calendar_event", ['list_calendar_events', 'create_calendar_event']),
        ("NONE", []),
        ("", []),
        ("  UPDATE_CALENDAR_EVENT  ", ['update_calendar_event']),
    ]
    
    for entrada, esperado in casos:
        resultado = parsear_respuesta_llm(entrada)
        exito = resultado == esperado
        emoji = "✅" if exito else "❌"
        
        print(f"   {emoji} '{entrada}' → {resultado}")
        
        if not exito:
            print(f"      Esperado: {esperado}")
            assert False, f"❌ Parseo incorrecto para '{entrada}'"
    
    print("\n✅ Todos los casos parseados correctamente")


def test_seleccion_listar():
    """Test 3: Selección para listar eventos"""
    print("\n" + "="*80)
    print("🧪 TEST 3: Selección - Listar Eventos")
    print("="*80 + "\n")
    
    state = {
        'messages': [
            {'role': 'user', 'content': '¿Qué reuniones tengo hoy?'}
        ],
        'user_id': 'test_user',
        'session_id': 'session_001',
        'contexto_episodico': None,
        'herramientas_seleccionadas': [],
        'cambio_de_tema': False,
        'resumen_actual': None,
        'timestamp': datetime.now().isoformat(),
        'sesion_expirada': False
    }
    
    print("💬 Usuario pregunta: '¿Qué reuniones tengo hoy?'")
    print("🤖 Llamando LLM para selección...")
    
    start = time.time()
    resultado = nodo_seleccion_herramientas(state)
    elapsed = time.time() - start
    
    herramientas = resultado['herramientas_seleccionadas']
    
    print(f"\n   ⏱️  Tiempo de selección: {elapsed:.2f}s")
    print(f"   ✅ Herramientas seleccionadas: {herramientas}")
    
    assert 'list_calendar_events' in herramientas, "❌ Debería seleccionar list_calendar_events"
    
    print("\n✅ Selección correcta para listar eventos")


def test_seleccion_crear():
    """Test 4: Selección para crear eventos"""
    print("\n" + "="*80)
    print("🧪 TEST 4: Selección - Crear Evento")
    print("="*80 + "\n")
    
    state = {
        'messages': [
            {'role': 'user', 'content': 'Quiero agendar una reunión con el equipo para mañana a las 3pm'}
        ],
        'user_id': 'test_user',
        'session_id': 'session_002',
        'contexto_episodico': None,
        'herramientas_seleccionadas': [],
        'cambio_de_tema': False,
        'resumen_actual': None,
        'timestamp': datetime.now().isoformat(),
        'sesion_expirada': False
    }
    
    print("💬 Usuario dice: 'Quiero agendar una reunión...'")
    print("🤖 Llamando LLM para selección...")
    
    start = time.time()
    resultado = nodo_seleccion_herramientas(state)
    elapsed = time.time() - start
    
    herramientas = resultado['herramientas_seleccionadas']
    
    print(f"\n   ⏱️  Tiempo de selección: {elapsed:.2f}s")
    print(f"   ✅ Herramientas seleccionadas: {herramientas}")
    
    assert 'create_calendar_event' in herramientas, "❌ Debería seleccionar create_calendar_event"
    
    print("\n✅ Selección correcta para crear evento")


if __name__ == "__main__":
    print("\n" + "🤖 "+"="*76 + "🤖")
    print("🤖 PRUEBAS DEL NODO 4 - Selección Inteligente de Herramientas")
    print("🤖 "+"="*76 + "🤖")
    
    print("\n⚠️  NOTA: Modo FALLBACK (sin PostgreSQL, herramientas hardcoded)\n")
    
    try:
        test_extraccion_mensaje()
        test_parseo_respuesta()
        test_seleccion_listar()
        test_seleccion_crear()
        
        print("\n" + "="*80)
        print("🎉 TODAS LAS PRUEBAS COMPLETADAS")
        print("="*80)
        print("\n📋 RESUMEN:")
        print("   ✅ Extracción de mensajes")
        print("   ✅ Parseo de respuestas LLM")
        print("   ✅ Selección inteligente funcionando")
        print("   ✅ Fallback robusto")
        
        print("\n✅ El agente ahora PIENSA qué herramientas necesita\n")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
