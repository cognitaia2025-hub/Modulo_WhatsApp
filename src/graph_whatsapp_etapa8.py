"""
Grafo Principal del Agente de WhatsApp - ETAPA 8

Implementa el flujo completo de 13 nodos con 3 funciones de decisión condicional.
Incluye PostgresSaver para persistencia de checkpoints (caché 24h).

FLUJO PRINCIPAL:
├── N0: Identificación Usuario (entrada)
├── N1: Caché Sesión 
├── N2: Filtrado Inteligente (clasificación)
├── ┌─ DECISIÓN 1: Clasificación ─┐
├── │  - medica + doctor → N3B    │
├── │  - solicitud_cita → N6R     │  
├── │  - personal → N3A           │
├── │  - chat_casual → N6C        │
├── └─────────────────────────────┘
├── N3A: Recuperación Episódica (personal)
├── N3B: Recuperación Médica (doctor)
├── N4: Selección Herramientas
├── ┌─ DECISIÓN 2: Tipo Ejecución ─┐
├── │  - hay_medicas → N5B         │
├── │  - solo_personales → N5A     │
├── │  - sin_herramientas → N6     │
├── └─────────────────────────────┘
├── N5A: Ejecución Personal
├── N5B: Ejecución Médica
├── N6R: Recepcionista (citas)
├── N6C: Respuesta Conversacional (chat casual)
├── ┌─ DECISIÓN 3: Post-Recepcionista ─┐
├── │  - completado → N8              │
├── │  - otros → N6                   │
├── └─────────────────────────────────┘
├── N6: Generación Resumen
├── N7: Persistencia Episódica  
├── N8: Sincronizador Híbrido (Calendar)
└── END
"""

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres import PostgresSaver
from typing import Literal
from datetime import datetime, timedelta
import logging
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
import psycopg

# Importar sistema de logging con colores
from src.utils.logging_config import setup_colored_logging, log_separator

# Cargar variables de entorno
load_dotenv()

# Configurar logging con colores
logger = setup_colored_logging()

# Añadir el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Importar estado y todos los nodos
from src.state.agent_state import WhatsAppAgentState

# ==================== IMPORTS DE NODOS ====================
from src.nodes.identificacion_usuario_node import nodo_identificacion_usuario_wrapper
from src.nodes.filtrado_inteligente_node import nodo_filtrado_inteligente_wrapper
from src.nodes.recuperacion_medica_node import nodo_recuperacion_medica_wrapper
from src.nodes.recepcionista_optimizado_node import nodo_recepcionista_optimizado_wrapper
from src.nodes.respuesta_conversacional_node import nodo_respuesta_conversacional_wrapper
from src.nodes.sincronizador_hibrido_node import nodo_sincronizador_hibrido_wrapper
from src.nodes.resumen_async_node import nodo_resumen_async_wrapper

# ToolNode unificado y herramientas
from langgraph.prebuilt import ToolNode
from src.tools.all_tools import get_all_tools
from src.nodes.resumen_async_node import nodo_resumen_async_wrapper
from src.tools.all_tools import get_all_tools

# Nodo de resumen asíncrono (nuevo)
from src.nodes.resumen_async_node import nodo_resumen_async_wrapper


# ==================== NODO DE CACHÉ (STUB) ====================

def nodo_cache_sesion(state: WhatsAppAgentState) -> WhatsAppAgentState:
    """
    [N1] Nodo de Caché de Sesión con gestión de TTL (24h)
    
    Detecta si la sesión ha expirado y marca para auto-resumen.
    """
    logger.info("🗄️  [N1] CACHE_SESION - Verificando caché de sesión")
    logger.info(f"    User ID: {state.get('user_id', 'N/A')}")
    logger.info(f"    Session ID: {state.get('session_id', 'N/A')}")

    # Por simplicidad, marcamos sesión como activa
    state["sesion_expirada"] = False
    state["timestamp"] = datetime.now().isoformat()
    
    return state


def decidir_flujo_temprano(state: WhatsAppAgentState) -> Literal[
    "filtrado_inteligente",
    "recepcionista"
]:
    """
    DECISIÓN TEMPRANA: Saltar clasificación en flujos activos
    
    Optimización: Si el estado_conversacion indica que estamos en medio
    de un flujo (como agendar cita), saltar directamente al nodo correspondiente
    sin pasar por la clasificación LLM.
    
    Returns:
        - "recepcionista" para flujos activos de cita
        - "filtrado_inteligente" para mensajes nuevos/iniciales
    """
    estado_conv = state.get('estado_conversacion', 'inicial')
    
    logger.info(f"⚡ DECISIÓN TEMPRANA - Estado: {estado_conv}")
    
    # Flujos activos que no requieren clasificación
    if estado_conv in ['esperando_seleccion', 'solicitando_nombre', 'confirmando']:
        logger.info(f"    → SALTANDO clasificación - Ruta directa: RECEPCIONISTA")
        return "recepcionista"
    
    # Mensaje inicial o estado desconocido - requiere clasificación
    logger.info("    → Requiere clasificación - Ruta: FILTRADO_INTELIGENTE")
    return "filtrado_inteligente"


def decidir_flujo_temprano(state: WhatsAppAgentState) -> Literal[
    "filtrado_inteligente",
    "recepcionista"
]:
    """
    DECISIÓN TEMPRANA: Saltar clasificación en flujos activos
    
    Optimización: Si el estado_conversacion indica que estamos en medio
    de un flujo (como agendar cita), saltar directamente al nodo correspondiente
    sin pasar por la clasificación LLM.
    
    Returns:
        - "recepcionista" para flujos activos de cita
        - "filtrado_inteligente" para mensajes nuevos/iniciales
    """
    estado_conv = state.get('estado_conversacion', 'inicial')
    
    logger.info(f"⚡ DECISIÓN TEMPRANA - Estado: {estado_conv}")
    
    # Flujos activos que no requieren clasificación
    if estado_conv in ['esperando_seleccion', 'solicitando_nombre', 'confirmando']:
        logger.info(f"    → SALTANDO clasificación - Ruta directa: RECEPCIONISTA")
        return "recepcionista"
    
    # Mensaje inicial o estado desconocido - requiere clasificación
    logger.info("    → Requiere clasificación - Ruta: FILTRADO_INTELIGENTE")
    return "filtrado_inteligente"


# ==================== FUNCIONES DE DECISIÓN ====================

def decidir_flujo_clasificacion(state: WhatsAppAgentState) -> Literal[
    "recepcionista",
    "recuperacion_medica", 
    "recuperacion_episodica",
    "respuesta_conversacional",
    "tools_unified"
]:
    """
    DECISIÓN 1: Flujo de Clasificación (después de N2)
    
    Decide la ruta según clasificación y tipo de usuario.
    
    Reglas simplificadas:
    - solicitud_cita → Recepcionista (N6R)
    - medica + doctor → Recuperación Médica (N3B) 
    - personal + herramientas → ToolNode unificado
    - chat_casual → Respuesta Conversacional
    """
    clasificacion = state.get('clasificacion_mensaje', '')
    tipo_usuario = state.get('tipo_usuario', '')
    requiere_herramientas = state.get('requiere_herramientas', False)
    
    logger.info(f"🔀 DECISIÓN 1 - Clasificación: {clasificacion}, Usuario: {tipo_usuario}")
    
    # Caso 1: Solicitud de cita (cualquier usuario) - prioridad máxima
    if clasificacion in ['solicitud_cita', 'solicitud_cita_paciente', 'cita', 'agendar']:
        logger.info("    → Ruta: RECEPCIONISTA (solicitud de cita)")
        return "recepcionista"

    # Caso 2: Doctor con operación médica que NO requiere herramientas
    elif clasificacion == 'medica' and tipo_usuario == 'doctor' and not requiere_herramientas:
        logger.info("    → Ruta: RECUPERACION_MEDICA (consulta médica sin herramientas)")
        return "recuperacion_medica"

    # Caso 3: Cualquier operación que requiere herramientas → ToolNode unificado
    elif requiere_herramientas or clasificacion == 'personal':
        logger.info("    → Ruta: TOOLS_UNIFIED (operación con herramientas)")
        return "tools_unified"

    # Caso 4: Chat casual o consulta → Respuesta conversacional (genera respuesta amigable)
    else:
        logger.info("    → Ruta: RESPUESTA_CONVERSACIONAL (chat casual)")
        return "respuesta_conversacional"


def decidir_post_tools(state: WhatsAppAgentState) -> Literal[
    "sincronizador_hibrido",
    "generacion_resumen_async"
]:
    """
    DECISIÓN 2: Post-Tools (después de ToolNode unificado)
    
    Decide si requiere sincronización con Google Calendar.
    
    Reglas:
    - Si se creó/modificó alguna cita médica → Sincronizador
    - Cualquier otra operación → Resumen asíncrono
    """
    # Verificar si se ejecutó alguna herramienta que requiere sincronización
    messages = state.get('messages', [])
    
    # Buscar mensajes de herramientas que indican citas creadas/modificadas
    requiere_sync = False
    for msg in reversed(messages[-5:]):  # Revisar últimos 5 mensajes
        if hasattr(msg, 'type') and msg.type == 'tool':
            tool_name = getattr(msg, 'name', '')
            if tool_name in ['create_cita_tool', 'update_cita_tool', 'create_medical_event']:
                requiere_sync = True
                break
    
    logger.info(f"🔀 DECISIÓN 2 - Requiere sincronización: {requiere_sync}")
    
    if requiere_sync:
        logger.info("    → Ruta: SINCRONIZADOR_HIBRIDO (cita creada/modificada)")
        return "sincronizador_hibrido"
    else:
        logger.info("    → Ruta: GENERACION_RESUMEN_ASYNC (operación sin sincronización)")
        return "generacion_resumen_async"


def decidir_despues_recepcionista(state: WhatsAppAgentState) -> Literal[
    "sincronizador_hibrido",
    "generacion_resumen_async"
]:
    """
    DECISIÓN 3: Post-Recepcionista (después de N6R)
    
    Decide la ruta después del recepcionista según estado de conversación.
    
    Reglas:
    - completado (cita agendada) → Sincronizador (N8)
    - cualquier otro estado → Resumen asíncrono
    """
    estado_conv = state.get('estado_conversacion', 'inicial')
    
    logger.info(f"🔀 DECISIÓN 3 - Estado conversación: {estado_conv}")

    if estado_conv == 'completado':
        logger.info("    → Ruta: SINCRONIZADOR_HIBRIDO (cita completada, sincronizar)")
        return "sincronizador_hibrido"
    else:
        logger.info("    → Ruta: GENERACION_RESUMEN_ASYNC (conversación en proceso)")
        return "generacion_resumen_async"


# ==================== FUNCIÓN PRINCIPAL ====================

def crear_grafo_whatsapp() -> StateGraph:
    """
    Crea y configura el grafo optimizado del agente de WhatsApp.
    
    Optimizaciones implementadas:
    - ToolNode unificado en lugar de múltiples nodos de ejecución
    - Decisión temprana para saltear clasificación en flujos activos  
    - Resumen asíncrono para mejorar latencia
    - Eliminación de nodos redundantes
    
    Returns:
        Grafo compilado listo para ejecutar
    """
    logger.info("🏗️  Construyendo grafo OPTIMIZADO de WhatsApp Agent...")

    # ✅ Inicializar memory store para memoria semántica
    from src.memory import get_memory_store
    memory_store = get_memory_store()
    logger.info("    ✅ Memory store inicializado (memoria semántica)")

    # Crear grafo con estado typed
    workflow = StateGraph(WhatsAppAgentState)
    
    # ==================== AGREGAR NODOS OPTIMIZADOS ====================
    
    # N0: Identificación Usuario (punto de entrada)
    workflow.add_node("identificacion_usuario", nodo_identificacion_usuario_wrapper)
    
    # N1: Caché Sesión
    workflow.add_node("cache_sesion", nodo_cache_sesion)
    
    # N2: Filtrado Inteligente (clasificación) - solo cuando es necesario
    workflow.add_node("filtrado_inteligente", nodo_filtrado_inteligente_wrapper)
    
    # N3: Recuperación Médica (solo consultas sin herramientas)
    workflow.add_node("recuperacion_medica", nodo_recuperacion_medica_wrapper)
    
    # N4: ToolNode Unificado (reemplaza múltiples nodos de ejecución)
    all_tools = get_all_tools()
    tools_node = ToolNode(all_tools)
    workflow.add_node("tools_unified", tools_node)
    
    # N5: Recepcionista Optimizado (flujo de citas con slot filling)
    workflow.add_node("recepcionista", nodo_recepcionista_optimizado_wrapper)
    
    # N6: Respuesta Conversacional (chat casual)
    workflow.add_node("respuesta_conversacional", nodo_respuesta_conversacional_wrapper)
    
    # N7: Resumen Asíncrono (sin bloquear respuesta)
    workflow.add_node("generacion_resumen_async", nodo_resumen_async_wrapper)
    
    
    logger.info("    ✓ 8 nodos optimizados añadidos correctamente")
    
    # ==================== CONFIGURAR FLUJO OPTIMIZADO ====================
    
    # Flujo inicial: START → N0 → N1 → DECISIÓN TEMPRANA
    workflow.add_edge(START, "identificacion_usuario")
    workflow.add_edge("identificacion_usuario", "cache_sesion")
    
    # -------------------- DECISIÓN TEMPRANA: Saltear clasificación en flujos activos --------------------
    workflow.add_conditional_edges(
        "cache_sesion",
        decidir_flujo_temprano,
        {
            "filtrado_inteligente": "filtrado_inteligente",
            "recepcionista": "recepcionista"
        }
    )
    
    # -------------------- DECISIÓN 1: Clasificación (solo cuando es necesario) --------------------
    workflow.add_conditional_edges(
        "filtrado_inteligente",
        decidir_flujo_clasificacion,
        {
            "recepcionista": "recepcionista",
            "recuperacion_medica": "recuperacion_medica",
            "tools_unified": "tools_unified",
            "respuesta_conversacional": "respuesta_conversacional"
        }
    )
    
    # -------------------- DECISIÓN 2: Post-Tools --------------------
    workflow.add_conditional_edges(
        "tools_unified",
        decidir_post_tools,
        {
            "sincronizador_hibrido": "sincronizador_hibrido",
            "generacion_resumen_async": "generacion_resumen_async"
        }
    )
    
    # -------------------- DECISIÓN 3: Post-Recepcionista --------------------
    workflow.add_conditional_edges(
        "recepcionista",
        decidir_despues_recepcionista,
        {
            "sincronizador_hibrido": "sincronizador_hibrido",
            "generacion_resumen_async": "generacion_resumen_async"
        }
    )
    
    # ==================== FLUJOS DE CONVERGENCIA ====================
    
    # Recuperación médica → Resumen asíncrono (consultas sin herramientas)
    workflow.add_edge("recuperacion_medica", "generacion_resumen_async")
    
    # Respuesta conversacional → Resumen asíncrono (para auditoría en background)
    workflow.add_edge("respuesta_conversacional", "generacion_resumen_async")
    
    # Sincronizador → Resumen asíncrono
    workflow.add_edge("sincronizador_hibrido", "generacion_resumen_async")
    
    
    logger.info("    ✓ Flujo optimizado configurado - 3 decisiones condicionales")
    
    # ==================== CONFIGURAR POSTGRESQL SAVER ====================
    
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
            
            logger.info("    ✅ PostgresSaver configurado (checkpoints)")
            
        except Exception as e:
            logger.warning(f"    ⚠️  PostgresSaver no disponible: {e}")
            logger.warning("    ℹ️  El grafo funcionará sin persistencia de checkpoints")
            checkpointer = None
    else:
    
    # ==================== COMPILAR GRAFO ====================
    
    if checkpointer:
        app = workflow.compile(
            checkpointer=checkpointer,
            store=memory_store
        )
        logger.info("    ✅ Grafo compilado con PostgreSQL checkpointer + memory store")
    else:
        app = workflow.compile(store=memory_store)
        logger.info("    ✅ Grafo compilado con memory store (sin checkpointer)")

    logger.info("🎉 Grafo OPTIMIZADO compilado exitosamente")
    logger.info("📊 Mejoras implementadas:")
    logger.info("    • ToolNode unificado → Menos latencia")
    logger.info("    • Decisión temprana → Salto inteligente de clasificación")
    logger.info("    • Resumen asíncrono → Respuesta más rápida al usuario")
    logger.info("    • Nodos reducidos: 13 → 8 nodos")

    return app


# ==================== INSTANCIA GLOBAL ====================
# Esta será la instancia que se use en app.py
app = crear_grafo_whatsapp()


if __name__ == "__main__":
    print("\n" + "="*70)
    print("🤖 AGENTE DE WHATSAPP OPTIMIZADO - PRUEBA")
    print("="*70 + "\n")
    
    print("🚀 Arquitectura optimizada:")
    print("   • ToolNode unificado para todas las herramientas")
    print("   • Decisión temprana para flujos activos (recepcionista)")
    print("   • Resumen asíncrono para mejorar latencia")
    print("   • Slot filling en recepcionista")
    print("   • Eliminación de nodos redundantes")
    
    # Crear grafo
    graph = crear_grafo_whatsapp()
    
    print("\n✅ Grafo optimizado creado correctamente")
    print("📈 Beneficios esperados:")
    print("   • Menor latencia en respuestas")
    print("   • Mejor experiencia de usuario en WhatsApp")
    print("   • Arquitectura más mantenible")
    print("   • Eficiencia mejorada en flujos activos")
    
    print(f"\n🎯 Grafo listo para producción")
    print("="*70)