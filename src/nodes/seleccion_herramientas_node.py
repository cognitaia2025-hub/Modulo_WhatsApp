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
from pydantic import BaseModel, Field
from langgraph.types import Command

from src.state.agent_state import WhatsAppAgentState
from src.database import get_herramientas_disponibles
from src.medical.tools import MEDICAL_TOOLS
from src.utils.logging_config import (
    log_separator, 
    log_node_io, 
    log_llm_interaction,
    log_user_message
)

load_dotenv()
logger = logging.getLogger(__name__)


# ==================== PYDANTIC MODEL ====================

class SeleccionHerramientas(BaseModel):
    """Respuesta estructurada del selector de herramientas."""
    
    herramientas_ids: List[str] = Field(
        description="Lista de IDs de herramientas a usar (ej: ['list_calendar_events'])"
    )
    
    razonamiento: str = Field(
        description="Breve explicación de por qué se eligieron estas herramientas"
    )


# ==================== CONSTANTES ====================

# Estados conversacionales que requieren saltar selección
ESTADOS_FLUJO_ACTIVO = [
    'ejecutando_herramienta',
    'esperando_confirmacion',
    'procesando_resultado',
    'recolectando_fecha',
    'recolectando_hora'
]


def obtener_herramientas_segun_clasificacion(
    clasificacion: str,
    tipo_usuario: str
) -> List[Dict[str, str]]:
    """
    Obtiene herramientas disponibles según clasificación del mensaje
    
    Args:
        clasificacion: Clasificación del mensaje ('personal', 'medica', 'chat', 'solicitud_cita_paciente')
        tipo_usuario: Tipo de usuario ('doctor', 'paciente_externo', etc.)
        
    Returns:
        Lista de herramientas disponibles
    """
    herramientas = []
    
    # Clasificación: personal → herramientas de calendario
    if clasificacion == "personal":
        herramientas = get_herramientas_disponibles()
    
    # Clasificación: medica → herramientas médicas (solo doctores)
    elif clasificacion == "medica":
        if tipo_usuario == "doctor":
            # Convertir herramientas médicas a formato compatible
            for tool in MEDICAL_TOOLS:
                herramientas.append({
                    'id_tool': tool.name,
                    'description': tool.description
                })
        else:
            logger.warning(f"⚠️  Usuario tipo '{tipo_usuario}' no puede usar herramientas médicas")
    
    # Clasificación: solicitud_cita_paciente → herramientas limitadas
    elif clasificacion == "solicitud_cita_paciente":
        # Solo herramientas de consulta y agendamiento
        for tool in MEDICAL_TOOLS:
            if tool.name in ["consultar_slots_disponibles", "agendar_cita_medica_completa"]:
                herramientas.append({
                    'id_tool': tool.name,
                    'description': tool.description
                })
    
    # Clasificación: chat → sin herramientas
    elif clasificacion == "chat":
        herramientas = []
    
    logger.info(f"  📦 Herramientas para '{clasificacion}': {len(herramientas)}")
    return herramientas


# LLM primario: DeepSeek con structured output
llm_primary_base = ChatOpenAI(
    model="deepseek-chat",
    temperature=0,
    max_tokens=200,  # Aumentado para JSON estructurado
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1",
    timeout=10.0,  # ✅ Reducido de 20s a 10s
    max_retries=0
)

llm_fallback_base = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    temperature=0,
    max_tokens=200,
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    timeout=10.0,  # ✅ Reducido de 15s a 10s
    max_retries=0
)

# Configurar structured output (sin json_schema para compatibilidad)
llm_primary = llm_primary_base.with_structured_output(
    SeleccionHerramientas,
    method="json_mode"
)

llm_fallback = llm_fallback_base.with_structured_output(
    SeleccionHerramientas
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
    Construye prompt optimizado para selección de herramientas.
    
    MEJORAS:
    ✅ Prompt más corto y directo
    ✅ Enfocado en IDs exactos
    ✅ Sin números ni índices
    """
    # Formatear herramientas
    herramientas_str = "\n".join([
        f"• {h['id_tool']}: {h['description']}"
        for h in herramientas
    ])
    
    # Contexto episódico si existe
    contexto_str = ""
    if contexto_episodico and contexto_episodico.get('episodios_recuperados'):
        episodios = contexto_episodico.get('texto_formateado', '')[:300]  # Truncar
        contexto_str = f"\n\nContexto relevante:\n{episodios}\n"
    
    prompt = f"""Selecciona las herramientas necesarias para esta solicitud.

HERRAMIENTAS DISPONIBLES:
{herramientas_str}

MENSAJE DEL USUARIO:
"{mensaje_usuario}"{contexto_str}

REGLAS:
1. Retorna SOLO los IDs exactos de las herramientas (ej: "list_calendar_events")
2. Si necesitas varias herramientas, inclúyelas en la lista
3. Si NO necesitas ninguna herramienta, retorna lista vacía
4. Usa el ID exacto como aparece arriba (sensible a mayúsculas)

EJEMPLOS:
- "¿Qué eventos tengo?" → ["list_calendar_events"]
- "Agendar cita mañana" → ["create_calendar_event"]
- "Hola" → []

Retorna JSON con herramientas_ids y razonamiento."""
    
    return prompt


def nodo_seleccion_herramientas(state: WhatsAppAgentState) -> Command:
    """
    Nodo 4: Selecciona herramientas basándose en la conversación y clasificación
    
    MEJORAS APLICADAS:
    ✅ Command pattern con routing directo
    ✅ Pydantic structured output
    ✅ Detección de estado conversacional
    ✅ Timeout reducido (10s)
    
    Flujo:
    1. Verifica estado conversacional (saltar si activo)
    2. Obtiene clasificación y tipo de usuario
    3. Obtiene herramientas según clasificación
    4. Consulta LLM para selección inteligente
    5. Valida herramientas seleccionadas
    6. Actualiza state['herramientas_seleccionadas']
    
    Returns:
        Command con update y goto
    """
    log_separator(logger, "NODO_4_SELECCION_HERRAMIENTAS", "INICIO")
    
    # Log del input
    state_input = f"messages: {len(state.get('messages', []))} mensajes\ncontexto: {bool(state.get('contexto_episodico'))}"
    log_node_io(logger, "INPUT", "NODO_4_SELECCION", state_input)
    
    # ✅ NUEVA VALIDACIÓN: Detectar estado conversacional
    estado_conversacion = state.get('estado_conversacion', 'inicial')
    
    if estado_conversacion in ESTADOS_FLUJO_ACTIVO:
        logger.info(f"   🔄 Flujo activo detectado (estado: {estado_conversacion}) - Saltando selección")
        return Command(
            update={'herramientas_seleccionadas': []},
            goto="ejecucion_herramientas"
        )
    
    try:
        # 1. Obtener clasificación y tipo de usuario
        clasificacion = state.get('clasificacion_mensaje', 'personal')
        tipo_usuario = state.get('tipo_usuario', 'paciente_externo')
        
        logger.info(f"    📊 Clasificación: {clasificacion}")
        logger.info(f"    👤 Tipo usuario: {tipo_usuario}")
        
        # 2. Obtener herramientas según clasificación
        herramientas = obtener_herramientas_segun_clasificacion(
            clasificacion=clasificacion,
            tipo_usuario=tipo_usuario
        )
        
        # Si es chat o sin herramientas
        if clasificacion == "chat" or not herramientas:
            logger.info("    ℹ️  Sin herramientas necesarias")
            return Command(
                update={'herramientas_seleccionadas': []},
                goto="generacion_resumen"
            )
        
        logger.info(f"    📦 Herramientas disponibles: {len(herramientas)}")
        
        # 3. Extraer último mensaje
        mensaje_usuario = extraer_ultimo_mensaje_usuario(state)
        
        if not mensaje_usuario:
            logger.warning("    ⚠️  Sin mensaje del usuario")
            return Command(
                update={'herramientas_seleccionadas': []},
                goto="generacion_resumen"
            )
        
        log_user_message(logger, mensaje_usuario)
        
        # 4. Obtener contexto episódico
        contexto = state.get('contexto_episodico')
        tiene_contexto = contexto and contexto.get('episodios_recuperados')
        logger.info(f"    📖 Contexto disponible: {tiene_contexto}")
        
        # 5. Construir prompt
        prompt = construir_prompt_seleccion(
            mensaje_usuario=mensaje_usuario,
            herramientas=herramientas,
            contexto_episodico=contexto
        )
        
        # 6. Consultar LLM (retorna Pydantic model)
        logger.info("    🤖 Consultando LLM para selección...")
        
        seleccion = llm_selector.invoke(prompt)  # ✅ Retorna SeleccionHerramientas
        
        # Log de interacción
        log_llm_interaction(
            logger, 
            "DeepSeek/Claude", 
            prompt, 
            f"IDs: {seleccion.herramientas_ids}, Razonamiento: {seleccion.razonamiento}",
            truncate_prompt=800,
            truncate_response=200
        )
        
        # 7. Validar herramientas seleccionadas contra disponibles
        ids_validos = [h['id_tool'] for h in herramientas]
        ids_seleccionados = []
        
        for tool_id in seleccion.herramientas_ids:
            if tool_id in ids_validos:
                ids_seleccionados.append(tool_id)
            else:
                logger.warning(f"    ⚠️  Herramienta '{tool_id}' no disponible, ignorando")
        
        logger.info(f"    ✅ Herramientas seleccionadas: {ids_seleccionados}")
        
        # Log del output
        output_data = f"herramientas: {ids_seleccionados}"
        log_node_io(logger, "OUTPUT", "NODO_4_SELECCION", output_data)
        log_separator(logger, "NODO_4_SELECCION_HERRAMIENTAS", "FIN")
        
        # ✅ Retornar Command
        return Command(
            update={'herramientas_seleccionadas': ids_seleccionados},
            goto="ejecucion_herramientas"
        )
        
    except Exception as e:
        # Fallback según clasificación
        logger.error(f"    ❌ Error en selección: {e}")
        logger.info("    🔄 Usando herramientas por defecto")
        
        clasificacion = state.get('clasificacion_mensaje', 'personal')
        fallback_tools = []
        
        if clasificacion == "personal":
            fallback_tools = ['list_calendar_events']
        elif clasificacion in ["medica", "solicitud_cita_paciente"]:
            fallback_tools = ['consultar_slots_disponibles']
        
        log_separator(logger, "NODO_4_SELECCION_HERRAMIENTAS", "FIN")
        
        return Command(
            update={'herramientas_seleccionadas': fallback_tools},
            goto="ejecucion_herramientas"
        )


# Wrapper para compatibilidad con grafo
def nodo_seleccion_herramientas_wrapper(state: WhatsAppAgentState) -> Command:
    """Wrapper para LangGraph - retorna Command directamente."""
    return nodo_seleccion_herramientas(state)
