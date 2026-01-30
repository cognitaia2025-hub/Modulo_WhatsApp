"""
Script para ejecutar migración de ETAPA 1 desde Python
"""
import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5434/agente_whatsapp")

print("=" * 60)
print("MIGRACIÓN ETAPA 1: Identificación de Usuarios")
print("=" * 60)

# Leer archivo SQL
with open("sql/migrate_etapa_1_identificacion.sql", "r", encoding="utf-8") as f:
    sql_script = f.read()

try:
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            print("\n✓ Conectado a la base de datos")
            print("✓ Ejecutando migración...\n")
            
            cur.execute(sql_script)
            conn.commit()
            
            print("\n" + "=" * 60)
            print("✅ MIGRACIÓN COMPLETADA EXITOSAMENTE")
            print("=" * 60)
            
            # Verificar resultado
            cur.execute("SELECT COUNT(*) FROM usuarios")
            total_usuarios = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM usuarios WHERE tipo_usuario = 'doctor'")
            total_doctores = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM usuarios WHERE tipo_usuario = 'paciente_externo'")
            total_pacientes = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM usuarios WHERE tipo_usuario = 'admin'")
            total_admins = cur.fetchone()[0]
            
            print(f"\n📊 Resumen de usuarios:")
            print(f"   • Total: {total_usuarios}")
            print(f"   • Doctores: {total_doctores}")
            print(f"   • Pacientes: {total_pacientes}")
            print(f"   • Administradores: {total_admins}")
            print()
            
except Exception as e:
    print("\n" + "=" * 60)
    print("❌ ERROR EN MIGRACIÓN")
    print("=" * 60)
    print(f"\nError: {e}")
    raise
