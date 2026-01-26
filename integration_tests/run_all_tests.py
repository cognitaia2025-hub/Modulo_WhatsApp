"""
EJECUTOR DE TESTS DE INTEGRACIÓN
Ejecuta todos los tests en orden secuencial
"""

import sys
import time
import importlib.util
from pathlib import Path
from colorama import Fore, Style, init
import io

# Configurar encoding UTF-8 para Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Inicializar colorama
init(autoreset=True)

# Importar todos los tests
sys.path.insert(0, str(Path(__file__).parent))

import importlib.util

# Cargar módulos dinámicamente (los archivos empiezan con números)
def load_test_module(file_name, class_name):
    """Carga un módulo de test dinámicamente"""
    spec = importlib.util.spec_from_file_location(
        f"test_{class_name}", 
        Path(__file__).parent / file_name
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, class_name)


def print_banner():
    """Imprime el banner inicial"""
    print("\n" + "=" * 80)
    print(Fore.CYAN + Style.BRIGHT + "🚀 SUITE DE TESTS DE INTEGRACIÓN - CALENDARIO AGENT")
    print("=" * 80 + "\n")


def print_summary(results):
    """Imprime el resumen final"""
    print("\n" + "=" * 80)
    print(Fore.CYAN + Style.BRIGHT + "📊 RESUMEN DE RESULTADOS")
    print("=" * 80 + "\n")
    
    total = len(results)
    passed = sum(1 for r in results if r['passed'])
    failed = total - passed
    
    for result in results:
        status = Fore.GREEN + "✅ PASS" if result['passed'] else Fore.RED + "❌ FAIL"
        print(f"{status} - Test #{result['number']:02d}: {result['name']}")
    
    print("\n" + "-" * 80)
    print(f"{Fore.CYAN}Total: {total} tests")
    print(f"{Fore.GREEN}Pasados: {passed}")
    print(f"{Fore.RED}Fallidos: {failed}")
    
    if failed == 0:
        print(f"\n{Fore.GREEN + Style.BRIGHT}🎉 ¡TODOS LOS TESTS PASARON!")
    else:
        print(f"\n{Fore.YELLOW + Style.BRIGHT}⚠️  Algunos tests fallaron. Revisa los logs.")
    
    print("=" * 80 + "\n")


def main():
    """Ejecuta todos los tests"""
    print_banner()
    
    # Cargar clases de tests dinámicamente
    Test01ListarInicial = load_test_module("01_test_listar_inicial.py", "Test01ListarInicial")
    Test02CrearEvento = load_test_module("02_test_crear_evento.py", "Test02CrearEvento")
    Test03VerificarCreacion = load_test_module("03_test_verificar_creacion.py", "Test03VerificarCreacion")
    Test04BuscarEvento = load_test_module("04_test_buscar_evento.py", "Test04BuscarEvento")
    Test05CrearSegundoEvento = load_test_module("05_test_crear_segundo_evento.py", "Test05CrearSegundoEvento")
    Test06ActualizarEvento = load_test_module("06_test_actualizar_evento.py", "Test06ActualizarEvento")
    Test07VerificarActualizacion = load_test_module("07_test_verificar_actualizacion.py", "Test07VerificarActualizacion")
    Test08BuscarRango = load_test_module("08_test_buscar_rango.py", "Test08BuscarRango")
    Test09EliminarEvento = load_test_module("09_test_eliminar_evento.py", "Test09EliminarEvento")
    Test10VerificarEliminacion = load_test_module("10_test_verificar_eliminacion.py", "Test10VerificarEliminacion")
    Test11SinHerramienta = load_test_module("11_test_sin_herramienta.py", "Test11SinHerramienta")
    Test12MultiplesHerramientas = load_test_module("12_test_multiples_herramientas.py", "Test12MultiplesHerramientas")
    
    # Lista de tests a ejecutar
    tests = [
        Test01ListarInicial(),
        Test02CrearEvento(),
        Test03VerificarCreacion(),
        Test04BuscarEvento(),
        Test05CrearSegundoEvento(),
        Test06ActualizarEvento(),
        Test07VerificarActualizacion(),
        Test08BuscarRango(),
        Test09EliminarEvento(),
        Test10VerificarEliminacion(),
        Test11SinHerramienta(),
        Test12MultiplesHerramientas(),
    ]
    
    results = []
    
    print(Fore.CYAN + f"📝 Se ejecutarán {len(tests)} tests en secuencia\n")
    print(Fore.YELLOW + "⚠️  IMPORTANTE: Asegúrate de que el backend esté corriendo en http://localhost:8000\n")
    
    input(Fore.GREEN + "Presiona ENTER para comenzar...")
    print()
    
    # Ejecutar cada test
    for i, test in enumerate(tests, 1):
        try:
            test.run()
            
            # Registrar resultado (simplificado - el test mismo guarda en JSON)
            results.append({
                'number': i,
                'name': test.test_name,
                'passed': True  # Por defecto True si no hay excepción
            })
            
            # Esperar entre tests
            if i < len(tests):
                print(Fore.CYAN + f"\n⏳ Esperando 3 segundos antes del siguiente test...\n")
                time.sleep(3)
        
        except KeyboardInterrupt:
            print(Fore.RED + "\n\n❌ Tests cancelados por el usuario")
            sys.exit(1)
        
        except Exception as e:
            print(Fore.RED + f"\n❌ Error en test {i}: {str(e)}\n")
            results.append({
                'number': i,
                'name': test.test_name,
                'passed': False
            })
    
    # Imprimir resumen
    print_summary(results)


if __name__ == "__main__":
    main()
