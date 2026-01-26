📋 PLAN DE IMPLEMENTACIÓN: Memoria Semántica para WhatsApp Agent

  🎯 Objetivo

  Integrar memoria semántica funcional entre mensajes usando LangGraph BaseStore con búsqueda semántica real.

  ---
  📚 Arquitectura Recomendada (Basada en Docs de LangGraph)

  Según la https://langchain-ai.github.io/langgraph/how-tos/memory/semantic-search/, tenemos dos opciones:

  Opción A: InMemoryStore con Embeddings Reales ✅ RECOMENDADA

  - Ventajas: Fácil de implementar, búsqueda semántica nativa, sin setup adicional
  - Desventajas: No persistente (se pierde al reiniciar)
  - Ideal para: Desarrollo y producción con checkpointers para persistencia

  Opción B: PostgresStore

  - Ventajas: Persistente, integración con pgvector existente
  - Desventajas: Requiere migración de datos, más complejo
  - Ideal para: Producción a largo plazo

  Decisión: Empezaremos con Opción A (InMemoryStore mejorado) porque:
  1. Ya tienes PostgreSQL para episodios (Nodo 3)
  2. PostgresSaver ya maneja persistencia de checkpoints
  3. Más rápido de implementar y probar

  ---
  🔧 FASE 1: Configurar InMemoryStore con Embeddings Reales

  Paso 1.1: Actualizar src/memory/store_config.py

  Cambios necesarios:
  # ❌ ELIMINAR: Embeddings falsos basados en hash
  def simple_embed(texts: list[str]) -> list[list[float]]:
      hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
      # ...

  # ✅ AGREGAR: Embeddings reales con Sentence Transformers
  from langchain_community.embeddings import HuggingFaceEmbeddings

  def get_memory_store(reset: bool = False) -> InMemoryStore:
      global _store_instance

      if reset or _store_instance is None:
          # Usar el mismo modelo que en embeddings locales (consistency)
          embeddings = HuggingFaceEmbeddings(
              model_name="sentence-transformers/paraphrase-MiniLM-L6-v2",
              model_kwargs={'device': 'cpu'}
          )

          _store_instance = InMemoryStore(
              index={
                  "embed": embeddings,  # ✅ Embeddings reales
                  "dims": 384,          # Dimensión del modelo
                  "fields": ["content"] # Campo a embeddear
              }
          )
          logger.info("Memory store inicializado con embeddings reales")

      return _store_instance

  Referencias:
  - https://www.blog.langchain.com/semantic-search-for-langgraph-memory/
  - https://langchain-ai.github.io/langgraph/how-tos/memory/semantic-search/

  ---
  🔧 FASE 2: Integrar Memory Store en el Grafo de WhatsApp

  Paso 2.1: Modificar src/graph_whatsapp.py - Inicializar Store

  Ubicación: Función crear_grafo() (línea 298)

  def crear_grafo() -> StateGraph:
      logger.info("🏗️  Construyendo grafo de WhatsApp Agent...")

      # ✅ AGREGAR: Inicializar memory store
      from src.memory import get_memory_store
      memory_store = get_memory_store()
      logger.info("    ✅ Memory store inicializado")

      # Crear grafo
      builder = StateGraph(WhatsAppAgentState)

      # ... (agregar nodos)

      # Configurar PostgresSaver para checkpoints
      checkpointer = PostgresSaver(conn) if database_url else None

      # ✅ MODIFICAR: Compilar con AMBOS (store + checkpointer)
      if checkpointer:
          graph = builder.compile(
              checkpointer=checkpointer,
              store=memory_store  # ✅ Pasar store al compilar
          )
          logger.info("    ✅ Grafo compilado con store + checkpointer")
      else:
          graph = builder.compile(store=memory_store)
          logger.info("    ✅ Grafo compilado con store")

      return graph

  Referencia:
  - https://docs.langchain.com/oss/python/langgraph/graph-api

  ---
  🔧 FASE 3: Acceder al Store en los Nodos

  Según la https://github.com/langchain-ai/langgraph/discussions/341, hay 3 formas de acceder al store en nodos.

  Opción Recomendada: Usar get_store() de LangGraph ✅

  Ventajas:
  - No requiere cambiar firmas de funciones
  - Compatible con código existente
  - LangGraph inyecta automáticamente el store

  Paso 3.1: Modificar src/nodes/ejecucion_herramientas_node.py

  Agregar imports:
  from langgraph.config import get_store
  from src.memory import get_user_preferences

  Modificar función nodo_ejecucion_herramientas() (línea 399):

  def nodo_ejecucion_herramientas(state: WhatsAppAgentState) -> Dict:
      log_separator(logger, "NODO_5_EJECUCION_HERRAMIENTAS", "INICIO")

      # ✅ AGREGAR: Obtener store y preferencias
      try:
          store = get_store()
          user_id = state.get('user_id', 'default_user')
          preferencias = get_user_preferences(store, user_id)

          # Extraer preferencias relevantes
          timezone_pref = preferencias.get("user_preferences", {}).get("timezone", "America/Tijuana")
          preferred_times = preferencias.get("user_preferences", {}).get("preferred_meeting_times", [])
          language_pref = preferencias.get("user_preferences", {}).get("language_preference", "formal")

          logger.info(f"    👤 Preferencias cargadas: timezone={timezone_pref}, estilo={language_pref}")

      except Exception as e:
          logger.warning(f"    ⚠️  No se pudieron cargar preferencias: {e}")
          preferencias = {}
          timezone_pref = "America/Tijuana"
          preferred_times = []
          language_pref = "formal"

      # ... (resto del código)

  Modificar función construir_prompt_orquestador() (línea 310):

  def construir_prompt_orquestador(
      tiempo_context: str,
      resultados_google: List[Dict],
      contexto_episodico: Dict,
      mensaje_usuario: str,
      preferencias_usuario: Dict  # ✅ NUEVO PARÁMETRO
  ) -> str:
      # Formatear preferencias
      prefs_str = ""
      if preferencias_usuario:
          user_prefs = preferencias_usuario.get("user_preferences", {})
          timezone = user_prefs.get("timezone", "America/Tijuana")
          language = user_prefs.get("language_preference", "formal")
          preferred_times = user_prefs.get("preferred_meeting_times", [])

          prefs_str = f"""
  PREFERENCIAS DEL USUARIO:
  - Zona horaria: {timezone}
  - Estilo de comunicación: {language}
  - Horarios preferidos: {', '.join(preferred_times) if preferred_times else 'No especificado'}
  """

      # ... (resto del prompt con prefs_str incluido)

  Actualizar llamada al Orquestador (línea 557):

  prompt = construir_prompt_orquestador(
      tiempo_context=tiempo_contexto,
      resultados_google=resultados,
      contexto_episodico=contexto_episodico,
      mensaje_usuario=mensaje_usuario,
      preferencias_usuario=preferencias  # ✅ PASAR PREFERENCIAS
  )

  ---
  🔧 FASE 4: Actualizar Preferencias Automáticamente

  Paso 4.1: Modificar src/memory/semantic.py

  Implementar extracción de preferencias con LLM:

  def update_semantic_memory(
      state: dict,
      store: BaseStore,
      user_id: str,
      llm: Optional[Any] = None
  ) -> Dict[str, Any]:
      namespace = ("semantic", user_id)
      current_memory = get_user_preferences(store, user_id)

      # ✅ IMPLEMENTAR: Extracción con LLM estructurado
      if llm and state.get("messages"):
          try:
              recent_messages = state["messages"][-5:]
              messages_text = "\n".join([
                  f"{msg.get('role', 'unknown')}: {msg.get('content', '')}"
                  for msg in recent_messages
              ])

              # Usar structured output de OpenAI/Anthropic
              from pydantic import BaseModel, Field

              class PreferencesUpdate(BaseModel):
                  timezone: Optional[str] = Field(None, description="Zona horaria mencionada")
                  preferred_times: Optional[List[str]] = Field(None, description="Horarios preferidos")
                  language_preference: Optional[str] = Field(None, description="formal o informal")

              prompt = f"""Analiza esta conversación y extrae SOLO nueva información sobre preferencias:

  Conversación:
  {messages_text}

  Preferencias actuales:
  {json.dumps(current_memory, indent=2)}

  Si NO hay nueva información relevante, devuelve campos null."""

              # Invocar con structured output
              response = llm.with_structured_output(PreferencesUpdate).invoke(prompt)

              # Actualizar solo si hay cambios
              if response.timezone or response.preferred_times or response.language_preference:
                  if response.timezone:
                      current_memory["user_preferences"]["timezone"] = response.timezone
                  if response.preferred_times:
                      current_memory["user_preferences"]["preferred_meeting_times"] = response.preferred_times
                  if response.language_preference:
                      current_memory["user_preferences"]["language_preference"] = response.language_preference

                  logger.info(f"✅ Preferencias actualizadas para {user_id}")

          except Exception as e:
              logger.error(f"Error extrayendo preferencias: {e}")

      # Actualizar timestamp y guardar
      current_memory["last_updated"] = datetime.now().isoformat()
      store.put(namespace, "preferences", current_memory)

      return current_memory

  Paso 4.2: Llamar a update_semantic_memory en Nodo 6

  Modificar src/nodes/generacion_resumen_node.py:

  from langgraph.config import get_store
  from src.memory import update_semantic_memory

  def nodo_generacion_resumen(state: WhatsAppAgentState) -> Dict:
      # ... (generar resumen)

      # ✅ AGREGAR: Actualizar preferencias después del resumen
      try:
          store = get_store()
          user_id = state.get('user_id')

          # Usar LLM para actualizar preferencias
          update_semantic_memory(state, store, user_id, llm=llm_orquestador)
          logger.info("    ✅ Preferencias actualizadas con contexto de conversación")

      except Exception as e:
          logger.warning(f"    ⚠️  Error actualizando preferencias: {e}")

      return {'resumen_actual': resumen}

  ---
  🔧 FASE 5: Unificar Memoria Episódica con Memory Store

  Opción A: Mantener PostgreSQL para Episodios ✅ RECOMENDADA

  - Nodo 3 sigue usando memoria_episodica (PostgreSQL + pgvector)
  - InMemoryStore solo para preferencias semánticas
  - Ventaja: No requiere migración de datos

  Opción B: Migrar Episodios a InMemoryStore

  - Consolidar todo en un solo sistema
  - Desventaja: Perder persistencia de episodios

  Decisión: Mantener arquitectura híbrida:
  - InMemoryStore: Preferencias del usuario (memoria semántica)
  - PostgreSQL: Resúmenes de conversaciones (memoria episódica)
  - PostgresSaver: Checkpoints para rolling window

  ---
  📊 RESUMEN DE CAMBIOS
  ┌──────────────────────────────────────────┬──────────────────────────────────────────────────┬───────────────┐
  │                 Archivo                  │                     Cambios                      │   Prioridad   │
  ├──────────────────────────────────────────┼──────────────────────────────────────────────────┼───────────────┤
  │ src/memory/store_config.py               │ Reemplazar embeddings hash por reales            │ 🔴 CRÍTICO    │
  ├──────────────────────────────────────────┼──────────────────────────────────────────────────┼───────────────┤
  │ src/graph_whatsapp.py                    │ Inicializar y pasar store al compilar            │ 🔴 CRÍTICO    │
  ├──────────────────────────────────────────┼──────────────────────────────────────────────────┼───────────────┤
  │ src/nodes/ejecucion_herramientas_node.py │ Cargar preferencias con get_store()              │ 🔴 CRÍTICO    │
  ├──────────────────────────────────────────┼──────────────────────────────────────────────────┼───────────────┤
  │ src/memory/semantic.py                   │ Implementar extracción LLM con structured output │ 🟡 IMPORTANTE │
  ├──────────────────────────────────────────┼──────────────────────────────────────────────────┼───────────────┤
  │ src/nodes/generacion_resumen_node.py     │ Llamar a update_semantic_memory()                │ 🟡 IMPORTANTE │
  └──────────────────────────────────────────┴──────────────────────────────────────────────────┴───────────────┘
  ---
  ✅ ORDEN DE IMPLEMENTACIÓN

  1. Fase 1 → Arreglar embeddings (15 min)
  2. Fase 2 → Integrar store en grafo (10 min)
  3. Fase 3 → Cargar preferencias en Nodo 5 (20 min)
  4. Fase 4 → Actualizar preferencias automáticamente (30 min)
  5. Fase 5 → Testing y validación (30 min)

  Tiempo total estimado: ~2 horas

  ---
  🔗 Referencias de Documentación

  - https://langchain-ai.github.io/langgraph/how-tos/memory/semantic-search/
  - https://www.blog.langchain.com/semantic-search-for-langgraph-memory/
  - https://docs.langchain.com/oss/python/langgraph/memory
  - https://docs.langchain.com/oss/python/langgraph/graph-api
  - https://reference.langchain.com/python/langgraph/store/

  ---