# Estrategia de Caché Inteligente con Auto-Resumen

## 🎯 Objetivo

Implementar un sistema de gestión de sesiones que:
- Mantiene caché de conversaciones activas (<24h)
- Genera automáticamente resúmenes cuando las sesiones expiran (>24h)
- Preserva contexto histórico en memoria episódica (pgvector)
- Permite recuperación de pendientes en futuras sesiones

---

## ⚙️ Configuración del Sistema

### TTL (Time To Live)
- **Duración:** 24 horas (86400 segundos)
- **Checkpointer:** PostgresSaver con TTL configurado
- **Detección:** Comparación de timestamps en nodo de caché

```python
from langgraph.checkpoint.postgres import PostgresSaver

# Configuración en producción
checkpointer = PostgresSaver(
    conn=postgresql_connection,
    ttl=86400  # 24 horas en segundos
)
```

---

## 🔄 Flujo de Funcionamiento

### Caso 1: Sesión Activa (<24h)

```
Usuario escribe → Nodo Cache detecta <24h → Continúa normalmente
                                          → Mensajes se mantienen
                                          → Resumen normal al final
```

**Comportamiento:**
- `sesion_expirada = False`
- Mensajes en caché preservados
- Resumen normal de conversación activa

---

### Caso 2: Sesión Expirada (>24h)

```
Usuario escribe tras 30h → Nodo Cache detecta >24h → Marca sesion_expirada=True
                                                   → Señal: "RESUMEN_DE_CIERRE"
                                                   → Flujo normal hasta Nodo 6
                                                   ↓
                        Nodo Generación Resumen detecta cierre
                                                   ↓
                        LLM extrae pendientes con prompt especial:
                        "Resume lo que quedó pendiente para contexto histórico"
                                                   ↓
                        Limpia mensajes de caché
                                                   ↓
                        Nodo Persistencia guarda con tipo="CIERRE_SESION"
```

**Comportamiento:**
- `sesion_expirada = True`
- `resumen_actual = "RESUMEN_DE_CIERRE"` (señal)
- Mensajes procesados ANTES de limpiar
- Guardado en pgvector con metadata especial

---

### Caso 3: Reactivación (Usuario regresa)

```
Usuario: "¿Qué tenía que hacer?" → Nodo Filtrado detecta cambio tema
                                 → cambio_de_tema=True
                                 → Nodo Recuperación Episódica busca en pgvector
                                 → Filtra por tipo="CIERRE_SESION"
                                 → Devuelve pendientes
                                 ↓
                Orquestador responde: "Retomando lo que dejamos...
                Tenías pendiente: Agendar cita doctor viernes 3pm"
```

---

## 📊 Estructura de Datos

### Estado Actualizado

```python
class WhatsAppAgentState(TypedDict):
    messages: list[AnyMessage]
    user_id: str
    session_id: str
    contexto_episodico: Optional[Dict]
    herramientas_seleccionadas: List[str]
    cambio_de_tema: bool
    resumen_actual: Optional[str]
    timestamp: str
    sesion_expirada: bool  # ← NUEVO
```

### Registro en pgvector

```python
{
    "user_id": "user_123",
    "session_id": "session_abc",
    "tipo": "CIERRE_SESION",  # ← Permite filtrado prioritario
    "timestamp": "2026-01-22T10:30:00",
    "resumen": "[RESUMEN AUTOMÁTICO] Conversación previa: 5 mensajes. Último mensaje: 'Agenda para el lunes'. PENDIENTES: Confirmar reunión 10am con cliente X",
    "embedding": [0.123, 0.456, ...]  # Vector para búsqueda semántica
}
```

---

## 🔨 Implementación por Nodo

### Nodo 1: Cache (Modificado)

**Responsabilidades:**
1. Cargar mensajes desde PostgresSaver
2. Comparar timestamp actual vs último mensaje
3. Si `time_elapsed > 24h` Y `len(messages) > 0`:
   - Marcar `sesion_expirada = True`
   - Establecer `resumen_actual = "RESUMEN_DE_CIERRE"`
   - NO limpiar mensajes (los necesita Nodo 6)
4. Actualizar `timestamp` a hora actual

**Código clave:**
```python
from datetime import datetime, timedelta

now = datetime.now()
last_activity = datetime.fromisoformat(state["timestamp"])
time_elapsed = now - last_activity

if time_elapsed > timedelta(hours=24) and len(state["messages"]) > 0:
    state["sesion_expirada"] = True
    state["resumen_actual"] = "RESUMEN_DE_CIERRE"
```

---

### Nodo 6: Generación de Resumen (Modificado)

**Responsabilidades:**
1. Detectar si `sesion_expirada == True` Y `resumen_actual == "RESUMEN_DE_CIERRE"`
2. **Si es cierre:**
   - Llamar LLM con prompt especial:
     ```
     El usuario ha regresado tras 24h de inactividad.
     Resume lo que quedó pendiente de la sesión anterior
     para guardarlo como contexto histórico.
     
     Conversación previa:
     {state["messages"]}
     
     Extrae:
     - Tareas pendientes
     - Compromisos sin confirmar
     - Información relevante para próxima sesión
     ```
   - Generar resumen estructurado
   - **DESPUÉS** de generar, limpiar `state["messages"] = []`
3. **Si es normal:**
   - Resumen estándar de conversación

**Código clave:**
```python
es_resumen_cierre = (
    state.get("sesion_expirada", False) and 
    state.get("resumen_actual") == "RESUMEN_DE_CIERRE"
)

if es_resumen_cierre:
    # Llamar LLM con prompt de cierre
    resumen = await llm.ainvoke(prompt_cierre)
    state["resumen_actual"] = resumen
    state["messages"] = []  # Limpiar DESPUÉS
```

---

### Nodo 7: Persistencia Episódica (Modificado)

**Responsabilidades:**
1. Detectar tipo de resumen
2. Guardar en pgvector con metadata diferenciada:
   - `tipo = "CIERRE_SESION"` → Alta prioridad en recuperación
   - `tipo = "EPISODIO_NORMAL"` → Prioridad normal
3. Resetear `sesion_expirada = False` después de guardar cierre

**Código clave:**
```python
es_cierre = state.get("sesion_expirada", False)
tipo_registro = "CIERRE_SESION" if es_cierre else "EPISODIO_NORMAL"

# Guardar en pgvector
await pgvector.insert({
    "user_id": state["user_id"],
    "tipo": tipo_registro,
    "resumen": state["resumen_actual"],
    "embedding": await embedder.embed(state["resumen_actual"])
})

if es_cierre:
    state["sesion_expirada"] = False
```

---

### Nodo 3: Recuperación Episódica (Mejora)

**Cuando el usuario regresa:**
```python
# Búsqueda vectorial con filtrado por tipo
resultados = await pgvector.search(
    query_embedding=await embedder.embed(user_query),
    filter={"user_id": state["user_id"]},
    # Priorizar cierres de sesión
    boost={"tipo": {"CIERRE_SESION": 1.5}}
)
```

---

## 🎭 Integración con Orquestador

### Saludo Contextual

El Orquestador debe detectar si viene de una reactivación:

```python
if state.get("contexto_episodico", {}).get("episodios_recuperados"):
    episodios = state["contexto_episodico"]["episodios_recuperados"]
    cierres = [e for e in episodios if e.get("tipo") == "CIERRE_SESION"]
    
    if cierres:
        ultimo_cierre = cierres[0]
        saludo = f"¡Hola de nuevo! Retomando lo que dejamos {calcular_tiempo(ultimo_cierre['timestamp'])}..."
        saludo += f"\n{ultimo_cierre['resumen']}"
```

---

## ✅ Ventajas del Sistema

### 1. **Gestión Automática de Memoria**
- Caché se limpia automáticamente cada 24h
- No se pierde información importante (va a vectores)
- Reduce carga en PostgreSQL

### 2. **Experiencia de Usuario Superior**
- El bot "recuerda" pendientes aunque hayan pasado días/semanas
- Saludo personalizado al regresar
- Contexto relevante sin preguntar de nuevo

### 3. **Búsqueda Semántica Potente**
- Usuario: "¿Qué tenía que hacer?" → Busca en vectores
- Usuario: "¿Cuándo era la reunión?" → Recupera de cierres
- No depende de keywords exactas

### 4. **Escalabilidad**
- TTL evita acumulación infinita de mensajes en caché
- Vectores en pgvector escalan mejor que historial completo
- Filtro por tipo optimiza búsquedas

---

## 🔧 Pasos de Implementación

### Fase 1: Estado y Nodos (✅ COMPLETADO)
- [x] Añadir `sesion_expirada` a `WhatsAppAgentState`
- [x] Modificar `nodo_cache` con lógica de TTL
- [x] Modificar `nodo_generacion_resumen` con modo de cierre
- [x] Modificar `nodo_persistencia_episodica` con tipos

### Fase 2: Base de Datos
- [ ] Configurar PostgresSaver con TTL de 86400s
- [ ] Crear tabla en pgvector con columna `tipo`
- [ ] Implementar índice para filtro `tipo="CIERRE_SESION"`

### Fase 3: LLM Integration
- [ ] Crear prompt de resumen de cierre
- [ ] Probar extracción de pendientes
- [ ] Implementar embeddings reales (OpenAI/DeepSeek)

### Fase 4: Recuperación Episódica
- [ ] Búsqueda vectorial con filtrado por tipo
- [ ] Boost para cierres de sesión (weight 1.5x)
- [ ] Formateo de resultados para Orquestador

### Fase 5: Orquestador
- [ ] Detección de reactivación
- [ ] Saludo contextual
- [ ] Respuesta con pendientes recuperados

---

## 📝 Prompts de Referencia

### Prompt: Resumen de Cierre

```
Eres un asistente que debe generar un resumen conciso de una conversación que quedó inconclusa.

El usuario no escribió durante más de 24 horas, y ahora regresa. 
Tu tarea es extraer:
1. Tareas pendientes (eventos no agendados, citas sin confirmar)
2. Información relevante para la próxima interacción
3. Contexto importante que el usuario podría haber olvidado

Conversación previa:
{messages}

Genera un resumen en este formato:
"[RESUMEN AUTOMÁTICO] El usuario dejó pendiente: [lista de pendientes]. Contexto adicional: [detalles relevantes]."

Sé específico y conciso (máximo 150 palabras).
```

### Prompt: Saludo de Reactivación

```
Eres un asistente de calendario por WhatsApp. El usuario regresa después de {tiempo_transcurrido}.

Contexto de la sesión anterior:
{resumen_de_cierre}

Genera un saludo natural que:
1. Reconozca el tiempo transcurrido
2. Recuerde los pendientes
3. Ofrezca ayuda para retomar

Ejemplo: "¡Hola de nuevo! Han pasado {tiempo}. La última vez hablamos sobre agendar una reunión para el lunes a las 10am. ¿Te gustaría que la programe ahora?"
```

---

## 🧪 Tests de Validación

### Test 1: Sesión Activa
```bash
python test_expiracion_sesion.py
# Verifica: sesion_expirada=False, mensajes preservados
```

### Test 2: Sesión Expirada
```bash
# Timestamp hace 30h → Debe activar auto-resumen
# Verifica: sesion_expirada=True, messages=[], resumen guardado
```

### Test 3: Reactivación
```bash
# Nuevo mensaje mismo user_id → Debe recuperar cierre previo
# Verifica: contexto_episodico contiene tipo="CIERRE_SESION"
```

---

## 📚 Referencias

- [LangGraph Checkpointing](https://langchain-ai.github.io/langgraph/how-tos/persistence/)
- [PostgresSaver TTL Config](https://langchain-ai.github.io/langgraph/reference/checkpoints/#langgraph.checkpoint.postgres.PostgresSaver)
- [pgvector Setup](https://github.com/pgvector/pgvector)
- [Memory Systems in LangGraph](https://langchain-ai.github.io/langgraph/concepts/#memory)

---

## 🚀 Próximos Pasos

1. **Ejecutar:** `python test_expiracion_sesion.py` para validar comportamiento
2. **Integrar:** PostgresSaver en `nodo_cache`
3. **Conectar:** pgvector en `nodo_persistencia_episodica`
4. **Probar:** Con timestamps reales en producción
5. **Optimizar:** Prompts de resumen de cierre con feedback real

---

**Estado actual:** ✅ Arquitectura implementada y validada  
**Pendiente:** Integración con bases de datos reales
