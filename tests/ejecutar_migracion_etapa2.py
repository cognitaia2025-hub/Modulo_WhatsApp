"""
Script para ejecutar migración de ETAPA 2 desde Python
"""
import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5434/agente_whatsapp")

print("=" * 60)
print("MIGRACIÓN ETAPA 2: Sistema de Turnos Automático")
print("=" * 60)

# Leer archivo SQL
with open("sql/migrate_etapa_2_turnos.sql", "r", encoding="utf-8") as f:
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
            cur.execute("SELECT COUNT(*) FROM control_turnos")
            total_control = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM disponibilidad_medica")
            total_disponibilidad = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM doctores WHERE id IN (1, 2)")
            total_doctores = cur.fetchone()[0]
            
            print(f"\n📊 Resumen:")
            print(f"   • Tabla control_turnos: {total_control} registros")
            print(f"   • Disponibilidad configurada: {total_disponibilidad} registros")
            print(f"   • Doctores activos (Santiago, Joana): {total_doctores}")
            print()
            
            if total_doctores < 2:
                print("⚠️  ADVERTENCIA: Faltan doctores en la BD.")
                print("    Verifica que existan Santiago (ID=1) y Joana (ID=2)")
                print()
            
except Exception as e:
    print("\n" + "=" * 60)
    print("❌ ERROR EN MIGRACIÓN")
    print("=" * 60)
    print(f"\nError: {e}")
    raise
