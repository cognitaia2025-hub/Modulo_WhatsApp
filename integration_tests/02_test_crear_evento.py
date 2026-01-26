"""
TEST #02: Crear evento simple
Objetivo: Crear primer evento
Herramienta esperada: create_calendar_event
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from integration_tests.test_base import IntegrationTestBase


class Test02CrearEvento(IntegrationTestBase):
    """PRUEBA 2: Crear evento simple"""
    
    def __init__(self):
        super().__init__("Crear evento simple - Reunion equipo", 2)
    
    def run(self):
        """Ejecuta el test"""
        self.print_header()
        
        # Mensaje del usuario
        mensaje = "Agenda una reunion con el equipo manana a las 10am"
        
        self.print_step("Objetivo: Crear primer evento")
        self.print_step(f"Herramienta esperada: create_calendar_event")
        print()
        
        # Enviar mensaje
        response = self.send_message(mensaje)
        
        # Esperar
        self.wait(2)
        
        # Verificar
        if "error" not in response:
            self.print_success("Test completado")
            self.print_info("Resultado esperado: Confirmacion de evento creado")
            self.print_info("   Titulo: 'reunion con el equipo'")
            self.print_info("   Fecha: Manana")
            self.print_info("   Hora: 10:00 AM")
            self.save_result(True, {"response": response})
        else:
            self.print_error(f"Test fallido: {response.get('error')}")
            self.save_result(False, {"error": response.get('error')})
        
        print()
        self.print_info("💡 Revisa los logs del backend para ver:")
        self.print_info("   - Si selecciono 'create_calendar_event'")
        self.print_info("   - Si extrajo correctamente los parametros")
        self.print_info("   - Si el evento se creo en Google Calendar")
        print()


if __name__ == "__main__":
    test = Test02CrearEvento()
    test.run()
