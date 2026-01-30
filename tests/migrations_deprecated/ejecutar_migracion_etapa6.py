#!/usr/bin/env python3
"""
EJECUTAR MIGRACIÓN - ETAPA 6
Script para ejecutar la migración de base de datos de ETAPA 6 usando Python
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv
import psycopg2

load_dotenv()

def main():
    print("=" * 70)
    print("🔧 EJECUTANDO MIGRACIÓN ETAPA 6 - RECORDATORIOS")
    print("=" * 70)
    print()
    
    # Verificar variables de entorno
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ ERROR: DATABASE_URL no está configurada en .env")
        return 1
    
    # Ruta al archivo SQL
    script_dir = Path(__file__).parent
    sql_file = script_dir / "sql" / "migrate_etapa_6_recordatorios.sql"
    
    if not sql_file.exists():
        print(f"❌ ERROR: No se encontró {sql_file}")
        return 1
    
    print(f"📄 Archivo SQL: {sql_file}")
    print(f"🗄️  Base de datos: {db_url.split('@')[1] if '@' in db_url else 'localhost'}")
    print()
    print("⚙️  Ejecutando migración...")
    print()
    
    try:
        # Leer archivo SQL
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Conectar a la base de datos
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Ejecutar SQL
        cursor.execute(sql_content)
        
        # Cerrar conexión
        cursor.close()
        conn.close()
        
        print()
        print("=" * 70)
        print("✅ MIGRACIÓN COMPLETADA EXITOSAMENTE")
        print("=" * 70)
        print()
        print("Componentes creados:")
        print("  • Columna recordatorio_enviado en citas_medicas")
        print("  • Columna recordatorio_fecha_envio en citas_medicas")
        print("  • Columna recordatorio_intentos en citas_medicas")
        print("  • Índice idx_citas_recordatorios_pendientes")
        print()
        return 0
    
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
