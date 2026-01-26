"""
Memoria Semántica - Hechos y Preferencias del Usuario

Gestiona el conocimiento sobre el usuario, sus preferencias y contexto laboral.
"""

from typing import Optional, Dict, Any
from datetime import datetime
import json
import logging
from langgraph.store.base import BaseStore

logger = logging.getLogger(__name__)


def get_user_facts(store: BaseStore, user_id: str) -> Dict[str, Any]:
    """
    Recupera hechos del usuario desde el namespace 'facts' (persistente cross-thread).

    Args:
        store: Instancia del memory store
        user_id: ID del usuario

    Returns:
        dict: Hechos del usuario (nombre, etc.)
    """
    facts_namespace = (user_id, "facts")

    try:
        result = store.get(facts_namespace, "user_name")
        if result and result.value:
            return {
                "user_name": result.value.get("value")
            }
    except Exception as e:
        logger.warning(f"Error recuperando facts del usuario: {e}")

    return {}


def get_user_preferences(store: BaseStore, user_id: str) -> Dict[str, Any]:
    """
    Obtiene las preferencias almacenadas del usuario.
    
    Args:
        store: Instancia del memory store
        user_id: ID del usuario
        
    Returns:
        dict: Preferencias del usuario o valores por defecto
    """
    namespace = ("semantic", user_id)
    
    try:
        result = store.get(namespace, "preferences")
        if result:
            logger.info(f"Preferencias recuperadas para usuario {user_id}")
            return result.value
    except Exception as e:
        logger.warning(f"Error recuperando preferencias: {e}")
    
    # Valores por defecto si no existen preferencias
    default_preferences = {
        "user_preferences": {
            "user_name": None,  # Se aprende de la conversación
            "preferred_meeting_times": ["09:00-11:00", "14:00-16:00"],
            "timezone": "America/Tijuana",
            "default_meeting_duration": 60,
            "language_preference": "formal",
            "notification_preference": "email",
        },
        "work_context": {
            "role": "User",
            "team": "",
            "working_hours": "09:00-17:00",
            "typical_meeting_types": ["meeting", "1:1", "review"],
        },
        "contact_preferences": {},
        "last_updated": datetime.now().isoformat()
    }
    
    # Guardar preferencias por defecto
    store.put(namespace, "preferences", default_preferences)
    logger.info(f"Preferencias por defecto creadas para usuario {user_id}")
    
    return default_preferences


def update_semantic_memory(
    state: dict,
    store: BaseStore,
    user_id: str,
    llm: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Actualiza memoria semántica basándose en nueva información de la conversación.

    Usa LLM con structured output para extraer preferencias automáticamente.

    Args:
        state: Estado actual del grafo con mensajes
        store: Instancia del memory store
        user_id: ID del usuario
        llm: Modelo LLM para extraer información (opcional)

    Returns:
        dict: Preferencias actualizadas
    """
    namespace = ("semantic", user_id)

    # Obtener memoria actual
    current_memory = get_user_preferences(store, user_id)

    # Si hay LLM, usar para extraer información
    if llm and state.get("messages"):
        try:
            # Extraer mensajes recientes
            recent_messages = state["messages"][-5:]  # Últimos 5 mensajes
            messages_text = ""

            for msg in recent_messages:
                # Manejar diferentes tipos de mensajes (dict vs objetos)
                if isinstance(msg, dict):
                    role = msg.get('role', 'unknown')
                    content = msg.get('content', '')
                elif hasattr(msg, 'type'):
                    role = 'user' if msg.type == 'human' else 'assistant'
                    content = msg.content if hasattr(msg, 'content') else ''
                else:
                    continue

                messages_text += f"{role}: {content}\n"

            # ✅ Usar Pydantic para structured output
            from pydantic import BaseModel, Field
            from typing import List

            class PreferencesUpdate(BaseModel):
                """Modelo para actualización de preferencias del usuario"""
                user_name: Optional[str] = Field(
                    None,
                    description="Nombre del usuario si lo menciona explícitamente"
                )
                timezone: Optional[str] = Field(
                    None,
                    description="Zona horaria mencionada explícitamente (ej: America/Tijuana, Europe/Madrid)"
                )
                preferred_meeting_times: Optional[List[str]] = Field(
                    None,
                    description="Horarios preferidos para reuniones (formato: HH:MM-HH:MM)"
                )
                language_preference: Optional[str] = Field(
                    None,
                    description="Estilo de comunicación: 'formal' o 'informal'"
                )
                default_meeting_duration: Optional[int] = Field(
                    None,
                    description="Duración típica de reuniones en minutos"
                )

            prompt = f"""Analiza esta conversación y extrae SOLO nueva información sobre preferencias del usuario en formato JSON.

CONVERSACIÓN RECIENTE:
{messages_text}

PREFERENCIAS ACTUALES:
{json.dumps(current_memory.get('user_preferences', {}), indent=2)}

INSTRUCCIONES:
1. Extrae SOLO información que el usuario mencionó EXPLÍCITAMENTE
2. Si el usuario NO mencionó una preferencia, deja ese campo como null
3. NO inventes información
4. Ejemplos de información válida:
   - "Prefiero reuniones por la mañana" → preferred_meeting_times: ["09:00-12:00"]
   - "Siempre uso un tono formal" → language_preference: "formal"
   - "Mis reuniones duran 30 minutos" → default_meeting_duration: 30

Si NO hay nueva información relevante, devuelve todos los campos como null.

RESPONDE EN FORMATO JSON con la siguiente estructura:
{{
    "user_name": null o "nombre del usuario",
    "timezone": null o "zona horaria",
    "preferred_meeting_times": null o ["HH:MM-HH:MM"],
    "language_preference": null o "formal/informal",
    "default_meeting_duration": null o número_en_minutos
}}"""

            # Invocar LLM con structured output (json_mode para compatibilidad con DeepSeek)
            # Nota: el prompt ahora contiene "JSON" que es requerido por DeepSeek
            structured_llm = llm.with_structured_output(PreferencesUpdate, method="json_mode")
            response = structured_llm.invoke(prompt)

            # Actualizar solo campos que no son None
            actualizado = False

            if response.user_name:
                # ✅ Guardar nombre en namespace 'facts' (persistente cross-thread)
                facts_namespace = (user_id, "facts")
                store.put(facts_namespace, "user_name", {"value": response.user_name})

                # También guardar en preferencias (legacy)
                current_memory["user_preferences"]["user_name"] = response.user_name
                logger.info(f"    ✅ Nombre guardado en facts (cross-thread): {response.user_name}")
                actualizado = True

            if response.timezone:
                current_memory["user_preferences"]["timezone"] = response.timezone
                logger.info(f"    ✅ Timezone actualizado: {response.timezone}")
                actualizado = True

            if response.preferred_meeting_times:
                current_memory["user_preferences"]["preferred_meeting_times"] = response.preferred_meeting_times
                logger.info(f"    ✅ Horarios preferidos actualizados: {response.preferred_meeting_times}")
                actualizado = True

            if response.language_preference:
                current_memory["user_preferences"]["language_preference"] = response.language_preference
                logger.info(f"    ✅ Estilo de comunicación actualizado: {response.language_preference}")
                actualizado = True

            if response.default_meeting_duration:
                current_memory["user_preferences"]["default_meeting_duration"] = response.default_meeting_duration
                logger.info(f"    ✅ Duración por defecto actualizada: {response.default_meeting_duration} min")
                actualizado = True

            if actualizado:
                logger.info(f"✅ Preferencias actualizadas para usuario {user_id}")
            else:
                logger.info(f"ℹ️  No se encontraron nuevas preferencias en la conversación")

        except Exception as e:
            logger.error(f"❌ Error extrayendo preferencias con LLM: {e}")
            logger.info("⚡ Continuando sin actualizar preferencias")

    # Actualizar timestamp
    current_memory["last_updated"] = datetime.now().isoformat()

    # Guardar memoria actualizada
    store.put(namespace, "preferences", current_memory)

    return current_memory


def get_work_context(store: BaseStore, user_id: str) -> Dict[str, Any]:
    """
    Obtiene el contexto laboral del usuario.
    
    Args:
        store: Instancia del memory store
        user_id: ID del usuario
        
    Returns:
        dict: Contexto laboral del usuario
    """
    preferences = get_user_preferences(store, user_id)
    return preferences.get("work_context", {})


def update_contact_preference(
    store: BaseStore,
    user_id: str,
    contact_name: str,
    preference_data: Dict[str, Any]
) -> None:
    """
    Actualiza preferencias para un contacto específico.
    
    Args:
        store: Instancia del memory store
        user_id: ID del usuario
        contact_name: Nombre del contacto
        preference_data: Datos de preferencia para el contacto
    """
    namespace = ("semantic", user_id)
    preferences = get_user_preferences(store, user_id)
    
    if "contact_preferences" not in preferences:
        preferences["contact_preferences"] = {}
    
    preferences["contact_preferences"][contact_name] = preference_data
    preferences["last_updated"] = datetime.now().isoformat()
    
    store.put(namespace, "preferences", preferences)
    logger.info(f"Preferencias actualizadas para contacto {contact_name}")


def get_preferred_time_slots(store: BaseStore, user_id: str) -> list[str]:
    """
    Obtiene los horarios preferidos del usuario.
    
    Args:
        store: Instancia del memory store
        user_id: ID del usuario
        
    Returns:
        list: Lista de horarios preferidos (formato "HH:MM-HH:MM")
    """
    preferences = get_user_preferences(store, user_id)
    return preferences.get("user_preferences", {}).get("preferred_meeting_times", [])
