"""
TEST #01: Listar eventos iniciales
Objetivo: Ver el estado inicial del calendario
Herramienta esperada: list_calendar_events
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from integration_tests.test_base import IntegrationTestBase


class Test01ListarInicial(IntegrationTestBase):
    """PRUEBA 1: Listar eventos (verificar calendario vacio/actual)"""
    
    def __init__(self):
        super().__init__("Listar eventos iniciales", 1)
    
    def run(self):
        """Ejecuta el test"""
        self.print_header()
        
        # Mensaje del usuario
        mensaje = "¿Que eventos tengo hoy?"
        
        self.print_step("Objetivo: Ver estado inicial del calendario")
        self.print_step(f"Herramienta esperada: list_calendar_events")
        print()
        
        # Enviar mensaje
        response = self.send_message(mensaje)
        
        # Esperar
        self.wait(2)
        
        # Verificar
        if "error" not in response:
            self.print_success("Test completado")
            self.print_info("Resultado esperado: Lista de eventos de hoy")
            self.save_result(True, {"response": response})
        else:
            self.print_error(f"Test fallido: {response.get('error')}")
            self.save_result(False, {"error": response.get('error')})
        
        print()
        self.print_info("💡 Revisa los logs del backend para ver:")
        self.print_info("   - Si selecciono 'list_calendar_events'")
        self.print_info("   - Los eventos encontrados")
        print()


if __name__ == "__main__":
    test = Test01ListarInicial()
    test.run()
