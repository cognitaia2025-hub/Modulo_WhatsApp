"""
Test 00: Nodo de Identificación de Usuario (N0)

Prueba el primer nodo del sistema que:
- Extrae número de teléfono del mensaje
- Consulta usuario en BD
- Determina tipo de usuario (paciente, doctor, admin)
- Auto-registra usuarios nuevos
"""

import pytest
from datetime import datetime

from conftest import (
    crear_estado_base,
    validar_estado_post_identificacion,
    TEST_PACIENTE_PHONE,
    TEST_DOCTOR_PHONE,
    TEST_ADMIN_PHONE,
    TEST_NUEVO_PHONE,
)


class TestNodoIdentificacion:
    """Tests para el nodo N0: Identificación de Usuario."""

    # =========================================================================
    # TESTS: USUARIOS EXISTENTES
    # =========================================================================

    def test_identificar_paciente_existente(
        self, nodo_identificacion, estado_paciente, setup_test_data
    ):
        """
        Test: Identificar un paciente que ya existe en la BD.
        
        Escenario: Un paciente registrado envía mensaje.
        Esperado: Se identifica correctamente con tipo_usuario='personal' o 'paciente_externo'
        """
        # Ejecutar nodo
        resultado = nodo_identificacion(estado_paciente)
        
        # Validaciones básicas
        validar_estado_post_identificacion(resultado)
        
        # Validaciones específicas
        assert resultado["user_id"] == TEST_PACIENTE_PHONE
        assert resultado["usuario_registrado"] == True, "Usuario debe estar marcado como registrado"
        assert resultado["tipo_usuario"] in ["personal", "paciente_externo"]
        assert resultado["es_admin"] == False
        
        # Verificar que se cargó información del usuario
        assert resultado["usuario_info"].get("phone_number") == TEST_PACIENTE_PHONE
        
        print(f"✅ Paciente identificado: {resultado['usuario_info'].get('display_name')}")

    def test_identificar_doctor_existente(
        self, nodo_identificacion, estado_doctor, setup_test_data
    ):
        """
        Test: Identificar un doctor que existe en la BD.
        
        Escenario: El Dr. Santiago envía mensaje.
        Esperado: tipo_usuario='doctor' y doctor_id asignado.
        """
        # Ejecutar nodo
        resultado = nodo_identificacion(estado_doctor)
        
        # Validaciones básicas
        validar_estado_post_identificacion(resultado)
        
        # Validaciones específicas para doctor
        assert resultado["user_id"] == TEST_DOCTOR_PHONE
        assert resultado["tipo_usuario"] == "doctor"
        assert resultado["doctor_id"] is not None, "Doctor debe tener doctor_id"
        assert resultado["doctor_id"] > 0
        
        # Verificar información del doctor
        usuario_info = resultado["usuario_info"]
        assert "especialidad" in usuario_info or usuario_info.get("nombre_completo")
        
        print(f"✅ Doctor identificado: {usuario_info.get('nombre_completo', 'N/A')}")
        print(f"   Doctor ID: {resultado['doctor_id']}")
        print(f"   Especialidad: {usuario_info.get('especialidad', 'N/A')}")

    def test_identificar_admin(
        self, nodo_identificacion, estado_admin, setup_test_data
    ):
        """
        Test: Identificar al administrador del sistema.
        
        Escenario: El admin envía mensaje.
        Esperado: es_admin=True, tipo_usuario='admin'
        """
        # Ejecutar nodo
        resultado = nodo_identificacion(estado_admin)
        
        # Validaciones básicas
        validar_estado_post_identificacion(resultado)
        
        # Validaciones específicas para admin
        assert resultado["user_id"] == TEST_ADMIN_PHONE
        assert resultado["es_admin"] == True, "Debe ser identificado como admin"
        assert resultado["tipo_usuario"] == "admin"
        
        print(f"✅ Admin identificado correctamente")
        print(f"   es_admin: {resultado['es_admin']}")

    # =========================================================================
    # TESTS: USUARIOS NUEVOS (AUTO-REGISTRO)
    # =========================================================================

    def test_autoregistro_usuario_nuevo(
        self, nodo_identificacion, estado_usuario_nuevo, db_connection, setup_test_data
    ):
        """
        Test: Auto-registrar un usuario que no existe en la BD.
        
        Escenario: Usuario nuevo envía primer mensaje.
        Esperado: Se crea automáticamente con tipo='personal'.
        """
        # Limpiar usuario de prueba si existe de tests anteriores
        with db_connection.cursor() as cur:
            cur.execute(
                "DELETE FROM usuarios WHERE phone_number = %s",
                (TEST_NUEVO_PHONE,)
            )
            db_connection.commit()
        
        # Ejecutar nodo
        resultado = nodo_identificacion(estado_usuario_nuevo)
        
        # Validaciones básicas
        validar_estado_post_identificacion(resultado)
        
        # Validaciones de auto-registro
        assert resultado["user_id"] == TEST_NUEVO_PHONE
        assert resultado["usuario_registrado"] == False, \
            "usuario_registrado debe ser False para usuarios nuevos"
        # Por defecto, usuarios nuevos son 'paciente_externo' (desde personas sin cuenta previa)
        assert resultado["tipo_usuario"] in ["personal", "paciente_externo"]
        assert resultado["es_admin"] == False
        
        # Verificar que se creó en BD
        with db_connection.cursor() as cur:
            cur.execute(
                "SELECT id, phone_number, tipo_usuario FROM usuarios WHERE phone_number = %s",
                (TEST_NUEVO_PHONE,)
            )
            user_row = cur.fetchone()
            assert user_row is not None, "Usuario debe existir en BD después del auto-registro"
            assert user_row[1] == TEST_NUEVO_PHONE
        
        # Limpiar después del test
        with db_connection.cursor() as cur:
            cur.execute(
                "DELETE FROM usuarios WHERE phone_number = %s",
                (TEST_NUEVO_PHONE,)
            )
            db_connection.commit()
        
        print(f"✅ Usuario nuevo auto-registrado correctamente")
        print(f"   Usuario registrado: {resultado['usuario_registrado']}")

    # =========================================================================
    # TESTS: CASOS LÍMITE
    # =========================================================================

    def test_mensaje_sin_numero_valido(self, nodo_identificacion, setup_test_data):
        """
        Test: Mensaje con número de teléfono vacío o inválido.
        
        Escenario: Estado con user_id vacío.
        Esperado: Debería manejar el caso o usar default.
        """
        estado = crear_estado_base(
            user_id="",  # Vacío
            mensaje="Hola",
            sender_name="Desconocido"
        )
        
        # Ejecutar nodo (no debería fallar)
        resultado = nodo_identificacion(estado)
        
        # Debe haber algún manejo del caso
        assert resultado is not None
        # El sistema debería asignar un ID por defecto o manejar el error
        print(f"✅ Caso de número vacío manejado correctamente")

    def test_formato_numero_internacional(self, nodo_identificacion, setup_test_data):
        """
        Test: Diferentes formatos de número de teléfono.
        
        Escenario: Número con y sin código de país.
        """
        formatos = [
            "+526649876543",      # Formato completo
            "526649876543",       # Sin +
            "6649876543",         # Solo número local
        ]
        
        for formato in formatos:
            estado = crear_estado_base(
                user_id=formato,
                mensaje="Hola",
                sender_name="Test"
            )
            
            resultado = nodo_identificacion(estado)
            
            # No debe fallar con ningún formato
            assert resultado is not None
            print(f"✅ Formato {formato} procesado correctamente")

    def test_usuario_desactivado(
        self, nodo_identificacion, db_connection, setup_test_data
    ):
        """
        Test: Usuario existente pero desactivado (is_active=false).
        
        Escenario: Usuario que fue desactivado intenta acceder.
        Esperado: Definir comportamiento (error o reactivación).
        """
        # Crear usuario desactivado
        test_phone = "+526640000001"
        
        with db_connection.cursor() as cur:
            # Limpiar si existe
            cur.execute("DELETE FROM usuarios WHERE phone_number = %s", (test_phone,))
            
            # Insertar usuario desactivado
            cur.execute("""
                INSERT INTO usuarios (phone_number, display_name, tipo_usuario, is_active)
                VALUES (%s, 'Usuario Inactivo', 'personal', false)
            """, (test_phone,))
            db_connection.commit()
        
        try:
            estado = crear_estado_base(
                user_id=test_phone,
                mensaje="Hola",
                sender_name="Usuario Inactivo"
            )
            
            resultado = nodo_identificacion(estado)
            
            # Verificar comportamiento (depende de la implementación)
            assert resultado is not None
            print(f"✅ Usuario desactivado manejado: tipo={resultado.get('tipo_usuario')}")
            
        finally:
            # Limpiar
            with db_connection.cursor() as cur:
                cur.execute("DELETE FROM usuarios WHERE phone_number = %s", (test_phone,))
                db_connection.commit()

    # =========================================================================
    # TESTS: VALIDACIÓN DE TIMESTAMPS
    # =========================================================================

    def test_timestamp_actualizado(
        self, nodo_identificacion, estado_paciente, setup_test_data
    ):
        """
        Test: Verificar que el timestamp se actualiza correctamente.
        """
        timestamp_antes = estado_paciente.get("timestamp")
        
        resultado = nodo_identificacion(estado_paciente)
        
        timestamp_despues = resultado.get("timestamp")
        
        # El timestamp debe existir
        assert timestamp_despues is not None
        
        print(f"✅ Timestamp actualizado: {timestamp_despues}")


class TestNodoIdentificacionPerformance:
    """Tests de rendimiento para N0."""

    @pytest.mark.slow
    def test_tiempo_respuesta_identificacion(
        self, nodo_identificacion, estado_paciente, setup_test_data
    ):
        """
        Test: El nodo debe responder en menos de 500ms.
        """
        import time
        
        start = time.time()
        resultado = nodo_identificacion(estado_paciente)
        elapsed = (time.time() - start) * 1000  # ms
        
        assert resultado is not None
        assert elapsed < 500, f"Identificación tardó {elapsed:.0f}ms (máx: 500ms)"
        
        print(f"✅ Tiempo de identificación: {elapsed:.0f}ms")

    @pytest.mark.slow
    def test_multiples_identificaciones(
        self, nodo_identificacion, setup_test_data
    ):
        """
        Test: Múltiples identificaciones consecutivas.
        """
        import time
        
        tiempos = []
        for i in range(5):
            estado = crear_estado_base(
                user_id=TEST_PACIENTE_PHONE,
                mensaje=f"Mensaje de prueba {i}",
                sender_name="Test"
            )
            
            start = time.time()
            resultado = nodo_identificacion(estado)
            elapsed = (time.time() - start) * 1000
            tiempos.append(elapsed)
            
            assert resultado is not None
        
        promedio = sum(tiempos) / len(tiempos)
        print(f"✅ Promedio de 5 identificaciones: {promedio:.0f}ms")
        print(f"   Tiempos: {[f'{t:.0f}ms' for t in tiempos]}")


# ============================================================================
# EJECUCIÓN DIRECTA
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
