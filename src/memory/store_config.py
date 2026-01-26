"""
Configuración del Memory Store para LangGraph

Gestiona la inicialización y configuración del store de memoria.
"""

from langgraph.store.memory import InMemoryStore
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Store global para reutilización
_store_instance: Optional[InMemoryStore] = None


def get_memory_store(reset: bool = False) -> InMemoryStore:
    """
    Obtiene o crea una instancia del memory store con embeddings reales.

    Usa el mismo modelo de embeddings que memoria episódica (paraphrase-MiniLM-L6-v2)
    para consistencia en búsquedas semánticas.

    Args:
        reset: Si True, crea una nueva instancia del store

    Returns:
        InMemoryStore: Instancia del store de memoria con búsqueda semántica
    """
    global _store_instance

    if reset or _store_instance is None:
        logger.info("🔧 Inicializando memory store con embeddings reales...")

        try:
            # Usar el mismo modelo que en src/embeddings/local_embedder.py
            # ✅ Actualizado: usar langchain-huggingface en lugar del deprecado langchain_community
            from langchain_huggingface import HuggingFaceEmbeddings

            embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/paraphrase-MiniLM-L6-v2",
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': True}
            )

            _store_instance = InMemoryStore(
                index={
                    "embed": embeddings,  # ✅ Embeddings reales con Sentence Transformers
                    "dims": 384,          # Dimensión del modelo MiniLM
                    "fields": ["content"] # Campo por defecto a embeddear
                }
            )
            logger.info("✅ Memory store inicializado con búsqueda semántica (384 dims)")

        except Exception as e:
            logger.error(f"❌ Error inicializando embeddings: {e}")
            logger.warning("⚠️  Fallback a InMemoryStore sin búsqueda semántica")

            # Fallback: Store sin embeddings (solo key-value básico)
            _store_instance = InMemoryStore()

    return _store_instance


def clear_memory_store():
    """Limpia completamente el store de memoria."""
    global _store_instance
    _store_instance = None
    logger.info("Memory store limpiado")


def get_store_stats(store: InMemoryStore) -> dict:
    """
    Obtiene estadísticas del store de memoria.
    
    Args:
        store: Instancia del store
        
    Returns:
        dict: Estadísticas del store
    """
    # TODO: Implementar conteo real de items por namespace
    return {
        "status": "active",
        "type": "InMemoryStore",
        "note": "Usar BaseStore con backend de BD para producción"
    }
