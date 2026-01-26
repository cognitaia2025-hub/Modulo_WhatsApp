"""
TEST #12: Multiples herramientas
Objetivo: Ver si puede ejecutar multiples herramientas en secuencia
Herramientas esperadas: create_calendar_event, list_calendar_events
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from integration_tests.test_base import IntegrationTestBase


class Test12MultiplesHerramientas(IntegrationTestBase):
    """PRUEBA 12: Multiples herramientas (si el sistema lo soporta)"""
    
    def __init__(self):
        super().__init__("Multiples herramientas en una peticion", 12)
    
    def run(self):
        """Ejecuta el test"""
        self.print_header()
        
        # Mensaje del usuario
        mensaje = 'Crea un evento para manana a las 2pm llamado "Gym" y luego muestrame mi agenda de manana'
        
        self.print_step("Objetivo: Ejecutar multiples herramientas")
        self.print_step(f"Herramientas esperadas:")
        self.print_step(f"   1. create_calendar_event")
        self.print_step(f"   2. list_calendar_events")
        print()
        
        # Enviar mensaje
        response = self.send_message(mensaje)
        
        # Esperar mas tiempo (multiples operaciones)
        self.wait(3)
        
        # Verificar
        if "error" not in response:
            self.print_success("Test completado")
            self.print_info("Resultado esperado:")
            self.print_info("   1. Crear evento 'Gym' a las 2pm")
            self.print_info("   2. Mostrar agenda incluyendo el nuevo evento")
            self.save_result(True, {"response": response})
        else:
            self.print_error(f"Test fallido: {response.get('error')}")
            self.save_result(False, {"error": response.get('error')})
        
        print()
        self.print_info("💡 Este test verifica si el agente puede:")
        self.print_info("   - Detectar multiples acciones en un mensaje")
        self.print_info("   - Ejecutarlas en el orden correcto")
        self.print_info("   - Dar una respuesta coherente combinando ambos resultados")
        print()


if __name__ == "__main__":
    test = Test12MultiplesHerramientas()
    test.run()
