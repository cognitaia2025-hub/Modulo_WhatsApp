"""
Nodo: Filtrado Inteligente con LLM

Clasifica mensajes de usuarios en:
- 'personal': Eventos de calendario personal
- 'medica': Solicitudes médicas (solo doctores)
- 'chat': Conversación casual
- 'solicitud_cita_paciente': Pacientes externos solo pueden pedir citas

Estrategia:
1. LLM (DeepSeek) clasifica el mensaje
2. Fallback automático a Claude si DeepSeek falla
3. Validación post-LLM: Pacientes externos → SOLO solicitud_cita_paciente
4. Auditoría en tabla clasificaciones_llm
"""

import logging
import time
from typing import Dict, Literal
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.types import Command
from pydantic import BaseModel, Field
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
    
    clasificacion: Literal["personal", "medica", "solicitud_cita_paciente", "chat"] = Field(
        description="""
        Categoría del mensaje:
        - personal: Eventos de calendario personal
        - medica: Solicitudes médicas de doctores
        - solicitud_cita_paciente: Paciente externo pide cita
        - chat: Conversación casual
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


# ==================== CONFIGURACIÓN LLM CON STRUCTURED OUTPUT ====================

# LLM primario: DeepSeek con structured output
llm_primary_base = ChatOpenAI(
    model="deepseek-chat",
    temperature=0,
    max_tokens=200,
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1",
    timeout=10.0,  # ✅ Reducido de 30s a 10s (alineado con Maya)
    max_retries=0
)

# LLM fallback: Claude con structured output
llm_fallback_base = ChatAnthropic(
    model="claude-3-5-haiku-20241022",
    temperature=0,
    max_tokens=200,
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    timeout=10.0,  # ✅ Reducido de 20s a 10s
    max_retries=0
)

# Configurar structured output
llm_primary = llm_primary_base.with_structured_output(
    ClasificacionResponse,
    method="json_schema",
    strict=True
)

llm_fallback = llm_fallback_base.with_structured_output(
    ClasificacionResponse,
    method="json_schema",
    strict=True
)


# ==================== CONSTANTES ====================

# Estados conversacionales que requieren saltar clasificación
ESTADOS_FLUJO_ACTIVO = [
    'recolectando_fecha',
    'recolectando_hora', 
    'esperando_confirmacion',
    'mostrando_opciones'
]

# Mapeo de estados a nodos destino
MAPEO_ESTADO_A_NODO = {
    'recolectando_fecha': 'recepcionista',
    'recolectando_hora': 'recepcionista',
    'esperando_confirmacion': 'recepcionista',
    'mostrando_opciones': 'generacion_resumen'
}


def construir_prompt_clasificacion(mensaje_usuario: str, tipo_usuario: str) -> list:
    """
    Construye prompt mejorado para clasificación de mensajes
    """
    system_prompt = """Eres un clasificador de mensajes para una clínica médica.

═══════════════════════════════════════════════════════════════
CATEGORÍAS DISPONIBLES
═══════════════════════════════════════════════════════════════

1. "personal" - Eventos de calendario personal
   • Cumpleaños, aniversarios
   • Reuniones personales
   • Recordatorios no médicos
   • Ejemplos: "Recuérdame el cumpleaños de María", "Tengo junta el viernes"

2. "medica" - Solicitudes médicas (SOLO DOCTORES)
   • Consultar pacientes específicos
   • Revisar historiales médicos
   • Agendar citas para pacientes
   • Ejemplos: "¿Cómo está mi paciente Juan?", "Agendar consulta para María"

3. "solicitud_cita_paciente" - Paciente externo pide cita
   • Cualquier intención de agendar del paciente
   • Consultas sobre disponibilidad
   • Ejemplos: "Quiero una cita", "Necesito agendar", "¿Tienen espacio mañana?"

4. "chat" - Conversación casual
   • Saludos y despedidas
   • Agradecimientos
   • Conversación general sin intención específica
   • Ejemplos: "Hola", "Gracias", "Hasta luego"

═══════════════════════════════════════════════════════════════
REGLAS DE CLASIFICACIÓN
═══════════════════════════════════════════════════════════════

⚠️ IMPORTANTE:

• Pacientes externos SOLO pueden tener "solicitud_cita_paciente" o "chat"
• Doctores pueden tener cualquier categoría
• Si dudas entre dos categorías, usa la más específica
• Confianza alta (>0.9) solo si estás muy seguro

═══════════════════════════════════════════════════════════════
EJEMPLOS COMPLETOS
═══════════════════════════════════════════════════════════════

Entrada: "Quiero agendar una cita"
Usuario: paciente_externo
Salida: {"clasificacion": "solicitud_cita_paciente", "confianza": 0.98, "razonamiento": "Paciente solicita cita directamente"}

Entrada: "¿Cómo está mi paciente Juan Pérez?"
Usuario: doctor
Salida: {"clasificacion": "medica", "confianza": 0.99, "razonamiento": "Doctor pregunta por paciente específico"}

Entrada: "Recuérdame el cumpleaños de mi esposa"
Usuario: doctor
Salida: {"clasificacion": "personal", "confianza": 0.95, "razonamiento": "Evento personal no relacionado con medicina"}

Entrada: "Hola buenos días"
Usuario: paciente_externo
Salida: {"clasificacion": "chat", "confianza": 0.99, "razonamiento": "Saludo casual sin intención específica"}

Entrada: "Gracias por la información"
Usuario: doctor
Salida: {"clasificacion": "chat", "confianza": 0.97, "razonamiento": "Agradecimiento general"}

Entrada: "Necesito ver a María García hoy"
Usuario: doctor
Salida: {"clasificacion": "medica", "confianza": 0.96, "razonamiento": "Doctor solicita atender paciente específico"}"""

    user_prompt = f"""Clasifica este mensaje:

Mensaje: "{mensaje_usuario}"
Tipo de usuario: {tipo_usuario}

Analiza el mensaje y responde con la clasificación correcta."""

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
    herramientas_seleccionadas: list = None
):
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


def nodo_filtrado_inteligente(state: WhatsAppAgentState) -> Command:
    """
    Nodo de filtrado inteligente con LLM
    """
    logger.info("\n" + "=" * 70)
    logger.info("🔍 NODO: FILTRADO INTELIGENTE")
    logger.info("=" * 70)
    
    inicio = time.time()
    
    # Extraer datos del state
    messages = state.get("messages", [])
    tipo_usuario = state.get("tipo_usuario", "paciente_externo")
    user_id = state.get("user_id", "unknown")
    estado_conversacion = state.get("estado_conversacion", "inicial")  # ✅ NUEVO
    
    # ✅ NUEVA VALIDACIÓN: Si hay flujo activo, dejar pasar sin clasificar
    if estado_conversacion in ESTADOS_FLUJO_ACTIVO:
        logger.info(f"   🔄 Flujo activo detectado (estado: {estado_conversacion}) - Saltando clasificación")
        
        # Determinar siguiente nodo según estado
        goto = MAPEO_ESTADO_A_NODO.get(estado_conversacion, "generacion_resumen")
        
        return Command(
            update={'requiere_clasificacion_llm': False},
            goto=goto
        )
    
    # Extraer último mensaje
    ultimo_mensaje = ""
    for msg in reversed(messages):
        if hasattr(msg, "type") and msg.type == "human":
            ultimo_mensaje = msg.content
            break
        elif isinstance(msg, dict) and msg.get("role") == "user":
            ultimo_mensaje = msg.get("content", "")
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
    logger.info(f"👤 Tipo usuario: {tipo_usuario}")
    
    # Construir prompt
    prompt_messages = construir_prompt_clasificacion(ultimo_mensaje, tipo_usuario)
    
    # Llamar a LLM con fallback
    modelo_usado = "deepseek"
    
    try:
        logger.info("🤖 Llamando a DeepSeek con structured output...")
        resultado: ClasificacionResponse = llm_primary.invoke(prompt_messages)
        modelo_usado = "deepseek"
    
    except Exception as e:
        logger.warning(f"⚠️  DeepSeek falló: {e}")
        logger.info("🔄 Intentando con Claude (fallback)...")
        
        try:
            resultado: ClasificacionResponse = llm_fallback.invoke(prompt_messages)
            modelo_usado = "claude"
        
        except Exception as e2:
            logger.error(f"❌ Ambos LLMs fallaron: {e2}")
            
            # Fallback final: clasificar como chat
            return Command(
                update={
                    "clasificacion_mensaje": "chat",
                    "confianza_clasificacion": 0.3,
                    "modelo_clasificacion_usado": "fallback"
                },
                goto="generacion_resumen"
            )
    
    # ✅ Ya no necesitamos parsear - Pydantic lo hizo
    clasificacion = resultado.clasificacion
    confianza = resultado.confianza
    razonamiento = resultado.razonamiento
    
    logger.info(f"📊 Clasificación: {clasificacion}")
    logger.info(f"💯 Confianza: {confianza}")
    logger.info(f"💭 Razonamiento: {razonamiento}")
    
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
    session_id = state.get("session_id", f"session_{user_id}")
    registrar_clasificacion_bd(
        user_id=user_id,
        session_id=session_id,
        mensaje=ultimo_mensaje,
        clasificacion=clasificacion,
        modelo_usado=modelo_usado,
        tiempo_ms=tiempo_ms,
        herramientas_seleccionadas=[]
    )
    
    # ✅ NUEVO: Determinar siguiente nodo según clasificación
    destinos = {
        "medica": "recuperacion_medica",
        "personal": "recuperacion_episodica",
        "solicitud_cita_paciente": "recepcionista",
        "chat": "generacion_resumen"
    }
    
    goto = destinos.get(clasificacion, "generacion_resumen")
    
    logger.info(f"✅ Filtrado completado → Siguiente: {goto}\n")
    
    # ✅ Retornar Command (no Dict)
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
def nodo_filtrado_inteligente_wrapper(state: WhatsAppAgentState) -> Command:
    """Wrapper para LangGraph - retorna Command directamente."""
    return nodo_filtrado_inteligente(state)
