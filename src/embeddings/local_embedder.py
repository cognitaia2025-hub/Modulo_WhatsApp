"""
Módulo de Embeddings Local para Recuperación Episódica

Gestiona la carga del modelo de sentence-transformers y la generación
de embeddings multilingües para búsqueda semántica.

OPTIMIZACIÓN: Singleton real - el modelo se carga UNA SOLA VEZ en memoria
para evitar latencia de ~4 segundos en cada invocación.
"""

from sentence_transformers import SentenceTransformer
import logging
from typing import List, Optional
import numpy as np
import threading

logger = logging.getLogger(__name__)

# Singleton: modelo se carga una sola vez (thread-safe)
_model_instance: Optional[SentenceTransformer] = None
_model_lock = threading.Lock()
_model_loaded = False


def get_embedder() -> SentenceTransformer:
    """
    Obtiene la instancia del modelo de embeddings (patrón singleton thread-safe).
    
    Usa paraphrase-multilingual-MiniLM-L12-v2:
    - 384 dimensiones
    - Optimizado para español y otros idiomas
    - Ligero y rápido en CPU
    
    Returns:
        Instancia del modelo SentenceTransformer
    """
    global _model_instance, _model_loaded
    
    # Double-checked locking para thread safety
    if not _model_loaded:
        with _model_lock:
            if not _model_loaded:
                logger.info("🚀 [INIT] Cargando modelo de embeddings en memoria por primera y única vez...")
                logger.info("   📦 Modelo: paraphrase-multilingual-MiniLM-L12-v2")
                logger.info("   📏 Dimensiones: 384")
                logger.info("   💻 Dispositivo: CPU")
                
                try:
                    import time
                    start_time = time.time()
                    
                    _model_instance = SentenceTransformer(
                        'paraphrase-multilingual-MiniLM-L12-v2',
                        device='cpu'  # Forzar CPU (ya que torch es CPU-only)
                    )
                    
                    elapsed = time.time() - start_time
                    _model_loaded = True
                    
                    logger.info(f"✅ Modelo cargado exitosamente en {elapsed:.2f}s")
                    logger.info("⚡ Las siguientes invocaciones serán instantáneas")
                    
                except Exception as e:
                    logger.error(f"❌ Error al cargar modelo: {e}")
                    raise
    
    return _model_instance


def warmup_embedder():
    """
    Pre-carga el modelo de embeddings en memoria.
    
    Llamar esta función al inicio del servidor (startup event) para que
    el modelo esté "caliente" cuando llegue el primer mensaje.
    
    Esta función es idempotente: puede llamarse múltiples veces sin efecto.
    """
    logger.info("🔥 Warming up embedder...")
    try:
        get_embedder()
        logger.info("🔥 Embedder warmup completado")
    except Exception as e:
        logger.error(f"❌ Error en warmup del embedder: {e}")
        raise


def generate_embedding(text: str) -> List[float]:
    """
    Genera embedding para un texto dado.
    
    Args:
        text: Texto a vectorizar
        
    Returns:
        Vector de 384 dimensiones como lista de floats
        
    Raises:
        ValueError: Si el texto está vacío
        RuntimeError: Si hay error al generar embedding
    """
    if not text or not text.strip():
        raise ValueError("El texto no puede estar vacío")
    
    try:
        model = get_embedder()
        
        # Generar embedding
        embedding = model.encode(
            text,
            convert_to_numpy=True,
            show_progress_bar=False,
            normalize_embeddings=True  # Normalizar para similitud de coseno
        )
        
        # Convertir a lista de floats
        return embedding.tolist()
        
    except Exception as e:
        logger.error(f"Error al generar embedding: {e}")
        raise RuntimeError(f"No se pudo generar embedding: {e}")


def get_embedding_dimension() -> int:
    """
    Retorna la dimensión del modelo de embeddings.
    
    Returns:
        384 (dimensiones del modelo multilingüe)
    """
    return 384


def is_model_loaded() -> bool:
    """
    Verifica si el modelo ya está cargado en memoria.
    
    Útil para debugging y monitoring.
    
    Returns:
        True si el modelo está cargado, False en caso contrario
    """
    return _model_loaded
