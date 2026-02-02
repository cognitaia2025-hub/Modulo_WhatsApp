"""
Nodo 2A: Maya Detective de Intención para Pacientes

Asistente conversacional que maneja consultas básicas de pacientes sin activar 
flujo completo, reduciendo latencia de 8 seg a 1 seg en 70% de casos.

Personalidad Maya:
- Tono casual y carismática
- Máximo 1 emoji por mensaje
- Entender antes de ofrecer, escuchar antes de hablar

Información clínica hardcoded:
- Ubicación: Avenida Electricistas 1978, Colonia Libertad, Mexicali B.C.
- Teléfono: 686 108 3647
- Horario: L-V 8:30-18:30, S-D 10:30-17:30, cerrado Ma-Mi
"""

import logging
import os
from typing import Dict, Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.types import Command
from dotenv import load_dotenv

from src.state.agent_state import WhatsAppAgentState
from src.medical.crud import get_paciente_by_phone
from src.utils.logging_config import setup_colored_logging

load_dotenv()
logger = setup_colored_logging()


# ==================== PYDANTIC SCHEMA ====================

class MayaResponse(BaseModel):
    """Respuesta estructurada de Maya Detective"""
    accion: Literal["responder_directo", "escalar_procedimental", "dejar_pasar"] = Field(
        description="Acción a tomar: responder_directo para consultas básicas, escalar_procedimental para solicitudes completas de cita/cancelar/reagendar, dejar_pasar si hay flujo activo"
    )
    respuesta: str = Field(
        description="Mensaje de respuesta de Maya al paciente (solo si accion=responder_directo)"
    )
    razon: str = Field(
        description="Razonamiento interno de por qué se tomó esta acción"
    )


# ==================== CONFIGURACIÓN LLM ====================

# LLM primario: DeepSeek
llm_primary = ChatOpenAI(
    model="deepseek-chat",
    temperature=0.1,
    max_tokens=300,
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1",
    timeout=30.0,
    max_retries=0
)

# LLM fallback: Claude Sonnet (soporta structured output)
llm_fallback = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    temperature=0.1,
    max_tokens=300,
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    timeout=20.0,
    max_retries=0
)

# LLM con fallback automático y structured output
llm_with_fallback = llm_primary.with_fallbacks([llm_fallback])
llm_structured = llm_with_fallback.with_structured_output(MayaResponse)


# ==================== INFORMACIÓN CLÍNICA ====================

CLINICA_INFO = {
    "ubicacion": "Avenida Electricistas 1978, Colonia Libertad, Mexicali B.C.",
    "telefono": "686 108 3647",
    "horario_lv": "Lunes a Viernes de 8:30 AM a 6:30 PM",
    "horario_sd": "Sábados y Domingos de 10:30 AM a 5:30 PM",
    "cerrado": "Martes y Miércoles"
}


# ==================== FUNCIONES AUXILIARES ====================

def obtener_contexto_paciente(phone_number: str) -> Dict[str, Any]:
    """
    Obtiene contexto del paciente desde la base de datos.
    
    Args:
        phone_number: Número de teléfono del paciente
        
    Returns:
        Dict con información del paciente o None si no existe
    """
    try:
        paciente = get_paciente_by_phone(phone_number)
        if paciente:
            return {
                "nombre": paciente.get("nombre_completo", ""),
                "es_conocido": True,
                "paciente_id": paciente.get("id")
            }
        return {"es_conocido": False}
    except Exception as e:
        logger.error(f"❌ Error obteniendo contexto paciente: {e}")
        return {"es_conocido": False}


def obtener_fecha_hora_actual() -> str:
    """
    Obtiene fecha y hora actual en formato legible.
    
    Returns:
        String con fecha y hora actual
    """
    now = datetime.now()
    dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
             "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    
    dia_semana = dias_semana[now.weekday()]
    dia = now.day
    mes = meses[now.month - 1]
    hora = now.strftime("%I:%M %p")
    
    return f"{dia_semana} {dia} de {mes}, {hora}"


def construir_prompt_maya(mensaje: str, estado_conversacion: str, contexto_paciente: Dict[str, Any]) -> list:
    """
    Construye el prompt para Maya con personalidad y contexto.
    
    Args:
        mensaje: Mensaje del paciente
        estado_conversacion: Estado actual de la conversación
        contexto_paciente: Información del paciente
        
    Returns:
        Lista de mensajes para el LLM
    """
    fecha_hora = obtener_fecha_hora_actual()
    
    # Personalización si es paciente conocido
    nombre_paciente = contexto_paciente.get("nombre", "")
    es_conocido = contexto_paciente.get("es_conocido", False)
    
    system_prompt = f"""Eres Maya, la asistente virtual carismática de la clínica médica. Tu trabajo es manejar consultas básicas de pacientes de manera rápida y amigable.

PERSONALIDAD MAYA:
- Tono casual y carismática
- Máximo 1 emoji por mensaje
- Entender antes de ofrecer, escuchar antes de hablar
- Ser breve pero cálida

INFORMACIÓN DE LA CLÍNICA:
📍 Ubicación: {CLINICA_INFO['ubicacion']}
📞 Teléfono: {CLINICA_INFO['telefono']}
🕒 Horario: {CLINICA_INFO['horario_lv']}
🕒 Fin de semana: {CLINICA_INFO['horario_sd']}
⚠️ Cerrado: {CLINICA_INFO['cerrado']}

FECHA Y HORA ACTUAL: {fecha_hora}

═══════════════════════════════════════════════════════════════
🗓️ MANEJO ESPECIAL: AGENDAMIENTO INCOMPLETO
═══════════════════════════════════════════════════════════════

⚠️ IMPORTANTE: Cuando detectes intención de agendar SIN detalles:

SI el usuario dice:
• "Quiero agendar una cita"
• "Necesito hacer una cita"
• "Quiero sacar cita"
• (Sin mencionar día, fecha u hora)

ENTONCES (accion: "responder_directo"):
→ Pregunta: "¿Qué día y hora te gustaría tu cita? Puedes decirme ambos juntos 😊"
→ NO escales todavía

PERO SI el usuario ya dio detalles:
• "Quiero agendar el martes a las 3pm" ✅ Tiene día + hora
• "Necesito cita mañana" ✅ Tiene día
• "A las 2 de la tarde" ✅ Tiene hora

ENTONCES (accion: "escalar_procedimental"):
→ Escala al Recepcionista con la info recolectada

═══════════════════════════════════════════════════════════════
🔄 DETECCIÓN DE FLUJO ACTIVO
═══════════════════════════════════════════════════════════════

Estado actual: {estado_conversacion}

SI estado_conversacion es uno de estos:
• recolectando_fecha
• recolectando_hora
• esperando_confirmacion
• mostrando_opciones

ENTONCES (accion: "dejar_pasar"):
→ El Recepcionista ya está manejando la conversación
→ NO interfieras, deja pasar el mensaje

═══════════════════════════════════════════════════════════════
EJEMPLOS DE CONVERSACIÓN MULTI-TURNO
═══════════════════════════════════════════════════════════════

CASO 1: Agendamiento sin detalles
Usuario: "Quiero agendar una cita"
Maya: accion="responder_directo"
      respuesta="¿Qué día y hora te gustaría tu cita? Puedes decirme ambos 😊"

Usuario: "El martes a las 3pm"
Maya: accion="dejar_pasar" (estado_conversacion ya no es 'inicial')
      → Recepcionista toma control

CASO 2: Agendamiento completo desde inicio
Usuario: "Necesito cita el jueves a las 10am"
Maya: accion="escalar_procedimental"
      → Recepcionista valida y agenda directamente

CASO 3: Ya hay flujo activo
estado_conversacion = "esperando_confirmacion"
Usuario: "Sí, confírmala"
Maya: accion="dejar_pasar"
      → Recepcionista procesa confirmación

═══════════════════════════════════════════════════════════════

DECISIONES QUE DEBES TOMAR:

1. **responder_directo**: Usa esta acción para:
   - Saludos ("hola", "buenos días", "hey")
   - Preguntas sobre horarios
   - Preguntas sobre ubicación
   - "Quiero agendar una cita" SIN especificar día u hora
   - Despedidas después de completar una cita
   - Consultas generales simples

2. **escalar_procedimental**: Usa esta acción cuando el paciente:
   - Especifica DÍA + HORA para agendar ("mañana a las 3pm", "el lunes por la tarde")
   - Quiere cancelar una cita existente
   - Quiere reagendar una cita existente
   - Quiere modificar una cita existente

3. **dejar_pasar**: Usa esta acción si el estado_conversacion está en:
   - esperando_confirmacion
   - mostrando_opciones
   - esperando_seleccion
   - recolectando_fecha
   - recolectando_hora
   (Esto significa que ya hay un flujo activo en curso)

ESTADO ACTUAL DE CONVERSACIÓN: {estado_conversacion}
PACIENTE CONOCIDO: {"Sí - " + nombre_paciente if es_conocido else "No (primer contacto)"}

REGLAS IMPORTANTES:
- Si el paciente dice "quiero agendar" sin especificar cuándo → responder_directo y pregunta cuándo prefiere
- Si el paciente especifica día+hora → escalar_procedimental (ir al flujo completo)
- Si ya hay flujo activo (esperando_seleccion, etc.) → dejar_pasar
- Responde SIEMPRE en español
- Sé breve (máximo 2-3 líneas)
- Usa máximo 1 emoji
"""

    user_prompt = f"""Mensaje del paciente: "{mensaje}"

Analiza el mensaje y decide qué acción tomar. Responde con el JSON estructurado."""

    return [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]


# ==================== NODO PRINCIPAL ====================

def nodo_maya_detective_paciente(state: WhatsAppAgentState) -> Command:
    """
    Nodo principal de Maya Detective de Intención.
    
    Analiza el mensaje del paciente y decide si:
    1. Responder directamente (consultas básicas) → generacion_resumen
    2. Escalar al flujo procedimental completo → recepcionista
    3. Dejar pasar (flujo ya activo) → recepcionista
    
    Args:
        state: Estado actual del agente
        
    Returns:
        Command con update y goto para routing en un solo paso
    """
    logger.info("🔍 === MAYA DETECTIVE DE INTENCIÓN ===")
    
    # Obtener datos del estado
    messages = state.get('messages', [])
    user_id = state.get('user_id', '')
    estado_conversacion = state.get('estado_conversacion', 'inicial')
    
    # Validar mensaje
    if not messages:
        logger.error("❌ No hay mensajes en el estado")
        return Command(
            update={
                "clasificacion_mensaje": "error",
                "mensaje_final": "Error: No se recibió mensaje"
            },
            goto="generacion_resumen"
        )
    
    ultimo_mensaje = messages[-1]
    mensaje_contenido = getattr(ultimo_mensaje, 'content', '')
    
    logger.info(f"📱 Paciente: {user_id}")
    logger.info(f"💬 Mensaje: {mensaje_contenido[:100]}...")
    logger.info(f"🔄 Estado conversación: {estado_conversacion}")
    
    # Obtener contexto del paciente
    contexto_paciente = obtener_contexto_paciente(user_id)
    
    # ✅ NUEVA VALIDACIÓN: Si Recepcionista está activo, dejar pasar
    if estado_conversacion in ['recolectando_fecha', 'recolectando_hora', 
                                'esperando_confirmacion', 'mostrando_opciones']:
        logger.info(f"   🔄 Recepcionista activo (estado: {estado_conversacion}) - Dejando pasar")
        return Command(
            update={'requiere_clasificacion_llm': False},
            goto="recepcionista"
        )
    
    try:
        # Construir prompt para Maya
        prompt = construir_prompt_maya(mensaje_contenido, estado_conversacion, contexto_paciente)
        
        # Invocar LLM con structured output
        logger.info("🤖 Invocando Maya (DeepSeek/Claude)...")
        inicio = datetime.now()
        
        maya_response: MayaResponse = llm_structured.invoke(prompt)
        
        tiempo_ms = int((datetime.now() - inicio).total_seconds() * 1000)
        logger.info(f"⚡ Respuesta en {tiempo_ms}ms")
        logger.info(f"📊 Acción: {maya_response.accion}")
        logger.info(f"💭 Razón: {maya_response.razon}")
        
        # Decidir routing según acción
        if maya_response.accion == "responder_directo":
            # Maya responde directamente, NO activar flujo completo
            logger.info(f"✅ Maya responde: {maya_response.respuesta[:80]}...")
            
            return Command(
                update={
                    "clasificacion_mensaje": "maya_respuesta_directa",
                    "respuesta_maya": maya_response.respuesta,
                    "razon_maya": maya_response.razon,
                    "tiempo_maya_ms": tiempo_ms,
                    "mensaje_final": maya_response.respuesta
                },
                goto="generacion_resumen"  # Skip flujo completo
            )
            
        elif maya_response.accion == "escalar_procedimental":
            # Escalar al flujo completo de recepcionista
            logger.info("🔄 Escalando a flujo procedimental (recepcionista)")
            
            return Command(
                update={
                    "clasificacion_mensaje": "solicitud_cita_paciente",
                    "respuesta_maya": maya_response.respuesta,
                    "razon_maya": maya_response.razon,
                    "tiempo_maya_ms": tiempo_ms,
                    "ruta_siguiente": "recepcionista"
                },
                goto="recepcionista"
            )
            
        else:  # dejar_pasar
            # Ya hay flujo activo, dejar que continúe
            logger.info("⏭️ Dejando pasar (flujo ya activo)")
            
            return Command(
                update={
                    "clasificacion_mensaje": "flujo_activo",
                    "razon_maya": maya_response.razon,
                    "tiempo_maya_ms": tiempo_ms
                },
                goto="recepcionista"
            )
    
    except Exception as e:
        logger.error(f"❌ Error en Maya Detective: {e}")
        
        # Fallback: escalar al flujo completo
        return Command(
            update={
                "clasificacion_mensaje": "error_maya",
                "error_maya": str(e)
            },
            goto="recepcionista"
        )


# ==================== WRAPPER PARA GRAFO ====================

def nodo_maya_detective_paciente_wrapper(state: WhatsAppAgentState) -> Command:
    """
    Wrapper para integración con el grafo.
    """
    return nodo_maya_detective_paciente(state)