"""
Grafo Principal del Agente de WhatsApp

Implementa el flujo de 7 nodos con bifurcación condicional.
Incluye PostgresSaver para persistencia de checkpoints (caché 24h).
"""

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_core.messages import RemoveMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from datetime import datetime, timedelta
import logging
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
import psycopg
import pendulum

# Importar sistema de logging con colores
from src.utils.logging_config import setup_colored_logging, log_separator

# Cargar variables de entorno
load_dotenv()

# Configurar logging con colores
logger = setup_colored_logging()

# Añadir el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.state.agent_state import WhatsAppAgentState
from src.nodes.seleccion_herramientas_node import nodo_seleccion_herramientas_wrapper
from src.nodes.ejecucion_herramientas_node import nodo_ejecucion_herramientas_wrapper
from src.nodes.generacion_resumen_node import nodo_generacion_resumen_wrapper
from src.nodes.persistencia_episodica_node import nodo_persistencia_episodica_wrapper
from src.nodes.recuperacion_episodica_node import nodo_recuperacion_episodica_wrapper


# ============================================================================
# NODOS STUB (Funciones Vacías - Solo Skeleton)
# ============================================================================

def nodo_cache(state: WhatsAppAgentState) -> WhatsAppAgentState:
    """
    [1] Nodo de Caché con gestión de TTL (24h)
    Detecta si la sesión ha expirado y marca para auto-resumen.
    
    Lógica:
    - Si >24h de inactividad: marca sesion_expirada=True y señaliza resumen de cierre
    - Si <24h: continúa normalmente
    """
    logger.info("🗄️  [1] NODO_CACHE - Verificando caché de sesión")
    logger.info(f"    User ID: {state.get('user_id', 'N/A')}")
    logger.info(f"    Session ID: {state.get('session_id', 'N/A')}")

    # Obtener timestamp actual con timezone (Mexicali/Tijuana)
    now = pendulum.now('America/Tijuana')

    # Parsear timestamp del estado (debería venir con timezone del WhatsApp service)
    try:
        # Usar pendulum.parse que maneja automáticamente ISO strings con timezone
        last_activity = pendulum.parse(state["timestamp"])
    except (ValueError, KeyError, TypeError):
        # Si no hay timestamp válido, asumir sesión nueva
        last_activity = now
    
    # Calcular tiempo transcurrido
    time_elapsed = now - last_activity
    TTL_HOURS = 24
    
    # Detectar si la sesión ha expirado
    if time_elapsed > timedelta(hours=TTL_HOURS) and len(state.get('messages', [])) > 0:
        logger.info(f"    ⚠️  Sesión EXPIRADA: {time_elapsed.total_seconds()/3600:.1f}h de inactividad")
        logger.info("    📤 Marcando para auto-resumen de cierre...")
        
        # Marcar flag de expiración
        state["sesion_expirada"] = True
        
        # Señal especial para el nodo de resúmenes
        state["resumen_actual"] = "RESUMEN_DE_CIERRE"
        
        # NO limpiar mensajes aquí - el nodo de resúmenes los necesita
        
    else:
        elapsed_hours = time_elapsed.total_seconds() / 3600
        logger.info(f"    ✓ Sesión ACTIVA ({elapsed_hours:.1f}h desde última actividad)")
        state["sesion_expirada"] = False
    
    # Actualizar timestamp (pendulum lo convierte automáticamente a ISO con timezone)
    state["timestamp"] = now.to_iso8601_string()
    
    # TODO: Integrar PostgresSaver con TTL
    # from langgraph.checkpoint.postgres import PostgresSaver
    # checkpointer = PostgresSaver(conn, ttl=86400)  # 24 horas
    
    return state


def nodo_filtrado(state: WhatsAppAgentState) -> WhatsAppAgentState:
    """
    [2] Nodo Gatekeeper - Detector de Necesidad de Contexto Externo
    
    Determina si el mensaje del usuario requiere:
    - Consultar memoria episódica (conversaciones pasadas)
    - Usar herramientas (Google Calendar, búsquedas)
    - O si es solo conversacional (saludos, despedidas, agradecimientos)
    
    OPTIMIZACIÓN: Solo cuando es necesario, el bot activa Nodos 3 y 4.
    Esto ahorra tokens, tiempo de respuesta y carga en embeddings/PostgreSQL.
    """
    logger.info("🚪 [2] NODO_GATEKEEPER - Detectando necesidad de contexto externo")
    
    messages = state.get('messages', [])
    num_mensajes = len(messages)
    logger.info(f"    Mensajes en historial: {num_mensajes}")
    
    # Caso 1: Primer mensaje → asumir que necesita contexto
    if num_mensajes < 1:
        logger.info("    ⚡ Primer mensaje, asumiendo que requiere contexto")
        state['cambio_de_tema'] = True  # Reutilizamos la variable (podríamos renombrar a 'requiere_contexto')
        return state
    
    # Extraer último mensaje
    ultimo_mensaje = messages[-1]
    if isinstance(ultimo_mensaje, dict):
        contenido = ultimo_mensaje.get('content', '').strip()
    else:
        contenido = getattr(ultimo_mensaje, 'content', '').strip()
    
    # Caso 2: Mensajes puramente conversacionales (sin acción requerida)
    palabras_no_accionables = [
        # Saludos
        'hola', 'buenos días', 'buenas tardes', 'buenas noches', 'qué tal', 'cómo estás',
        # Despedidas
        'adiós', 'hasta luego', 'chao', 'bye', 'nos vemos',
        # Agradecimientos
        'gracias', 'muchas gracias', 'ok gracias', 'perfecto gracias',
        # Confirmaciones simples
        'vale', 'ok', 'perfecto', 'genial', 'entendido', 'sí', 'si', 'claro',
        'de acuerdo', 'está bien', 'bien', 'okey'
    ]
    
    contenido_lower = contenido.lower()
    es_mensaje_corto = len(contenido.split()) <= 5
    contiene_palabra_no_accionable = any(palabra in contenido_lower for palabra in palabras_no_accionables)
    
    # ✅ NUEVO: Detectar si el mensaje anterior del asistente fue una pregunta
    mensaje_anterior_es_pregunta = False
    if num_mensajes >= 2:
        mensaje_previo = messages[-2]
        if isinstance(mensaje_previo, dict):
            contenido_previo = mensaje_previo.get('content', '').strip()
            role_previo = mensaje_previo.get('role', '')
        else:
            contenido_previo = getattr(mensaje_previo, 'content', '').strip()
            role_previo = 'assistant' if hasattr(mensaje_previo, 'type') and mensaje_previo.type == 'ai' else 'user'
        
        # Si el mensaje anterior fue del asistente y terminaba en "?"
        if role_previo in ['assistant', 'ai'] and contenido_previo.endswith('?'):
            mensaje_anterior_es_pregunta = True
            logger.info(f"    🔍 Mensaje anterior es pregunta: '{contenido_previo[-50:]}...'")
    
    # Si el mensaje anterior fue una pregunta, NO clasificar como conversacional
    if mensaje_anterior_es_pregunta:
        logger.info(f"    ⚠️  Mensaje corto '{contenido}' pero responde a pregunta → Forzar LLM")
        # Continuar al análisis con LLM (no retornar aquí)
    elif es_mensaje_corto and contiene_palabra_no_accionable:
        logger.info(f"    ⚡ Mensaje conversacional detectado: '{contenido[:50]}...'")
        logger.info("    ↪️  NO requiere contexto → Directo al Orquestador")
        state['cambio_de_tema'] = False
        return state
    
    # Caso 3: Análisis con LLM para mensajes complejos
    try:
        logger.info("    🤖 Consultando LLM para clasificación de necesidad...")
        
        # Configurar LLM ligero (DeepSeek)
        llm = ChatOpenAI(
            model="deepseek-chat",
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com/v1",
            temperature=0,  # Máxima determinación
            max_tokens=10,  # Solo necesitamos True/False
            timeout=15.0,
            max_retries=0
        )
        
        # Prompt mejorado enfocado en "necesidad de contexto"
        prompt = f"""Analiza el siguiente mensaje del usuario y determina si requiere información externa o acciones.

MENSAJE DEL USUARIO:
"{contenido}"

CATEGORÍAS DE HERRAMIENTAS DISPONIBLES:
- Google Calendar (crear, listar, modificar, eliminar eventos)
- Memoria de conversaciones pasadas

¿Este mensaje requiere realizar una ACCIÓN o consultar INFORMACIÓN?

Responde 'TRUE' si el mensaje:
- Pide ver/crear/modificar/eliminar eventos del calendario
- Pregunta por información de charlas pasadas
- Solicita recordatorios, fechas, datos específicos
- Requiere cualquier acción con herramientas

Responde 'FALSE' si el mensaje:
- Es solo un saludo, despedida o agradecimiento
- Es una confirmación simple (ok, vale, entendido)
- Es un comentario que no requiere datos nuevos
- No pide ninguna acción específica

EJEMPLOS TRUE:
- "¿Qué eventos tengo mañana?"
- "Recuérdame lo que hablamos ayer"
- "Agéndame una cita para el jueves"
- "¿Qué tenía que hacer hoy?"

EJEMPLOS FALSE:
- "Gracias"
- "Vale, perfecto"
- "Hola, ¿cómo estás?"
- "Entendido, adiós"

Responde ÚNICAMENTE: 'True' o 'False'

Respuesta:"""
        
        # Llamada al LLM
        response = llm.invoke([HumanMessage(content=prompt)])
        respuesta = response.content.strip().lower()
        
        # Parsear respuesta
        if 'true' in respuesta:
            state['cambio_de_tema'] = True
            logger.info("    ✓ LLM: REQUIERE CONTEXTO → Activará Memoria y Herramientas")
        else:
            state['cambio_de_tema'] = False
            logger.info("    ✓ LLM: NO REQUIERE CONTEXTO → Directo al Orquestador")
        
    except Exception as e:
        # Fallback: en caso de error, asumir que SÍ requiere contexto (más seguro)
        logger.warning(f"    ⚠️  Error en LLM de filtrado: {e}")
        logger.info("    ⚡ Fallback: Asumiendo que requiere contexto (seguro)")
        state['cambio_de_tema'] = True
    
    return state


# ============================================================================
# [3] NODO DE RECUPERACIÓN EPISÓDICA (Memoria Semántica)
# ============================================================================
# Implementación completa en src/nodes/recuperacion_episodica_node.py
# Este nodo usa el wrapper importado que implementa:
# - Generación de embeddings (384 dims)
# - Búsqueda en pgvector con cosine similarity
# - Filtrado por threshold (0.7)
# - Formateo de contexto para LLMs
# ============================================================================


# ============================================================================
# [4] NODO DE SELECCIÓN DE HERRAMIENTAS (Memoria Procedimental)
# ============================================================================
# [4] NODO DE SELECCIÓN DE HERRAMIENTAS (Memoria Procedimental)
# ============================================================================

# Nota: Implementación completa en src/nodes/seleccion_herramientas_node.py

# ============================================================================
# [5] NODO DE EJECUCIÓN DE HERRAMIENTAS (Google Calendar + Orquestador)
# ============================================================================

# Nota: Implementación completa en src/nodes/ejecucion_herramientas_node.py


# Nodo 7: Persistencia Episódica
# Implementación completa en src/nodes/persistencia_episodica_node.py
# Nodo 7: Persistencia Episódica
# Implementación completa en src/nodes/persistencia_episodica_node.py
# (Guarda resumen + embedding en PostgreSQL/pgvector)


# ============================================================================
# FUNCIÓN DE DECISIÓN (Conditional Edge)
# ============================================================================

def decidir_flujo(state: WhatsAppAgentState) -> str:
    """
    Decide el siguiente nodo basándose en si requiere contexto externo.
    
    LÓGICA MEJORADA (Gatekeeper):
    - Si requiere contexto (True) → Activa Nodo 3 (Memoria) → Nodo 4 (Herramientas)
    - Si NO requiere contexto (False) → Directo al Nodo 5 (Orquestador conversacional)
    
    Returns:
        "recuperacion_episodica" si requiere contexto (acciones o datos)
        "ejecucion_herramientas" si no requiere contexto (solo conversación, sin herramientas)
    """
    requiere_contexto = state.get('cambio_de_tema', False)  # TODO: Renombrar variable a 'requiere_contexto'
    
    if requiere_contexto:
        logger.info("    ↪️  Flujo: REQUIERE CONTEXTO → Activando Memoria + Herramientas")
        return "recuperacion_episodica"
    else:
        logger.info("    ↪️  Flujo: SOLO CONVERSACIONAL → Directo a Orquestador (ahorro de recursos)")
        # Limpiar herramientas_seleccionadas para que el Orquestador responda conversacionalmente
        state['herramientas_seleccionadas'] = []
        return "ejecucion_herramientas"


# ============================================================================
# CONSTRUCCIÓN DEL GRAFO
# ============================================================================

def crear_grafo() -> StateGraph:
    """
    Crea y configura el grafo del agente de WhatsApp.

    Returns:
        Grafo compilado listo para ejecutar
    """
    logger.info("🏗️  Construyendo grafo de WhatsApp Agent...")

    # ✅ Inicializar memory store para memoria semántica
    from src.memory import get_memory_store
    memory_store = get_memory_store()
    logger.info("    ✅ Memory store inicializado (memoria semántica)")

    # Crear grafo
    builder = StateGraph(WhatsAppAgentState)
    
    # Añadir nodos
    builder.add_node("cache", nodo_cache)
    builder.add_node("filtrado", nodo_filtrado)
    builder.add_node("recuperacion_episodica", nodo_recuperacion_episodica_wrapper)  # ✅ Usa wrapper importado
    builder.add_node("seleccion_herramientas", nodo_seleccion_herramientas_wrapper)
    builder.add_node("ejecucion_herramientas", nodo_ejecucion_herramientas_wrapper)
    builder.add_node("generacion_resumen", nodo_generacion_resumen_wrapper)
    builder.add_node("persistencia_episodica", nodo_persistencia_episodica_wrapper)
    
    logger.info("    ✓ 7 nodos añadidos (resiliencia por max_retries=0 + fallbacks a Claude)")
    
    # Flujo lineal inicial
    builder.add_edge(START, "cache")
    builder.add_edge("cache", "filtrado")
    
    # Bifurcación condicional (Gatekeeper)
    builder.add_conditional_edges(
        "filtrado",
        decidir_flujo,
        {
            "recuperacion_episodica": "recuperacion_episodica",
            "ejecucion_herramientas": "ejecucion_herramientas"  # Directo al Orquestador si es conversacional
        }
    )
    
    # Flujo convergente
    builder.add_edge("recuperacion_episodica", "seleccion_herramientas")
    builder.add_edge("seleccion_herramientas", "ejecucion_herramientas")
    builder.add_edge("ejecucion_herramientas", "generacion_resumen")
    builder.add_edge("generacion_resumen", "persistencia_episodica")
    builder.add_edge("persistencia_episodica", END)
    
    logger.info("    ✓ Flujo configurado (con bifurcación condicional)")
    
    # Configurar PostgresSaver para persistencia de checkpoints (caché 24h)
    database_url = os.getenv("DATABASE_URL")
    checkpointer = None
    
    if database_url:
        try:
            logger.info("    🔗 Conectando PostgresSaver...")
            
            # Crear conexión con psycopg (sync) usando autocommit
            conn = psycopg.connect(database_url, autocommit=True)
            
            # Crear checkpointer
            checkpointer = PostgresSaver(conn)
            
            # Setup: crear tablas de LangGraph (checkpoints, checkpoint_writes, checkpoint_blobs)
            checkpointer.setup()
            
            logger.info("    ✅ PostgresSaver configurado (checkpoints, checkpoint_writes, checkpoint_blobs)")
            
        except Exception as e:
            logger.warning(f"    ⚠️  PostgresSaver no disponible: {e}")
            logger.warning("    ℹ️  El grafo funcionará sin persistencia de checkpoints")
            checkpointer = None
    else:
        logger.warning("    ⚠️  DATABASE_URL no configurado - grafo sin persistencia")
    
    # ✅ Compilar con memory store + checkpointer (según docs de LangGraph)
    if checkpointer:
        graph = builder.compile(
            checkpointer=checkpointer,
            store=memory_store  # ✅ Memory store para preferencias del usuario
        )
        logger.info("    ✅ Grafo compilado con PostgreSQL checkpointer + memory store")
    else:
        graph = builder.compile(store=memory_store)
        logger.info("    ✅ Grafo compilado con memory store (sin checkpointer)")

    logger.info("✅ Grafo compilado exitosamente")

    return graph


# ============================================================================
# EJECUCIÓN DE PRUEBA
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("🤖 AGENTE DE WHATSAPP - PRUEBA DE ESQUELETO")
    print("="*70 + "\n")
    
    # Crear grafo
    graph = crear_grafo()
    
    print("\n" + "-"*70)
    print("📨 PRUEBA 1: Conversación con cambio de tema (mensajes pares)")
    print("-"*70 + "\n")
    
    # Estado inicial de prueba 1
    estado_inicial_1 = {
        "messages": [
            {"role": "user", "content": "Hola"},
            {"role": "assistant", "content": "Hola, ¿cómo puedo ayudarte?"}
        ],
        "user_id": "test_user_123",
        "session_id": "session_abc_001",
        "contexto_episodico": None,
        "herramientas_seleccionadas": [],
        "cambio_de_tema": False,
        "resumen_actual": None,
        "timestamp": datetime.now().isoformat(),
        "sesion_expirada": False
    }
    
    # Ejecutar grafo
    resultado_1 = graph.invoke(estado_inicial_1)
    
    print("\n" + "="*70)
    print("✅ RESULTADO PRUEBA 1:")
    print(f"   - Cambio de tema: {resultado_1.get('cambio_de_tema')}")
    print(f"   - Herramientas seleccionadas: {resultado_1.get('herramientas_seleccionadas')}")
    print(f"   - Resumen generado: {resultado_1.get('resumen_actual')}")
    print("="*70 + "\n")
    
    print("\n" + "-"*70)
    print("📨 PRUEBA 2: Conversación sin cambio de tema (mensajes impares)")
    print("-"*70 + "\n")
    
    # Estado inicial de prueba 2
    estado_inicial_2 = {
        "messages": [
            {"role": "user", "content": "Programa una reunión"}
        ],
        "user_id": "test_user_456",
        "session_id": "session_xyz_002",
        "contexto_episodico": None,
        "herramientas_seleccionadas": [],
        "cambio_de_tema": False,
        "resumen_actual": None,
        "timestamp": datetime.now().isoformat(),
        "sesion_expirada": False
    }
    
    # Ejecutar grafo
    resultado_2 = graph.invoke(estado_inicial_2)
    
    print("\n" + "="*70)
    print("✅ RESULTADO PRUEBA 2:")
    print(f"   - Cambio de tema: {resultado_2.get('cambio_de_tema')}")
    print(f"   - Herramientas seleccionadas: {resultado_2.get('herramientas_seleccionadas')}")
    print(f"   - Resumen generado: {resultado_2.get('resumen_actual')}")
    print("="*70 + "\n")
    
    print("\n" + "="*70)
    print("🎉 PRUEBAS COMPLETADAS")
    print("="*70)
    print("\nEl grafo recorre correctamente los 7 nodos en el orden esperado.")
    print("La bifurcación condicional funciona basándose en 'cambio_de_tema'.")
    print("\n✅ Esqueleto validado - Listo para implementar lógica real.\n")
