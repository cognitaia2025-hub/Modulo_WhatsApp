"""
TEST #04: Buscar evento especifico
Objetivo: Encontrar el evento creado previamente
Herramienta esperada: search_calendar_events
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from integration_tests.test_base import IntegrationTestBase


class Test04BuscarEvento(IntegrationTestBase):
    """PRUEBA 4: Buscar evento especifico"""
    
    def __init__(self):
        super().__init__("Buscar evento por palabra clave", 4)
    
    def run(self):
        """Ejecuta el test"""
        self.print_header()
        
        # Mensaje del usuario
        mensaje = 'Busca eventos que tengan la palabra "reunion"'
        
        self.print_step("Objetivo: Encontrar el evento creado previamente")
        self.print_step(f"Herramienta esperada: search_calendar_events")
        print()
        
        # Enviar mensaje
        response = self.send_message(mensaje)
        
        # Esperar
        self.wait(2)
        
        # Verificar
        if "error" not in response:
            self.print_success("Test completado")
            self.print_info("Resultado esperado: Debe encontrar 'reunion con el equipo'")
            self.save_result(True, {"response": response})
        else:
            self.print_error(f"Test fallido: {response.get('error')}")
            self.save_result(False, {"error": response.get('error')})
        
        print()
        self.print_info("💡 Revisa los logs del backend para ver:")
        self.print_info("   - Si selecciono 'search_calendar_events'")
        self.print_info("   - Si encontro la reunion")
        print()


if __name__ == "__main__":
    test = Test04BuscarEvento()
    test.run()
