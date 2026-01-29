"""Script para ejecutar migraciones de las Etapas 1, 2 y 3"""
import psycopg
import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar .env
load_dotenv()

def ejecutar_sql_file(conn, filepath: str, etapa: str):
    """Ejecuta un archivo SQL y muestra resultado"""
    print(f"\n{'='*60}")
    print(f"📄 Ejecutando: {filepath}")
    print(f"{'='*60}")

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            sql_content = f.read()

        with conn.cursor() as cur:
            # Ejecutar el SQL
            cur.execute(sql_content)
            conn.commit()

        print(f"✅ {etapa} - Migración completada exitosamente")
        return True

    except Exception as e:
        print(f"❌ Error en {etapa}: {e}")
        conn.rollback()
        return False

def main():
    print("\n🔧 EJECUTANDO MIGRACIONES - ETAPAS 1, 2, 3\n")

    try:
        # Construir URL de BD directamente
        db_url = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"

        # Conectar a BD
        print(f"📡 Conectando a PostgreSQL...")
        with psycopg.connect(db_url) as conn:
            print(f"✅ Conexión exitosa\n")

            # Ejecutar migraciones en orden
            # Primero las base, luego las etapas
            migraciones = [
                ("sql/migrate_medical_system.sql", "BASE - Sistema Médico"),
                ("sql/migrate_etapa_1_identificacion.sql", "ETAPA 1"),
                ("sql/migrate_etapa_2_turnos.sql", "ETAPA 2"),
                ("sql/migrate_etapa_3_flujo_inteligente_clean.sql", "ETAPA 3"),
            ]

            resultados = []

            for sql_file, etapa in migraciones:
                filepath = Path(__file__).parent.parent / sql_file
                if filepath.exists():
                    resultado = ejecutar_sql_file(conn, str(filepath), etapa)
                    resultados.append((etapa, resultado))
                else:
                    print(f"⚠️  Archivo no encontrado: {sql_file}")
                    resultados.append((etapa, False))

            # Resumen final
            print(f"\n{'='*60}")
            print("📊 RESUMEN DE MIGRACIONES")
            print(f"{'='*60}")
            for etapa, exito in resultados:
                status = "✅ EXITOSA" if exito else "❌ FALLIDA"
                print(f"{etapa}: {status}")

            todas_exitosas = all(r[1] for r in resultados)

            if todas_exitosas:
                print(f"\n🎉 Todas las migraciones completadas correctamente")
                return 0
            else:
                print(f"\n⚠️  Algunas migraciones fallaron. Revisar errores arriba.")
                return 1

    except Exception as e:
        print(f"\n❌ Error crítico: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
