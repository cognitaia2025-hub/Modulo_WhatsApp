"""
Configuración de conexión a PostgreSQL

Centraliza la configuración de base de datos para todos los nodos.
"""

import os
import psycopg2
import logging
from typing import Optional
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


def get_db_connection() -> Optional[psycopg2.extensions.connection]:
    """
    Crea una conexión a PostgreSQL usando variables de entorno.
    
    Variables requeridas en .env:
    - POSTGRES_HOST (default: localhost)
    - POSTGRES_PORT (default: 5432)
    - POSTGRES_DB (default: agente_whatsapp)
    - POSTGRES_USER (default: postgres)
    - POSTGRES_PASSWORD
    
    Returns:
        Conexión de psycopg2 o None si falla
    """
    try:
        conn = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST', 'localhost'),
            port=int(os.getenv('POSTGRES_PORT', '5432')),
            database=os.getenv('POSTGRES_DB', 'agente_whatsapp'),
            user=os.getenv('POSTGRES_USER', 'postgres'),
            password=os.getenv('POSTGRES_PASSWORD', '')
        )
        return conn
    except psycopg2.Error as e:
        logger.error(f"Error conectando a PostgreSQL: {e}")
        return None
    except Exception as e:
        logger.error(f"Error inesperado en conexión DB: {e}")
        return None


if __name__ == "__main__":
    """Test de conexión"""
    print("\n🧪 Test de Conexión a PostgreSQL\n")
    
    conn = get_db_connection()
    if conn:
        print("✅ Conexión exitosa")
        
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"   PostgreSQL version: {version[0]}")
        
        cursor.close()
        conn.close()
    else:
        print("❌ No se pudo conectar")
        print("   Verifica las variables en .env:")
        print("   - POSTGRES_HOST")
        print("   - POSTGRES_PORT")
        print("   - POSTGRES_DB")
        print("   - POSTGRES_USER")
        print("   - POSTGRES_PASSWORD")
