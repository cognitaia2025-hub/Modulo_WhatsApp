#!/usr/bin/env python3
"""
Script para aplicar migración: crear función check_conflicto_horario()
"""
import psycopg
import os
from pathlib import Path

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:password123@localhost:5434/agente_whatsapp")

def apply_migration():
    """Ejecuta el archivo SQL de migración"""
    
    # Leer archivo SQL
    sql_file = Path(__file__).parent.parent / "sql" / "migrate_add_check_conflicto.sql"
    
    with open(sql_file, "r", encoding="utf-8") as f:
        sql_content = f.read()
    
    # Conectar y ejecutar
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(sql_content)
            conn.commit()
            print("✅ Migración aplicada: función check_conflicto_horario() creada")
            
            # Verificar que la función existe
            cur.execute("""
                SELECT proname 
                FROM pg_proc 
                WHERE proname = 'check_conflicto_horario'
            """)
            result = cur.fetchone()
            if result:
                print(f"✅ Función verificada: {result[0]}")
            else:
                print("❌ Error: función no encontrada después de migración")

if __name__ == "__main__":
    apply_migration()
