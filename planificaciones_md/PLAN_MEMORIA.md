# 🧠 Plan de Integración de Sistema de Memoria Multi-Tipo para Calendar AI Agent

## 📋 Resumen Ejecutivo

Integración de **3 tipos de memoria** basados en arquitectura humana para mejorar la inteligencia del agente:

### Tipos de Memoria

| Tipo | Propósito | Ejemplo en Calendario |
|------|-----------|----------------------|
| **Semántica** | Hechos y preferencias del usuario | "Usuario prefiere reuniones por la mañana", "Trabaja EST timezone" |
| **Episódica** | Experiencias pasadas y acciones | "Canceló 3 reuniones con cliente X", "Siempre pospone reuniones de lunes" |
| **Procedimental** | Reglas y comportamiento del agente | "Siempre confirmar antes de eliminar", "Usar lenguaje formal con cliente X" |

---

## 🏗️ Arquitectura Propuesta

```
┌─────────────────────────────────────────────────────────────┐
│                    Calendar AI Agent                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────┐    │
│  │   MEMORIA    │  │    MEMORIA    │  │   MEMORIA    │    │
│  │  SEMÁNTICA   │  │   EPISÓDICA   │  │ PROCEDIMENTAL│    │
│  └──────────────┘  └───────────────┘  └──────────────┘    │
│        │                  │                   │             │
│        └──────────────────┼───────────────────┘             │
│                          │                                  │
│                    ┌─────▼─────┐                           │
│                    │  LangGraph │                           │
│                    │   Store    │                           │
│                    └────────────┘                           │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │          Nodos del Grafo LangGraph                 │    │
│  │  ┌─────────┐  ┌──────────┐  ┌─────────────┐      │    │
│  │  │call_model│→│   tools   │→│memory_update│      │    │
│  │  └─────────┘  └──────────┘  └─────────────┘      │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## 📦 1. MEMORIA SEMÁNTICA (Hechos y Preferencias)

### Objetivo
Almacenar conocimiento sobre el usuario, sus preferencias y contexto laboral.

### Datos a Almacenar

```python
{
    "user_preferences": {
        "preferred_meeting_times": ["09:00-11:00", "14:00-16:00"],
        "timezone": "America/New_York",
        "default_meeting_duration": 60,  # minutos
        "language_preference": "formal",
        "notification_preference": "email",
    },
    "work_context": {
        "role": "Product Manager",
        "team": "Engineering",
        "working_hours": "09:00-17:00",
        "typical_meeting_types": ["1:1", "standup", "planning"],
    },
    "contact_preferences": {
        "client_x": {
            "preferred_communication": "formal",
            "typical_meeting_length": 30,
            "notes": "Prefiere reuniones breves y directas"
        }
    }
}
```

### Implementación

**Namespace**: `("semantic", user_id)`

**Cuándo actualizar:**
- Durante onboarding inicial
- Cuando usuario explícitamente comparte preferencias
- Mediante nodo `update_semantic_memory` que analiza conversaciones

```python
# src/memory/semantic.py
from langgraph.store.memory import InMemoryStore

async def update_semantic_memory(state, store, user_id):
    """Actualiza memoria semántica basada en nueva información"""
    namespace = ("semantic", user_id)
    
    # Obtener memoria actual
    current_memory = store.get(namespace, "preferences")
    
    # Extraer nueva información con LLM
    prompt = f"""
    Analiza esta conversación y extrae:
    1. Preferencias de horarios
    2. Preferencias de comunicación
    3. Contexto laboral
    
    Conversación: {state['messages'][-5:]}
    Memoria actual: {current_memory}
    
    Devuelve JSON con actualizaciones.
    """
    
    updates = llm.invoke(prompt)
    
    # Merge y guardar
    updated_memory = merge_preferences(current_memory, updates)
    store.put(namespace, "preferences", updated_memory)
```

---

## 📖 2. MEMORIA EPISÓDICA (Experiencias Pasadas)

### Objetivo
Recordar acciones pasadas, patrones de comportamiento y eventos históricos.

### Datos a Almacenar

```python
{
    "event_id": "evt_123",
    "timestamp": "2026-01-23T10:00:00Z",
    "action": "postpone_meeting",
    "context": {
        "original_time": "2026-01-23T15:00:00",
        "new_time": "2026-01-24T10:00:00",
        "meeting_title": "Client Review",
        "reason": "Conflicto con otra reunión",
        "participants": ["client_x"]
    },
    "outcome": "success",
    "user_sentiment": "satisfied"
}
```

### Patrones Detectables

- "Usuario siempre pospone reuniones de lunes"
- "Ha cancelado 3 veces con este cliente"
- "Prefiere mover reuniones a mañanas"
- "Nunca acepta reuniones después de las 4 PM"

### Implementación

**Namespace**: `("episodic", user_id)`

**Cuándo actualizar:** Después de cada acción exitosa del agente

```python
# src/memory/episodic.py
async def log_episode(state, store, user_id, action_type):
    """Registra un episodio/experiencia"""
    namespace = ("episodic", user_id)
    
    episode = {
        "id": generate_id(),
        "timestamp": datetime.now().isoformat(),
        "action": action_type,
        "context": extract_context(state),
        "outcome": "success",
    }
    
    # Guardar como nuevo documento
    store.put(namespace, episode["id"], episode)


async def get_relevant_episodes(state, store, user_id, query):
    """Busca episodios relevantes para contexto actual"""
    namespace = ("episodic", user_id)
    
    # Búsqueda semántica
    episodes = store.search(
        namespace,
        query=query,
        limit=5
    )
    
    return episodes


async def detect_patterns(state, store, user_id):
    """Detecta patrones de comportamiento"""
    namespace = ("episodic", user_id)
    
    # Obtener últimos 20 episodios
    recent_episodes = store.search(namespace, limit=20)
    
    # Analizar con LLM
    prompt = f"""
    Analiza estos episodios y detecta patrones:
    {json.dumps(recent_episodes)}
    
    ¿Qué patrones observas en el comportamiento del usuario?
    """
    
    patterns = llm.invoke(prompt)
    
    # Guardar patrones en semántica
    await update_semantic_memory_with_patterns(patterns)
```

---

## 📜 3. MEMORIA PROCEDIMENTAL (Reglas y Comportamiento)

### Objetivo
Almacenar y adaptar las instrucciones del agente basándose en feedback y uso.

### Datos a Almacenar

```python
{
    "system_prompt": """
    Eres un asistente de calendario profesional.
    
    REGLAS APRENDIDAS:
    - Siempre pedir confirmación antes de eliminar eventos
    - Con cliente_x usar lenguaje formal y ser directo
    - Sugerir alternativas cuando no hay disponibilidad
    - Si usuario pospone >2 veces, preguntar si desea cancelar
    
    ESTILO COMUNICACIÓN:
    - Breve y directo
    - Usar emojis: ✅ ❌ 📅
    """,
    "version": "1.5",
    "last_updated": "2026-01-23T10:00:00Z",
    "improvement_notes": [
        "Usuario pidió más confirmaciones -> agregado",
        "Feedback: respuestas muy largas -> simplificado"
    ]
}
```

### Implementación

**Namespace**: `("procedural", "agent")`

**Cuándo actualizar:**
- Cuando usuario da feedback explícito
- Periódicamente mediante análisis de conversaciones
- Cuando se detectan errores repetidos

```python
# src/memory/procedural.py
async def get_agent_instructions(store):
    """Obtiene instrucciones actuales del agente"""
    namespace = ("procedural", "agent")
    instructions = store.get(namespace, "system_prompt")
    return instructions.value["system_prompt"]


async def refine_instructions(state, store, feedback=None):
    """Refina instrucciones basándose en feedback o conversación"""
    namespace = ("procedural", "agent")
    
    current_instructions = await get_agent_instructions(store)
    
    prompt = f"""
    Instrucciones actuales:
    {current_instructions}
    
    Conversación reciente:
    {state['messages'][-10:]}
    
    Feedback del usuario:
    {feedback}
    
    ¿Cómo mejorarías las instrucciones del agente?
    Devuelve las instrucciones mejoradas.
    """
    
    new_instructions = llm.invoke(prompt)
    
    # Guardar nueva versión
    store.put(namespace, "system_prompt", {
        "system_prompt": new_instructions,
        "version": increment_version(),
        "last_updated": datetime.now().isoformat(),
    })


async def call_model_with_memory(state, store):
    """Llama al modelo usando instrucciones procedimentales"""
    instructions = await get_agent_instructions(store)
    
    # Usar instrucciones personalizadas
    messages = [
        {"role": "system", "content": instructions},
        *state["messages"]
    ]
    
    response = llm.invoke(messages)
    return {"messages": [response]}
```

---

## 🔧 4. INTEGRACIÓN EN EL GRAFO LANGGRAPH

### Modificaciones a `src/graph.py`

```python
from langgraph.store.memory import InMemoryStore
from langgraph.checkpoint.memory import MemorySaver
from src.memory.semantic import update_semantic_memory, get_user_preferences
from src.memory.episodic import log_episode, get_relevant_episodes
from src.memory.procedural import get_agent_instructions, refine_instructions

# Inicializar store
store = InMemoryStore()
checkpointer = MemorySaver()

# Nodo mejorado con memoria semántica
async def call_model_with_context(state, config, store):
    """Llama al modelo con contexto de memorias"""
    user_id = config.get("configurable", {}).get("user_id", "default")
    
    # 1. Obtener instrucciones procedimentales
    instructions = await get_agent_instructions(store)
    
    # 2. Obtener preferencias semánticas
    preferences = await get_user_preferences(store, user_id)
    
    # 3. Buscar episodios relevantes
    query = state["messages"][-1]["content"]
    relevant_episodes = await get_relevant_episodes(state, store, user_id, query)
    
    # 4. Construir prompt enriquecido
    enriched_context = f"""
    {instructions}
    
    PREFERENCIAS DEL USUARIO:
    {json.dumps(preferences, indent=2)}
    
    EXPERIENCIAS PASADAS RELEVANTES:
    {format_episodes(relevant_episodes)}
    """
    
    messages = [
        {"role": "system", "content": enriched_context},
        *state["messages"]
    ]
    
    response = model_with_tools.invoke(messages)
    return {"messages": [response]}


# Nuevo nodo para actualizar memorias
async def memory_update_node(state, config, store):
    """Actualiza memorias después de acciones"""
    user_id = config.get("configurable", {}).get("user_id", "default")
    
    # Detectar tipo de acción
    last_tool_message = next(
        (msg for msg in reversed(state["messages"]) if isinstance(msg, ToolMessage)),
        None
    )
    
    if last_tool_message:
        # Log episódico
        await log_episode(state, store, user_id, last_tool_message.name)
        
        # Actualizar semántica si hay nueva info
        await update_semantic_memory(state, store, user_id)
    
    return state


# Grafo actualizado
builder = StateGraph(MessagesState)
builder.add_node("call_model", call_model_with_context)
builder.add_node("tools", tool_dispatch_node)
builder.add_node("memory_update", memory_update_node)

builder.add_edge(START, "call_model")
builder.add_conditional_edges("call_model", should_continue, ["tools", END])
builder.add_edge("tools", "memory_update")
builder.add_edge("memory_update", "call_model")

# Compilar con store y checkpointer
graph = builder.compile(
    checkpointer=checkpointer,
    store=store
)
```

---

## 🗂️ 5. ESTRUCTURA DE ARCHIVOS

```
src/
├── memory/
│   ├── __init__.py
│   ├── semantic.py          # Memoria semántica (preferencias)
│   ├── episodic.py          # Memoria episódica (experiencias)
│   ├── procedural.py        # Memoria procedimental (instrucciones)
│   └── store_config.py      # Configuración del store
├── graph.py                 # Grafo actualizado con memoria
├── tool.py
└── utilities.py
```

---

## 📊 6. CASOS DE USO PRÁCTICOS

### Caso 1: Usuario pide "Agenda una reunión"

**Sin memoria:**
- Agente: "¿Cuándo quieres la reunión?"

**Con memoria semántica:**
- Agente: "Claro! Por tus preferencias, ¿te va bien mañana a las 10 AM? (tu horario preferido)"

---

### Caso 2: Usuario cancela reunión por tercera vez

**Sin memoria:**
- Agente: "✅ Reunión cancelada"

**Con memoria episódica:**
- Agente: "He notado que has cancelado esta reunión 3 veces. ¿Prefieres que la eliminemos definitivamente o la reprogramemos para otro momento?"

---

### Caso 3: Usuario da feedback negativo

**Sin memoria:**
- Comportamiento no cambia

**Con memoria procedimental:**
- Agente actualiza sus instrucciones internas
- En futuras interacciones aplica el aprendizaje

---

## 🚀 7. PLAN DE IMPLEMENTACIÓN

### Fase 1: Base (1-2 días)
1. ✅ Crear estructura de archivos `src/memory/`
2. ✅ Implementar `store_config.py` con InMemoryStore
3. ✅ Crear schemas básicos para cada tipo de memoria

### Fase 2: Memoria Semántica (2-3 días)
1. ✅ Implementar `semantic.py` con funciones CRUD
2. ✅ Crear nodo de actualización semántica
3. ✅ Integrar en grafo para leer preferencias

### Fase 3: Memoria Episódica (2-3 días)
1. ✅ Implementar `episodic.py` con logging de acciones
2. ✅ Crear búsqueda semántica de episodios
3. ✅ Integrar detección de patrones

### Fase 4: Memoria Procedimental (2-3 días)
1. ✅ Implementar `procedural.py` con gestión de prompts
2. ✅ Crear mecanismo de refinamiento
3. ✅ Sistema de versionado de instrucciones

### Fase 5: Integración y Testing (2-3 días)
1. ✅ Integrar todos los tipos en el grafo
2. ✅ Implementar nodo `memory_update`
3. ✅ Testing end-to-end
4. ✅ Ajustes de rendimiento

### Fase 6: Base de Datos Persistente (2 días)
1. ✅ Migrar de InMemoryStore a PostgreSQL/Redis
2. ✅ Configurar persistencia real
3. ✅ Deployment en producción

---

## 📈 8. MÉTRICAS DE ÉXITO

- **Personalización**: % de respuestas que usan preferencias del usuario
- **Relevancia**: Similitud entre episodios recuperados y acción actual
- **Adaptabilidad**: Número de refinamientos procedimentales por semana
- **Satisfacción**: Feedback positivo del usuario (+30% esperado)
- **Eficiencia**: Reducción en número de preguntas redundantes (-50%)

---

## 🔐 9. CONSIDERACIONES

### Privacidad
- Encriptar datos sensibles en memoria semántica
- Permitir al usuario ver/eliminar sus memorias
- Compliance con GDPR/regulaciones

### Rendimiento
- Limitar búsquedas a últimos N episodios
- Cachear preferencias semánticas
- Actualizar procedural en background

### Mantenimiento
- Limpiar episodios antiguos (>6 meses)
- Validar schemas de memoria
- Monitorear calidad de memorias generadas

---

## 📚 10. RECURSOS Y REFERENCIAS

- [LangGraph Memory Docs](https://docs.langchain.com/oss/python/langgraph/memory)
- [Memory Agent Template](https://github.com/langchain-ai/memory-agent)
- [Memory Service Template](https://github.com/langchain-ai/memory-template)
- [CoALA Paper (Memory Types)](https://arxiv.org/pdf/2309.02427)

---

## ✅ PRÓXIMOS PASOS

1. **Revisar este plan** - Confirmar enfoque y prioridades
2. **Crear estructura** - Setup inicial de archivos
3. **Implementar Fase 1** - Base y configuración
4. **Iteración incremental** - Implementar fase por fase

¿Quieres que empiece con la implementación? 🚀
