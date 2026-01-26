"""
Nodo 4: Selección Inteligente de Herramientas (Memoria Procedimental)

Este nodo determina qué herramientas de Google Calendar necesita el agente
basándose en la conversación y el contexto episódico.

Estrategia:
1. Consulta PostgreSQL (herramientas_disponibles) con caché de 5 minutos
2. Usa LLM (DeepSeek) para analizar intención del usuario
3. Selecciona herramientas relevantes comparando con descripciones
4. Actualiza state['herramientas_seleccionadas']
"""

import logging
from typing import Dict, List
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from dotenv import load_dotenv
import os

from src.state.agent_state import WhatsAppAgentState
from src.database import get_herramientas_disponibles
from src.utils.logging_config import (
    log_separator, 
    log_node_io, 
    log_llm_interaction,
    log_user_message
)

load_dotenv()
logger = logging.getLogger(__name__)

# LLM principal para selección (DeepSeek)
llm_primary = ChatOpenAI(
    model="deepseek-chat",
    temperature=0,
    max_tokens=100,
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1",
    timeout=20.0,
    max_retries=0  # ✅ Reintentos los maneja LangGraph
)

# Fallback: Claude Haiku 4.5
llm_fallback = ChatAnthropic(
    model="claude-3-5-haiku-20241022",
    temperature=0,
    max_tokens=100,
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    timeout=15.0,
    max_retries=0
)

# Selector con fallback automático
llm_selector = llm_primary.with_fallbacks([llm_fallback])


def extraer_ultimo_mensaje_usuario(state: WhatsAppAgentState) -> str:
    """
    Extrae el último mensaje del usuario desde el historial
    
    Returns:
        String con el mensaje o cadena vacía
    """
    mensajes = state.get('messages', [])
    
    # Buscar último mensaje de rol 'user'
    for mensaje in reversed(mensajes):
        if isinstance(mensaje, dict):
            if mensaje.get('role') == 'user':
                return mensaje.get('content', '')
        elif hasattr(mensaje, 'type'):
            if mensaje.type == 'human':
                return mensaje.content
    
    return ""


def construir_prompt_seleccion(
    mensaje_usuario: str,
    herramientas: List[Dict[str, str]],
    contexto_episodico: Dict = None
) -> str:
    """
    Construye el prompt para el LLM de selección de herramientas
    
    Args:
        mensaje_usuario: Último mensaje del usuario
        herramientas: Lista de dicts con id_tool y description
        contexto_episodico: Contexto histórico (opcional)
        
    Returns:
        Prompt estructurado para el LLM
    """
    # Formatear herramientas disponibles SIN NUMERACIÓN (usar viñetas)
    herramientas_str = "\n".join([
        f"• {h['id_tool']} — {h['description']}"
        for h in herramientas
    ])
    
    # Agregar contexto episódico si existe
    contexto_str = ""
    if contexto_episodico and contexto_episodico.get('episodios_recuperados'):
        contexto_str = f"\n\nContexto histórico relevante:\n{contexto_episodico.get('texto_formateado', '')}\n"
    
    prompt = f"""Eres un selector de herramientas de calendario. Tu trabajo es ÚNICAMENTE responder con el ID exacto de la herramienta.

HERRAMIENTAS DISPONIBLES:
{herramientas_str}

MENSAJE DEL USUARIO:
"{mensaje_usuario}"{contexto_str}

REGLAS ESTRICTAS:
1. NO utilices números, índices ni explicaciones
2. Responde ÚNICAMENTE con el ID exacto de la herramienta (ej: list_calendar_events)
3. Si necesitas múltiples herramientas, sepáralas con comas sin espacios
4. Si NO estás seguro o NO se necesita ninguna herramienta, responde: NONE
5. Tu respuesta debe contener SOLO el ID de la herramienta, nada más

GUÍA RÁPIDA:
- ¿Pregunta por agenda/eventos? → list_calendar_events
- ¿Crear/agendar evento? → create_calendar_event
- ¿Modificar hora/detalles? → update_calendar_event
- ¿Eliminar evento? → delete_calendar_event
- ¿Buscar eventos? → search_calendar_events
- ¿Sin acción de calendario? → NONE

RESPUESTA (solo ID o NONE):"""
    
    return prompt


def parsear_respuesta_llm(respuesta: str, herramientas_disponibles: List[Dict[str, str]]) -> List[str]:
    """
    Parsea la respuesta del LLM a lista de IDs con robustez contra errores comunes
    
    Args:
        respuesta: String del LLM (ej: "list_calendar_events" o "1")
        herramientas_disponibles: Lista de herramientas con id_tool para mapeo
        
    Returns:
        Lista de IDs limpia (ej: ['list_calendar_events'])
    """
    # Limpieza profunda: quitar espacios, saltos de línea, comillas
    respuesta = respuesta.strip().replace('\n', '').replace('"', '').replace("'", '')
    
    logger.info(f"    [DEBUG] Respuesta limpia: '{respuesta}'")
    
    # Caso: No necesita herramientas
    if respuesta.upper() == "NONE" or respuesta == "":
        logger.info("    [DEBUG] Sin herramientas (NONE)")
        return []
    
    # MAPEO DE SEGURIDAD: Si el LLM responde con número, mapearlo al ID
    if respuesta.isdigit():
        indice = int(respuesta) - 1  # "1" → índice 0
        if 0 <= indice < len(herramientas_disponibles):
            id_mapeado = herramientas_disponibles[indice]['id_tool']
            logger.warning(f"    ⚠️  LLM respondió con número '{respuesta}', mapeando a '{id_mapeado}'")
            return [id_mapeado]
        else:
            logger.error(f"    ❌ Índice '{respuesta}' fuera de rango (max: {len(herramientas_disponibles)})")
            return []
    
    # Limpiar y separar por comas
    ids = [
        id_tool.strip().lower()
        for id_tool in respuesta.split(',')
        if id_tool.strip()
    ]
    
    # Validar contra IDs reales en la base de datos
    ids_validos_db = [h['id_tool'] for h in herramientas_disponibles]
    logger.info(f"    [DEBUG] IDs Válidos en DB: {ids_validos_db}")
    
    ids_finales = []
    for id_tool in ids:
        if id_tool in ids_validos_db:
            ids_finales.append(id_tool)
        else:
            logger.warning(f"    ⚠️  ID '{id_tool}' no existe en DB, ignorando")
    
    return ids_finales


def nodo_seleccion_herramientas(state: WhatsAppAgentState) -> Dict:
    """
    Nodo 4: Selecciona herramientas de Google Calendar basándose en la conversación
    
    Flujo:
    1. Obtiene herramientas disponibles (con caché de 5 min)
    2. Extrae último mensaje del usuario
    3. Consulta LLM para selección inteligente
    4. Parsea respuesta a lista de IDs
    5. Actualiza state['herramientas_seleccionadas']
    
    Args:
        state: WhatsAppAgentState con mensajes y contexto
        
    Returns:
        Dict con 'herramientas_seleccionadas': List[str]
    """
    log_separator(logger, "NODO_4_SELECCION_HERRAMIENTAS", "INICIO")
    
    # Log del input del nodo
    state_input = f"messages: {len(state.get('messages', []))} mensajes\ncontexto_episodico: {bool(state.get('contexto_episodico'))}"
    log_node_io(logger, "INPUT", "NODO_4_SELECCION", state_input)
    
    try:
        # 1. Obtener herramientas disponibles (usa caché si está vigente)
        herramientas = get_herramientas_disponibles()
        logger.info(f"    📦 Herramientas disponibles: {len(herramientas)}")
        
        # 2. Extraer último mensaje del usuario
        mensaje_usuario = extraer_ultimo_mensaje_usuario(state)
        
        if not mensaje_usuario:
            logger.warning("    ⚠️  No se encontró mensaje del usuario")
            return {'herramientas_seleccionadas': []}
        
        log_user_message(logger, mensaje_usuario)
        
        # 3. Obtener contexto episódico si existe
        contexto = state.get('contexto_episodico')
        tiene_contexto = contexto and contexto.get('episodios_recuperados')
        
        logger.info(f"    📖 Contexto episódico disponible: {tiene_contexto}")
        
        # 4. Construir prompt para LLM
        prompt = construir_prompt_seleccion(
            mensaje_usuario=mensaje_usuario,
            herramientas=herramientas,
            contexto_episodico=contexto
        )
        
        # 5. Consultar LLM para selección inteligente
        logger.info("    🤖 Consultando LLM para selección...")
        
        respuesta = llm_selector.invoke(prompt)
        respuesta_texto = respuesta.content.strip()
        
        # Log detallado de interacción con LLM
        log_llm_interaction(logger, "DeepSeek/Claude", prompt, respuesta_texto, truncate_prompt=800, truncate_response=200)
        
        # 6. Parsear respuesta a lista de IDs con mapeo robusto
        ids_seleccionados = parsear_respuesta_llm(respuesta_texto, herramientas)
        
        logger.info(f"    ✅ Herramientas seleccionadas: {ids_seleccionados}")
        
        # Log del output del nodo
        output_data = f"herramientas_seleccionadas: {ids_seleccionados}"
        log_node_io(logger, "OUTPUT", "NODO_4_SELECCION", output_data)
        log_separator(logger, "NODO_4_SELECCION_HERRAMIENTAS", "FIN")
        
        return {
            'herramientas_seleccionadas': ids_seleccionados
        }
        
    except Exception as e:
        # Fallback: selección por defecto (list + create)
        logger.error(f"    ❌ Error en selección de herramientas: {e}")
        logger.info("    🔄 Usando herramientas por defecto (fallback)")
        
        log_separator(logger, "NODO_4_SELECCION_HERRAMIENTAS", "FIN")
        
        return {
            'herramientas_seleccionadas': ['list_calendar_events', 'create_calendar_event']
        }


# Wrapper para compatibilidad con grafo
def nodo_seleccion_herramientas_wrapper(state: WhatsAppAgentState) -> WhatsAppAgentState:
    """
    Wrapper que mantiene la firma esperada por el grafo
    """
    resultado = nodo_seleccion_herramientas(state)
    
    # Actualizar estado
    state['herramientas_seleccionadas'] = resultado['herramientas_seleccionadas']
    
    return state
