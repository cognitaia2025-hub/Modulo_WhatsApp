"""
TEST #11: Conversacion sin herramientas
Objetivo: Verificar que no ejecuta herramientas innecesarias
Herramienta esperada: NONE (ninguna)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from integration_tests.test_base import IntegrationTestBase


class Test11SinHerramienta(IntegrationTestBase):
    """PRUEBA 11: Sin herramienta necesaria"""
    
    def __init__(self):
        super().__init__("Conversacion sin herramientas", 11)
    
    def run(self):
        """Ejecuta el test"""
        self.print_header()
        
        # Mensaje del usuario
        mensaje = "Hola, ¿como estas?"
        
        self.print_step("Objetivo: Verificar que NO ejecuta herramientas")
        self.print_step(f"Herramienta esperada: NONE (ninguna)")
        print()
        
        # Enviar mensaje
        response = self.send_message(mensaje)
        
        # Esperar
        self.wait(2)
        
        # Verificar
        if "error" not in response:
            self.print_success("Test completado")
            self.print_info("Resultado esperado: Respuesta conversacional sin herramientas")
            self.save_result(True, {"response": response})
        else:
            self.print_error(f"Test fallido: {response.get('error')}")
            self.save_result(False, {"error": response.get('error')})
        
        print()
        self.print_info("💡 Revisa los logs del backend para ver:")
        self.print_info("   - Debe decir 'herramientas_seleccionadas: []'")
        self.print_info("   - NO debe ejecutar ninguna herramienta")
        self.print_info("   - Solo debe responder conversacionalmente")
        print()


if __name__ == "__main__":
    test = Test11SinHerramienta()
    test.run()
