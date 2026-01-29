"""
Connection Pool para PostgreSQL con psycopg

Proporciona un pool de conexiones compartido para mejorar performance.
"""

import os
import logging
from typing import Optional
from psycopg_pool import ConnectionPool
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:password123@localhost:5434/agente_whatsapp")

logger = logging.getLogger(__name__)

# Pool global de conexiones
_pool: Optional[ConnectionPool] = None


def get_connection_pool() -> ConnectionPool:
    """
    Obtiene el pool de conexiones (singleton).
    
    Configuración:
    - min_size=2: Mínimo 2 conexiones siempre abiertas
    - max_size=10: Máximo 10 conexiones concurrentes
    - timeout=30: Espera máxima para obtener conexión
    
    Returns:
        Pool de conexiones psycopg
    """
    global _pool
    
    if _pool is None:
        try:
            _pool = ConnectionPool(
                DATABASE_URL,
                min_size=2,
                max_size=10,
                timeout=30,
                kwargs={
                    "autocommit": False,
                    "row_factory": None
                }
            )
            logger.info("✅ Connection pool creado (min=2, max=10)")
        except Exception as e:
            logger.error(f"❌ Error creando connection pool: {e}")
            raise
    
    return _pool


def close_connection_pool():
    """Cierra el pool de conexiones al finalizar la aplicación."""
    global _pool
    if _pool:
        _pool.close()
        _pool = None
        logger.info("🔒 Connection pool cerrado")


def get_connection():
    """
    Obtiene una conexión del pool (context manager).
    
    Uso:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT ...")
    """
    pool = get_connection_pool()
    return pool.connection()
