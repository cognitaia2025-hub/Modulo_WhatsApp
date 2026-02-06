#!/usr/bin/env python3
"""
Script de Inicialización Consolidada de Base de Datos
=====================================================

Este script ejecuta todos los archivos SQL necesarios en el orden correcto
para inicializar completamente la base de datos del sistema.

Ya NO es necesario ejecutar migraciones separadas.
Todos los cambios de las Etapas 1-7 están consolidados aquí.

Uso:
    python sql/init_database_consolidated.py
    
    # O con opciones:
    python sql/init_database_consolidated.py --drop-existing
    python sql/init_database_consolidated.py --skip-seed
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv
import psycopg
from typing import List, Any, Optional
import argparse

# Cargar variables de entorno
load_dotenv()

# Configuración
DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5434/agente_whatsapp")
SQL_DIR: Path = Path(__file__).parent

# Lista de archivos SQL en orden de ejecución
SQL_FILES: List[str] = [
    "init_database.sql"
]

def print_header(text: str):
    """Imprime un header formateado"""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70 + "\n")

def print_success(text: str):
    """Imprime mensaje de éxito"""
    print(f"✅ {text}")

def print_error(text: str):
    """Imprime mensaje de error"""
    print(f"❌ {text}")

def print_warning(text: str):
    """Imprime mensaje de advertencia"""
    print(f"⚠️  {text}")

def print_info(text: str):
    """Imprime mensaje informativo"""
    print(f"ℹ️  {text}")

def execute_sql_file(conn: psycopg.Connection[Any], sql_file: Path, file_name: str):
    """
    Ejecuta un archivo SQL completo
    
    Args:
        conn: Conexión a PostgreSQL
        sql_file: Path al archivo SQL
        file_name: Nombre del archivo para mostrar
    """
    try:
        print(f"📄 Ejecutando: {file_name}...", end=" ", flush=True)
        
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        with conn.cursor() as cur:
            cur.execute(sql_content)  # type: ignore[arg-type]
        
        conn.commit()
        print("✅")
        
    except Exception as e:
        print("❌")
        print_error(f"Error en {file_name}: {str(e)}")
        raise

def verify_database_connection(database_url: str) -> bool:
    """Verifica que se puede conectar a la base de datos"""
    try:
        with psycopg.connect(database_url, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT version()")
                result = cur.fetchone()
                if result:
                    version = str(result[0])
                    print_info(f"PostgreSQL: {version.split(',')[0]}")
                    return True
                return False
    except Exception as e:
        print_error(f"No se puede conectar a la base de datos: {e}")
        return False

def verify_pgvector(conn: psycopg.Connection[Any]) -> bool:
    """Verifica que la extensión pgvector esté disponible"""
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT extversion FROM pg_extension WHERE extname = 'vector'")  # type: ignore[arg-type]
            result = cur.fetchone()
            if result:
                print_info(f"Extensión pgvector: {result[0]}")
                return True
            else:
                print_warning("Extensión pgvector no encontrada (se instalará)")
                return False
    except Exception as e:
        print_warning(f"No se pudo verificar pgvector: {e}")
        return False

def count_tables(conn: psycopg.Connection[Any]) -> int:
    """Cuenta las tablas en el schema public"""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = 'public'
                AND table_type = 'BASE TABLE'
        """)
        row = cur.fetchone()
        return int(row[0]) if row else 0

def drop_database_if_exists(database_url: str):
    """Elimina la base de datos si existe (para inicialización limpia)"""
    try:
        # Conectar a postgres (DB por defecto)
        parts = database_url.replace("postgresql://", "").split("/")
        base_url = "postgresql://" + parts[0] + "/postgres"
        db_name = parts[1].split("?")[0] if "?" in parts[1] else parts[1]
        
        print_warning(f"Eliminando base de datos '{db_name}'...")
        
        with psycopg.connect(base_url, autocommit=True) as conn:
            with conn.cursor() as cur:
                # Terminar conexiones existentes
                cur.execute(f"""
                    SELECT pg_terminate_backend(pg_stat_activity.pid)
                    FROM pg_stat_activity
                    WHERE pg_stat_activity.datname = '{db_name}'
                        AND pid <> pg_backend_pid()
                """)
                
                # Eliminar base de datos
                cur.execute(f"DROP DATABASE IF EXISTS {db_name}")
                
                # Crear nueva base de datos
                cur.execute(f"CREATE DATABASE {db_name}")
                
        print_success(f"Base de datos '{db_name}' recreada limpiamente")
        
    except Exception as e:
        print_error(f"Error al recrear base de datos: {e}")
        raise

def show_summary(conn: psycopg.Connection[Any]):
    """Muestra un resumen del estado de la base de datos"""
    print_header("RESUMEN DE INICIALIZACIÓN")
    
    try:
        with conn.cursor() as cur:
            # Contar tablas
            cur.execute("""
                SELECT COUNT(*)
                FROM information_schema.tables
                WHERE table_schema = 'public'
                    AND table_type = 'BASE TABLE'
            """)
            row_tables = cur.fetchone()
            total_tables = row_tables[0] if row_tables else 0
            print_info(f"Tablas creadas: {total_tables}")
            
            # Contar usuarios
            cur.execute("SELECT COUNT(*) FROM usuarios")  # type: ignore[arg-type]
            row_users = cur.fetchone()
            total_users = row_users[0] if row_users else 0
            print_info(f"Usuarios: {total_users}")
            
            # Contar doctores
            cur.execute("SELECT COUNT(*) FROM doctores")  # type: ignore[arg-type]
            row_doctors = cur.fetchone()
            total_doctors = row_doctors[0] if row_doctors else 0
            print_info(f"Doctores: {total_doctors}")
            
            # Contar disponibilidad
            cur.execute("SELECT COUNT(*) FROM disponibilidad_medica")  # type: ignore[arg-type]
            row_avail = cur.fetchone()
            total_availability = row_avail[0] if row_avail else 0
            print_info(f"Registros de disponibilidad: {total_availability}")
            
            # Contar herramientas
            cur.execute("SELECT COUNT(*) FROM herramientas_disponibles")
            row_tools = cur.fetchone()
            total_tools = row_tools[0] if row_tools else 0
            print_info(f"Herramientas disponibles: {total_tools}")
            
            # Verificar extensión vector
            cur.execute("""
                SELECT EXISTS(
                    SELECT 1 FROM pg_extension WHERE extname = 'vector'
                )
            """)
            row_vector = cur.fetchone()
            has_vector = row_vector[0] if row_vector else False
            if has_vector:
                print_success("Extensión pgvector: Instalada")
            else:
                print_warning("Extensión pgvector: NO instalada")
            
    except Exception as e:
        print_error(f"Error al generar resumen: {e}")

def main():
    """Función principal"""
    parser = argparse.ArgumentParser(
        description="Inicializa la base de datos con el esquema consolidado"
    )
    parser.add_argument(
        "--drop-existing",
        action="store_true",
        help="Elimina la base de datos existente antes de inicializar"
    )
    parser.add_argument(
        "--skip-seed",
        action="store_true",
        help="Omite la inserción de datos iniciales"
    )
    
    args = parser.parse_args()
    
    print_header("INICIALIZACIÓN DE BASE DE DATOS CONSOLIDADA")
    
    print_info("Configuración:")
    print(f"   Database URL: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else DATABASE_URL}")
    print(f"   SQL Directory: {SQL_DIR}")
    print()
    
    # Verificar que los archivos SQL existan
    print("📋 Verificando archivos SQL...")
    sql_files_to_execute = SQL_FILES.copy()
    
    if args.skip_seed:
        sql_files_to_execute.remove("seed_initial_data.sql")
        print_warning("Se omitirá seed_initial_data.sql")
    
    missing_files: List[str] = []
    for sql_file in sql_files_to_execute:
        file_path = SQL_DIR / sql_file
        if not file_path.exists():
            missing_files.append(sql_file)
            print_error(f"Archivo no encontrado: {sql_file}")
        else:
            print_success(f"Encontrado: {sql_file}")
    
    if missing_files:
        print_error(f"Faltan {len(missing_files)} archivo(s). Abortando.")
        return 1
    
    # Drop database si se solicita
    if args.drop_existing:
        print()
        try:
            drop_database_if_exists(DATABASE_URL)
        except Exception as e:
            print_error("No se pudo recrear la base de datos")
            return 1
    
    # Verificar conexión
    print()
    print("🔌 Verificando conexión a PostgreSQL...")
    if not verify_database_connection(DATABASE_URL):
        return 1
    
    print_success("Conexión exitosa")
    
    # Ejecutar archivos SQL
    print()
    print_header("EJECUTANDO SCRIPTS SQL")
    
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            # Verificar pgvector antes de empezar
            verify_pgvector(conn)
            
            print()
            tables_before = count_tables(conn)
            print_info(f"Tablas existentes antes: {tables_before}")
            print()
            
            # Ejecutar cada archivo SQL
            for sql_file in sql_files_to_execute:
                file_path = SQL_DIR / sql_file
                execute_sql_file(conn, file_path, sql_file)
            
            print()
            tables_after = count_tables(conn)
            print_info(f"Tablas existentes después: {tables_after}")
            new_tables = tables_after - tables_before
            if new_tables > 0:
                print_success(f"Se crearon {new_tables} nuevas tablas")
            
            # Mostrar resumen
            print()
            show_summary(conn)
            
    except Exception as e:
        print()
        print_error(f"Error durante la inicialización: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Mensaje final
    print()
    print_header("✨ INICIALIZACIÓN COMPLETADA EXITOSAMENTE ✨")
    print()
    print("📝 Próximos pasos:")
    print("   1. Ejecutar la aplicación normalmente")
    print("   2. Las tablas de LangGraph se crearán automáticamente")
    print("   3. Ya NO ejecutes scripts de migración por separado")
    print()
    print("📚 Documentación: sql/README.md")
    print()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
