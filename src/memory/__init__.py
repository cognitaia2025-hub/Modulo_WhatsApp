"""
Sistema de Memoria Multi-Tipo para Calendar AI Agent

Implementa tres tipos de memoria:
- Semántica: Hechos y preferencias del usuario
- Episódica: Experiencias y acciones pasadas
- Procedimental: Reglas y comportamiento del agente
"""

from .store_config import get_memory_store
from .semantic import (
    get_user_preferences,
    get_user_facts,  # ✅ Nueva función para hechos cross-thread
    update_semantic_memory,
    get_work_context
)
from .episodic import (
    log_episode,
    get_relevant_episodes,
    detect_patterns
)
from .procedural import (
    get_agent_instructions,
    refine_instructions
)

__all__ = [
    "get_memory_store",
    "get_user_preferences",
    "get_user_facts",  # ✅ Nueva función exportada
    "update_semantic_memory",
    "get_work_context",
    "log_episode",
    "get_relevant_episodes",
    "detect_patterns",
    "get_agent_instructions",
    "refine_instructions",
]
