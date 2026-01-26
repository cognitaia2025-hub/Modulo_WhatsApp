"""
Script para configurar tabla user_sessions con Rolling Window
==============================================================

Ejecuta el SQL para crear la tabla y funciones necesarias.
"""

import psycopg
import os
from dotenv import load_dotenv

load_dotenv()

def setup_user_sessions_table():
    """Crea la tabla y funciones para rolling window"""
    
    # Leer SQL file
    with open('sql/setup_user_sessions.sql', 'r', encoding='utf-8') as f:
        sql_script = f.read()
    
    # Conectar a PostgreSQL
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL no configurado en .env")
        return False
    
    try:
        print("🔗 Conectando a PostgreSQL...")
        conn = psycopg.connect(database_url, autocommit=True)
        cursor = conn.cursor()
        
        print("📝 Ejecutando SQL...")
        cursor.execute(sql_script)
        
        print("\n✅ Tabla user_sessions creada exitosamente\n")
        
        # Verificar tabla
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'user_sessions'
            ORDER BY ordinal_position
        """)
        
        print("📋 Estructura de la tabla:")
        for row in cursor.fetchall():
            print(f"   - {row[0]}: {row[1]}")
        
        # Mostrar funciones creadas
        cursor.execute("""
            SELECT routine_name 
            FROM information_schema.routines 
            WHERE routine_schema = 'public' 
                AND routine_name LIKE '%session%'
        """)
        
        print("\n🔧 Funciones creadas:")
        for row in cursor.fetchall():
            print(f"   - {row[0]}()")
        
        cursor.close()
        conn.close()
        
        print("\n✅ Setup completado correctamente")
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


if __name__ == "__main__":
    print("\n" + "="*70)
    print("🏗️  SETUP: Tabla user_sessions (Rolling Window)")
    print("="*70 + "\n")
    
    success = setup_user_sessions_table()
    
    if success:
        print("\n" + "="*70)
        print("🎉 ¡LISTO! Ahora puedes usar rolling window")
        print("="*70)
        print("""
📝 Próximos pasos:

1. Usa get_or_create_session() en tu handler de WhatsApp
2. Verifica sesiones activas:
   SELECT * FROM active_sessions_24h;
   
3. Ver estadísticas:
   SELECT * FROM session_statistics;
   
4. Limpiar sesiones antiguas:
   SELECT cleanup_old_sessions();
        """)
    else:
        print("\n⚠️  Hubo problemas en el setup. Revisa los errores arriba.")
