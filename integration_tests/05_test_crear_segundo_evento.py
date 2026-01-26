"""
TEST #05: Crear segundo evento
Objetivo: Crear segundo evento para tener más datos
Herramienta esperada: create_calendar_event
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from integration_tests.test_base import IntegrationTestBase


class Test05CrearSegundoEvento(IntegrationTestBase):
    """PRUEBA 5: Crear segundo evento"""

    def __init__(self):
        super().__init__("Crear segundo evento - Cita doctor", 5)

    def run(self):
        """Ejecuta el test"""
        self.print_header()

        # Mensaje del usuario
        mensaje = 'Crea un evento llamado "Cita con el doctor" para pasado manana a las 3pm'

        self.print_step("Objetivo: Crear segundo evento")
        self.print_step(f"Herramienta esperada: create_calendar_event")
        print()

        # Enviar mensaje
        response = self.send_message(mensaje)

        # Esperar
        self.wait(2)

        # Verificar
        if "error" not in response:
            self.print_success("Test completado")
            self.print_info("Resultado esperado: Confirmacion de evento 'Cita con el doctor'")
            self.print_info("   Fecha: Pasado manana")
            self.print_info("   Hora: 3:00 PM")
            self.save_result(True, {"response": response})
        else:
            self.print_error(f"Test fallido: {response.get('error')}")
            self.save_result(False, {"error": response.get("error")})

        print()
        self.print_info("💡 Ahora tenemos 2 eventos en el calendario:")
        self.print_info("   1. Reunion con el equipo (manana 10am)")
        self.print_info("   2. Cita con el doctor (pasado manana 3pm)")
        print()


if __name__ == "__main__":
    test = Test05CrearSegundoEvento()
    test.run()
