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
import json
import time
from typing import Dict
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv
import os
import psycopg

from src.state.agent_state import WhatsAppAgentState

load_dotenv()
logger = logging.getLogger(__name__)

# Configuración de LLMs
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5434/agente_whatsapp")

# LLM primario: DeepSeek
llm_primary = ChatOpenAI(
    model="deepseek-chat",
    temperature=0,
    max_tokens=200,
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1",
    timeout=30.0,
    max_retries=0
)

# LLM fallback: Claude
llm_fallback = ChatAnthropic(
    model="claude-3-5-haiku-20241022",
    temperature=0,
    max_tokens=200,
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    timeout=20.0,
    max_retries=0
)

# LLM con fallback automático
llm_with_fallback = llm_primary.with_fallbacks([llm_fallback])


def construir_prompt_clasificacion(mensaje_usuario: str, tipo_usuario: str) -> list:
    """
    Construye prompt para clasificación de mensajes
    
    Args:
        mensaje_usuario: Mensaje del usuario
        tipo_usuario: Tipo de usuario ('doctor', 'paciente_externo', etc.)
        
    Returns:
        Lista de mensajes para el LLM
    """
    system_prompt = """Eres un clasificador de mensajes médicos. Tu trabajo es clasificar mensajes en EXACTAMENTE una de estas categorías:

CATEGORÍAS PERMITIDAS:
1. "personal" - Eventos de calendario personal (cumpleaños, reuniones personales, recordatorios no médicos)
2. "medica" - Solicitudes médicas de un doctor (revisar pacientes, agendar, historiales)
3. "chat" - Conversación casual (saludos, despedidas, chat general)
4. "solicitud_cita_paciente" - Paciente externo pide cita médica

REGLAS ESTRICTAS:
- Responde ÚNICAMENTE con un JSON válido
- Formato: {"clasificacion": "CATEGORIA", "confianza": 0.95, "razonamiento": "breve explicación"}
- NO agregues texto fuera del JSON
- confianza debe ser número entre 0.0 y 1.0

EJEMPLOS:

Usuario dice: "Quiero una cita médica"
Respuesta: {"clasificacion": "solicitud_cita_paciente", "confianza": 0.95, "razonamiento": "Paciente solicita cita"}

Usuario dice (doctor): "¿Cómo está mi paciente Juan?"
Respuesta: {"clasificacion": "medica", "confianza": 0.98, "razonamiento": "Doctor pregunta por paciente"}

Usuario dice: "Hola buenos días"
Respuesta: {"clasificacion": "chat", "confianza": 0.99, "razonamiento": "Saludo casual"}

Usuario dice: "Recuérdame el cumpleaños de María"
Respuesta: {"clasificacion": "personal", "confianza": 0.97, "razonamiento": "Evento personal"}"""

    user_prompt = f"""Mensaje del usuario: "{mensaje_usuario}"
Tipo de usuario: {tipo_usuario}

Clasifica este mensaje en la categoría correcta. Responde SOLO con el JSON."""

    return [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]


def parsear_respuesta_llm(respuesta: str) -> Dict:
    """
    Parsea respuesta del LLM a diccionario
    
    Args:
        respuesta: String del LLM (JSON esperado)
        
    Returns:
        Dict con clasificacion, confianza, razonamiento
    """
    try:
        # Limpiar respuesta
        respuesta = respuesta.strip()
        
        # Extraer JSON si está envuelto en markdown
        if "```json" in respuesta:
            respuesta = respuesta.split("```json")[1].split("```")[0].strip()
        elif "```" in respuesta:
            respuesta = respuesta.split("```")[1].split("```")[0].strip()
        
        # Parsear JSON
        resultado = json.loads(respuesta)
        
        # Validar campos requeridos
        if "clasificacion" not in resultado:
            raise ValueError("Falta campo 'clasificacion'")
        
        # Valores por defecto
        return {
            "clasificacion": resultado["clasificacion"],
            "confianza": resultado.get("confianza", 0.8),
            "razonamiento": resultado.get("razonamiento", "Sin razonamiento")
        }
    
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"❌ Error parseando respuesta LLM: {e}")
        logger.error(f"    Respuesta recibida: {respuesta}")
        
        # Fallback: clasificar como chat
        return {
            "clasificacion": "chat",
            "confianza": 0.5,
            "razonamiento": "Error en parseo, clasificado como chat por defecto"
        }


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
    user_phone: str,
    mensaje: str,
    clasificacion: str,
    confianza: float,
    modelo_usado: str,
    tipo_usuario: str,
    tiempo_ms: int,
    hubo_fallback: bool,
    razon_fallback: str = None
):
    """
    Registra clasificación en la base de datos para auditoría
    
    Args:
        user_phone: Teléfono del usuario
        mensaje: Mensaje clasificado
        clasificacion: Clasificación asignada
        confianza: Nivel de confianza (0.0-1.0)
        modelo_usado: Modelo LLM usado
        tipo_usuario: Tipo de usuario
        tiempo_ms: Tiempo de procesamiento en ms
        hubo_fallback: Si se usó fallback
        razon_fallback: Razón del fallback
    """
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO clasificaciones_llm (
                        user_phone,
                        mensaje_usuario,
                        clasificacion,
                        confianza,
                        modelo_usado,
                        tipo_usuario,
                        tiempo_procesamiento_ms,
                        hubo_fallback,
                        razon_fallback
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    user_phone,
                    mensaje[:500],  # Limitar tamaño
                    clasificacion,
                    confianza,
                    modelo_usado,
                    tipo_usuario,
                    tiempo_ms,
                    hubo_fallback,
                    razon_fallback
                ))
                conn.commit()
        
        logger.info(f"✅ Clasificación registrada en BD: {clasificacion}")
    
    except Exception as e:
        logger.error(f"❌ Error registrando clasificación: {e}")
        # No fallar el flujo principal si falla el registro


def nodo_filtrado_inteligente(state: WhatsAppAgentState) -> Dict:
    """
    Nodo de filtrado inteligente con LLM
    
    Flujo:
    1. Extrae último mensaje del usuario
    2. Construye prompt de clasificación
    3. Llama a LLM (DeepSeek con fallback a Claude)
    4. Parsea respuesta
    5. Valida según tipo de usuario
    6. Registra en BD para auditoría
    7. Actualiza state
    
    Args:
        state: WhatsAppAgentState
        
    Returns:
        Dict con actualizaciones del state
    """
    logger.info("\n" + "=" * 70)
    logger.info("🔍 NODO: FILTRADO INTELIGENTE")
    logger.info("=" * 70)
    
    inicio = time.time()
    
    # Extraer datos del state
    messages = state.get("messages", [])
    tipo_usuario = state.get("tipo_usuario", "paciente_externo")
    user_id = state.get("user_id", "unknown")
    
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
        return {
            "clasificacion_mensaje": "chat",
            "confianza_clasificacion": 0.5
        }
    
    logger.info(f"📝 Mensaje: {ultimo_mensaje[:100]}...")
    logger.info(f"👤 Tipo usuario: {tipo_usuario}")
    
    # Construir prompt
    prompt_messages = construir_prompt_clasificacion(ultimo_mensaje, tipo_usuario)
    
    # Llamar a LLM con fallback
    modelo_usado = "deepseek"
    hubo_fallback = False
    razon_fallback = None
    
    try:
        logger.info("🤖 Llamando a DeepSeek...")
        respuesta_llm = llm_primary.invoke(prompt_messages)
        modelo_usado = "deepseek"
    
    except Exception as e:
        logger.warning(f"⚠️  DeepSeek falló: {e}")
        logger.info("🔄 Intentando con Claude (fallback)...")
        
        try:
            respuesta_llm = llm_fallback.invoke(prompt_messages)
            modelo_usado = "claude"
            hubo_fallback = True
            razon_fallback = str(e)[:200]
        
        except Exception as e2:
            logger.error(f"❌ Ambos LLMs fallaron: {e2}")
            
            # Fallback final: clasificar como chat
            return {
                "clasificacion_mensaje": "chat",
                "confianza_clasificacion": 0.3
            }
    
    # Parsear respuesta
    resultado = parsear_respuesta_llm(respuesta_llm.content)
    
    clasificacion = resultado["clasificacion"]
    confianza = resultado["confianza"]
    razonamiento = resultado["razonamiento"]
    
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
    registrar_clasificacion_bd(
        user_phone=user_id,
        mensaje=ultimo_mensaje,
        clasificacion=clasificacion,
        confianza=confianza,
        modelo_usado=modelo_usado,
        tipo_usuario=tipo_usuario,
        tiempo_ms=tiempo_ms,
        hubo_fallback=hubo_fallback,
        razon_fallback=razon_fallback
    )
    
    logger.info("✅ Filtrado inteligente completado\n")
    
    # Retornar actualizaciones del state
    return {
        "clasificacion_mensaje": clasificacion,
        "confianza_clasificacion": confianza,
        "modelo_clasificacion_usado": modelo_usado,
        "tiempo_clasificacion_ms": tiempo_ms
    }


# Wrapper para compatibilidad con grafo
def nodo_filtrado_inteligente_wrapper(state: WhatsAppAgentState) -> WhatsAppAgentState:
    """
    Wrapper que mantiene la firma esperada por el grafo
    """
    try:
        # Llamar al nodo principal
        resultado = nodo_filtrado_inteligente(state)
        
        # Retornar solo las actualizaciones del estado (no el estado completo)
        return {
            "clasificacion_mensaje": resultado.get("clasificacion_mensaje", "chat"),
            "confianza_clasificacion": resultado.get("confianza_clasificacion", 0.0),
            "modelo_clasificacion_usado": resultado.get("modelo_clasificacion_usado", "fallback"),
            "tiempo_clasificacion_ms": resultado.get("tiempo_clasificacion_ms", 0)
        }
        
    except Exception as e:
        logger.error(f"❌ Error en nodo filtrado inteligente: {e}")

        # Respuesta de fallback
        return {
            "clasificacion_mensaje": "chat",
            "confianza_clasificacion": 0.0,
            "modelo_clasificacion_usado": "fallback_error",
            "tiempo_clasificacion_ms": 0
        }
