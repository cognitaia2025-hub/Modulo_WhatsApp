"""
TEST #09: Eliminar evento
Objetivo: Probar eliminacion de evento
Herramienta esperada: delete_calendar_event
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from integration_tests.test_base import IntegrationTestBase


class Test09EliminarEvento(IntegrationTestBase):
    """PRUEBA 9: Eliminar evento"""

    def __init__(self):
        super().__init__("Eliminar cita con el doctor", 9)

    def run(self):
        """Ejecuta el test"""
        self.print_header()

        # Mensaje del usuario
        mensaje = "Elimina la cita con el doctor"

        self.print_step("Objetivo: Probar eliminacion")
        self.print_step(f"Herramienta esperada: delete_calendar_event")
        print()

        # Enviar mensaje
        response = self.send_message(mensaje)

        # Esperar
        self.wait(2)

        # Verificar
        if "error" not in response:
            self.print_success("Test completado")
            self.print_info("Resultado esperado: Confirmacion de eliminacion")
            self.save_result(True, {"response": response})
        else:
            self.print_error(f"Test fallido: {response.get('error')}")
            self.save_result(False, {"error": response.get("error")})

        print()
        self.print_info("💡 Revisa los logs del backend para ver:")
        self.print_info("   - Si selecciono 'delete_calendar_event'")
        self.print_info("   - Si encontro el evento correcto")
        self.print_info("   - Si lo elimino exitosamente")
        print()


if __name__ == "__main__":
    test = Test09EliminarEvento()
    test.run()
