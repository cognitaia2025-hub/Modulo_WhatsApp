"""
Memoria Episódica - Experiencias y Acciones Pasadas

Registra y recupera episodios de interacciones pasadas para detectar patrones.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import json
import logging
from langgraph.store.base import BaseStore
import uuid

logger = logging.getLogger(__name__)


def log_episode(
    state: dict,
    store: BaseStore,
    user_id: str,
    action_type: str,
    additional_context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Registra un episodio/experiencia de interacción.
    
    Args:
        state: Estado actual del grafo
        store: Instancia del memory store
        user_id: ID del usuario
        action_type: Tipo de acción (create_event, postpone_meeting, etc.)
        additional_context: Contexto adicional del episodio
        
    Returns:
        str: ID del episodio creado
    """
    namespace = ("episodic", user_id)
    episode_id = str(uuid.uuid4())
    
    # Extraer contexto de los mensajes
    context = extract_context_from_state(state)
    if additional_context:
        context.update(additional_context)
    
    episode = {
        "id": episode_id,
        "timestamp": datetime.now().isoformat(),
        "action": action_type,
        "context": context,
        "outcome": "success",  # Se puede actualizar después
        "user_sentiment": "neutral"  # Se puede detectar con LLM
    }
    
    # Guardar episodio
    store.put(namespace, episode_id, episode)
    logger.info(f"Episodio {episode_id} registrado para usuario {user_id}: {action_type}")
    
    return episode_id


def extract_context_from_state(state: dict) -> Dict[str, Any]:
    """
    Extrae contexto relevante del estado actual.
    
    Args:
        state: Estado del grafo
        
    Returns:
        dict: Contexto extraído
    """
    context = {}
    
    if "messages" in state and state["messages"]:
        last_human_msg = None
        last_ai_msg = None
        
        # Buscar últimos mensajes relevantes
        for msg in reversed(state["messages"]):
            msg_type = msg.get("type") or msg.get("role")
            if msg_type in ["human", "user"] and not last_human_msg:
                last_human_msg = msg.get("content", "")
            elif msg_type in ["ai", "assistant"] and not last_ai_msg:
                last_ai_msg = msg.get("content", "")
            
            if last_human_msg and last_ai_msg:
                break
        
        context["user_request"] = last_human_msg
        context["agent_response"] = last_ai_msg
    
    return context


def get_relevant_episodes(
    state: dict,
    store: BaseStore,
    user_id: str,
    query: Optional[str] = None,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Busca episodios relevantes para el contexto actual.
    
    Args:
        state: Estado actual del grafo
        store: Instancia del memory store
        user_id: ID del usuario
        query: Query de búsqueda (opcional, usa último mensaje si no se provee)
        limit: Número máximo de episodios a retornar
        
    Returns:
        list: Lista de episodios relevantes
    """
    namespace = ("episodic", user_id)
    
    # Determinar query de búsqueda
    search_query = query
    if not search_query and state.get("messages"):
        # Usar último mensaje del usuario como query
        for msg in reversed(state["messages"]):
            msg_type = msg.get("type") or msg.get("role")
            if msg_type in ["human", "user"]:
                search_query = msg.get("content", "")
                break
    
    if not search_query:
        logger.warning("No se pudo determinar query para búsqueda de episodios")
        return []
    
    try:
        # Búsqueda semántica
        results = store.search(
            namespace,
            query=search_query,
            limit=limit
        )
        
        episodes = [item.value for item in results]
        logger.info(f"Encontrados {len(episodes)} episodios relevantes para usuario {user_id}")
        return episodes
        
    except Exception as e:
        logger.error(f"Error buscando episodios: {e}")
        return []


def detect_patterns(
    store: BaseStore,
    user_id: str,
    llm: Optional[Any] = None,
    lookback_limit: int = 20
) -> Dict[str, Any]:
    """
    Detecta patrones de comportamiento del usuario.
    
    Args:
        store: Instancia del memory store
        user_id: ID del usuario
        llm: Modelo LLM para análisis (opcional)
        lookback_limit: Número de episodios recientes a analizar
        
    Returns:
        dict: Patrones detectados
    """
    namespace = ("episodic", user_id)
    
    try:
        # Obtener episodios recientes
        recent_episodes = store.search(
            namespace,
            query="",  # Query vacío para obtener todos
            limit=lookback_limit
        )
        
        if not recent_episodes:
            logger.info(f"No hay episodios para analizar para usuario {user_id}")
            return {"patterns": [], "note": "Insufficient data"}
        
        # Análisis simple de patrones sin LLM
        patterns = analyze_patterns_simple([item.value for item in recent_episodes])
        
        # Si hay LLM, hacer análisis más profundo
        if llm:
            try:
                episodes_text = json.dumps(
                    [item.value for item in recent_episodes],
                    indent=2
                )
                
                prompt = f"""
Analiza estos episodios de interacción del usuario y detecta patrones:

{episodes_text}

Identifica:
1. Acciones repetidas
2. Horarios preferidos
3. Comportamientos recurrentes
4. Tendencias (cancelaciones, postergaciones, etc.)

Devuelve un JSON con los patrones encontrados.
"""
                
                # TODO: Invocar LLM
                logger.info("Análisis de patrones con LLM (pendiente)")
                
            except Exception as e:
                logger.error(f"Error en análisis con LLM: {e}")
        
        logger.info(f"Patrones detectados para usuario {user_id}: {len(patterns.get('patterns', []))} patrones")
        return patterns
        
    except Exception as e:
        logger.error(f"Error detectando patrones: {e}")
        return {"patterns": [], "error": str(e)}


def analyze_patterns_simple(episodes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Análisis simple de patrones sin usar LLM.
    
    Args:
        episodes: Lista de episodios
        
    Returns:
        dict: Patrones detectados
    """
    if not episodes:
        return {"patterns": []}
    
    # Contar acciones
    action_counts = {}
    for episode in episodes:
        action = episode.get("action", "unknown")
        action_counts[action] = action_counts.get(action, 0) + 1
    
    patterns = []
    
    # Detectar acciones frecuentes
    for action, count in action_counts.items():
        if count >= 3:
            patterns.append({
                "type": "frequent_action",
                "action": action,
                "count": count,
                "description": f"Usuario ha realizado '{action}' {count} veces"
            })
    
    # Detectar cancelaciones/postergaciones frecuentes
    cancel_count = action_counts.get("delete_event", 0) + action_counts.get("postpone_event", 0)
    if cancel_count >= 3:
        patterns.append({
            "type": "cancellation_pattern",
            "count": cancel_count,
            "description": f"Usuario tiende a cancelar/posponer reuniones ({cancel_count} veces)"
        })
    
    return {
        "patterns": patterns,
        "total_episodes_analyzed": len(episodes),
        "action_distribution": action_counts
    }


def get_recent_episodes(
    store: BaseStore,
    user_id: str,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Obtiene los episodios más recientes del usuario.
    
    Args:
        store: Instancia del memory store
        user_id: ID del usuario
        limit: Número de episodios a retornar
        
    Returns:
        list: Lista de episodios recientes
    """
    namespace = ("episodic", user_id)
    
    try:
        results = store.search(namespace, query="", limit=limit)
        episodes = [item.value for item in results]
        
        # Ordenar por timestamp (más reciente primero)
        episodes.sort(
            key=lambda x: x.get("timestamp", ""),
            reverse=True
        )
        
        return episodes
    except Exception as e:
        logger.error(f"Error obteniendo episodios recientes: {e}")
        return []
