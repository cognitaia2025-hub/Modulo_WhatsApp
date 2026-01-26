"""
Módulo de Base de Datos para Memoria Procedimental
Gestiona la conexión a PostgreSQL y caché de herramientas
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Configuración de caché (5 minutos)
_herramientas_cache: Optional[List[Dict]] = None
_cache_timestamp: Optional[datetime] = None
CACHE_DURATION_MINUTES = 5


def get_db_connection():
    """
    Crea conexión a PostgreSQL usando variables de entorno
    
    Variables requeridas en .env:
        POSTGRES_HOST
        POSTGRES_PORT
        POSTGRES_DB
        POSTGRES_USER
        POSTGRES_PASSWORD
    """
    try:
        conn = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST', 'localhost'),
            port=os.getenv('POSTGRES_PORT', '5432'),
            database=os.getenv('POSTGRES_DB', 'calendar_agent'),
            user=os.getenv('POSTGRES_USER', 'postgres'),
            password=os.getenv('POSTGRES_PASSWORD', ''),
            cursor_factory=RealDictCursor
        )
        return conn
    except psycopg2.Error as e:
        logger.error(f"❌ Error conectando a PostgreSQL: {e}")
        raise


def is_cache_valid() -> bool:
    """Verifica si el caché de herramientas aún es válido (< 5 minutos)"""
    global _cache_timestamp
    
    if _cache_timestamp is None or _herramientas_cache is None:
        return False
    
    age = datetime.now() - _cache_timestamp
    return age < timedelta(minutes=CACHE_DURATION_MINUTES)


def get_herramientas_disponibles(force_refresh: bool = False) -> List[Dict[str, str]]:
    """
    Obtiene lista de herramientas activas desde PostgreSQL con caché inteligente
    
    Args:
        force_refresh: Si es True, ignora caché y consulta la BD
        
    Returns:
        Lista de diccionarios con 'id_tool' y 'description'
        
    Ejemplo:
        [
            {'id_tool': 'create_calendar_event', 'description': 'Crear nuevos...'},
            {'id_tool': 'list_calendar_events', 'description': 'Listar eventos...'}
        ]
    """
    global _herramientas_cache, _cache_timestamp
    
    # Usar caché si es válido
    if not force_refresh and is_cache_valid():
        logger.info(f"📦 Usando caché de herramientas ({len(_herramientas_cache)} items)")
        return _herramientas_cache
    
    # Consultar base de datos
    try:
        logger.info("🔍 Consultando herramientas disponibles desde PostgreSQL...")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # ✅ ACTUALIZADO: Ahora usa 'id' y 'tool_name'
        cursor.execute("""
            SELECT id, tool_name, descripcion 
            FROM herramientas_disponibles 
            WHERE activa = TRUE
            ORDER BY id
        """)
        
        resultados = cursor.fetchall()
        
        # Convertir a lista de dicts
        herramientas = [
            {
                'id_tool': row['tool_name'],  # ✅ Ahora usa tool_name (string)
                'description': row['descripcion']
            }
            for row in resultados
        ]
        
        cursor.close()
        conn.close()
        
        # Actualizar caché
        _herramientas_cache = herramientas
        _cache_timestamp = datetime.now()
        
        logger.info(f"✅ Herramientas cargadas: {len(herramientas)} activas")
        return herramientas
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo herramientas: {e}")
        
        # Fallback: herramientas hardcoded (sin cambios)
        logger.warning("⚠️  Usando herramientas hardcoded (fallback)")
        return [
            {
                'id_tool': 'create_calendar_event',
                'description': 'Crear nuevos eventos con título, fecha y hora.'
            },
            {
                'id_tool': 'list_calendar_events',
                'description': 'Listar eventos para ver la agenda en un rango de fechas.'
            },
            {
                'id_tool': 'update_calendar_event',
                'description': 'Modificar la hora, título o detalles de un evento existente.'
            },
            {
                'id_tool': 'delete_calendar_event',
                'description': 'Eliminar un evento específico del calendario.'
            },
            {
                'id_tool': 'search_calendar_events',
                'description': 'Buscar eventos por palabras clave en el título o descripción.'
            }
        ]


def clear_cache():
    """Limpia manualmente el caché de herramientas"""
    global _herramientas_cache, _cache_timestamp
    _herramientas_cache = None
    _cache_timestamp = None
    logger.info("🧹 Caché de herramientas limpiado")


def test_connection() -> bool:
    """
    Prueba la conexión a PostgreSQL
    
    Returns:
        True si la conexión es exitosa, False en caso contrario
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        logger.info("✅ Conexión a PostgreSQL exitosa")
        return True
    except Exception as e:
        logger.error(f"❌ Error de conexión: {e}")
        return False
