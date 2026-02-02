"""
Nodo 5A: Ejecución de Herramientas y Orquestador

Este nodo es el corazón de la acción del agente:
1. Ejecuta herramientas de Google Calendar
2. Usa el Orquestador (LLM) para generar respuestas naturales
3. Integra contexto de tiempo de Mexicali
4. Maneja errores de forma amigable

MEJORAS APLICADAS (Modernización):
✅ Command pattern con routing directo
✅ Pydantic structured output para extracción
✅ Detección de estado conversacional
✅ Timeout reducido de 25s/20s a 10s

Flujo:
Usuario → Nodos 1-4 → [NODO 5A] → Respuesta WhatsApp
"""

import logging
from typing import Dict, List, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage
from dotenv import load_dotenv
import os
from pydantic import BaseModel, Field
from langgraph.types import Command

from src.state.agent_state import WhatsAppAgentState
from src.auth import get_calendar_service
from src.utils import get_time_context, get_current_time
from src.utils.logging_config import (
    log_separator,
    log_node_io,
    log_llm_interaction,
    log_user_message
)
from src.tool import (
    create_event_tool,
    list_events_tool,
    postpone_event_tool,
    update_event_tool,
    delete_event_tool,
    search_calendar_events_tool
)
from src.database.db_auditoria import insertar_auditoria
import json
import pendulum

# ✅ Imports para memoria semántica (LangGraph Store)
from langgraph.store.base import BaseStore
from src.memory import get_user_preferences, get_user_facts

load_dotenv()
logger = logging.getLogger(__name__)


# ==================== PYDANTIC MODELS ====================

# Models para extracción de parámetros
class CreateEventParams(BaseModel):
    """Parámetros para crear evento."""
    summary: str = Field(description="Título del evento")
    start_datetime: str = Field(description="Fecha/hora inicio YYYY-MM-DDTHH:MM:SS")
    end_datetime: str = Field(description="Fecha/hora fin YYYY-MM-DDTHH:MM:SS")
    location: Optional[str] = Field(default=None, description="Ubicación")
    description: Optional[str] = Field(default=None, description="Descripción")

class DeleteEventParams(BaseModel):
    """Parámetros para eliminar evento."""
    event_id: str = Field(description="ID del evento a eliminar")
    event_description: str = Field(description="Descripción del evento")

class UpdateEventParams(BaseModel):
    """Parámetros para actualizar evento."""
    event_id: str = Field(description="ID del evento")
    event_description: str = Field(description="Descripción del evento")
    new_start_datetime: str = Field(description="Nueva fecha/hora inicio")
    new_end_datetime: str = Field(description="Nueva fecha/hora fin")

class SearchEventParams(BaseModel):
    """Parámetros para buscar eventos."""
    query: str = Field(description="Palabras clave a buscar")
    start_datetime: str = Field(description="Inicio del rango de búsqueda")
    end_datetime: str = Field(description="Fin del rango de búsqueda")
    max_results: int = Field(default=10)

# ==================== LLM CONFIGURATION ====================

# LLM principal para Orquestador (DeepSeek)
llm_primary = ChatOpenAI(
    model="deepseek-chat",
    temperature=0.7,
    max_tokens=300,
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1",
    timeout=10.0,  # ✅ Reducido de 25s a 10s
    max_retries=0
)

# Fallback: Claude Haiku 4.5
llm_fallback = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    temperature=0.7,
    max_tokens=300,
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    timeout=10.0,  # ✅ Reducido de 20s a 10s
    max_retries=0
)

# Orquestador con fallback automático
llm_orquestador = llm_primary.with_fallbacks([llm_fallback])

# LLM con structured output para extracción
llm_extractor = llm_primary.with_fallbacks([llm_fallback])


# ==================== CONSTANTES ====================

# Estados conversacionales que requieren saltar ejecución
ESTADOS_FLUJO_ACTIVO = [
    'esperando_confirmacion',
    'recolectando_fecha',
    'recolectando_hora',
    'recolectando_ubicacion'
]

# Mapeo de IDs a funciones de herramientas
TOOL_MAPPING = {
    'create_calendar_event': create_event_tool,
    'list_calendar_events': list_events_tool,
    'update_calendar_event': update_event_tool,
    'delete_calendar_event': delete_event_tool,
    'postpone_calendar_event': postpone_event_tool,
    'search_calendar_events': search_calendar_events_tool
}


def ejecutar_herramienta(tool_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ejecuta una herramienta específica de Google Calendar
    
    Args:
        tool_id: ID de la herramienta (ej: 'list_calendar_events')
        params: Parámetros para la herramienta
        
    Returns:
        Dict con 'success', 'data', 'error'
    """
    try:
        tool_func = TOOL_MAPPING.get(tool_id)
        
        if not tool_func:
            return {
                'success': False,
                'error': f"Herramienta '{tool_id}' no encontrada",
                'data': None
            }
        
        logger.info(f"   🔧 Ejecutando: {tool_id}")
        
        # Ejecutar herramienta
        resultado = tool_func.invoke(params)
        
        return {
            'success': True,
            'data': resultado,
            'error': None
        }
        
    except Exception as e:
        logger.error(f"   ❌ Error en {tool_id}: {e}")
        return {
            'success': False,
            'error': str(e),
            'data': None
        }


def extraer_parametros_con_llm(tool_id: str, mensaje_usuario: str, tiempo_context: str) -> Dict[str, Any]:
    """
    Usa Pydantic structured output para extraer parámetros.
    
    MEJORAS:
    ✅ Pydantic valida automáticamente
    ✅ Type-safe
    ✅ Sin parsing JSON manual
    """
    logger.info(f"    🔍 Extrayendo parámetros para {tool_id}...")
    
    if tool_id == 'create_calendar_event':
        # Configurar structured output (sin json_schema para compatibilidad)
        llm_with_structure = llm_extractor.with_structured_output(
            CreateEventParams
        )
        
        prompt = f"""Extrae información del evento de calendario.

CONTEXTO DE TIEMPO:
{tiempo_context}

MENSAJE DEL USUARIO:
"{mensaje_usuario}"

Extrae:
- summary: título del evento
- start_datetime: inicio en YYYY-MM-DDTHH:MM:SS
- end_datetime: fin en YYYY-MM-DDTHH:MM:SS (1 hora después si no se especifica)
- location: ubicación (null si no se menciona)
- description: descripción (null si no se menciona)

Retorna JSON válido con estos campos."""
        
        try:
            params = llm_with_structure.invoke(prompt)
            return params.model_dump()
        except Exception as e:
            logger.error(f"    ❌ Error extrayendo parámetros: {e}")
            return {}
    
    elif tool_id == 'list_calendar_events':
        now = pendulum.now('America/Tijuana')
        return {
            'start_datetime': now.start_of('day').format('YYYY-MM-DDTHH:mm:ss'),
            'end_datetime': now.end_of('day').format('YYYY-MM-DDTHH:mm:ss'),
            'max_results': 10,
            'timezone': 'America/Tijuana'
        }
    
    elif tool_id == 'delete_calendar_event':
        llm_with_structure = llm_extractor.with_structured_output(DeleteEventParams)
        
        prompt = f"""Extrae el ID del evento a eliminar.

MENSAJE: "{mensaje_usuario}"

Retorna event_id y event_description."""
        
        try:
            params = llm_with_structure.invoke(prompt)
            return params.model_dump()
        except:
            return {}
    
    elif tool_id in ['postpone_calendar_event', 'update_calendar_event']:
        llm_with_structure = llm_extractor.with_structured_output(UpdateEventParams)
        
        prompt = f"""Extrae información para modificar evento.

CONTEXTO: {tiempo_context}
MENSAJE: "{mensaje_usuario}"

Retorna event_id, event_description, new_start_datetime, new_end_datetime."""
        
        try:
            params = llm_with_structure.invoke(prompt)
            return params.model_dump()
        except:
            return {}
    
    elif tool_id == 'search_calendar_events':
        llm_with_structure = llm_extractor.with_structured_output(SearchEventParams)
        
        prompt = f"""Extrae parámetros de búsqueda.

CONTEXTO: {tiempo_context}
MENSAJE: "{mensaje_usuario}"

Retorna query, start_datetime, end_datetime, max_results."""
        
        try:
            params = llm_with_structure.invoke(prompt)
            return params.model_dump()
        except:
            return {}
    
    else:
        logger.warning(f"    ⚠️  No hay plantilla para {tool_id}")
        return {}


def extraer_parametros_con_llm_delete(mensaje_usuario: str, tiempo_context: str, ultimo_listado: List[Dict]) -> Dict[str, Any]:
    """
    Extrae parámetros para delete_calendar_event usando el contexto del último listado.
    
    Args:
        mensaje_usuario: Mensaje del usuario
        tiempo_context: Contexto de tiempo
        ultimo_listado: Lista de eventos del último list_calendar_events
        
    Returns:
        Dict con event_id extraído
    """
    logger.info("    🔍 Extrayendo event_id con contexto de último listado...")
    
    # Formatear eventos del listado para el prompt
    eventos_str = ""
    for i, evento in enumerate(ultimo_listado, 1):
        titulo = evento.get('summary', 'Sin título')
        event_id = evento.get('id', 'sin-id')
        inicio = evento.get('start', 'Fecha no especificada')
        eventos_str += f"\n{i}. {titulo} (ID: {event_id}) - {inicio}"
    
    prompt = f"""Analiza el mensaje del usuario y los eventos disponibles para identificar cuál quiere eliminar.

CONTEXTO DE TIEMPO:
{tiempo_context}

EVENTOS DISPONIBLES:
{eventos_str}

MENSAJE DEL USUARIO:
"{mensaje_usuario}"

Identifica el evento que el usuario quiere eliminar basándote en:
- Nombre/título del evento
- Posición en la lista (ej: "el primero", "el segundo")
- Descripción o contexto

Responde SOLO con JSON:
{{
  "event_id": "ID del evento a eliminar",
  "event_description": "descripción del evento seleccionado"
}}

JSON:"""

    try:
        respuesta = llm_primary.invoke(prompt)
        json_str = respuesta.content.strip()
        
        # Limpiar markdown si el LLM envuelve en ```json
        if json_str.startswith('```'):
            json_str = json_str.split('```')[1]
            if json_str.startswith('json'):
                json_str = json_str[4:]
        
        parametros = json.loads(json_str)
        logger.info(f"    ✅ Event ID extraído del contexto: {parametros.get('event_id')}")
        return parametros
        
    except Exception as e:
        logger.error(f"    ❌ Error extrayendo event_id con contexto: {e}")
        return {}


def formatear_evento(evento: Dict[str, Any], numero: int) -> str:
    """
    Formatea un evento individual de Google Calendar de forma legible
    
    Args:
        evento: Dict con {start, end, summary, description, location, hangoutLink, id, is_all_day}
        numero: Número de evento en la lista
        
    Returns:
        String formateado del evento
    """
    titulo = evento.get('summary', 'Sin título')
    inicio = evento.get('start', 'Fecha no especificada')
    fin = evento.get('end', '')
    ubicacion = evento.get('location')
    descripcion = evento.get('description')
    event_id = evento.get('id', 'sin-id')
    is_all_day = evento.get('is_all_day', False)
    
    # Formato base
    evento_str = f"\n   Evento #{numero}: {titulo}"
    
    # Formatear horario según el tipo de evento
    if is_all_day:
        evento_str += f"\n   📅 Tipo: Evento de todo el día"
        evento_str += f"\n   📅 Fecha: {inicio}"
    else:
        evento_str += f"\n   📅 Inicio: {inicio}"
        if fin:
            evento_str += f"\n   📅 Fin: {fin}"
    
    if ubicacion:
        evento_str += f"\n   📍 Ubicación: {ubicacion}"
    if descripcion:
        evento_str += f"\n   📝 Descripción: {descripcion}"
    evento_str += f"\n   🔑 ID: {event_id}"
    
    return evento_str


def formatear_resultado_herramienta(tool_id: str, data: Any) -> str:
    """
    Formatea el resultado de una herramienta según su tipo
    
    Args:
        tool_id: ID de la herramienta ejecutada
        data: Datos devueltos por la herramienta
        
    Returns:
        String formateado y legible para el LLM
    """
    # Herramientas que devuelven listas de eventos
    if tool_id in ['list_calendar_events', 'search_calendar_events']:
        if isinstance(data, list):
            if len(data) == 0:
                return "   ❌ No se encontraron eventos en el calendario."
            else:
                resultado = f"   ✅ Se encontraron {len(data)} evento(s):"
                for i, evento in enumerate(data, 1):
                    resultado += formatear_evento(evento, i)
                return resultado
        else:
            return f"   ⚠️ Formato inesperado: {data}"
    
    # Herramientas que devuelven strings (create, update, delete)
    elif tool_id in ['create_calendar_event', 'update_calendar_event', 'delete_calendar_event', 'postpone_calendar_event']:
        if isinstance(data, str):
            return f"   ✅ {data}"
        else:
            return f"   ✅ Operación completada: {data}"
    
    # Fallback para herramientas desconocidas
    else:
        return f"   Resultado: {data}"


def construir_prompt_orquestador(
    tiempo_context: str,
    resultados_google: List[Dict],
    contexto_episodico: Dict,
    mensaje_usuario: str,
    preferencias_usuario: Dict = None  # ✅ NUEVO PARÁMETRO
) -> str:
    """
    Construye el prompt para el Orquestador (voz de WhatsApp)

    Args:
        tiempo_context: "Hoy es jueves, 23 de enero..."
        resultados_google: Lista de resultados de herramientas ejecutadas
        contexto_episodico: Contexto histórico del usuario
        mensaje_usuario: Última petición del usuario
        preferencias_usuario: Preferencias semánticas del usuario (timezone, estilo, etc.)

    Returns:
        Prompt estructurado para el LLM
    """
    # Formatear resultados de Google con formato mejorado
    resultados_str = ""

    if not resultados_google:
        resultados_str = "\n⚠️ No se ejecutó ninguna herramienta."
    else:
        for i, res in enumerate(resultados_google, 1):
            tool_name = res.get('tool_id', 'desconocida')

            if res['success']:
                data = res.get('data')
                resultados_str += f"\n{i}. Herramienta: {tool_name}\n"
                resultados_str += formatear_resultado_herramienta(tool_name, data)
                resultados_str += "\n"
            else:
                error = res.get('error', 'Error desconocido')
                resultados_str += f"\n{i}. Herramienta: {tool_name}\n"
                resultados_str += f"   ❌ Error: {error}\n"

    # Contexto episódico si existe
    episodico_str = ""
    if contexto_episodico and contexto_episodico.get('episodios_recuperados'):
        episodico_str = f"\n\nMemoria de conversaciones pasadas:\n{contexto_episodico.get('texto_formateado', '')}"

    # ✅ NUEVO: Formatear preferencias del usuario
    prefs_str = ""
    if preferencias_usuario:
        user_prefs = preferencias_usuario.get("user_preferences", {})
        user_name = user_prefs.get("user_name")
        timezone = user_prefs.get("timezone", "America/Tijuana")
        language = user_prefs.get("language_preference", "formal")
        preferred_times = user_prefs.get("preferred_meeting_times", [])

        prefs_str = f"""
PREFERENCIAS DEL USUARIO:"""
        if user_name:
            prefs_str += f"\n- Nombre: {user_name}"
        prefs_str += f"""
- Zona horaria: {timezone}
- Estilo de comunicación: {language}
- Horarios preferidos: {', '.join(preferred_times) if preferred_times else 'No especificado'}
"""

    prompt = f"""Eres un asistente de WhatsApp amigable y eficiente que ayuda con la gestión de calendarios.

CONTEXTO DE TIEMPO:
{tiempo_context}
{prefs_str}
PETICIÓN DEL USUARIO:
"{mensaje_usuario}"

RESULTADOS DE GOOGLE CALENDAR:
{resultados_str}{episodico_str}

INSTRUCCIONES CRÍTICAS:
1. LEE CUIDADOSAMENTE los resultados arriba. Si dice "Se encontraron X eventos", entonces SÍ hay eventos
2. Si dice "No se encontraron eventos", entonces NO hay eventos - responde apropiadamente
3. Redacta una respuesta natural, breve y útil en español
4. Adapta tu tono según el estilo de comunicación del usuario (formal/informal)
5. Si agendaste algo, confirma los detalles (fecha, hora, título)
6. Si hubo un error, explícalo amablemente sin tecnicismos
7. Si listaste eventos, resume los más importantes (no repitas todos los detalles)
8. Sé conversacional como un chat de WhatsApp
9. No uses emojis en exceso (máximo 1-2)
10. Máximo 3-4 líneas de texto

RESPUESTA:"""

    return prompt


def extraer_ultimo_mensaje_usuario(state: WhatsAppAgentState) -> str:
    """
    Extrae el último mensaje del usuario
    
    Returns:
        String con el mensaje o cadena vacía
    """
    mensajes = state.get('messages', [])
    
    for mensaje in reversed(mensajes):
        if isinstance(mensaje, dict):
            if mensaje.get('role') == 'user':
                return mensaje.get('content', '')
        elif hasattr(mensaje, 'type'):
            if mensaje.type == 'human':
                return mensaje.content
    
    return ""


def nodo_ejecucion_herramientas(state: WhatsAppAgentState, store: BaseStore) -> Command:
    """
    Nodo 5A: Ejecuta herramientas de Google Calendar y orquesta la respuesta
    
    MEJORAS APLICADAS:
    ✅ Command pattern con routing directo
    ✅ Pydantic structured output
    ✅ Detección de estado conversacional
    ✅ Timeout reducido (10s)
    
    Returns:
        Command con update y goto
    """
    log_separator(logger, "NODO_5A_EJECUCION_PERSONAL", "INICIO")

    herramientas = state.get('herramientas_seleccionadas', [])
    user_id = state.get('user_id', 'default_user')
    estado_conversacion = state.get('estado_conversacion', 'inicial')

    # Log del input
    input_data = f"herramientas: {herramientas}\nestado: {estado_conversacion}\nuser_id: {user_id}"
    log_node_io(logger, "INPUT", "NODO_5A_EJECUCION", input_data)
    
    # ✅ NUEVA VALIDACIÓN: Detectar estado conversacional
    if estado_conversacion in ESTADOS_FLUJO_ACTIVO:
        logger.info(f"   🔄 Flujo activo detectado (estado: {estado_conversacion}) - Saltando ejecución")
        return Command(
            update={},
            goto="generacion_resumen"
        )

    # ✅ Cargar preferencias y facts del usuario desde memory store
    preferencias = {}
    facts = {}
    try:
        preferencias = get_user_preferences(store, user_id)
        facts = get_user_facts(store, user_id)  # ✅ Cargar facts (cross-thread)

        # Extraer preferencias relevantes para logging
        timezone_pref = preferencias.get("user_preferences", {}).get("timezone", "America/Tijuana")
        language_pref = preferencias.get("user_preferences", {}).get("language_preference", "formal")
        preferred_times = preferencias.get("user_preferences", {}).get("preferred_meeting_times", [])
        user_name_fact = facts.get("user_name")  # ✅ Nombre desde facts

        logger.info(f"    👤 Preferencias y facts cargados:")
        if user_name_fact:
            logger.info(f"       - Nombre (facts): {user_name_fact}")
        logger.info(f"       - Timezone: {timezone_pref}")
        logger.info(f"       - Estilo: {language_pref}")
        logger.info(f"       - Horarios preferidos: {preferred_times if preferred_times else 'No especificado'}")

        # ✅ Inyectar nombre en preferencias para el orquestador
        if user_name_fact and "user_preferences" in preferencias:
            preferencias["user_preferences"]["user_name"] = user_name_fact

    except Exception as e:
        logger.warning(f"    ⚠️  Error cargando preferencias/facts: {e}")
        logger.info("    ℹ️  Continuando sin preferencias del usuario")
        preferencias = {}
    
    logger.info(f"    📋 Herramientas a ejecutar: {herramientas}")
    
    # Caso: No hay herramientas seleccionadas
    if not herramientas:
        logger.info("    ℹ️  No hay herramientas para ejecutar")

        # Aún así, usar Orquestador para responder
        mensaje_usuario = extraer_ultimo_mensaje_usuario(state)
        log_user_message(logger, mensaje_usuario)
        tiempo_ctx = get_time_context()

        # ✅ Incluir preferencias Y FACTS en respuesta conversacional
        prefs_str = ""
        if preferencias:
            user_prefs = preferencias.get("user_preferences", {})
            user_name = user_prefs.get("user_name")  # Nombre desde facts
            language = user_prefs.get("language_preference", "formal")

            # Construir sección de información del usuario
            prefs_str = "\n\nINFORMACION DEL USUARIO:"
            if user_name:
                prefs_str += f"\n- Nombre: {user_name}"
            prefs_str += f"\n- Estilo de comunicacion preferido: {language}"

        prompt = f"""Eres un asistente de WhatsApp amigable.

CONTEXTO DE TIEMPO:
{tiempo_ctx}{prefs_str}

MENSAJE DEL USUARIO:
"{mensaje_usuario}"

El usuario no necesita ninguna accion de calendario, solo responde de forma conversacional y util.
Adapta tu tono al estilo de comunicacion preferido del usuario.
Si conoces el nombre del usuario, usaló naturalmente en tu respuesta.

RESPUESTA:"""
        
        try:
            respuesta = llm_orquestador.invoke(prompt)
            respuesta_texto = respuesta.content.strip()
            
            # Log de interacción con LLM
            log_llm_interaction(logger, "Orquestador", prompt, respuesta_texto)
            
        except Exception as e:
            logger.error(f"    ❌ Error en Orquestador: {e}")
            respuesta_texto = "Entendido. ¿Hay algo más en lo que pueda ayudarte con tu calendario?"
        
        # Log de output
        output_data = f"respuesta: {respuesta_texto}"
        log_node_io(logger, "OUTPUT", "NODO_5_EJECUCION", output_data)
        log_separator(logger, "NODO_5_EJECUCION_HERRAMIENTAS", "FIN")

        # ✅ AUDITORÍA: Registrar conversación
        try:
            user_id = state.get('user_id', 'unknown')
            session_id = state.get('session_id', 'unknown')
            insertar_auditoria(user_id, session_id, 'user', mensaje_usuario)
            insertar_auditoria(user_id, session_id, 'assistant', respuesta_texto)
        except Exception as audit_err:
            logger.debug(f"    ⚠️  Auditoría no disponible: {audit_err}")

        # Agregar respuesta al estado
        return Command(
            update={'messages': [AIMessage(content=respuesta_texto)]},
            goto="generacion_resumen"
        )
    
    # Paso 1: Inyectar contexto de tiempo
    tiempo_contexto = get_time_context()
    logger.info(f"    ⏰ {tiempo_contexto}")
    
    # Paso 2: Ejecutar herramientas
    resultados = []
    mensaje_usuario = extraer_ultimo_mensaje_usuario(state)
    ultimo_listado = state.get('ultimo_listado', [])
    
    for tool_id in herramientas:
        logger.info(f"    🔧 Procesando: {tool_id}")
        
        # PASO 1: Extraer parámetros con LLM
        logger.info(f"    🔍 Extrayendo parámetros para {tool_id}...")
        parametros = extraer_parametros_con_llm(tool_id, mensaje_usuario, tiempo_contexto)
        
        # PASO 2: Procesar según el tipo de herramienta
        if tool_id == 'create_calendar_event':
            # Validar que tenemos parámetros mínimos
            if not parametros.get('summary') or not parametros.get('start_datetime'):
                resultado = {
                    'success': False,
                    'error': 'Necesito más detalles: ¿cuál es el título del evento y cuándo debe ser?',
                    'data': None,
                    'tool_id': tool_id
                }
                resultados.append(resultado)
                logger.warning(f"    ⚠️  Parámetros incompletos para {tool_id}")
                continue
            
            # Asegurar timezone
            parametros['timezone'] = 'America/Tijuana'
            resultado = ejecutar_herramienta(tool_id, parametros)
            
        elif tool_id == 'list_calendar_events':
            # Ya tiene parámetros por defecto (hoy)
            resultado = ejecutar_herramienta(tool_id, parametros)
            
            # ✅ GUARDAR resultado en ultimo_listado para contexto futuro
            if resultado['success'] and isinstance(resultado.get('data'), list):
                state['ultimo_listado'] = resultado['data']
                logger.info(f"    💾 Guardado ultimo_listado con {len(resultado['data'])} eventos")
            
        elif tool_id == 'update_calendar_event':
            # ✅ NUEVO: Manejar update con contexto del listado
            if not parametros.get('event_id') and ultimo_listado:
                logger.info("    🔍 Buscando evento en ultimo_listado para update...")
                parametros_ctx = extraer_parametros_con_llm_delete(
                    mensaje_usuario, 
                    tiempo_contexto, 
                    ultimo_listado
                )
                # Fusionar event_id encontrado con otros parámetros
                if parametros_ctx.get('event_id'):
                    parametros['event_id'] = parametros_ctx['event_id']
            
            # Validar que tenemos event_id y nueva fecha
            if not parametros.get('event_id'):
                resultado = {
                    'success': False,
                    'error': 'Necesito identificar el evento. ¿Puedes ser más específico?',
                    'data': None,
                    'tool_id': tool_id
                }
                resultados.append(resultado)
                logger.warning(f"    ⚠️  No se pudo identificar event_id para update")
                continue
            
            if not parametros.get('new_start_datetime'):
                resultado = {
                    'success': False,
                    'error': 'Necesito saber la nueva fecha/hora del evento.',
                    'data': None,
                    'tool_id': tool_id
                }
                resultados.append(resultado)
                logger.warning(f"    ⚠️  No se pudo extraer nueva fecha/hora")
                continue
            
            resultado = ejecutar_herramienta(tool_id, parametros)
            
        elif tool_id == 'delete_calendar_event':
            # ✅ USAR ultimo_listado como contexto si no hay event_id
            if not parametros.get('event_id') and ultimo_listado:
                logger.info("    🔍 Buscando evento en ultimo_listado para delete...")
                parametros = extraer_parametros_con_llm_delete(
                    mensaje_usuario, 
                    tiempo_contexto, 
                    ultimo_listado
                )
            
            # Validar que tenemos event_id
            if not parametros.get('event_id'):
                resultado = {
                    'success': False,
                    'error': 'Necesito el ID del evento a eliminar. Primero lista tus eventos con "¿qué tengo hoy?"',
                    'data': None,
                    'tool_id': tool_id
                }
                resultados.append(resultado)
                logger.warning(f"    ⚠️  No se pudo identificar event_id para delete")
                continue
            
            resultado = ejecutar_herramienta(tool_id, parametros)
            
        elif tool_id == 'postpone_calendar_event':
            # Similar a update
            if not parametros.get('event_id') and ultimo_listado:
                logger.info("    🔍 Buscando evento en ultimo_listado para postpone...")
                parametros_ctx = extraer_parametros_con_llm_delete(
                    mensaje_usuario, 
                    tiempo_contexto, 
                    ultimo_listado
                )
                if parametros_ctx.get('event_id'):
                    parametros['event_id'] = parametros_ctx['event_id']
            
            if not parametros.get('event_id') or not parametros.get('new_start_datetime'):
                resultado = {
                    'success': False,
                    'error': 'Necesito el ID del evento y la nueva fecha/hora.',
                    'data': None,
                    'tool_id': tool_id
                }
                resultados.append(resultado)
                logger.warning(f"    ⚠️  Parámetros incompletos para postpone")
                continue
            
            parametros['timezone'] = 'America/Tijuana'
            resultado = ejecutar_herramienta(tool_id, parametros)

        elif tool_id == 'search_calendar_events':
            # Búsqueda de eventos por palabras clave
            if not parametros.get('query'):
                resultado = {
                    'success': False,
                    'error': 'Necesito una palabra clave para buscar. Por ejemplo: "Busca citas con García"',
                    'data': None,
                    'tool_id': tool_id
                }
                resultados.append(resultado)
                logger.warning(f"    ⚠️  Sin query para search")
                continue

            # Asegurar rango de fechas por defecto (próximos 30 días)
            if not parametros.get('start_datetime'):
                from src.utils.time_utils import get_current_time
                now = get_current_time()
                parametros['start_datetime'] = now.start_of('day').to_datetime_string()
                parametros['end_datetime'] = now.add(days=30).end_of('day').to_datetime_string()

            resultado = ejecutar_herramienta(tool_id, parametros)

            # Guardar resultados para contexto futuro
            if resultado['success'] and isinstance(resultado.get('data'), list):
                state['ultimo_listado'] = resultado['data']
                logger.info(f"    💾 Guardado resultado de búsqueda con {len(resultado['data'])} eventos")

        else:
            # Otras herramientas
            resultado = {
                'success': False,
                'error': f'Herramienta {tool_id} no implementada aún',
                'data': None,
                'tool_id': tool_id
            }
        
        resultados.append(resultado)
        
        if resultado['success']:
            logger.info(f"    ✅ {tool_id} exitoso")
        else:
            logger.warning(f"    ⚠️  {tool_id}: {resultado.get('error')}")
    
    # Paso 3: Orquestador genera respuesta natural
    logger.info("    🎭 Orquestador generando respuesta...")
    
    mensaje_usuario = extraer_ultimo_mensaje_usuario(state)
    log_user_message(logger, mensaje_usuario)
    
    contexto_episodico = state.get('contexto_episodico', {})
    
    prompt = construir_prompt_orquestador(
        tiempo_context=tiempo_contexto,
        resultados_google=resultados,
        contexto_episodico=contexto_episodico,
        mensaje_usuario=mensaje_usuario,
        preferencias_usuario=preferencias  # ✅ Pasar preferencias al orquestador
    )
    
    try:
        respuesta = llm_orquestador.invoke(prompt)
        respuesta_texto = respuesta.content.strip()
        
        # Log detallado de LLM
        log_llm_interaction(logger, "Orquestador (DeepSeek/Claude)", prompt, respuesta_texto, truncate_prompt=1500)
        
        logger.info(f"    💬 Respuesta generada: '{respuesta_texto[:60]}...'")
        
    except Exception as e:
        logger.error(f"    ❌ Error en Orquestador: {e}")
        respuesta_texto = "Hubo un problema procesando tu solicitud. ¿Puedes intentar de nuevo?"
    
    # Log de output
    output_data = f"respuesta: {respuesta_texto}\nherramientas_ejecutadas: {len(resultados)}"
    log_node_io(logger, "OUTPUT", "NODO_5A_EJECUCION", output_data)
    log_separator(logger, "NODO_5A_EJECUCION_PERSONAL", "FIN")

    # ✅ AUDITORÍA: Registrar conversación con herramientas
    try:
        insertar_auditoria(user_id, state.get('session_id', 'unknown'), 'user', mensaje_usuario)
        insertar_auditoria(user_id, state.get('session_id', 'unknown'), 'assistant', respuesta_texto)
    except Exception as audit_err:
        logger.debug(f"    ⚠️  Auditoría no disponible: {audit_err}")

    # ✅ Retornar Command
    return Command(
        update={
            'messages': [AIMessage(content=respuesta_texto)],
            'herramientas_seleccionadas': [],
            'ultimo_listado': state.get('ultimo_listado')
        },
        goto="generacion_resumen"
    )


# Wrapper para compatibilidad con grafo
def nodo_ejecucion_herramientas_wrapper(state: WhatsAppAgentState, store: BaseStore) -> Command:
    """Wrapper para LangGraph - retorna Command directamente."""
    return nodo_ejecucion_herramientas(state, store)
