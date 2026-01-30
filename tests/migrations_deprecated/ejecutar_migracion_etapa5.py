"""
Ejecutar migración Etapa 5 - Sincronización Google Calendar
"""

import os
import psycopg
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5434/agente_whatsapp")

def ejecutar_migracion():
    """Ejecutar migración SQL de Etapa 5"""
    
    try:
        # Conectar a BD
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                print("🚀 Ejecutando migración Etapa 5...")
                
                # 1. Agregar columnas faltantes a sincronizacion_calendar si no existen
                print("📝 Actualizando tabla sincronizacion_calendar...")
                
                # Verificar y agregar columna max_intentos
                cur.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'sincronizacion_calendar' 
                    AND column_name = 'max_intentos'
                """)
                
                if not cur.fetchone():
                    cur.execute("ALTER TABLE sincronizacion_calendar ADD COLUMN max_intentos INTEGER DEFAULT 5")
                    print("✅ Columna 'max_intentos' agregada")
                else:
                    print("✅ Columna 'max_intentos' ya existe")
                
                # Verificar y agregar columna intentos
                cur.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'sincronizacion_calendar' 
                    AND column_name = 'intentos'
                """)
                
                if not cur.fetchone():
                    cur.execute("ALTER TABLE sincronizacion_calendar ADD COLUMN intentos INTEGER DEFAULT 0")
                    print("✅ Columna 'intentos' agregada")
                else:
                    print("✅ Columna 'intentos' ya existe")
                
                # 2. Actualizar constraint de estado para incluir error_permanente
                print("📝 Actualizando constraint de estado...")
                cur.execute("""
                    ALTER TABLE sincronizacion_calendar 
                    DROP CONSTRAINT IF EXISTS sincronizacion_calendar_estado_check
                """)
                cur.execute("""
                    ALTER TABLE sincronizacion_calendar 
                    ADD CONSTRAINT sincronizacion_calendar_estado_check 
                    CHECK (estado IN ('sincronizada', 'pendiente', 'error', 'reintentando', 'error_permanente'))
                """)
                print("✅ Constraint de estado actualizado")
                
                # 3. Verificar columnas en citas_medicas
                print("📝 Verificando columnas en citas_medicas...")
                
                cur.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'citas_medicas' 
                    AND column_name = 'sincronizada_google'
                """)
                
                if not cur.fetchone():
                    cur.execute("ALTER TABLE citas_medicas ADD COLUMN sincronizada_google BOOLEAN DEFAULT FALSE")
                    print("✅ Columna 'sincronizada_google' agregada a citas_medicas")
                else:
                    print("✅ Columna 'sincronizada_google' ya existe en citas_medicas")
                
                # 4. Crear índices si no existen
                print("📝 Creando índices...")
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_sync_pendientes
                    ON sincronizacion_calendar(estado, siguiente_reintento)
                    WHERE estado IN ('error', 'pendiente', 'reintentando')
                """)
                print("✅ Índice idx_sync_pendientes creado")
                
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_sync_cita_id
                    ON sincronizacion_calendar(cita_id)
                """)
                print("✅ Índice idx_sync_cita_id creado")
                
                conn.commit()
                print("✅ Migración ejecutada exitosamente")
                
                # Verificación final
                print("\n📊 Verificación final:")
                cur.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_name = 'sincronizacion_calendar'
                """)
                
                if cur.fetchone():
                    print("✅ Tabla 'sincronizacion_calendar' existe")
                    
                    # Verificar estructura
                    cur.execute("""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name = 'sincronizacion_calendar'
                        ORDER BY ordinal_position
                    """)
                    
                    columnas = [row[0] for row in cur.fetchall()]
                    print(f"📋 Columnas: {', '.join(columnas)}")
                else:
                    print("❌ Error: Tabla 'sincronizacion_calendar' no encontrada")
                
    except Exception as e:
        print(f"❌ Error ejecutando migración: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("\n" + "="*60)
    print("MIGRACIÓN ETAPA 5 - SINCRONIZACIÓN GOOGLE CALENDAR")
    print("="*60)
    
    if ejecutar_migracion():
        print("\n🎉 MIGRACIÓN COMPLETADA EXITOSAMENTE")
    else:
        print("\n💥 ERROR EN MIGRACIÓN")
    
    print("="*60)