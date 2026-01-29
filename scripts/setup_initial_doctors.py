"""Insertar doctores base Santiago y Joana"""
import psycopg
import os
from dotenv import load_dotenv

load_dotenv()

db_url = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"

print("\n👨‍⚕️ CONFIGURANDO DOCTORES INICIALES\n")

with psycopg.connect(db_url) as conn:
    with conn.cursor() as cur:
        # Verificar si existen usuarios para los doctores
        print("1. Verificando/creando usuarios...")

        # Santiago
        cur.execute("""
            INSERT INTO usuarios (phone_number, display_name, es_admin, tipo_usuario, timezone, is_active)
            VALUES ('+526641234567', 'Dr. Santiago de Jesús Ornelas Reynoso', FALSE, 'doctor', 'America/Tijuana', TRUE)
            ON CONFLICT (phone_number) DO UPDATE
            SET tipo_usuario = 'doctor', display_name = 'Dr. Santiago de Jesús Ornelas Reynoso'
            RETURNING id
        """)
        santiago_user = cur.fetchone()
        print(f"   ✅ Usuario Santiago: {santiago_user[0]}")

        # Joana
        cur.execute("""
            INSERT INTO usuarios (phone_number, display_name, es_admin, tipo_usuario, timezone, is_active)
            VALUES ('+526647654321', 'Dra. Joana Ibeth Meraz Arregín', FALSE, 'doctor', 'America/Tijuana', TRUE)
            ON CONFLICT (phone_number) DO UPDATE
            SET tipo_usuario = 'doctor', display_name = 'Dra. Joana Ibeth Meraz Arregín'
            RETURNING id
        """)
        joana_user = cur.fetchone()
        print(f"   ✅ Usuario Joana: {joana_user[0]}")

        conn.commit()

        # Insertar doctores
        print("\n2. Verificando/creando registros de doctores...")

        # Santiago (ID=1)
        cur.execute("""
            INSERT INTO doctores (id, phone_number, nombre_completo, especialidad, num_licencia, orden_turno, total_citas_asignadas, años_experiencia)
            VALUES (1, '+526641234567', 'Santiago de Jesús Ornelas Reynoso', 'Medicina General', 'LIC-SANTIAGO-001', 0, 0, 5)
            ON CONFLICT (id) DO UPDATE
            SET nombre_completo = 'Santiago de Jesús Ornelas Reynoso',
                phone_number = '+526641234567',
                especialidad = 'Medicina General'
            RETURNING id
        """)
        santiago_doctor = cur.fetchone()
        print(f"   ✅ Doctor Santiago (ID={santiago_doctor[0]})")

        # Joana (ID=2)
        cur.execute("""
            INSERT INTO doctores (id, phone_number, nombre_completo, especialidad, num_licencia, orden_turno, total_citas_asignadas, años_experiencia)
            VALUES (2, '+526647654321', 'Joana Ibeth Meraz Arregín', 'Pediatría', 'LIC-JOANA-001', 0, 0, 3)
            ON CONFLICT (id) DO UPDATE
            SET nombre_completo = 'Joana Ibeth Meraz Arregín',
                phone_number = '+526647654321',
                especialidad = 'Pediatría'
            RETURNING id
        """)
        joana_doctor = cur.fetchone()
        print(f"   ✅ Doctora Joana (ID={joana_doctor[0]})")

        conn.commit()

        print("\n✅ Doctores configurados correctamente\n")
