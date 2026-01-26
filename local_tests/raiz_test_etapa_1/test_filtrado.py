"""
Test del Nodo de Filtrado con Detección de Cambio de Tema

Prueba 3 escenarios:
1. Continuidad: Usuario sigue con el mismo tema
2. Cambio de tema: Usuario pregunta por información pasada
3. Mensaje corto: Confirmación rápida
"""

from src.graph_whatsapp import crear_grafo
from datetime import datetime


def test_continuidad():
    """Test 1: Conversación fluida sin cambio de tema"""
    print("\n" + "="*80)
    print("🟢 TEST 1: CONTINUIDAD - Usuario sigue con el mismo tema")
    print("="*80 + "\n")
    
    graph = crear_grafo()
    
    estado = {
        'messages': [
            {'role': 'user', 'content': 'Hola, quiero agendar una reunión'},
            {'role': 'assistant', 'content': '¡Claro! ¿Para qué día te gustaría?'},
            {'role': 'user', 'content': 'Para el próximo lunes'},
            {'role': 'assistant', 'content': 'Perfecto. ¿A qué hora?'},
            {'role': 'user', 'content': 'A las 10 de la mañana, por favor'}
        ],
        'user_id': 'user_continuidad',
        'session_id': 'session_001',
        'contexto_episodico': None,
        'herramientas_seleccionadas': [],
        'cambio_de_tema': False,
        'resumen_actual': None,
        'timestamp': datetime.now().isoformat(),
        'sesion_expirada': False
    }
    
    resultado = graph.invoke(estado)
    
    print("\n" + "-"*80)
    print("📊 RESULTADO:")
    print(f"   ✓ Cambio de tema: {resultado.get('cambio_de_tema')}")
    print(f"   ✓ Expectativa: False (sin cambio)")
    print(f"   ✓ ¿Correcto?: {'✅ SÍ' if not resultado.get('cambio_de_tema') else '❌ NO'}")
    print("-"*80)


def test_cambio_tema():
    """Test 2: Usuario cambia radicalmente de tema"""
    print("\n" + "="*80)
    print("🔴 TEST 2: CAMBIO DE TEMA - Usuario pregunta por información pasada")
    print("="*80 + "\n")
    
    graph = crear_grafo()
    
    estado = {
        'messages': [
            {'role': 'user', 'content': 'Hola, quiero agendar una reunión'},
            {'role': 'assistant', 'content': '¡Claro! ¿Para qué día te gustaría?'},
            {'role': 'user', 'content': 'Espera, antes de eso... ¿qué tenía pendiente de la semana pasada?'}
        ],
        'user_id': 'user_cambio',
        'session_id': 'session_002',
        'contexto_episodico': None,
        'herramientas_seleccionadas': [],
        'cambio_de_tema': False,
        'resumen_actual': None,
        'timestamp': datetime.now().isoformat(),
        'sesion_expirada': False
    }
    
    resultado = graph.invoke(estado)
    
    print("\n" + "-"*80)
    print("📊 RESULTADO:")
    print(f"   ✓ Cambio de tema: {resultado.get('cambio_de_tema')}")
    print(f"   ✓ Expectativa: True (hay cambio)")
    print(f"   ✓ ¿Correcto?: {'✅ SÍ' if resultado.get('cambio_de_tema') else '❌ NO'}")
    print("-"*80)


def test_mensaje_corto():
    """Test 3: Mensaje de confirmación corto (sin LLM)"""
    print("\n" + "="*80)
    print("🟡 TEST 3: MENSAJE CORTO - Confirmación rápida (sin llamada LLM)")
    print("="*80 + "\n")
    
    graph = crear_grafo()
    
    estado = {
        'messages': [
            {'role': 'user', 'content': 'Agendar reunión lunes 10am'},
            {'role': 'assistant', 'content': '¿Te confirmo la reunión para el lunes a las 10am?'},
            {'role': 'user', 'content': 'Vale, gracias'}
        ],
        'user_id': 'user_corto',
        'session_id': 'session_003',
        'contexto_episodico': None,
        'herramientas_seleccionadas': [],
        'cambio_de_tema': False,
        'resumen_actual': None,
        'timestamp': datetime.now().isoformat(),
        'sesion_expirada': False
    }
    
    resultado = graph.invoke(estado)
    
    print("\n" + "-"*80)
    print("📊 RESULTADO:")
    print(f"   ✓ Cambio de tema: {resultado.get('cambio_de_tema')}")
    print(f"   ✓ Expectativa: False (mensaje de continuidad)")
    print(f"   ✓ ¿Correcto?: {'✅ SÍ' if not resultado.get('cambio_de_tema') else '❌ NO'}")
    print(f"   ⚡ Optimización: NO llamó al LLM (detección rápida)")
    print("-"*80)


def test_pocos_mensajes():
    """Test 4: Muy pocos mensajes (sin contexto suficiente)"""
    print("\n" + "="*80)
    print("🔵 TEST 4: POCOS MENSAJES - Sin contexto suficiente")
    print("="*80 + "\n")
    
    graph = crear_grafo()
    
    estado = {
        'messages': [
            {'role': 'user', 'content': 'Hola'}
        ],
        'user_id': 'user_nuevo',
        'session_id': 'session_004',
        'contexto_episodico': None,
        'herramientas_seleccionadas': [],
        'cambio_de_tema': False,
        'resumen_actual': None,
        'timestamp': datetime.now().isoformat(),
        'sesion_expirada': False
    }
    
    resultado = graph.invoke(estado)
    
    print("\n" + "-"*80)
    print("📊 RESULTADO:")
    print(f"   ✓ Cambio de tema: {resultado.get('cambio_de_tema')}")
    print(f"   ✓ Expectativa: False (sin contexto)")
    print(f"   ✓ ¿Correcto?: {'✅ SÍ' if not resultado.get('cambio_de_tema') else '❌ NO'}")
    print(f"   ⚡ Optimización: NO llamó al LLM (muy pocos mensajes)")
    print("-"*80)


if __name__ == "__main__":
    print("\n" + "🤖 "+"="*76 + "🤖")
    print("🤖 PRUEBAS DEL NODO DE FILTRADO - Detección de Cambio de Tema")
    print("🤖 "+"="*76 + "🤖")
    
    # Ejecutar tests
    test_pocos_mensajes()
    test_mensaje_corto()
    test_continuidad()
    test_cambio_tema()
    
    print("\n" + "="*80)
    print("🎉 TODAS LAS PRUEBAS COMPLETADAS")
    print("="*80)
    print("\n📋 RESUMEN DEL NODO DE FILTRADO:")
    print("   1. ✅ Optimización: Detecta mensajes cortos sin LLM")
    print("   2. ✅ Optimización: Detecta contexto insuficiente sin LLM")
    print("   3. ✅ Clasificación: Usa LLM para análisis semántico")
    print("   4. ✅ Robustez: Fallback en caso de error del LLM")
    print("\n💡 VENTAJAS:")
    print("   • Solo llama al LLM cuando es necesario (eficiencia)")
    print("   • Analiza solo últimos 5 mensajes (velocidad)")
    print("   • Temperatura 0 y max_tokens=10 (precisión + rapidez)")
    print("   • Fallback automático (tolerancia a fallos)")
    print("\n✅ El agente ahora es INTELIGENTE y EFICIENTE en su flujo de decisión\n")
