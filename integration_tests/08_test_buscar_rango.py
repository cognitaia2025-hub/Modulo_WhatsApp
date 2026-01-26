"""
TEST #08: Buscar con rango de fechas
Objetivo: Probar busqueda por rango de fechas
Herramienta esperada: search_calendar_events
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from integration_tests.test_base import IntegrationTestBase


class Test08BuscarRango(IntegrationTestBase):
    """PRUEBA 8: Buscar con rango de fechas"""

    def __init__(self):
        super().__init__("Buscar eventos proxima semana", 8)

    def run(self):
        """Ejecuta el test"""
        self.print_header()

        # Mensaje del usuario
        mensaje = "Busca eventos de la proxima semana"

        self.print_step("Objetivo: Probar busqueda por rango")
        self.print_step(f"Herramienta esperada: search_calendar_events")
        print()

        # Enviar mensaje
        response = self.send_message(mensaje)

        # Esperar
        self.wait(2)

        # Verificar
        if "error" not in response:
            self.print_success("Test completado")
            self.print_info("Resultado esperado: Ambos eventos creados")
            self.print_info("   1. Reunion del equipo (11am)")
            self.print_info("   2. Cita con el doctor (3pm)")
            self.save_result(True, {"response": response})
        else:
            self.print_error(f"Test fallido: {response.get('error')}")
            self.save_result(False, {"error": response.get("error")})

        print()
        self.print_info("💡 Ambos eventos deben aparecer en el resultado")
        print()


if __name__ == "__main__":
    test = Test08BuscarRango()
    test.run()
