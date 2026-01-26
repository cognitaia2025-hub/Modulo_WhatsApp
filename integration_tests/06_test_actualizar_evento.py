"""
TEST #06: Actualizar evento
Objetivo: Modificar la hora del primer evento
Herramienta esperada: update_calendar_event
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from integration_tests.test_base import IntegrationTestBase


class Test06ActualizarEvento(IntegrationTestBase):
    """PRUEBA 6: Actualizar evento"""
    
    def __init__(self):
        super().__init__("Actualizar hora de reunion", 6)
    
    def run(self):
        """Ejecuta el test"""
        self.print_header()
        
        # Mensaje del usuario
        mensaje = "Cambia la reunion del equipo para las 11am"
        
        self.print_step("Objetivo: Modificar hora del primer evento")
        self.print_step(f"Herramienta esperada: update_calendar_event")
        print()
        
        # Enviar mensaje
        response = self.send_message(mensaje)
        
        # Esperar
        self.wait(2)
        
        # Verificar
        if "error" not in response:
            self.print_success("Test completado")
            self.print_info("Resultado esperado: Confirmacion de cambio 10am → 11am")
            self.save_result(True, {"response": response})
        else:
            self.print_error(f"Test fallido: {response.get('error')}")
            self.save_result(False, {"error": response.get('error')})
        
        print()
        self.print_info("💡 Revisa los logs del backend para ver:")
        self.print_info("   - Si selecciono 'update_calendar_event'")
        self.print_info("   - Si encontro el evento correcto")
        self.print_info("   - Si actualizo la hora correctamente")
        print()


if __name__ == "__main__":
    test = Test06ActualizarEvento()
    test.run()
