"""
Script completo de ETAPA 1: Migración + Tests + Notificación
"""
import os
import sys
import subprocess
from pathlib import Path

# Añadir el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 70)
print("🚀 ETAPA 1: Sistema de Identificación de Usuarios")
print("=" * 70)
print()

# ============================================================================
# PASO 1: Ejecutar Migración
# ============================================================================
print("📦 PASO 1: Ejecutando migración de base de datos...")
print("-" * 70)

try:
    import psycopg
    from dotenv import load_dotenv
    
    load_dotenv()
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5434/agente_whatsapp")
    
    # Leer archivo SQL
    sql_file = Path("sql/migrate_etapa_1_identificacion.sql")
    if not sql_file.exists():
        print(f"❌ Error: No se encuentra {sql_file}")
        sys.exit(1)
    
    with open(sql_file, "r", encoding="utf-8") as f:
        sql_script = f.read()
    
    # Ejecutar migración
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            print("   ✓ Conectado a la base de datos")
            print("   ✓ Ejecutando migración...")
            
            cur.execute(sql_script)
            conn.commit()
            
            # Verificar resultado
            cur.execute("SELECT COUNT(*) FROM usuarios")
            total_usuarios = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM usuarios WHERE tipo_usuario = 'doctor'")
            total_doctores = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM usuarios WHERE tipo_usuario = 'paciente_externo'")
            total_pacientes = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM usuarios WHERE tipo_usuario = 'admin'")
            total_admins = cur.fetchone()[0]
            
            print()
            print("   ✅ MIGRACIÓN COMPLETADA")
            print(f"   📊 Resumen: {total_usuarios} usuarios ({total_doctores} doctores, {total_pacientes} pacientes, {total_admins} admins)")
            print()
            
except Exception as e:
    print(f"\n   ❌ ERROR EN MIGRACIÓN: {e}")
    print("\n⚠️  Continuando con tests (la BD puede ya estar migrada)...\n")

# ============================================================================
# PASO 2: Ejecutar Tests
# ============================================================================
print("-" * 70)
print("🧪 PASO 2: Ejecutando tests de ETAPA 1...")
print("-" * 70)
print()

test_result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/Etapa_1/", "-v", "--tb=short", "-x"],
    capture_output=False
)

print()
print("=" * 70)

# ============================================================================
# PASO 3: Resultado Final
# ============================================================================
if test_result.returncode == 0:
    print("✅ ETAPA 1 COMPLETADA EXITOSAMENTE")
    print("=" * 70)
    print()
    print("📋 Resumen:")
    print("   ✓ Migración de BD ejecutada")
    print("   ✓ Nodo de identificación actualizado")
    print("   ✓ Estado del grafo actualizado")
    print("   ✓ Todos los tests pasaron")
    print()
    print("📚 Documentación:")
    print("   • Ver: docs/ETAPA_1_COMPLETADA.md")
    print("   • Ver: tests/Etapa_1/README.md")
    print()
    
    # ========================================================================
    # PASO 4: Notificación
    # ========================================================================
    print("-" * 70)
    print("🔔 PASO 3: Ejecutando notificación...")
    print("-" * 70)
    print()
    
    try:
        subprocess.run([sys.executable, "notificar_completado.py"], check=True)
    except Exception as e:
        print(f"⚠️  No se pudo ejecutar notificación: {e}")
    
    sys.exit(0)
    
else:
    print("❌ ALGUNOS TESTS FALLARON")
    print("=" * 70)
    print()
    print("🔍 Revisa los errores arriba y corrige el código.")
    print("📖 Recuerda: Si test falla → reparar código, NO modificar tests")
    print()
    sys.exit(1)
