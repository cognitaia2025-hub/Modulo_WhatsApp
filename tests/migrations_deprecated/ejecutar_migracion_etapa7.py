"""
Script para ejecutar la migración SQL de la Etapa 7: Herramientas Médicas Avanzadas
"""
import sys
import os
import psycopg
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def ejecutar_migracion():
    """Ejecuta el script SQL de migración de la Etapa 7"""
    
    # Obtener configuración desde variable de entorno
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5434/agente_whatsapp")
    
    sql_file = Path(__file__).parent / 'sql' / 'migrate_etapa_7_herramientas_medicas.sql'
    
    print("=" * 80)
    print("MIGRACIÓN ETAPA 7: HERRAMIENTAS MÉDICAS AVANZADAS")
    print("=" * 80)
    print(f"\nArchivo SQL: {sql_file}")
    print(f"Database URL: {DATABASE_URL[:50]}...")
    
    if not sql_file.exists():
        print(f"\n❌ ERROR: No se encontró el archivo {sql_file}")
        return False
    
    conn = None
    try:
        # Conectar a la base de datos
        print("\n📡 Conectando a PostgreSQL...")
        conn = psycopg.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Leer y ejecutar el SQL
        print("📄 Leyendo archivo SQL...")
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        print("⚙️  Ejecutando migración...")
        cursor.execute(sql_content)
        
        # Commit
        conn.commit()
        print("\n✅ Migración ejecutada exitosamente!")
        
        # Verificar componentes creados
        print("\n🔍 Verificando componentes creados:")
        
        # Verificar tabla metricas_consultas
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'metricas_consultas'
            );
        """)
        if cursor.fetchone()[0]:
            print("   ✓ Tabla metricas_consultas")
        
        # Verificar tabla reportes_generados
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'reportes_generados'
            );
        """)
        if cursor.fetchone()[0]:
            print("   ✓ Tabla reportes_generados")
        
        # Verificar función actualizar_metricas_doctor
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM pg_proc 
                WHERE proname = 'actualizar_metricas_doctor'
            );
        """)
        if cursor.fetchone()[0]:
            print("   ✓ Función actualizar_metricas_doctor()")
        
        # Verificar función buscar_citas_por_periodo
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM pg_proc 
                WHERE proname = 'buscar_citas_por_periodo'
            );
        """)
        if cursor.fetchone()[0]:
            print("   ✓ Función buscar_citas_por_periodo()")
        
        # Verificar vista vista_estadisticas_doctores
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.views 
                WHERE table_schema = 'public' 
                AND table_name = 'vista_estadisticas_doctores'
            );
        """)
        if cursor.fetchone()[0]:
            print("   ✓ Vista vista_estadisticas_doctores")
        
        # Verificar trigger
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM pg_trigger 
                WHERE tgname = 'trigger_actualizar_metricas'
            );
        """)
        if cursor.fetchone()[0]:
            print("   ✓ Trigger trigger_actualizar_metricas")
        
        print("\n📊 RESUMEN DE LA MIGRACIÓN:")
        print("   • Tablas creadas: 2")
        print("   • Funciones creadas: 2")
        print("   • Vistas creadas: 1")
        print("   • Triggers creados: 1")
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 80)
        print("✅ MIGRACIÓN COMPLETADA CON ÉXITO")
        print("=" * 80)
        
        return True
        
    except psycopg.Error as e:
        print(f"\n❌ ERROR de PostgreSQL:")
        print(f"   {str(e)}")
        if conn:
            conn.rollback()
            conn.close()
        return False
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.rollback()
            conn.close()
        return False


if __name__ == '__main__':
    exito = ejecutar_migracion()
    sys.exit(0 if exito else 1)
