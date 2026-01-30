"""
Nodo de Respuesta Conversacional (Chat Casual)

Este nodo maneja saludos y conversaciones casuales que no requieren
herramientas ni operaciones específicas. Genera respuestas amigables
y orienta al usuario hacia los servicios disponibles.

Responsabilidades:
- Generar respuestas amigables para saludos
- Informar sobre servicios disponibles
- Mantener contexto conversacional
- Pasar al nodo de auditoría (generacion_resumen)

Casos de uso:
- "Hola, buenos días" → Bienvenida + oferta de servicios
- "¿Qué pueden hacer?" → Explicación de capacidades
- Despedidas, agradecimientos, etc.
"""

import logging
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage
from src.utils.time_utils import get_current_time
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ==================== LLM CONFIGURATION ====================

# LLM principal para respuestas conversacionales
llm_primary = ChatOpenAI(
    model="deepseek-chat",
    temperature=0.7,  # Más creativo para respuestas naturales
    max_tokens=200,   # Respuestas breves pero completas
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1",
    timeout=10.0,
    max_retries=0
)

# Fallback: Claude Haiku (respuestas rápidas)
llm_fallback = ChatAnthropic(
    model="claude-3-5-haiku-20241022",
    temperature=0.7,
    max_tokens=200,
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    timeout=10.0,
    max_retries=0
)

# LLM con fallback automático
llm_conversacional = llm_primary.with_fallbacks([llm_fallback])


# ==================== PROMPT TEMPLATES ====================

PROMPT_BIENVENIDA = """Eres un asistente virtual amigable de una clínica médica.
Un usuario te ha saludado. Responde de manera:
- Cálida y profesional
- Breve (máximo 2-3 oraciones)
- Mencionando que puedes ayudar con citas médicas

Hora actual: {hora_actual}
Mensaje del usuario: "{mensaje}"

Responde en español de México, de forma natural y acogedora.
NO uses emojis excesivos. Máximo 1-2 emojis si son apropiados.

Tu respuesta:"""

PROMPT_GENERAL = """Eres un asistente virtual de una clínica médica.
El usuario ha enviado un mensaje casual. Responde de manera:
- Amable y servicial
- Breve pero útil
- Orientando hacia los servicios disponibles (citas médicas)

Hora actual: {hora_actual}
Mensaje del usuario: "{mensaje}"

Servicios disponibles:
- Agendar citas médicas
- Consultar horarios disponibles
- Gestionar citas existentes

Responde en español de México, de forma natural.

Tu respuesta:"""


# ==================== HELPER FUNCTIONS ====================

def es_saludo(mensaje: str) -> bool:
    """Detecta si el mensaje es un saludo."""
    saludos = [
        'hola', 'buenos días', 'buenas tardes', 'buenas noches',
        'buen día', 'hey', 'hi', 'hello', 'qué tal', 'que tal',
        'cómo estás', 'como estas', 'saludos'
    ]
    mensaje_lower = mensaje.lower().strip()
    return any(saludo in mensaje_lower for saludo in saludos)


def es_despedida(mensaje: str) -> bool:
    """Detecta si el mensaje es una despedida."""
    despedidas = [
        'adiós', 'adios', 'bye', 'chao', 'hasta luego',
        'nos vemos', 'gracias', 'muchas gracias', 'hasta pronto'
    ]
    mensaje_lower = mensaje.lower().strip()
    return any(despedida in mensaje_lower for despedida in despedidas)


def obtener_mensaje_usuario(state: Dict[str, Any]) -> str:
    """Extrae el último mensaje del usuario del state."""
    messages = state.get('messages', [])
    
    for msg in reversed(messages):
        if hasattr(msg, 'content') and hasattr(msg, 'type'):
            if msg.type == 'human':
                return msg.content
        elif isinstance(msg, dict):
            if msg.get('role') == 'user':
                return msg.get('content', '')
    
    return ""


# ==================== MAIN NODE ====================

def nodo_respuesta_conversacional(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Nodo para generar respuestas conversacionales (chat casual).
    
    Maneja saludos, despedidas y mensajes generales que no requieren
    herramientas específicas.
    
    Args:
        state: Estado del grafo con messages, clasificacion_mensaje, etc.
        
    Returns:
        State actualizado con respuesta en messages y respuesta_generada
    """
    logger.info("💬 [RESPUESTA_CONVERSACIONAL] Procesando mensaje casual")
    
    clasificacion = state.get('clasificacion_mensaje', 'chat')
    mensaje = obtener_mensaje_usuario(state)
    
    if not mensaje:
        logger.warning("    ⚠️  No se encontró mensaje del usuario")
        respuesta = "¡Hola! Soy el asistente de la clínica. ¿En qué puedo ayudarte hoy? 🏥"
    else:
        logger.info(f"    📨 Mensaje: '{mensaje[:50]}...'")
        logger.info(f"    🏷️  Clasificación: {clasificacion}")
        
        try:
            # Obtener hora actual
            hora_actual = get_current_time().format('dddd, DD [de] MMMM [de] YYYY [a las] HH:mm', locale='es')
            
            # Seleccionar prompt según tipo de mensaje
            if es_saludo(mensaje):
                logger.info("    👋 Tipo: SALUDO")
                prompt = PROMPT_BIENVENIDA.format(
                    hora_actual=hora_actual,
                    mensaje=mensaje
                )
            elif es_despedida(mensaje):
                logger.info("    🚪 Tipo: DESPEDIDA")
                respuesta = "¡Hasta luego! Fue un gusto atenderte. Recuerda que estamos aquí cuando necesites agendar una cita. 👋"
                # Skip LLM for simple farewell
                return _crear_respuesta_state(state, respuesta)
            else:
                logger.info("    💭 Tipo: MENSAJE GENERAL")
                prompt = PROMPT_GENERAL.format(
                    hora_actual=hora_actual,
                    mensaje=mensaje
                )
            
            # Invocar LLM
            logger.info("    🤖 Generando respuesta con LLM...")
            response = llm_conversacional.invoke(prompt)
            respuesta = response.content.strip()
            
            logger.info(f"    ✅ Respuesta generada: '{respuesta[:60]}...'")
            
        except Exception as e:
            logger.error(f"    ❌ Error generando respuesta: {e}")
            # Fallback sin LLM
            respuesta = "¡Hola! Soy el asistente virtual de la clínica. ¿Te gustaría agendar una cita médica?"
    
    return _crear_respuesta_state(state, respuesta)


def _crear_respuesta_state(state: Dict[str, Any], respuesta: str) -> Dict[str, Any]:
    """Crea el state de respuesta con el mensaje añadido."""
    ai_message = AIMessage(content=respuesta)
    
    messages = state.get('messages', [])
    
    return {
        **state,
        'messages': messages + [ai_message],
        'respuesta_generada': respuesta,
        'nodo_ejecutado': 'respuesta_conversacional'
    }


def nodo_respuesta_conversacional_wrapper(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Wrapper para compatibilidad con LangGraph.
    No requiere store ya que no usa memoria semántica.
    """
    return nodo_respuesta_conversacional(state)


# ==================== STANDALONE TEST ====================

if __name__ == "__main__":
    """Test standalone del nodo."""
    from langchain_core.messages import HumanMessage
    
    print("\n🧪 Test del Nodo: Respuesta Conversacional\n")
    
    # Test 1: Saludo
    print("Test 1: Saludo simple")
    state_test1 = {
        'messages': [HumanMessage(content="Hola, buenos días")],
        'clasificacion_mensaje': 'chat',
        'user_id': 'test_user'
    }
    resultado1 = nodo_respuesta_conversacional(state_test1)
    print(f"✅ Respuesta: {resultado1.get('respuesta_generada', 'N/A')}\n")
    
    # Test 2: Pregunta general
    print("Test 2: Pregunta general")
    state_test2 = {
        'messages': [HumanMessage(content="¿Qué servicios tienen?")],
        'clasificacion_mensaje': 'chat',
        'user_id': 'test_user'
    }
    resultado2 = nodo_respuesta_conversacional(state_test2)
    print(f"✅ Respuesta: {resultado2.get('respuesta_generada', 'N/A')}\n")
    
    # Test 3: Despedida
    print("Test 3: Despedida")
    state_test3 = {
        'messages': [HumanMessage(content="Gracias, hasta luego")],
        'clasificacion_mensaje': 'chat',
        'user_id': 'test_user'
    }
    resultado3 = nodo_respuesta_conversacional(state_test3)
    print(f"✅ Respuesta: {resultado3.get('respuesta_generada', 'N/A')}\n")
    
    print("🎉 Tests completados")
