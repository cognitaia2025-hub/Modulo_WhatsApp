"""
Nodo 2: Filtrado Inteligente con Detección de Intención

FUNCIONES PRINCIPALES:
1. Detectar la intención del usuario usando contexto completo (N1)
2. Determinar si la intención es CLARA o NECESITA MÁS INFORMACIÓN
3. Si intención no es clara → Pedir aclaraciones (loop interno, no avanza)
4. Si intención es clara → Clasificar y pasar al siguiente nodo

CLASIFICACIONES POSIBLES:
- 'personal': Eventos de calendario personal
- 'medica': Solicitudes médicas (solo doctores)
- 'solicitud_cita_paciente': Pacientes externos solicitan citas
- 'chat': Conversación casual (pero intención clara)
- 'necesita_aclaracion': Intención NO clara, requiere más información

ESTRATEGIA DE CONVERSACIONES FRAGMENTADAS:
• Usuario: "Hola" → necesita_aclaracion → Responde: "¿En qué puedo ayudarte?"
• Usuario: "quiero agendar" → solicitud_cita_paciente → Pasa a recepcionista
• Usuario: "mi nombre es Juan" (sin contexto) → necesita_aclaracion → "¿Qué necesitas hacer, Juan?"

ARQUITECTURA:
1. N0 (Identificación) → Carga user_id, tipo_usuario en el state
2. N1 (Caché) → Usa user_id para recuperar contexto histórico
3. N2 (Este nodo) → Usa contexto + tipo_usuario para clasificar
4. Si clara → Siguiente nodo | Si no clara → Loop (pide aclaraciones)
"""

import logging
import time
from typing import Literal, Any, Optional, List, cast
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage, AIMessage
from langgraph.types import Command
from pydantic import BaseModel, Field, SecretStr
from dotenv import load_dotenv
import os
import psycopg
from psycopg.types.json import Json

from src.state.agent_state import WhatsAppAgentState

load_dotenv()
logger = logging.getLogger(__name__)

# Configuración de LLMs
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5434/agente_whatsapp")


# ==================== PYDANTIC MODEL ====================

class ClasificacionResponse(BaseModel):
    """Respuesta estructurada del clasificador."""
    
    clasificacion: Literal["personal", "medica", "solicitud_cita_paciente", "chat", "necesita_aclaracion"] = Field(
        description="""
        Categoría del mensaje:
        - personal: Eventos de calendario personal (intención CLARA)
        - medica: Solicitudes médicas de doctores (intención CLARA)
        - solicitud_cita_paciente: Paciente externo pide cita (intención CLARA)
        - chat: Conversación casual pero intención clara (despedidas, agradecimientos)
        - necesita_aclaracion: Intención NO clara, requiere más información del usuario
        """
    )
    
    confianza: float = Field(
        ge=0.0,
        le=1.0,
        description="Nivel de confianza en la clasificación (0.0 a 1.0)"
    )
    
    razonamiento: str = Field(
        description="Breve explicación de por qué se eligió esta clasificación"
    )
    
    pregunta_aclaracion: Optional[str] = Field(
        default=None,
        description="Si clasificacion='necesita_aclaracion', pregunta para pedir más información"
    )


# ==================== CONFIGURACIÓN LLM CON STRUCTURED OUTPUT ====================

# LLM primario: DeepSeek con JSON mode (más compatible)
llm_primary_base = ChatOpenAI(
    model="deepseek-chat",
    temperature=0,
    max_tokens=200,
    api_key=SecretStr(os.getenv("DEEPSEEK_API_KEY") or ""),
    base_url="https://api.deepseek.com/v1",
    timeout=10.0,
    max_retries=0,
    model_kwargs={"response_format": {"type": "json_object"}}
)

# LLM fallback: Claude Sonnet (soporta structured output)
llm_fallback_base = ChatAnthropic(
    model_name="claude-3-5-sonnet-20240620",
    temperature=0,
    max_tokens=200,
    api_key=SecretStr(os.getenv("ANTHROPIC_API_KEY") or ""),
    timeout=10.0,
    max_retries=0,
    stop=None
)

# Configurar structured output - usar method="json_mode" para mayor compatibilidad
llm_primary = llm_primary_base.with_structured_output(  # type: ignore[no-untyped-call]
    ClasificacionResponse,
    method="json_mode"
)

llm_fallback = llm_fallback_base.with_structured_output(  # type: ignore[no-untyped-call]
    ClasificacionResponse
)


# ==================== CONSTANTES ====================

# ✅ ESTADOS CORREGIDOS (Sincronizados con logs del recepcionista)
ESTADOS_FLUJO_ACTIVO = [
    'solicitando_nombre',
    'recolectando_slots',
    'confirmando_cita',
    'mostrando_opciones',
    # Estados legacy por compatibilidad
    'recolectando_fecha',
    'recolectando_hora', 
    'esperando_confirmacion'
]

# ✅ MAPEO CORREGIDO - Todos los estados de cita van a recepcionista
MAPEO_ESTADO_A_NODO = {
    'solicitando_nombre': 'recepcionista',
    'recolectando_slots': 'recepcionista',
    'confirmando_cita': 'recepcionista',
    'mostrando_opciones': 'recepcionista',
    # Estados legacy
    'recolectando_fecha': 'recepcionista',
    'recolectando_hora': 'recepcionista',
    'esperando_confirmacion': 'recepcionista'
}


def construir_prompt_clasificacion(
    mensaje_usuario: str, 
    tipo_usuario: str,
    contexto_previo: List[str]
) -> List[Any]:
    """
    Construye prompt mejorado para clasificación con detección de intención clara
    
    Args:
        mensaje_usuario: Último mensaje del usuario
        tipo_usuario: Tipo de usuario (doctor, paciente_externo, admin)
        contexto_previo: Lista de mensajes previos de la conversación
    """
    # Formatear contexto
    contexto_str = ""
    if contexto_previo:
        contexto_str = "\n".join([f"- {msg}" for msg in contexto_previo[-5:]])  # Últimos 5 mensajes
    
    system_prompt = """Eres un clasificador de intención para una clínica médica.

Tu trabajo es DETERMINAR si la intención del usuario es CLARA o NECESITA MÁS INFORMACIÓN.

═══════════════════════════════════════════════════════════════
CATEGORÍAS CUANDO LA INTENCIÓN ES CLARA
═══════════════════════════════════════════════════════════════

1. "personal" - Eventos de calendario personal
   • Usuario pide recordatorio personal
   • Menciona eventos no médicos
   • Ejemplos CLAROS: "Recuérdame el cumpleaños de María el viernes"

2. "medica" - Solicitudes médicas (SOLO DOCTORES)
   • Doctor pregunta por paciente específico
   • Doctor revisa historiales
   • Ejemplos CLAROS: "¿Cómo está mi paciente Juan?", "Ver expediente de María"

3. "solicitud_cita_paciente" - Paciente externo pide cita
   • Menciona explícitamente "cita", "agendar", "consulta"
   • Pregunta por disponibilidad
   • Ejemplos CLAROS: "Quiero una cita", "Necesito agendar", "¿Tienen espacio mañana?"

4. "chat" - Conversación casual CON INTENCIÓN CLARA
   • Despedidas: "Adiós", "Hasta luego", "Nos vemos"
   • Agradecimientos: "Gracias", "Muchas gracias", "Te agradezco"
   • Afirmaciones: "OK", "Entendido", "Perfecto"
   • ⚠️ NO uses "chat" para saludos iniciales sin intención

═══════════════════════════════════════════════════════════════
CATEGORÍA CUANDO LA INTENCIÓN NO ES CLARA
═══════════════════════════════════════════════════════════════

5. "necesita_aclaracion" - Intención NO clara
   • Saludos iniciales sin contexto: "Hola", "Buenos días"
   • Fragmentos de información: "mi nombre es Juan" (sin decir qué quiere)
   • Mensajes ambiguos: "Necesito ayuda" (sin especificar con qué)
   • Información personal sin solicitud: "Tengo 30 años" (¿y qué necesita?)
   
   ⚡ ACCIÓN REQUERIDA: Generar pregunta_aclaracion para pedir más información
   
   Ejemplos de preguntas:
   • "¡Hola! ¿En qué puedo ayudarte hoy?"
   • "Entendido, {nombre}. ¿Qué necesitas hacer?"
   • "Claro, ¿necesitas agendar una cita, revisar algo o consultar información?"

═══════════════════════════════════════════════════════════════
REGLAS DE CLASIFICACIÓN
═══════════════════════════════════════════════════════════════

⚠️ CRÍTICO:

1. USA EL CONTEXTO: Si los mensajes anteriores dan pistas, úsalas
   • Contexto: ["Hola", "quiero agendar"] → "solicitud_cita_paciente"
   • Sin contexto: "Hola" → "necesita_aclaracion"

2. PACIENTES EXTERNOS:
   • Si intención CLARA y NO es cita → "necesita_aclaracion" + pregunta
   • Solo pueden: "solicitud_cita_paciente", "chat", "necesita_aclaracion"

3. CONFIANZA:
   • Alta (>0.9): Intención muy clara
   • Media (0.5-0.9): Intención probable pero con algo de ambigüedad
   • Baja (<0.5): Intención poco clara → "necesita_aclaracion"

4. PREGUNTA DE ACLARACIÓN:
   • SIEMPRE incluir si clasificacion="necesita_aclaracion"
   • Debe ser específica y natural
   • Puede mencionar info que el usuario ya dio

═══════════════════════════════════════════════════════════════
EJEMPLOS COMPLETOS
═══════════════════════════════════════════════════════════════

Entrada: "Hola"
Contexto: []
Usuario: paciente_externo
Salida: {
  "clasificacion": "necesita_aclaracion", 
  "confianza": 0.4,
  "razonamiento": "Saludo inicial sin contexto ni intención",
  "pregunta_aclaracion": "¡Hola! ¿En qué puedo ayudarte hoy?"
}

Entrada: "quiero agendar"
Contexto: ["Hola", "Buenos días"]
Usuario: paciente_externo
Salida: {
  "clasificacion": "solicitud_cita_paciente",
  "confianza": 0.95,
  "razonamiento": "Intención clara de agendar cita",
  "pregunta_aclaracion": null
}

Entrada: "mi nombre es Juan"
Contexto: []
Usuario: paciente_externo
Salida: {
  "clasificacion": "necesita_aclaracion",
  "confianza": 0.3,
  "razonamiento": "Proporciona nombre pero no dice qué necesita",
  "pregunta_aclaracion": "Mucho gusto, Juan. ¿Qué necesitas hacer hoy?"
}

Entrada: "necesito ayuda"
Contexto: []
Usuario: paciente_externo
Salida: {
  "clasificacion": "necesita_aclaracion",
  "confianza": 0.4,
  "razonamiento": "Solicitud de ayuda pero no especifica con qué",
  "pregunta_aclaracion": "Claro, ¿necesitas agendar una cita o consultar algo?"
}

Entrada: "Gracias por todo"
Contexto: ["Quiero cita", "Te confirmo para mañana 10am", "Perfecto"]
Usuario: paciente_externo
Salida: {
  "clasificacion": "chat",
  "confianza": 0.98,
  "razonamiento": "Agradecimiento al finalizar conversación",
  "pregunta_aclaracion": null
}

Entrada: "¿Cómo está Juan Pérez?"
Contexto: []
Usuario: doctor
Salida: {
  "clasificacion": "medica",
  "confianza": 0.99,
  "razonamiento": "Doctor pregunta por paciente específico",
  "pregunta_aclaracion": null
}"""

    # Formatear contexto previo
    contexto_display = f"\nContexto de conversación previa:\n{contexto_str}" if contexto_str else "\nContexto: (Primera interacción)"

    user_prompt = f"""Clasifica este mensaje considerando el contexto completo:{contexto_display}

Mensaje actual: "{mensaje_usuario}"
Tipo de usuario: {tipo_usuario}

IMPORTANTE: 
- Si la intención NO es clara → clasificacion="necesita_aclaracion" + generar pregunta_aclaracion
- Si la intención es clara → clasificar en la categoría correcta

Analiza y responde en formato JSON."""

    return [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]


def validar_clasificacion_por_tipo_usuario(
    clasificacion: str,
    tipo_usuario: str
) -> str:
    """
    Valida que la clasificación sea compatible con el tipo de usuario
    
    Regla crítica: Pacientes externos SOLO pueden tener 'solicitud_cita_paciente'
    
    Args:
        clasificacion: Clasificación del LLM
        tipo_usuario: Tipo de usuario
        
    Returns:
        Clasificación validada (puede ser modificada)
    """
    # Pacientes externos: SOLO solicitud_cita_paciente o chat
    if tipo_usuario == "paciente_externo":
        if clasificacion in ["medica", "personal"]:
            logger.warning(
                f"⚠️  Paciente externo clasificado como '{clasificacion}', "
                f"corrigiendo a 'solicitud_cita_paciente'"
            )
            return "solicitud_cita_paciente"
    
    # Doctores: todas las clasificaciones permitidas
    return clasificacion


def registrar_clasificacion_bd(
    user_id: str,
    session_id: str,
    mensaje: str,
    clasificacion: str,
    modelo_usado: str,
    tiempo_ms: int,
    herramientas_seleccionadas: Optional[List[Any]] = None
) -> None:
    """
    Registra clasificación en la base de datos para auditoría
    
    Args:
        user_id: ID del usuario (teléfono)
        session_id: ID de la sesión
        mensaje: Mensaje clasificado
        clasificacion: Clasificación asignada
        modelo_usado: Modelo LLM usado
        tiempo_ms: Tiempo de procesamiento en ms
        herramientas_seleccionadas: Lista de herramientas seleccionadas
    """
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO clasificaciones_llm (
                        session_id,
                        user_id,
                        modelo,
                        clasificacion,
                        herramientas_seleccionadas,
                        mensaje_usuario,
                        tiempo_respuesta_ms
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    session_id,
                    user_id,
                    modelo_usado,
                    clasificacion,
                    Json(herramientas_seleccionadas or []),
                    mensaje[:1000],  # Limitar tamaño
                    tiempo_ms
                ))
                conn.commit()
        
        logger.info(f"✅ Clasificación registrada en BD: {clasificacion}")
    
    except Exception as e:
        logger.error(f"❌ Error registrando clasificación: {e}")
        # No fallar el flujo principal si falla el registro


def nodo_filtrado_inteligente(state: WhatsAppAgentState) -> Command[Any]:
    """
    Nodo de filtrado inteligente con detección de intención clara
    
    LÓGICA:
    1. Extrae contexto previo de N1 (cache)
    2. Analiza mensaje actual + contexto
    3. Si intención NO clara → Pide aclaraciones (loop interno)
    4. Si intención clara → Clasifica y pasa al siguiente nodo
    """
    logger.info("\n" + "=" * 70)
    logger.info("🔍 NODO N2: FILTRADO INTELIGENTE + DETECCIÓN DE INTENCIÓN")
    logger.info("=" * 70)
    
    inicio = time.time()
    
    # Extraer datos del state
    messages = cast(List[Any], state.get("messages", []))
    tipo_usuario = str(state.get("tipo_usuario", "paciente_externo"))
    user_id = str(state.get("user_id", "unknown"))
    estado_conversacion = str(state.get("estado_conversacion", "inicial"))
    contexto_recuperado = cast(List[str], state.get("contexto_recuperado", []))
    
    logger.info(f"👤 Usuario: {user_id} ({tipo_usuario})")
    logger.info(f"📚 Contexto recuperado (N1): {len(contexto_recuperado)} memorias")
    
    # ✅ VALIDACIÓN: Si hay flujo activo, saltar sin clasificar
    if estado_conversacion in ESTADOS_FLUJO_ACTIVO:
        goto_node = str(MAPEO_ESTADO_A_NODO.get(estado_conversacion, "generacion_resumen"))
        logger.info(f"   ⚡ Flujo activo: {estado_conversacion} -> Saltando a {goto_node}")
        
        return Command(
            update={
                "requiere_clasificacion_llm": False,
                "ruta_siguiente": goto_node
            },
            goto=goto_node
        )
    
    # Extraer último mensaje y contexto previo de la conversación actual
    ultimo_mensaje = ""
    contexto_conversacion: List[str] = []
    
    for msg_item in messages:
        # Manejo robusto de BaseMessage o dict
        if isinstance(msg_item, BaseMessage):
            content = msg_item.content
            # content puede ser str o list[str | dict]
            if isinstance(content, str):
                texto = content
            elif isinstance(content, list) and len(content) > 0:
                texto = str(content[0]) if content[0] else ""
            else:
                continue
            
            # Agregar al contexto (últimos 5 mensajes)
            if msg_item.type == "human":
                contexto_conversacion.append(f"Usuario: {texto}")
            elif msg_item.type == "ai":
                contexto_conversacion.append(f"Asistente: {texto}")
                
        elif isinstance(msg_item, dict):
            role = cast(Any, msg_item.get("role"))
            content_val = cast(Any, msg_item.get("content", ""))
            texto = str(content_val)
            
            if role == "user":
                contexto_conversacion.append(f"Usuario: {texto}")
            elif role == "assistant":
                contexto_conversacion.append(f"Asistente: {texto}")
    
    # El último mensaje del usuario
    for msg_item in reversed(messages):
        if isinstance(msg_item, BaseMessage):
            if msg_item.type == "human":
                content = msg_item.content
                if isinstance(content, str):
                    ultimo_mensaje = content
                elif isinstance(content, list) and len(content) > 0:
                    ultimo_mensaje = str(content[0]) if content[0] else ""
                break
        elif isinstance(msg_item, dict):
            role = cast(Any, msg_item.get("role"))
            if role == "user":
                content_val = cast(Any, msg_item.get("content", ""))
                ultimo_mensaje = str(content_val)
                break
    
    if not ultimo_mensaje:
        logger.warning("⚠️  No se encontró mensaje del usuario")
        return Command(
            update={
                "clasificacion_mensaje": "chat",
                "confianza_clasificacion": 0.5
            },
            goto="generacion_resumen"
        )
    
    logger.info(f"📝 Mensaje: {ultimo_mensaje[:100]}...")
    logger.info(f"💬 Contexto conversación: {len(contexto_conversacion)} mensajes")
    
    # Construir prompt con contexto
    # Tomar últimos 10 mensajes de contexto (5 intercambios)
    contexto_para_prompt = contexto_conversacion[-10:] if len(contexto_conversacion) > 10 else contexto_conversacion
    
    prompt_messages = construir_prompt_clasificacion(
        ultimo_mensaje, 
        tipo_usuario,
        contexto_para_prompt
    )
    
    # Llamar a LLM con fallback
    modelo_usado = "deepseek"
    
    try:
        logger.info("🤖 Llamando a DeepSeek con structured output...")
        resultado = cast(ClasificacionResponse, llm_primary.invoke(prompt_messages))
        modelo_usado = "deepseek"
    
    except Exception as e:
        logger.warning(f"⚠️  DeepSeek falló: {e}")
        logger.info("🔄 Intentando con Claude (fallback)...")
        
        try:
            resultado = cast(ClasificacionResponse, llm_fallback.invoke(prompt_messages))
            modelo_usado = "claude"
        
        except Exception as e2:
            logger.error(f"❌ Ambos LLMs fallaron: {e2}")
            
            # Fallback final: pedir aclaración
            return Command(
                update={
                    "clasificacion_mensaje": "necesita_aclaracion",
                    "confianza_clasificacion": 0.3,
                    "modelo_clasificacion_usado": "fallback",
                    "messages": messages + [AIMessage(content="Disculpa, tuve un problema técnico. ¿Podrías decirme en qué puedo ayudarte?")]
                },
                goto="END"  # Loop: espera nuevo mensaje del usuario
            )
    
    # Extraer resultado
    clasificacion = resultado.clasificacion
    confianza = resultado.confianza
    razonamiento = resultado.razonamiento
    pregunta_aclaracion = resultado.pregunta_aclaracion
    
    logger.info(f"📊 Clasificación: {clasificacion}")
    logger.info(f"💯 Confianza: {confianza}")
    logger.info(f"💭 Razonamiento: {razonamiento}")
    
    # ✅ CASO ESPECIAL: Intención NO clara → Pedir aclaración (LOOP)
    if clasificacion == "necesita_aclaracion":
        logger.warning(f"⚠️  Intención NO clara - Pidiendo aclaraciones")
        
        # Usar la pregunta generada por el LLM o fallback
        pregunta = pregunta_aclaracion or "¿En qué puedo ayudarte hoy?"
        
        logger.info(f"❓ Pregunta: {pregunta}")
        
        # Agregar mensaje de aclaración y NO avanzar (loop interno)
        return Command(
            update={
                "clasificacion_mensaje": "necesita_aclaracion",
                "confianza_clasificacion": confianza,
                "modelo_clasificacion_usado": modelo_usado,
                "messages": messages + [AIMessage(content=pregunta)]
            },
            goto="END"  # END = Loop, espera nuevo mensaje del usuario
        )
    
    # Validar según tipo de usuario
    clasificacion_validada = validar_clasificacion_por_tipo_usuario(
        clasificacion,
        tipo_usuario
    )
    
    if clasificacion != clasificacion_validada:
        logger.warning(
            f"⚠️  Clasificación ajustada: {clasificacion} → {clasificacion_validada}"
        )
        clasificacion = clasificacion_validada
    
    # Calcular tiempo
    tiempo_ms = int((time.time() - inicio) * 1000)
    logger.info(f"⏱️  Tiempo: {tiempo_ms}ms")
    
    # Registrar en BD
    session_id_val = state.get("session_id")
    session_id = str(session_id_val) if session_id_val else ""
    
    if not session_id:
        thread_id_val = state.get("thread_id")
        session_id = str(thread_id_val) if thread_id_val else f"sess_{user_id}"
        
    registrar_clasificacion_bd(
        user_id=user_id,
        session_id=session_id,
        mensaje=ultimo_mensaje,
        clasificacion=clasificacion,
        modelo_usado=modelo_usado,
        tiempo_ms=tiempo_ms,
        herramientas_seleccionadas=[]
    )
    
    # ✅ Determinar siguiente nodo según clasificación
    destinos = {
        "medica": "recuperacion_medica",
        "personal": "recuperacion_episodica",
        "solicitud_cita_paciente": "recepcionista",
        "chat": "generacion_resumen"
    }
    
    goto = destinos.get(clasificacion, "generacion_resumen")
    
    logger.info(f"✅ Filtrado completado → Siguiente: {goto}\n")
    
    return Command(
        update={
            "clasificacion_mensaje": clasificacion,
            "confianza_clasificacion": confianza,
            "modelo_clasificacion_usado": modelo_usado,
            "tiempo_clasificacion_ms": tiempo_ms
        },
        goto=goto
    )

# Wrapper para compatibilidad con grafo
def nodo_filtrado_inteligente_wrapper(state: WhatsAppAgentState) -> Command[Any]:
    """Wrapper para LangGraph - retorna Command directamente."""
    return nodo_filtrado_inteligente(state)
