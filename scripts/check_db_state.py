"""Verificar estado actual de la BD"""
import psycopg
import os
from dotenv import load_dotenv

load_dotenv()

db_url = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"

print("\n📊 ESTADO ACTUAL DE LA BASE DE DATOS\n")

with psycopg.connect(db_url) as conn:
    with conn.cursor() as cur:
        # Listar tablas
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)

        tablas = cur.fetchall()

        print(f"Tablas existentes ({len(tablas)}):")
        for tabla in tablas:
            print(f"  • {tabla[0]}")

        print("\n" + "="*60)

        # Verificar columnas de usuarios
        if any(t[0] == 'usuarios' for t in tablas):
            cur.execute("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'usuarios'
                ORDER BY ordinal_position
            """)

            cols_usuarios = cur.fetchall()
            print("\nColumnas de tabla 'usuarios':")
            for col in cols_usuarios:
                print(f"  • {col[0]} ({col[1]})")
