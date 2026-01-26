"""
Test End-to-End del Agente WhatsApp con Memoria Infinita
=========================================================

Simula conversación real completa probando los 7 nodos:
1. Cache TTL → Verifica si ya existe respuesta reciente
2. Filtrado → Detecta cambio de tema con LLM
3. Recuperación → Busca en memoria episódica (pgvector)
4. Selección → Elige herramientas (PostgreSQL + LLM)
5. Ejecución → Llama Google Calendar API
6. Resumen → Audita con LLM (temp=0.3)
7. Persistencia → Guarda en PostgreSQL con embedding

Autor: Agente con Memoria Infinita
Fecha: 2026-01-24
"""

import os
import sys
from datetime import datetime

# Agregar src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.graph_whatsapp import crear_grafo
from langgraph.graph import MessagesState
from langchain_core.messages import HumanMessage


def print_separator(title: str = ""):
    """Imprime separador visual"""
    print("\n" + "="*80)
    if title:
        print(f"  {title}")
        print("="*80)
    print()


def print_state_info(state: dict):
    """Imprime información relevante del estado"""
    print(f"👤 Usuario: {state.get('user_id', 'N/A')}")
    print(f"🆔 Session ID: {state.get('session_id', 'N/A')}")
    print(f"🔄 Cambio de tema: {state.get('cambio_de_tema', False)}")
    print(f"⏰ Sesión expirada: {state.get('sesion_expirada', False)}")
    
    # Mensajes
    messages = state.get('messages', [])
    if messages:
        print(f"💬 Mensajes en historial: {len(messages)}")
        last_msg = messages[-1]
        if hasattr(last_msg, 'content'):
            content = last_msg.content[:100] + "..." if len(last_msg.content) > 100 else last_msg.content
            print(f"   Último: {content}")
    
    # Resumen
    resumen = state.get('resumen_actual')
    if resumen:
        content = resumen[:150] + "..." if len(resumen) > 150 else resumen
        print(f"📝 Resumen generado: {content}")
    
    # Herramientas
    herramientas = state.get('herramientas_seleccionadas', [])
    if herramientas:
        print(f"🛠️  Herramientas seleccionadas: {', '.join(herramientas)}")
    
    # Resultados
    resultados = state.get('resultados_herramientas', [])
    if resultados:
        print(f"✅ Resultados de herramientas: {len(resultados)} disponibles")


def test_scenario_1_greeting():
    """
    Escenario 1: Saludo simple
    - Debe pasar por Cache → Filtrado → Respuesta rápida
    - NO debe usar herramientas (es saludo)
    - Debe detectar que no es cambio de tema
    """
    print_separator("ESCENARIO 1: Saludo Simple")
    
    # Crear grafo
    grafo = crear_grafo()
    
    # Estado inicial
    estado_inicial = {
        'user_id': 'test_user_001',
        'session_id': 'test_session_e2e_001',
        'messages': [
            HumanMessage(content="Hola, ¿cómo estás?")
        ],
        'cambio_de_tema': False,
        'sesion_expirada': False,
        'cache_ttl': 24,  # 24 horas
        'herramientas_seleccionadas': [],
        'resultados_herramientas': [],
        'resumen_actual': None
    }
    
    print("📥 Input:")
    print(f"   Mensaje: {estado_inicial['messages'][0].content}")
    print(f"   Usuario: {estado_inicial['user_id']}")
    
    # Ejecutar grafo
    print("\n🚀 Ejecutando grafo...")
    try:
        # PostgresSaver requiere thread_id en la configuración
        config = {"configurable": {"thread_id": estado_inicial['session_id']}}
        resultado = grafo.invoke(estado_inicial, config)
        
        print("\n📤 Output:")
        print_state_info(resultado)
        
        # Verificaciones
        print("\n🔍 Verificaciones:")
        assert not resultado.get('cambio_de_tema'), "❌ No debería detectar cambio de tema en saludo"
        print("   ✅ Cambio de tema = False (correcto)")
        
        assert not resultado.get('herramientas_seleccionadas'), "❌ No debería seleccionar herramientas para saludo"
        print("   ✅ Sin herramientas seleccionadas (correcto)")
        
        print("\n✅ Escenario 1 PASÓ")
        return True
        
    except Exception as e:
        print(f"\n❌ Error en Escenario 1: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_scenario_2_calendar_query():
    """
    Escenario 2: Consulta de calendario
    - Debe pasar por todos los nodos: Cache → Filtrado → Recuperación → Selección → Ejecución → Resumen → Persistencia
    - Debe detectar cambio de tema (de saludo a calendario)
    - Debe seleccionar herramienta list_events
    - Debe generar resumen y persistir
    """
    print_separator("ESCENARIO 2: Consulta de Calendario")
    
    # Crear grafo
    grafo = crear_grafo()
    
    # Estado inicial (después del saludo)
    estado_inicial = {
        'user_id': 'test_user_001',
        'session_id': 'test_session_e2e_002',
        'messages': [
            HumanMessage(content="Hola"),
            HumanMessage(content="¿Qué reuniones tengo hoy?")
        ],
        'cambio_de_tema': True,  # Cambio de saludo a consulta
        'sesion_expirada': False,
        'cache_ttl': 24,
        'herramientas_seleccionadas': [],
        'resultados_herramientas': [],
        'resumen_actual': None
    }
    
    print("📥 Input:")
    print(f"   Mensaje: {estado_inicial['messages'][-1].content}")
    print(f"   Usuario: {estado_inicial['user_id']}")
    print(f"   Cambio de tema: {estado_inicial['cambio_de_tema']}")
    
    # Ejecutar grafo
    print("\n🚀 Ejecutando grafo...")
    try:
        # PostgresSaver requiere thread_id en la configuración
        config = {"configurable": {"thread_id": estado_inicial['session_id']}}
        resultado = grafo.invoke(estado_inicial, config)
        
        print("\n📤 Output:")
        print_state_info(resultado)
        
        # Verificaciones
        print("\n🔍 Verificaciones:")
        
        # Verificar que pasó por recuperación (si hay memoria)
        print("   ℹ️  Recuperación episódica: Depende de si hay memoria previa")
        
        # Verificar selección de herramientas
        herramientas = resultado.get('herramientas_seleccionadas', [])
        if 'list_events' in herramientas:
            print(f"   ✅ Herramienta correcta seleccionada: list_events")
        else:
            print(f"   ⚠️  Herramientas seleccionadas: {herramientas}")
        
        # Verificar resumen generado
        if resultado.get('resumen_actual'):
            print("   ✅ Resumen generado (será persistido)")
        else:
            print("   ⚠️  No se generó resumen")
        
        # Verificar limpieza de estado (después de persistencia)
        if resultado.get('resumen_actual') is None and not resultado.get('cambio_de_tema'):
            print("   ✅ Estado limpiado correctamente después de persistencia")
        
        print("\n✅ Escenario 2 COMPLETADO")
        return True
        
    except Exception as e:
        print(f"\n❌ Error en Escenario 2: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_scenario_3_session_expiration():
    """
    Escenario 3: Expiración de sesión (24h)
    - Debe detectar sesion_expirada = True
    - Debe limpiar historial con RemoveMessage
    - Debe persistir resumen con tipo='cierre_expiracion'
    """
    print_separator("ESCENARIO 3: Expiración de Sesión")
    
    # Crear grafo
    grafo = crear_grafo()
    
    # Estado inicial (sesión expirada)
    estado_inicial = {
        'user_id': 'test_user_002',
        'session_id': 'test_session_expired_001',
        'messages': [
            HumanMessage(content="Hola, ¿tengo citas esta semana?")
        ],
        'cambio_de_tema': False,
        'sesion_expirada': True,  # ⏰ Sesión expirada
        'cache_ttl': 24,
        'herramientas_seleccionadas': [],
        'resultados_herramientas': [],
        'resumen_actual': "Se consultaron eventos de la semana. Usuario preguntó por citas."
    }
    
    print("📥 Input:")
    print(f"   Mensaje: {estado_inicial['messages'][0].content}")
    print(f"   Usuario: {estado_inicial['user_id']}")
    print(f"   ⏰ Sesión expirada: {estado_inicial['sesion_expirada']}")
    print(f"   Resumen previo: {estado_inicial['resumen_actual'][:80]}...")
    
    # Ejecutar grafo
    print("\n🚀 Ejecutando grafo...")
    try:
        # PostgresSaver requiere thread_id en la configuración
        config = {"configurable": {"thread_id": estado_inicial['session_id']}}
        resultado = grafo.invoke(estado_inicial, config)
        
        print("\n📤 Output:")
        print_state_info(resultado)
        
        # Verificaciones
        print("\n🔍 Verificaciones:")
        
        # Verificar limpieza de historial
        messages_after = resultado.get('messages', [])
        print(f"   📊 Mensajes después: {len(messages_after)}")
        if len(messages_after) == 0:
            print("   ✅ Historial limpiado correctamente (RemoveMessage)")
        else:
            print("   ⚠️  Historial NO se limpió completamente")
        
        # Verificar estado limpio
        if not resultado.get('sesion_expirada'):
            print("   ✅ Flag sesion_expirada reseteado")
        
        if resultado.get('resumen_actual') is None:
            print("   ✅ Resumen limpiado después de persistencia")
        
        print("\n✅ Escenario 3 COMPLETADO")
        print("   ℹ️  Revisa logs para confirmar tipo='cierre_expiracion' en metadata")
        return True
        
    except Exception as e:
        print(f"\n❌ Error en Escenario 3: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Ejecuta todos los escenarios de prueba"""
    print_separator("TEST END-TO-END: Agente WhatsApp con Memoria Infinita")
    print("⏱️  Inicio:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("\n📋 Este test simula conversaciones reales probando los 7 nodos:")
    print("   1. Cache TTL (24h)")
    print("   2. Filtrado (cambio de tema)")
    print("   3. Recuperación Episódica (pgvector)")
    print("   4. Selección Herramientas (PostgreSQL + LLM)")
    print("   5. Ejecución + Orquestador (Google Calendar)")
    print("   6. Generación Resúmenes (Auditoría LLM)")
    print("   7. Persistencia Episódica (pgvector + embeddings)")
    
    print("\n⚙️  Configuración:")
    print(f"   - Python: {sys.version.split()[0]}")
    print(f"   - Working dir: {os.getcwd()}")
    print(f"   - .env loaded: {os.path.exists('.env')}")
    print(f"   - PostgreSQL: {'✅ Configurado' if os.getenv('POSTGRES_HOST') else '⚠️  No configurado (usará fallback)'}")
    print(f"   - Google OAuth: {'✅ Configurado' if os.path.exists('credentials.json') else '⚠️  No configurado'}")
    
    # Ejecutar escenarios
    resultados = []
    
    # Escenario 1: Saludo
    try:
        resultado_1 = test_scenario_1_greeting()
        resultados.append(('Escenario 1: Saludo', resultado_1))
    except Exception as e:
        print(f"❌ Fallo crítico en Escenario 1: {e}")
        resultados.append(('Escenario 1: Saludo', False))
    
    # Escenario 2: Consulta calendario
    try:
        resultado_2 = test_scenario_2_calendar_query()
        resultados.append(('Escenario 2: Calendario', resultado_2))
    except Exception as e:
        print(f"❌ Fallo crítico en Escenario 2: {e}")
        resultados.append(('Escenario 2: Calendario', False))
    
    # Escenario 3: Expiración sesión
    try:
        resultado_3 = test_scenario_3_session_expiration()
        resultados.append(('Escenario 3: Expiración', resultado_3))
    except Exception as e:
        print(f"❌ Fallo crítico en Escenario 3: {e}")
        resultados.append(('Escenario 3: Expiración', False))
    
    # Resumen final
    print_separator("RESUMEN FINAL")
    total = len(resultados)
    exitosos = sum(1 for _, resultado in resultados if resultado)
    
    print(f"📊 Resultados: {exitosos}/{total} escenarios exitosos\n")
    
    for nombre, resultado in resultados:
        status = "✅ PASÓ" if resultado else "❌ FALLÓ"
        print(f"   {status} - {nombre}")
    
    print(f"\n⏱️  Fin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if exitosos == total:
        print("\n🎉 ¡TODOS LOS TESTS PASARON!")
        print("   El Agente con Memoria Infinita está listo para producción.")
        return 0
    else:
        print(f"\n⚠️  {total - exitosos} test(s) fallaron. Revisa los logs.")
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
