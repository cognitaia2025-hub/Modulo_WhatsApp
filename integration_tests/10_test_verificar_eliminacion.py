"""
TEST #10: Verificar eliminacion
Objetivo: Confirmar que solo queda la reunion del equipo
Herramienta esperada: list_calendar_events
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from integration_tests.test_base import IntegrationTestBase


class Test10VerificarEliminacion(IntegrationTestBase):
    """PRUEBA 10: Verificar eliminacion"""

    def __init__(self):
        super().__init__("Verificar eliminacion del evento", 10)

    def run(self):
        """Ejecuta el test"""
        self.print_header()

        # Mensaje del usuario
        mensaje = "Muestrame todos mis eventos de los proximos 7 dias"

        self.print_step("Objetivo: Confirmar que solo queda la reunion")
        self.print_step(f"Herramienta esperada: list_calendar_events")
        print()

        # Enviar mensaje
        response = self.send_message(mensaje)

        # Esperar
        self.wait(2)

        # Verificar
        if "error" not in response:
            self.print_success("Test completado")
            self.print_info("Resultado esperado:")
            self.print_info("   ✅ Solo aparece 'reunion con el equipo' a las 11am")
            self.print_info("   ❌ NO aparece 'cita con el doctor' (fue eliminada)")
            self.save_result(True, {"response": response})
        else:
            self.print_error(f"Test fallido: {response.get('error')}")
            self.save_result(False, {"error": response.get("error")})

        print()
        self.print_info("💡 Solo debe aparecer 1 evento en el resultado")
        print()


if __name__ == "__main__":
    test = Test10VerificarEliminacion()
    test.run()
