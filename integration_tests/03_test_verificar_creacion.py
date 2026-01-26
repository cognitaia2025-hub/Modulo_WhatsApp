"""
TEST #03: Verificar creacion de evento
Objetivo: Confirmar que el evento se creo correctamente
Herramienta esperada: list_calendar_events
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from integration_tests.test_base import IntegrationTestBase


class Test03VerificarCreacion(IntegrationTestBase):
    """PRUEBA 3: Listar eventos (verificar creacion)"""
    
    def __init__(self):
        super().__init__("Verificar creacion del evento", 3)
    
    def run(self):
        """Ejecuta el test"""
        self.print_header()
        
        # Mensaje del usuario
        mensaje = "Muestrame mi agenda de manana"
        
        self.print_step("Objetivo: Confirmar que el evento se creo")
        self.print_step(f"Herramienta esperada: list_calendar_events")
        print()
        
        # Enviar mensaje
        response = self.send_message(mensaje)
        
        # Esperar
        self.wait(2)
        
        # Verificar
        if "error" not in response:
            self.print_success("Test completado")
            self.print_info("Resultado esperado: Debe aparecer la reunion del equipo a las 10am")
            self.save_result(True, {"response": response})
        else:
            self.print_error(f"Test fallido: {response.get('error')}")
            self.save_result(False, {"error": response.get('error')})
        
        print()
        self.print_info("💡 Verifica en la respuesta:")
        self.print_info("   - ¿Aparece 'reunion con el equipo'?")
        self.print_info("   - ¿La hora es 10:00 AM?")
        self.print_info("   - ¿La fecha es manana?")
        print()


if __name__ == "__main__":
    test = Test03VerificarCreacion()
    test.run()
