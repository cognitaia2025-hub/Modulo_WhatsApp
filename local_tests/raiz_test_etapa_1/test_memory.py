"""
Script de prueba para el sistema de memoria multi-tipo

Demuestra el uso de memoria semántica, episódica y procedimental.
"""

from src.memory import (
    get_memory_store,
    get_user_preferences,
    update_semantic_memory,
    log_episode,
    get_relevant_episodes,
    detect_patterns,
    get_agent_instructions,
    get_instruction_version
)

def test_semantic_memory():
    """Prueba memoria semántica (preferencias del usuario)"""
    print("\n" + "="*60)
    print("🧠 PRUEBA DE MEMORIA SEMÁNTICA")
    print("="*60)
    
    store = get_memory_store()
    user_id = "test_user_123"
    
    # Obtener preferencias
    print("\n1. Obteniendo preferencias del usuario...")
    prefs = get_user_preferences(store, user_id)
    print(f"✅ Preferencias cargadas:")
    print(f"   - Zona horaria: {prefs['user_preferences']['timezone']}")
    print(f"   - Horarios preferidos: {prefs['user_preferences']['preferred_meeting_times']}")
    print(f"   - Duración default: {prefs['user_preferences']['default_meeting_duration']} min")
    
    print("\n✨ Memoria semántica funcionando correctamente!")


def test_episodic_memory():
    """Prueba memoria episódica (experiencias pasadas)"""
    print("\n" + "="*60)
    print("📖 PRUEBA DE MEMORIA EPISÓDICA")
    print("="*60)
    
    store = get_memory_store()
    user_id = "test_user_123"
    
    # Simular varios episodios
    print("\n1. Registrando episodios de interacción...")
    
    episodes_data = [
        {
            "action": "create_event_tool",
            "state": {"messages": [{"role": "user", "content": "Crea reunión mañana 10 AM"}]},
        },
        {
            "action": "postpone_event_tool",
            "state": {"messages": [{"role": "user", "content": "Posponer reunión de cliente"}]},
        },
        {
            "action": "postpone_event_tool",
            "state": {"messages": [{"role": "user", "content": "Cambiar reunión de lunes"}]},
        },
        {
            "action": "delete_event_tool",
            "state": {"messages": [{"role": "user", "content": "Cancelar reunión con Juan"}]},
        },
        {
            "action": "create_event_tool",
            "state": {"messages": [{"role": "user", "content": "Nueva reunión el jueves"}]},
        },
    ]
    
    for ep_data in episodes_data:
        episode_id = log_episode(
            state=ep_data["state"],
            store=store,
            user_id=user_id,
            action_type=ep_data["action"]
        )
        print(f"   ✅ Episodio registrado: {ep_data['action']} (ID: {episode_id[:8]}...)")
    
    # Buscar episodios relevantes
    print("\n2. Buscando episodios relevantes...")
    query_state = {"messages": [{"role": "user", "content": "Quiero posponer una reunión"}]}
    relevant = get_relevant_episodes(query_state, store, user_id, limit=3)
    print(f"   ✅ Encontrados {len(relevant)} episodios relevantes")
    for ep in relevant[:2]:
        print(f"      - {ep['action']}: {ep['timestamp'][:19]}")
    
    # Detectar patrones
    print("\n3. Detectando patrones de comportamiento...")
    patterns = detect_patterns(store, user_id, lookback_limit=10)
    print(f"   ✅ Patrones detectados: {len(patterns['patterns'])}")
    for pattern in patterns['patterns']:
        print(f"      - {pattern['description']}")
    
    print("\n✨ Memoria episódica funcionando correctamente!")


def test_procedural_memory():
    """Prueba memoria procedimental (reglas del agente)"""
    print("\n" + "="*60)
    print("📜 PRUEBA DE MEMORIA PROCEDIMENTAL")
    print("="*60)
    
    store = get_memory_store()
    
    # Obtener instrucciones
    print("\n1. Obteniendo instrucciones del agente...")
    instructions = get_agent_instructions(store)
    version = get_instruction_version(store)
    print(f"✅ Instrucciones cargadas (v{version})")
    print(f"   Primeras líneas: {instructions[:150]}...")
    
    print("\n✨ Memoria procedimental funcionando correctamente!")


def test_integration():
    """Prueba integración de todos los tipos de memoria"""
    print("\n" + "="*60)
    print("🔗 PRUEBA DE INTEGRACIÓN COMPLETA")
    print("="*60)
    
    store = get_memory_store()
    user_id = "integration_test_user"
    
    print("\n1. Simulando flujo completo de usuario...")
    
    # Usuario crea un evento
    state1 = {"messages": [
        {"role": "user", "content": "Crea una reunión mañana a las 2 PM"}
    ], "user_id": user_id}
    
    # Registrar episodio
    log_episode(state1, store, user_id, "create_event_tool")
    print("   ✅ Episodio 1: Creó un evento")
    
    # Usuario consulta preferencias
    prefs = get_user_preferences(store, user_id)
    print(f"   ✅ Preferencias cargadas: {prefs['user_preferences']['timezone']}")
    
    # Usuario pospone evento
    state2 = {"messages": [
        {"role": "user", "content": "Posponer la reunión de mañana"}
    ], "user_id": user_id}
    
    log_episode(state2, store, user_id, "postpone_event_tool")
    print("   ✅ Episodio 2: Pospuso el evento")
    
    # Detectar patrones
    patterns = detect_patterns(store, user_id)
    print(f"   ✅ Patrones detectados: {len(patterns.get('patterns', []))}")
    
    # Obtener contexto para próxima interacción
    print("\n2. Preparando contexto para próxima interacción...")
    relevant_episodes = get_relevant_episodes(state2, store, user_id, limit=2)
    print(f"   ✅ {len(relevant_episodes)} episodios relevantes recuperados")
    
    instructions = get_agent_instructions(store)
    print(f"   ✅ Instrucciones del agente cargadas")
    
    print("\n✨ Integración completa funcionando correctamente!")
    print("\n💡 El agente ahora tiene:")
    print("   - Conocimiento de preferencias del usuario")
    print("   - Historial de acciones pasadas")
    print("   - Reglas de comportamiento adaptables")


if __name__ == "__main__":
    print("\n" + "🚀 " + "="*56)
    print("SISTEMA DE MEMORIA MULTI-TIPO - PRUEBAS")
    print("="*58)
    
    try:
        # Ejecutar todas las pruebas
        test_semantic_memory()
        test_episodic_memory()
        test_procedural_memory()
        test_integration()
        
        print("\n" + "="*60)
        print("✅ TODAS LAS PRUEBAS COMPLETADAS EXITOSAMENTE")
        print("="*60)
        print("\n💫 El sistema de memoria está listo para usar!")
        print("   Ahora tu agente puede:")
        print("   - 🧠 Recordar preferencias del usuario")
        print("   - 📖 Aprender de experiencias pasadas")
        print("   - 📜 Adaptar su comportamiento con el tiempo")
        print()
        
    except Exception as e:
        print(f"\n❌ Error durante las pruebas: {e}")
        import traceback
        traceback.print_exc()
