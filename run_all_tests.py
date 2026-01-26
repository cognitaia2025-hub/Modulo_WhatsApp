"""
🧪 Test Suite Runner - AI Calendar Agent with Infinite Memory
==============================================================

Ejecuta todos los tests del proyecto de manera organizada y genera un reporte completo.

Autor: Test Automation
Fecha: 24/01/2026
"""

import os
import sys
import subprocess
import time
from datetime import datetime
from typing import List, Tuple, Dict


class TestRunner:
    def __init__(self):
        self.results: List[Dict] = []
        self.start_time = None
        self.end_time = None
        
    def print_header(self):
        """Imprime encabezado del test suite"""
        print("=" * 100)
        print("🧪 TEST SUITE RUNNER - AI CALENDAR AGENT WITH INFINITE MEMORY".center(100))
        print("=" * 100)
        print(f"\n⏱️  Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📂 Working dir: {os.getcwd()}\n")
        
    def print_separator(self, title: str = ""):
        """Imprime separador visual"""
        print("\n" + "-" * 100)
        if title:
            print(f"  {title}")
            print("-" * 100)
        print()
    
    def run_test_file(self, test_file: str, description: str, timeout: int = 120) -> Dict:
        """
        Ejecuta un archivo de test y captura el resultado
        
        Args:
            test_file: Ruta al archivo de test
            description: Descripción del test
            timeout: Timeout en segundos (default 120s)
            
        Returns:
            Dict con resultado del test
        """
        self.print_separator(f"🧪 {description}")
        print(f"📄 Archivo: {test_file}")
        print(f"⏱️  Timeout: {timeout}s")
        
        if not os.path.exists(test_file):
            print(f"❌ Archivo no encontrado: {test_file}")
            return {
                'file': test_file,
                'description': description,
                'status': 'NOT_FOUND',
                'duration': 0,
                'exit_code': -1,
                'output': 'Archivo no encontrado'
            }
        
        start = time.time()
        try:
            # Ejecutar test con Python (usando UTF-8 para Windows)
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            
            result = subprocess.run(
                [sys.executable, test_file],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=os.getcwd(),
                env=env,
                encoding='utf-8',
                errors='replace'
            )
            
            duration = time.time() - start
            
            # Determinar status
            if result.returncode == 0:
                status = 'PASSED'
                icon = '✅'
            else:
                status = 'FAILED'
                icon = '❌'
            
            print(f"\n{icon} Status: {status}")
            print(f"⏱️  Duración: {duration:.2f}s")
            print(f"📤 Exit Code: {result.returncode}")
            
            # Mostrar últimas líneas del output
            if result.stdout:
                lines = result.stdout.strip().split('\n')
                preview_lines = lines[-10:] if len(lines) > 10 else lines
                print("\n📋 Output (últimas líneas):")
                for line in preview_lines:
                    print(f"   {line}")
            
            if result.stderr:
                print("\n⚠️  Stderr:")
                stderr_lines = result.stderr.strip().split('\n')[:5]
                for line in stderr_lines:
                    print(f"   {line}")
            
            return {
                'file': test_file,
                'description': description,
                'status': status,
                'duration': duration,
                'exit_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start
            print(f"\n⏱️  TIMEOUT después de {timeout}s")
            return {
                'file': test_file,
                'description': description,
                'status': 'TIMEOUT',
                'duration': duration,
                'exit_code': -1,
                'output': f'Test excedió timeout de {timeout}s'
            }
            
        except Exception as e:
            duration = time.time() - start
            print(f"\n❌ Error ejecutando test: {e}")
            return {
                'file': test_file,
                'description': description,
                'status': 'ERROR',
                'duration': duration,
                'exit_code': -1,
                'output': str(e)
            }
    
    def run_all_tests(self):
        """Ejecuta todos los tests del proyecto"""
        self.start_time = time.time()
        
        # Definir tests a ejecutar en orden de prioridad
        tests = [
            # Tests de configuración básica
            ('test_config_check.py', '⚙️  Configuración y Variables de Entorno', 30),
            
            # Tests de componentes individuales
            ('test_memory.py', '🧠 Sistema de Memoria (Embeddings)', 60),
            ('test_postgresql_integration.py', '🐘 Integración PostgreSQL', 45),
            
            # Tests por nodo del grafo
            ('test_filtrado.py', '🔍 Nodo 2: Filtrado (Detección Cambio Tema)', 60),
            ('test_nodo3_episodico.py', '💾 Nodo 3: Recuperación Episódica', 60),
            ('test_nodo4_seleccion.py', '🛠️  Nodo 4: Selección de Herramientas', 60),
            ('test_nodo5_ejecucion.py', '⚙️  Nodo 5: Ejecución de Herramientas', 60),
            ('test_nodo6_proteccion.py', '🛡️  Nodo 6: Protección (Validaciones)', 45),
            ('test_nodo6_resumen.py', '📝 Nodo 6: Generación de Resúmenes', 60),
            
            # Tests de escenarios especiales
            ('test_expiracion_sesion.py', '⏰ Expiración de Sesión (24h)', 45),
            ('test_timeout_fix.py', '⏱️  Manejo de Timeouts', 90),
            ('test_timeout_simple.py', '⏱️  Timeouts Simplificados', 45),
            ('test_resilience.py', '🔄 Resiliencia y Recuperación', 90),
            
            # Test quick (opcional)
            ('test_quick.py', '⚡ Tests Rápidos', 30),
            
            # Test end-to-end (el más importante)
            ('test_end_to_end.py', '🎯 END-TO-END: Flujo Completo (3 Escenarios)', 180),
        ]
        
        print("\n📋 Tests a ejecutar:")
        for i, (file, desc, timeout) in enumerate(tests, 1):
            exists = "✅" if os.path.exists(file) else "❌"
            print(f"   {i:2d}. {exists} {desc}")
        
        print(f"\n🚀 Iniciando ejecución de {len(tests)} tests...\n")
        
        # Ejecutar cada test
        for test_file, description, timeout in tests:
            result = self.run_test_file(test_file, description, timeout)
            self.results.append(result)
        
        self.end_time = time.time()
    
    def print_summary(self):
        """Imprime resumen final de todos los tests"""
        self.print_separator("📊 RESUMEN FINAL DE TESTS")
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r['status'] == 'PASSED')
        failed = sum(1 for r in self.results if r['status'] == 'FAILED')
        timeout = sum(1 for r in self.results if r['status'] == 'TIMEOUT')
        error = sum(1 for r in self.results if r['status'] == 'ERROR')
        not_found = sum(1 for r in self.results if r['status'] == 'NOT_FOUND')
        
        total_duration = self.end_time - self.start_time
        
        print(f"📈 Estadísticas Generales:")
        print(f"   Total de tests:     {total}")
        print(f"   ✅ Pasados:         {passed} ({passed/total*100:.1f}%)")
        print(f"   ❌ Fallados:        {failed} ({failed/total*100:.1f}%)")
        print(f"   ⏱️  Timeout:         {timeout} ({timeout/total*100:.1f}%)")
        print(f"   🔥 Errores:         {error} ({error/total*100:.1f}%)")
        print(f"   📂 No encontrados:  {not_found} ({not_found/total*100:.1f}%)")
        print(f"   ⏱️  Duración total:   {total_duration:.2f}s ({total_duration/60:.2f}min)")
        
        print("\n📋 Resultados Detallados:\n")
        
        # Agrupar por status
        for status_filter, icon, title in [
            ('PASSED', '✅', 'Tests Exitosos'),
            ('FAILED', '❌', 'Tests Fallados'),
            ('TIMEOUT', '⏱️', 'Tests con Timeout'),
            ('ERROR', '🔥', 'Tests con Error'),
            ('NOT_FOUND', '📂', 'Tests No Encontrados')
        ]:
            filtered = [r for r in self.results if r['status'] == status_filter]
            if filtered:
                print(f"{icon} {title}:")
                for r in filtered:
                    print(f"   - {r['description']}")
                    print(f"     Archivo: {r['file']}")
                    print(f"     Duración: {r['duration']:.2f}s")
                    if r['status'] in ['FAILED', 'ERROR']:
                        print(f"     Exit Code: {r['exit_code']}")
                print()
        
        # Resultado final
        print("=" * 100)
        if failed == 0 and error == 0 and timeout == 0 and not_found == 0:
            print("🎉 ¡TODOS LOS TESTS PASARON!".center(100))
            print("El sistema está completamente funcional y listo para producción.".center(100))
        elif passed > 0:
            print(f"⚠️  {passed}/{total} TESTS PASARON".center(100))
            print(f"Hay {failed + error + timeout} test(s) que requieren atención.".center(100))
        else:
            print("❌ TODOS LOS TESTS FALLARON".center(100))
            print("Revisa la configuración del entorno y las dependencias.".center(100))
        print("=" * 100)
        
        print(f"\n⏱️  Fin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Retornar exit code
        if failed == 0 and error == 0 and timeout == 0:
            return 0
        else:
            return 1
    
    def save_report(self, filename: str = 'test_report.txt'):
        """Guarda reporte detallado en archivo"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("=" * 100 + "\n")
                f.write("TEST REPORT - AI CALENDAR AGENT\n")
                f.write("=" * 100 + "\n\n")
                f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Duración total: {self.end_time - self.start_time:.2f}s\n\n")
                
                for r in self.results:
                    f.write("-" * 100 + "\n")
                    f.write(f"Test: {r['description']}\n")
                    f.write(f"Archivo: {r['file']}\n")
                    f.write(f"Status: {r['status']}\n")
                    f.write(f"Duración: {r['duration']:.2f}s\n")
                    f.write(f"Exit Code: {r['exit_code']}\n")
                    
                    if 'stdout' in r and r['stdout']:
                        f.write("\nOutput:\n")
                        f.write(r['stdout'])
                        f.write("\n")
                    
                    if 'stderr' in r and r['stderr']:
                        f.write("\nStderr:\n")
                        f.write(r['stderr'])
                        f.write("\n")
                    
                    f.write("\n")
                
            print(f"\n💾 Reporte guardado en: {filename}")
            
        except Exception as e:
            print(f"\n⚠️  Error guardando reporte: {e}")


def main():
    """Función principal"""
    runner = TestRunner()
    
    # Imprimir encabezado
    runner.print_header()
    
    # Verificar entorno
    print("🔍 Verificando entorno...")
    print(f"   Python: {sys.version.split()[0]}")
    print(f"   OS: {os.name}")
    print(f"   .env: {'✅' if os.path.exists('.env') else '⚠️ No encontrado'}")
    
    # Ejecutar todos los tests
    runner.run_all_tests()
    
    # Mostrar resumen
    exit_code = runner.print_summary()
    
    # Guardar reporte
    runner.save_report('test_report.txt')
    
    return exit_code


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
