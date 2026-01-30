#!/usr/bin/env python3
"""
EJECUTAR MIGRACIÓN - ETAPA 3
Script para ejecutar la migración de base de datos de ETAPA 3
"""

import subprocess
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def main():
    print("=" * 70)
    print("🔧 EJECUTANDO MIGRACIÓN ETAPA 3")
    print("=" * 70)
    print()
    
    # Verificar variables de entorno
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ ERROR: DATABASE_URL no está configurada en .env")
        return 1
    
    # Ruta al archivo SQL
    script_dir = Path(__file__).parent
    sql_file = script_dir / "sql" / "migrate_etapa_3_flujo_inteligente.sql"
    
    if not sql_file.exists():
        print(f"❌ ERROR: No se encontró {sql_file}")
        return 1
    
    print(f"📄 Archivo SQL: {sql_file}")
    print(f"🗄️  Base de datos: {db_url.split('@')[1] if '@' in db_url else 'localhost'}")
    print()
    print("⚙️  Ejecutando migración...")
    print()
    
    try:
        # Parsear DATABASE_URL
        # postgresql://user:pass@host:port/dbname
        parts = db_url.replace("postgresql://", "").split("@")
        user_pass = parts[0].split(":")
        host_db = parts[1].split("/")
        host_port = host_db[0].split(":")
        
        user = user_pass[0]
        password = user_pass[1] if len(user_pass) > 1 else ""
        host = host_port[0]
        port = host_port[1] if len(host_port) > 1 else "5432"
        dbname = host_db[1]
        
        # Comando psql
        env = os.environ.copy()
        env["PGPASSWORD"] = password
        
        command = [
            "psql",
            "-h", host,
            "-p", port,
            "-U", user,
            "-d", dbname,
            "-f", str(sql_file)
        ]
        
        result = subprocess.run(
            command,
            env=env,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(result.stdout)
            print()
            print("=" * 70)
            print("✅ MIGRACIÓN COMPLETADA EXITOSAMENTE")
            print("=" * 70)
            print()
            print("Componentes creados:")
            print("  • Tabla clasificaciones_llm")
            print("  • Columna embedding en historiales_medicos")
            print("  • Índice HNSW para búsqueda vectorial")
            print("  • Vista resumen_clasificaciones")
            print("  • Vista metricas_llm_por_modelo")
            print("  • Función buscar_historiales_semantica()")
            print("  • Función registrar_clasificacion()")
            print("  • Función obtener_estadisticas_doctor_completas()")
            print()
            return 0
        else:
            print("❌ ERROR en migración:")
            print(result.stderr)
            return 1
    
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
