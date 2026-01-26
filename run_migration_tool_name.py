"""
Script de Migración: Agregar columna tool_name a herramientas_disponibles

Este script ejecuta la migración SQL que:
1. Agrega columna tool_name VARCHAR(100)
2. Pobla la columna con nombres predefinidos
3. Renombra id_tool → id
4. Hace tool_name NOT NULL y UNIQUE

Uso:
    python run_migration_tool_name.py
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def ejecutar_migracion():
    """
    Ejecuta la migración SQL desde el archivo migrate_add_tool_name.sql
    """
    print("=" * 80)
    print("MIGRACIÓN: Agregar columna tool_name a herramientas_disponibles")
    print("=" * 80)
    
    # Conexión a PostgreSQL
    try:
        conn = psycopg2.connect(
            host=os.getenv("PGHOST", "localhost"),
            port=os.getenv("PGPORT", "5434"),
            database=os.getenv("PGDATABASE", "agente_whatsapp"),
            user=os.getenv("PGUSER", "admin"),
            password=os.getenv("PGPASSWORD")
        )
        conn.autocommit = False  # Usar transacciones manuales
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        print("\n✅ Conectado a PostgreSQL")
        print(f"   Base de datos: {os.getenv('PGDATABASE', 'agente_whatsapp')}")
        print(f"   Puerto: {os.getenv('PGPORT', '5434')}\n")
        
        # Leer script SQL
        sql_path = os.path.join(os.path.dirname(__file__), 'sql', 'migrate_add_tool_name.sql')
        
        if not os.path.exists(sql_path):
            print(f"❌ ERROR: No se encuentra el archivo {sql_path}")
            return False
        
        with open(sql_path, 'r', encoding='utf-8') as f:
            sql_script = f.read()
        
        print("📄 Script SQL cargado correctamente\n")
        
        # Mostrar estado ANTES de la migración
        print("📊 ESTADO ANTES DE LA MIGRACIÓN:")
        print("-" * 80)
        
        try:
            cursor.execute("""
                SELECT id_tool, LEFT(descripcion, 40) as desc_preview, activa
                FROM herramientas_disponibles
                ORDER BY id_tool
            """)
            
            rows = cursor.fetchall()
            print(f"{'ID':<5} {'Descripción':<42} {'Activa':<7}")
            print("-" * 80)
            for row in rows:
                print(f"{row['id_tool']:<5} {row['desc_preview']:<42} {row['activa']}")
            
        except Exception as e:
            print(f"   Info: {e}")
        
        print("\n" + "=" * 80)
        print("🔧 EJECUTANDO MIGRACIÓN...")
        print("=" * 80 + "\n")
        
        # Ejecutar migración
        cursor.execute(sql_script)
        
        # Mostrar estado DESPUÉS de la migración
        print("\n📊 ESTADO DESPUÉS DE LA MIGRACIÓN:")
        print("-" * 80)
        
        cursor.execute("""
            SELECT 
                id,
                tool_name,
                LEFT(descripcion, 30) || '...' as desc_preview,
                activa
            FROM herramientas_disponibles
            ORDER BY id
        """)
        
        rows = cursor.fetchall()
        print(f"{'ID':<5} {'Tool Name':<30} {'Descripción':<35} {'Activa':<7}")
        print("-" * 80)
        for row in rows:
            print(f"{row['id']:<5} {row['tool_name']:<30} {row['desc_preview']:<35} {row['activa']}")
        
        # Confirmar cambios
        print("\n" + "=" * 80)
        respuesta = input("¿Confirmar migración? (S/n): ").strip().lower()
        
        if respuesta in ['s', 'si', 'sí', 'yes', '']:
            conn.commit()
            print("\n✅ MIGRACIÓN EXITOSA - Cambios confirmados")
            print("\n📋 Resumen:")
            print("   • Columna 'tool_name' agregada")
            print("   • Nombres de herramientas poblados")
            print("   • Columna 'id_tool' renombrada a 'id'")
            print("   • Constraints NOT NULL y UNIQUE aplicados")
            return True
        else:
            conn.rollback()
            print("\n❌ MIGRACIÓN CANCELADA - Cambios revertidos")
            return False
        
    except Exception as e:
        print(f"\n❌ ERROR durante la migración: {e}")
        if 'conn' in locals():
            conn.rollback()
            print("   Cambios revertidos (ROLLBACK)")
        return False
    
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()
            print("\n🔌 Conexión cerrada")


if __name__ == "__main__":
    exito = ejecutar_migracion()
    
    if exito:
        print("\n" + "=" * 80)
        print("✅ PRÓXIMOS PASOS:")
        print("=" * 80)
        print("1. El código Python ya está actualizado para usar 'tool_name'")
        print("2. Reinicia el servidor FastAPI (uvicorn)")
        print("3. Prueba el Nodo 4 con: '¿qué eventos tengo?'")
        print("4. Verifica en logs que muestre: [DEBUG] IDs Válidos en DB: ['list_calendar_events', ...]")
    else:
        print("\n⚠️  La migración no se completó. Revisa los errores arriba.")
