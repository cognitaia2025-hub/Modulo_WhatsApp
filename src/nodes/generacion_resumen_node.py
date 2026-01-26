"""
Nodo 6: Generación de Resúmenes (Auditoría)

Este nodo actúa como "auditor" de la sesión, transformando la conversación
cruda en una cápsula de conocimiento estructurado.

Responsabilidades:
- Extraer hechos, pendientes, perfil y estado
- Generar resumen ejecutivo (<100 palabras)
- Comportamiento especial para sesión expirada (retomar hilo)
- Incluir timestamp de Mexicali
- Preparar texto para Nodo 7 (persistencia pgvector)
"""

import logging
from typing import Dict, List, Any
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from src.utils.time_utils import get_current_time
import os
from dotenv import load_dotenv

# ✅ Imports para memoria semántica
from langgraph.store.base import BaseStore
from src.memory import update_semantic_memory

load_dotenv()

logger = logging.getLogger(__name__)

# LLM principal para auditoría
llm_primary = ChatOpenAI(
    model="deepseek-chat",
    temperature=0.2,  # Más preciso para resúmenes concisos
    max_tokens=120,   # Límite estricto: ~80-100 palabras
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1",
    timeout=15.0,  # Timeout reducido a 15 segundos
    max_retries=0  # ✅ Reintentos los maneja LangGraph
)

# Fallback: Claude Haiku 4.5 (análisis rápido)
llm_fallback = ChatAnthropic(
    model="claude-3-5-haiku-20241022",
    temperature=0.2,
    max_tokens=120,
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    timeout=15.0,
    max_retries=0
)

# Auditor con fallback automático
llm_auditor = llm_primary.with_fallbacks([llm_fallback])


def extraer_mensajes_relevantes(messages: List[Any]) -> str:
    """
    Extrae y formatea los mensajes de la conversación excluyendo ruido.
    
    Args:
        messages: Lista de mensajes del state
        
    Returns:
        String con conversación formateada
    """
    conversacion = []
    
    for msg in messages:
        # Extraer contenido según tipo de mensaje
        if hasattr(msg, 'content'):
            contenido = msg.content
        elif isinstance(msg, dict) and 'content' in msg:
            contenido = msg['content']
        else:
            contenido = str(msg)
        
        # Extraer rol
        if hasattr(msg, 'role'):
            rol = msg.role
        elif isinstance(msg, dict) and 'role' in msg:
            rol = msg['role']
        elif hasattr(msg, '__class__'):
            rol = 'ai' if 'AI' in msg.__class__.__name__ else 'user'
        else:
            rol = 'desconocido'
        
        # Filtrar mensajes vacíos o muy cortos
        if contenido and len(contenido.strip()) > 2:
            conversacion.append(f"{rol.upper()}: {contenido}")
    
    return "\n".join(conversacion) if conversacion else ""


def construir_prompt_auditoria(
    conversacion: str,
    contexto_episodico: Any,
    sesion_expirada: bool
) -> str:
    """
    Construye el prompt de auditoría para el LLM según el contexto.
    
    Args:
        conversacion: Conversación formateada
        contexto_episodico: Memoria de conversaciones previas
        sesion_expirada: Si la sesión fue interrumpida por timeout
        
    Returns:
        Prompt estructurado para el auditor
    """
    timestamp = get_current_time().format('dddd, DD [de] MMMM [de] YYYY [a las] HH:mm', locale='es')
    
    # Extraer contexto previo si existe
    contexto_previo = ""
    if contexto_episodico and isinstance(contexto_episodico, dict):
        if 'resumen' in contexto_episodico:
            contexto_previo = f"\nCONTEXTO PREVIO:\n{contexto_episodico['resumen']}\n"
    
    # Instrucción especial para sesión expirada
    enfoque_especial = ""
    if sesion_expirada:
        enfoque_especial = """
⚠️ IMPORTANTE: Esta sesión fue interrumpida hace 24 horas por timeout.
Tu resumen debe permitir retomar la conversación EXACTAMENTE donde se quedó.
Prioriza:
- Estado específico de la tarea (completada/pendiente/interrumpida)
- Última petición del usuario que quedó sin resolver
- Contexto necesario para continuar sin repetir información
"""
    
    prompt = f"""Resume esta conversación de WhatsApp en MÁXIMO 50 PALABRAS.

FECHA: {timestamp}
{contexto_previo}
CONVERSACIÓN:
{conversacion}
{enfoque_especial}
Incluye: (1) Qué se hizo, (2) Qué falta, (3) Estado (completada/pendiente).
Usa texto plano SIN formato markdown. Sé directo y conciso.

Si no hay info relevante, responde solo: "Sin cambios relevantes"

RESUMEN:"""
    
    return prompt


def nodo_generacion_resumen(state: Dict[str, Any], store: BaseStore) -> Dict[str, Any]:
    """
    Nodo 6: Genera resumen ejecutivo de la sesión para memoria a largo plazo.

    Este nodo es la "auditoría" que transforma conversación cruda en
    conocimiento estructurado antes de persistir en pgvector.

    También actualiza preferencias del usuario usando LLM structured output.

    Args:
        state: Estado del grafo con messages, contexto_episodico, sesion_expirada
        store: BaseStore con memoria semántica (inyectado por LangGraph)

    Returns:
        State actualizado con resumen_actual
    """
    logger.info("📝 [6] NODO_GENERACION_RESUMEN - Auditando sesión")

    messages = state.get('messages', [])
    contexto_episodico = state.get('contexto_episodico')
    sesion_expirada = state.get('sesion_expirada', False)
    user_id = state.get('user_id', 'default_user')
    
    # Validar que hay suficientes mensajes para resumir
    if len(messages) < 2:
        logger.info("    ⚠️  Pocos mensajes para generar resumen")
        return {
            **state,
            'resumen_actual': "Sin cambios relevantes"
        }
    
    # Extraer conversación relevante
    conversacion = extraer_mensajes_relevantes(messages)
    
    if not conversacion or len(conversacion.strip()) < 10:
        logger.info("    ⚠️  No hay contenido relevante para resumir")
        return {
            **state,
            'resumen_actual': "Sin cambios relevantes"
        }
    
    logger.info(f"    📋 Conversación a auditar: {len(conversacion)} caracteres")
    logger.info(f"    {'⏰' if sesion_expirada else '✅'} Modo: {'RECUPERACIÓN (sesión expirada)' if sesion_expirada else 'NORMAL'}")
    
    # Construir prompt de auditoría
    prompt = construir_prompt_auditoria(
        conversacion=conversacion,
        contexto_episodico=contexto_episodico,
        sesion_expirada=sesion_expirada
    )
    
    try:
        # Invocar LLM auditor
        logger.info("    🤖 Invocando auditor LLM...")
        respuesta = llm_auditor.invoke(prompt)
        resumen = respuesta.content.strip()
        
        # Añadir timestamp al resumen
        timestamp = get_current_time().format('DD/MM/YYYY HH:mm', locale='es')
        resumen_con_fecha = f"[{timestamp}] {resumen}"
        
        logger.info(f"    ✅ Resumen generado: '{resumen[:80]}...'")
        logger.info(f"    📊 Longitud: {len(resumen)} caracteres")

        # ✅ Actualizar preferencias del usuario automáticamente
        try:
            logger.info("    🧠 Actualizando preferencias del usuario...")
            update_semantic_memory(
                state=state,
                store=store,
                user_id=user_id,
                llm=llm_auditor  # Reutilizar el mismo LLM auditor
            )
            logger.info("    ✅ Preferencias procesadas")
        except Exception as pref_error:
            logger.error(f"    ❌ Error actualizando preferencias: {pref_error}")
            import traceback
            logger.error(traceback.format_exc())

        return {
            **state,
            'resumen_actual': resumen_con_fecha
        }
        
    except Exception as e:
        logger.error(f"    ❌ Error al generar resumen: {e}")
        
        # Fallback: Resumen básico sin LLM
        timestamp = get_current_time().format('DD/MM/YYYY HH:mm', locale='es')
        resumen_fallback = f"[{timestamp}] Conversación con {len(messages)} mensajes. Estado: {'Sesión expirada' if sesion_expirada else 'Activa'}."
        
        return {
            **state,
            'resumen_actual': resumen_fallback
        }


def nodo_generacion_resumen_wrapper(state: Dict[str, Any], store: BaseStore) -> Dict[str, Any]:
    """
    Wrapper para compatibilidad con LangGraph.
    Recibe store de LangGraph (REQUERIDO) y lo pasa al nodo principal.
    """
    return nodo_generacion_resumen(state, store)


if __name__ == "__main__":
    """
    Test standalone del nodo de auditoría.
    """
    print("\n🧪 Test del Nodo 6: Generación de Resúmenes\n")
    
    # Test 1: Conversación normal con agendamiento
    print("Test 1: Conversación con agendamiento")
    state_test1 = {
        'messages': [
            {'role': 'user', 'content': 'Necesito agendar una reunión para mañana'},
            {'role': 'ai', 'content': '¿A qué hora te gustaría agendar?'},
            {'role': 'user', 'content': 'A las 3 de la tarde'},
            {'role': 'ai', 'content': 'Perfecto, agendé tu reunión para mañana a las 15:00'}
        ],
        'user_id': 'test_user',
        'session_id': 'session_test1',
        'contexto_episodico': None,
        'sesion_expirada': False
    }
    
    resultado1 = nodo_generacion_resumen(state_test1)
    print(f"✅ Resumen: {resultado1['resumen_actual']}\n")
    
    # Test 2: Sesión expirada con tarea pendiente
    print("Test 2: Sesión expirada (recuperación)")
    state_test2 = {
        'messages': [
            {'role': 'user', 'content': 'Ponme una cita para el miércoles pero déjame confirmar el lugar'},
            {'role': 'ai', 'content': 'Ok, ¿a qué hora?'},
            {'role': 'user', 'content': 'A las 10 am'}
        ],
        'user_id': 'test_user',
        'session_id': 'session_test2',
        'contexto_episodico': {
            'resumen': 'Usuario prefiere reuniones por la mañana'
        },
        'sesion_expirada': True
    }
    
    resultado2 = nodo_generacion_resumen(state_test2)
    print(f"✅ Resumen: {resultado2['resumen_actual']}\n")
    
    # Test 3: Conversación sin contenido relevante
    print("Test 3: Sin contenido relevante")
    state_test3 = {
        'messages': [
            {'role': 'user', 'content': 'Hola'},
            {'role': 'ai', 'content': '¡Hola! ¿En qué puedo ayudarte?'}
        ],
        'user_id': 'test_user',
        'session_id': 'session_test3',
        'contexto_episodico': None,
        'sesion_expirada': False
    }
    
    resultado3 = nodo_generacion_resumen(state_test3)
    print(f"✅ Resumen: {resultado3['resumen_actual']}\n")
    
    print("🎉 Tests completados")
