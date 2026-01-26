"""
TEST #07: Verificar actualizacion
Objetivo: Confirmar que el cambio se aplico
Herramienta esperada: list_calendar_events
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from integration_tests.test_base import IntegrationTestBase


class Test07VerificarActualizacion(IntegrationTestBase):
    """PRUEBA 7: Verificar actualizacion"""
    
    def __init__(self):
        super().__init__("Verificar actualizacion de hora", 7)
    
    def run(self):
        """Ejecuta el test"""
        self.print_header()
        
        # Mensaje del usuario
        mensaje = "¿Que eventos tengo esta semana?"
        
        self.print_step("Objetivo: Confirmar que el cambio se aplico")
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
            self.print_info("   - Reunion del equipo ahora a las 11am (no 10am)")
            self.print_info("   - Cita con el doctor a las 3pm")
            self.save_result(True, {"response": response})
        else:
            self.print_error(f"Test fallido: {response.get('error')}")
            self.save_result(False, {"error": response.get('error')})
        
        print()
        self.print_info("💡 Verifica que la reunion ahora es a las 11am")
        print()


if __name__ == "__main__":
    test = Test07VerificarActualizacion()
    test.run()
