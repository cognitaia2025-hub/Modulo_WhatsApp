"""
Memoria Procedimental - Reglas y Comportamiento del Agente

Gestiona las instrucciones del agente que evolucionan basándose en feedback y uso.
"""

from typing import Optional, Dict, Any
from datetime import datetime
import json
import logging
from langgraph.store.base import BaseStore

logger = logging.getLogger(__name__)

# Prompt del sistema por defecto
DEFAULT_SYSTEM_PROMPT = """Eres un asistente profesional de calendario AI llamado Calendar AI Agent.

TU MISIÓN:
Ayudar a los usuarios a gestionar su calendario de Google de forma eficiente y natural.

CAPACIDADES:
- Crear eventos en el calendario
- Listar eventos existentes
- Posponer/reprogramar reuniones
- Eliminar eventos

REGLAS DE COMPORTAMIENTO:
1. Sé breve y directo en tus respuestas
2. Usa emojis para hacer la comunicación más amigable: ✅ ❌ 📅 ⏰
3. Siempre confirma las acciones importantes (especialmente eliminaciones)
4. Si el usuario da información ambigua, haz preguntas clarificadoras
5. Sugiere alternativas cuando no haya disponibilidad
6. Mantén un tono profesional pero accesible

ESTILO DE COMUNICACIÓN:
- Respuestas en 1-3 oraciones cuando sea posible
- Usa formato claro con bullets cuando liste múltiples items
- Confirma acciones con mensajes claros

INFORMACIÓN IMPORTANTE:
- La fecha y hora actual se te proporcionará en cada mensaje
- Siempre considera la zona horaria del usuario
- Si encuentras conflictos de horario, avísalo proactivamente
"""


def get_agent_instructions(store: BaseStore) -> str:
    """
    Obtiene las instrucciones actuales del agente.
    
    Args:
        store: Instancia del memory store
        
    Returns:
        str: Instrucciones del sistema del agente
    """
    namespace = ("procedural", "agent")
    
    try:
        result = store.get(namespace, "system_prompt")
        if result and result.value:
            logger.info("Instrucciones del agente recuperadas")
            return result.value.get("system_prompt", DEFAULT_SYSTEM_PROMPT)
    except Exception as e:
        logger.warning(f"Error recuperando instrucciones: {e}")
    
    # Guardar prompt por defecto si no existe
    initial_data = {
        "system_prompt": DEFAULT_SYSTEM_PROMPT,
        "version": "1.0",
        "last_updated": datetime.now().isoformat(),
        "improvement_notes": ["Versión inicial"]
    }
    
    store.put(namespace, "system_prompt", initial_data)
    logger.info("Instrucciones por defecto del agente inicializadas")
    
    return DEFAULT_SYSTEM_PROMPT


def refine_instructions(
    state: dict,
    store: BaseStore,
    llm: Optional[Any] = None,
    feedback: Optional[str] = None
) -> str:
    """
    Refina las instrucciones del agente basándose en feedback o conversación.
    
    Args:
        state: Estado actual del grafo
        store: Instancia del memory store
        llm: Modelo LLM para refinamiento (opcional)
        feedback: Feedback explícito del usuario (opcional)
        
    Returns:
        str: Instrucciones actualizadas
    """
    namespace = ("procedural", "agent")
    
    # Obtener instrucciones actuales
    current_data = _get_instruction_data(store)
    current_instructions = current_data.get("system_prompt", DEFAULT_SYSTEM_PROMPT)
    
    # Si no hay LLM o feedback relevante, retornar instrucciones actuales
    if not llm or (not feedback and not _has_relevant_feedback(state)):
        logger.info("No hay feedback relevante para refinar instrucciones")
        return current_instructions
    
    try:
        # Preparar contexto para el refinamiento
        recent_messages = state.get("messages", [])[-10:]
        messages_text = "\n".join([
            f"{msg.get('role', 'unknown')}: {msg.get('content', '')}"
            for msg in recent_messages
        ])
        
        prompt = f"""
Analiza las instrucciones actuales del agente y la conversación reciente.

INSTRUCCIONES ACTUALES:
{current_instructions}

CONVERSACIÓN RECIENTE:
{messages_text}

FEEDBACK DEL USUARIO:
{feedback if feedback else "No hay feedback explícito"}

TAREA:
1. Identifica si hay problemas o áreas de mejora en el comportamiento del agente
2. Si es necesario, propón mejoras específicas a las instrucciones
3. Mantén la estructura y formato existente
4. NO hagas cambios si no son necesarios

Si NO hay necesidad de cambios, responde: "NO_CHANGES"
Si HAY mejoras, devuelve las instrucciones completas mejoradas.
"""
        
        # TODO: Invocar LLM para refinamiento
        logger.info("Refinamiento de instrucciones con LLM (pendiente)")
        
        # Por ahora, retornar instrucciones actuales
        return current_instructions
        
    except Exception as e:
        logger.error(f"Error refinando instrucciones: {e}")
        return current_instructions


def _get_instruction_data(store: BaseStore) -> Dict[str, Any]:
    """Obtiene datos completos de instrucciones."""
    namespace = ("procedural", "agent")
    
    try:
        result = store.get(namespace, "system_prompt")
        if result and result.value:
            return result.value
    except Exception:
        pass
    
    return {
        "system_prompt": DEFAULT_SYSTEM_PROMPT,
        "version": "1.0",
        "last_updated": datetime.now().isoformat(),
        "improvement_notes": []
    }


def _has_relevant_feedback(state: dict) -> bool:
    """Detecta si hay feedback relevante en la conversación."""
    if not state.get("messages"):
        return False
    
    # Palabras clave que indican feedback
    feedback_keywords = [
        "no me gusta",
        "prefiero",
        "mejor",
        "cambia",
        "no hagas",
        "siempre",
        "nunca",
        "demasiado",
        "muy",
        "feedback",
        "sugerencia"
    ]
    
    recent_messages = state["messages"][-5:]
    for msg in recent_messages:
        content = msg.get("content", "").lower()
        if any(keyword in content for keyword in feedback_keywords):
            return True
    
    return False


def update_instructions_with_note(
    store: BaseStore,
    new_instructions: str,
    improvement_note: str
) -> None:
    """
    Actualiza instrucciones con una nota de mejora.
    
    Args:
        store: Instancia del memory store
        new_instructions: Nuevas instrucciones del agente
        improvement_note: Nota explicando la mejora
    """
    namespace = ("procedural", "agent")
    current_data = _get_instruction_data(store)
    
    # Incrementar versión
    current_version = current_data.get("version", "1.0")
    try:
        major, minor = map(int, current_version.split("."))
        new_version = f"{major}.{minor + 1}"
    except:
        new_version = "1.1"
    
    # Actualizar datos
    updated_data = {
        "system_prompt": new_instructions,
        "version": new_version,
        "last_updated": datetime.now().isoformat(),
        "improvement_notes": current_data.get("improvement_notes", []) + [
            {
                "version": new_version,
                "date": datetime.now().isoformat(),
                "note": improvement_note
            }
        ]
    }
    
    store.put(namespace, "system_prompt", updated_data)
    logger.info(f"Instrucciones actualizadas a versión {new_version}: {improvement_note}")


def get_instruction_version(store: BaseStore) -> str:
    """
    Obtiene la versión actual de las instrucciones.
    
    Args:
        store: Instancia del memory store
        
    Returns:
        str: Versión de las instrucciones
    """
    data = _get_instruction_data(store)
    return data.get("version", "1.0")


def get_improvement_history(store: BaseStore) -> list:
    """
    Obtiene el historial de mejoras de las instrucciones.
    
    Args:
        store: Instancia del memory store
        
    Returns:
        list: Lista de notas de mejora
    """
    data = _get_instruction_data(store)
    return data.get("improvement_notes", [])
