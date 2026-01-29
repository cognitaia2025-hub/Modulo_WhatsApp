"""
Script para ejecutar la correccion del tipo_usuario del admin.
Resuelve los tests fallando en Etapa 1.
"""
import os
import psycopg
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5434/agente_whatsapp")

def ejecutar_fix_admin():
    """Ejecuta el SQL para corregir el tipo_usuario del admin"""

    print("[*] Ejecutando correccion del tipo_usuario del admin...")
    print(f"[*] Base de datos: {DATABASE_URL}")

    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                # Leer el archivo SQL
                with open('sql/fix_admin_tipo_usuario.sql', 'r', encoding='utf-8') as f:
                    sql = f.read()

                # Ejecutar el SQL
                cur.execute(sql)
                conn.commit()

                print("[OK] Correccion ejecutada exitosamente")

                # Verificar el resultado
                cur.execute("""
                    SELECT phone_number, display_name, es_admin, tipo_usuario
                    FROM usuarios
                    WHERE phone_number = '+526641234567'
                """)

                resultado = cur.fetchone()
                if resultado:
                    phone, nombre, es_admin, tipo = resultado
                    print(f"\n[INFO] Estado actual del admin:")
                    print(f"   Telefono: {phone}")
                    print(f"   Nombre: {nombre}")
                    print(f"   Es admin: {es_admin}")
                    print(f"   Tipo: {tipo}")

                    if tipo == 'admin':
                        print("\n[OK] Correccion exitosa! El admin ahora tiene tipo_usuario = 'admin'")
                        return True
                    else:
                        print(f"\n[WARN] tipo_usuario = '{tipo}' (esperado: 'admin')")
                        return False
                else:
                    print("[ERROR] No se encontro el usuario admin")
                    return False

    except Exception as e:
        print(f"[ERROR] Error ejecutando correccion: {e}")
        return False

if __name__ == '__main__':
    exito = ejecutar_fix_admin()

    if exito:
        print("\n[NEXT] Ahora ejecuta los tests de Etapa 1:")
        print("   python -m pytest tests/Etapa_1/ -v")
    else:
        print("\n[WARN] Hubo un problema con la correccion")
