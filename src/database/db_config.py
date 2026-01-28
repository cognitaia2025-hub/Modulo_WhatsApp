"""
Configuración de conexión a PostgreSQL

Centraliza la configuración de base de datos para todos los nodos.
"""

import psycopg2
import logging
from typing import Optional
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from src.config.secure_config import get_config


load_dotenv()
logger = logging.getLogger(__name__)

# ===== CONFIGURACIÓN SQLALCHEMY =====


def get_database_url() -> str:
    """Construye la URL de conexión para SQLAlchemy"""
    try:
        config = get_config()
        return config.get_database_url()
    except Exception as e:
        logger.error(f"Error obteniendo configuración de BD: {e}")
        raise


# Motor SQLAlchemy global (lazy loading)
engine = None


def get_engine():
    global engine
    if engine is None:
        try:
            engine = create_engine(
                get_database_url(),
                pool_size=5,
                max_overflow=10,
                pool_timeout=30,
                pool_recycle=3600,
                echo=False,
            )
        except Exception as e:
            logger.error(f"Error creating database engine: {e}")
            raise
    return engine


def get_session_local():
    return sessionmaker(autocommit=False, autoflush=False, bind=get_engine())


@contextmanager
def get_db_session() -> Session:
    """Context manager para sesiones SQLAlchemy"""
    SessionLocal = get_session_local()
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def test_sqlalchemy_connection() -> bool:
    """Test de conexión con SQLAlchemy"""
    try:
        with get_db_session() as session:
            result = session.execute(text("SELECT 1")).scalar()
            return result == 1
    except Exception as e:
        logger.error(f"Error en test SQLAlchemy: {e}")
        return False


def get_db_connection() -> Optional[psycopg2.extensions.connection]:
    """
    Crea una conexión a PostgreSQL usando configuración segura.

    Variables requeridas en .env:
    - POSTGRES_HOST
    - POSTGRES_PORT
    - POSTGRES_DB
    - POSTGRES_USER
    - POSTGRES_PASSWORD

    Returns:
        Conexión de psycopg2 o None si falla
    """
    try:
        config = get_config()
        db_config = config.get_database_config()

        conn = psycopg2.connect(
            host=db_config["host"],
            port=db_config["port"],
            database=db_config["database"],
            user=db_config["user"],
            password=db_config["password"],
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
