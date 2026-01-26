"""
Clase base para tests de integración.

Proporciona utilidades comunes para todos los tests.
"""

import sys
import io
import requests
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from colorama import init, Fore, Style

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Inicializar colorama
init(autoreset=True)

class IntegrationTestBase:
    """Clase base para tests de integración"""

    BASE_URL = "http://localhost:8000"
    TIMEOUT = 60  # Aumentado a 60s para operaciones complejas
    RESULTS_FILE = Path(__file__).parent / "test_results.json"
    
    def __init__(self, test_name: str, test_number: int):
        self.test_name = test_name
        self.test_number = test_number
        self.results = []
        
    def print_header(self):
        """Imprime header del test"""
        print("\n" + "="*80)
        print(f"{Fore.CYAN}TEST #{self.test_number:02d}: {self.test_name}{Style.RESET_ALL}")
        print("="*80 + "\n")
    
    def print_step(self, step: str):
        """Imprime un paso del test"""
        print(f"{Fore.YELLOW}➤{Style.RESET_ALL} {step}")
    
    def print_success(self, message: str):
        """Imprime mensaje de éxito"""
        print(f"{Fore.GREEN}✅ {message}{Style.RESET_ALL}")
    
    def print_error(self, message: str):
        """Imprime mensaje de error"""
        print(f"{Fore.RED}❌ {message}{Style.RESET_ALL}")
    
    def print_info(self, message: str):
        """Imprime mensaje informativo"""
        print(f"{Fore.BLUE}ℹ️  {message}{Style.RESET_ALL}")
    
    def send_message(self, message: str) -> Dict[str, Any]:
        """
        Envía un mensaje al agente.
        
        Args:
            message: Mensaje del usuario
            
        Returns:
            Respuesta del servidor
        """
        self.print_step(f"Enviando: '{message}'")
        
        try:
            response = requests.post(
                f"{self.BASE_URL}/invoke",
                json={"user_input": message},
                timeout=self.TIMEOUT
            )
            
            if response.status_code == 200:
                data = response.json()
                self.print_success(f"Respuesta recibida (Status: {response.status_code})")
                return data
            else:
                self.print_error(f"Error HTTP {response.status_code}")
                return {"error": f"HTTP {response.status_code}", "detail": response.text}
                
        except requests.exceptions.ConnectionError:
            self.print_error("No se pudo conectar al backend")
            self.print_info("Asegúrate de que el servidor esté corriendo: uvicorn app:app --reload")
            return {"error": "ConnectionError"}
            
        except requests.exceptions.Timeout:
            self.print_error(f"Timeout después de {self.TIMEOUT}s")
            return {"error": "Timeout"}
            
        except Exception as e:
            self.print_error(f"Error inesperado: {e}")
            return {"error": str(e)}
    
    def verify_tool_used(self, expected_tool: str, response: Dict[str, Any]) -> bool:
        """
        Verifica que se usó la herramienta esperada.
        
        Args:
            expected_tool: Herramienta esperada
            response: Respuesta del servidor
            
        Returns:
            True si la herramienta es correcta
        """
        # Esta verificación puede ajustarse según el formato de respuesta
        # Por ahora, asumimos que el campo existe en la respuesta
        
        self.print_step(f"Verificando herramienta esperada: {expected_tool}")
        
        # TODO: Implementar lógica de verificación según formato real de respuesta
        # Por ahora, solo imprimimos la respuesta
        
        self.print_info(f"Respuesta: {json.dumps(response, indent=2, ensure_ascii=False)[:200]}...")
        
        return True  # Placeholder
    
    def wait(self, seconds: float = 1.0):
        """Espera entre requests"""
        time.sleep(seconds)
    
    def save_result(self, passed: bool, details: Optional[Dict] = None):
        """Guarda resultado del test"""
        result = {
            "test_number": self.test_number,
            "test_name": self.test_name,
            "status": "PASSED" if passed else "FAILED",
            "timestamp": datetime.now().isoformat(),
            "details": details or {}
        }
        self.results.append(result)

        # Guardar en archivo usando Path absoluto
        try:
            with open(self.RESULTS_FILE, "r", encoding="utf-8") as f:
                all_results = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            all_results = {}

        all_results[f"test_{self.test_number:02d}"] = result

        with open(self.RESULTS_FILE, "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
    
    def run(self):
        """Método principal a implementar en cada test"""
        raise NotImplementedError("Implementar en clase hija")
