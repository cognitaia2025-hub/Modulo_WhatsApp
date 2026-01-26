"""
Runner Maestro de Tests - Ejecuta Toda la Suite de Integración

Este script ejecuta todos los tests de integración en orden secuencial
y genera un reporte completo de resultados.

Uso:
    python run_all_integration_tests.py
    python run_all_integration_tests.py --fast  # Solo tests críticos
    python run_all_integration_tests.py --verbose  # Con logs detallados
"""

import sys
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

# Asegurar que estamos en el directorio correcto
os.chdir('/workspaces/Modulo_WhatsApp')
sys.path.insert(0, '/workspaces/Modulo_WhatsApp')

# Lista de tests en orden de ejecución
TESTS_SUITE = [
    # Tests básicos (CRUD)
    {
        "id": "01",
        "name": "Listar Inicial",
        "file": "integration_tests/01_test_listar_inicial.py",
        "critical": True,
        "description": "Verificar que el sistema puede listar eventos"
    },
    {
        "id": "02",
        "name": "Crear Evento",
        "file": "integration_tests/02_test_crear_evento.py",
        "critical": True,
        "description": "Verificar creación de eventos"
    },
    {
        "id": "03",
        "name": "Verificar Creación",
        "file": "integration_tests/03_test_verificar_creacion.py",
        "critical": True,
        "description": "Confirmar que el evento fue creado"
    },
    {
        "id": "04",
        "name": "Buscar Evento",
        "file": "integration_tests/04_test_buscar_evento.py",
        "critical": False,
        "description": "Búsqueda de evento específico"
    },
    {
        "id": "05",
        "name": "Crear Segundo Evento",
        "file": "integration_tests/05_test_crear_segundo_evento.py",
        "critical": False,
        "description": "Manejo de múltiples eventos"
    },
    # Tests de actualización (NUEVOS)
    {
        "id": "06",
        "name": "Actualizar Evento",
        "file": "integration_tests/06_test_actualizar_evento.py",
        "critical": True,
        "description": "Verificar funcionalidad de update_calendar_event"
    },
    {
        "id": "07",
        "name": "Verificar Actualización",
        "file": "integration_tests/07_test_verificar_actualizacion.py",
        "critical": True,
        "description": "Confirmar que las actualizaciones persisten"
    },
    {
        "id": "08",
        "name": "Buscar Rango",
        "file": "integration_tests/08_test_buscar_rango.py",
        "critical": False,
        "description": "Búsqueda por rango de fechas"
    },
    # Tests de eliminación
    {
        "id": "09",
        "name": "Eliminar Evento",
        "file": "integration_tests/09_test_eliminar_evento.py",
        "critical": True,
        "description": "Verificar funcionalidad de delete_calendar_event"
    },
    {
        "id": "10",
        "name": "Verificar Eliminación",
        "file": "integration_tests/10_test_verificar_eliminacion.py",
        "critical": True,
        "description": "Confirmar que el evento fue eliminado"
    },
    # Tests avanzados
    {
        "id": "11",
        "name": "Sin Herramienta",
        "file": "integration_tests/11_test_sin_herramienta.py",
        "critical": False,
        "description": "Respuestas conversacionales sin herramientas"
    },
    {
        "id": "12",
        "name": "Múltiples Herramientas",
        "file": "integration_tests/12_test_multiples_herramientas.py",
        "critical": False,
        "description": "Ejecución de múltiples herramientas en una request"
    },
    # Tests críticos nuevos
    {
        "id": "13",
        "name": "Eliminar con Contexto",
        "file": "integration_tests/13_test_eliminar_con_contexto.py",
        "critical": True,
        "description": "Eliminación usando contexto del último listado"
    },
    {
        "id": "14",
        "name": "Memoria Persistente",
        "file": "integration_tests/14_test_memoria_persistente.py",
        "critical": True,
        "description": "Verificar memoria episódica entre sesiones"
    }
]


class TestRunner:
    def __init__(self, fast_mode=False, verbose=False):
        self.fast_mode = fast_mode
        self.verbose = verbose
        self.results = []
        self.start_time = None
        self.end_time = None
    
    def print_header(self):
        """Imprime el encabezado de la suite"""
        print("\n" + "="*100)
        print(" "*35 + "🧪 SUITE DE TESTS DE INTEGRACIÓN 🧪")
        print("="*100)
        print(f"\n📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🏃 Modo: {'RÁPIDO (solo críticos)' if self.fast_mode else 'COMPLETO'}")
        print(f"📊 Tests a ejecutar: {len([t for t in TESTS_SUITE if not self.fast_mode or t['critical']])}")
        print("\n" + "="*100 + "\n")
    
    def run_test(self, test_info):
        """Ejecuta un test individual"""
        test_id = test_info['id']
        test_name = test_info['name']
        test_file = test_info['file']
        
        # Si estamos en modo fast y no es crítico, skip
        if self.fast_mode and not test_info['critical']:
            print(f"⏭️  Skipping {test_id}: {test_name} (no crítico)")
            return {
                'id': test_id,
                'name': test_name,
                'status': 'SKIPPED',
                'duration': 0,
                'error': None
            }
        
        print(f"\n{'='*100}")
        print(f"▶️  TEST {test_id}: {test_name}")
        print(f"📝 {test_info['description']}")
        print(f"{'='*100}\n")
        
        start = time.time()
        
        try:
            # Ejecutar el test
            result = subprocess.run(
                [sys.executable, test_file],
                capture_output=not self.verbose,
                text=True,
                timeout=180  # 3 minutos máximo por test
            )
            
            duration = time.time() - start
            
            if result.returncode == 0:
                print(f"\n✅ TEST {test_id} PASSED ({duration:.2f}s)")
                return {
                    'id': test_id,
                    'name': test_name,
                    'status': 'PASS',
                    'duration': duration,
                    'error': None
                }
            else:
                print(f"\n❌ TEST {test_id} FAILED ({duration:.2f}s)")
                error_msg = result.stderr if result.stderr else "Unknown error"
                if self.verbose:
                    print(f"Error: {error_msg}")
                return {
                    'id': test_id,
                    'name': test_name,
                    'status': 'FAIL',
                    'duration': duration,
                    'error': error_msg
                }
        
        except subprocess.TimeoutExpired:
            duration = time.time() - start
            print(f"\n⏰ TEST {test_id} TIMEOUT ({duration:.2f}s)")
            return {
                'id': test_id,
                'name': test_name,
                'status': 'TIMEOUT',
                'duration': duration,
                'error': 'Test exceeded 3 minute timeout'
            }
        
        except Exception as e:
            duration = time.time() - start
            print(f"\n💥 TEST {test_id} ERROR ({duration:.2f}s)")
            print(f"Error: {str(e)}")
            return {
                'id': test_id,
                'name': test_name,
                'status': 'ERROR',
                'duration': duration,
                'error': str(e)
            }
    
    def run_all(self):
        """Ejecuta todos los tests"""
        self.print_header()
        self.start_time = time.time()
        
        for test_info in TESTS_SUITE:
            result = self.run_test(test_info)
            self.results.append(result)
            
            # Pausa entre tests
            if result['status'] not in ['SKIPPED']:
                time.sleep(2)
        
        self.end_time = time.time()
        self.print_summary()
    
    def print_summary(self):
        """Imprime el resumen de resultados"""
        print("\n\n" + "="*100)
        print(" "*40 + "📊 RESUMEN DE RESULTADOS")
        print("="*100 + "\n")
        
        # Tabla de resultados
        print(f"{'ID':<6} {'Status':<12} {'Duration':<12} {'Test Name':<40} {'Critical'}")
        print("-"*100)
        
        for result in self.results:
            # Buscar info del test
            test_info = next(t for t in TESTS_SUITE if t['id'] == result['id'])
            
            status_icon = {
                'PASS': '✅',
                'FAIL': '❌',
                'ERROR': '💥',
                'TIMEOUT': '⏰',
                'SKIPPED': '⏭️'
            }.get(result['status'], '❓')
            
            critical_icon = '🔴' if test_info['critical'] else '⚪'
            
            duration_str = f"{result['duration']:.2f}s" if result['duration'] > 0 else "-"
            
            print(f"{result['id']:<6} {status_icon} {result['status']:<10} "
                  f"{duration_str:<12} {result['name']:<40} {critical_icon}")
        
        print("-"*100)
        
        # Estadísticas
        total = len([r for r in self.results if r['status'] != 'SKIPPED'])
        passed = len([r for r in self.results if r['status'] == 'PASS'])
        failed = len([r for r in self.results if r['status'] == 'FAIL'])
        errors = len([r for r in self.results if r['status'] == 'ERROR'])
        timeouts = len([r for r in self.results if r['status'] == 'TIMEOUT'])
        skipped = len([r for r in self.results if r['status'] == 'SKIPPED'])
        
        total_duration = self.end_time - self.start_time
        
        print(f"\n📈 ESTADÍSTICAS:")
        print(f"   Total ejecutados: {total}")
        print(f"   ✅ Pasados: {passed} ({passed/total*100:.1f}%)")
        print(f"   ❌ Fallidos: {failed}")
        print(f"   💥 Errores: {errors}")
        print(f"   ⏰ Timeouts: {timeouts}")
        print(f"   ⏭️  Saltados: {skipped}")
        print(f"\n⏱️  Tiempo total: {total_duration:.2f}s ({total_duration/60:.1f} minutos)")
        
        # Tests críticos
        critical_results = [r for r in self.results 
                           if next(t for t in TESTS_SUITE if t['id'] == r['id'])['critical']]
        critical_passed = len([r for r in critical_results if r['status'] == 'PASS'])
        critical_total = len([r for r in critical_results if r['status'] != 'SKIPPED'])
        
        print(f"\n🔴 TESTS CRÍTICOS: {critical_passed}/{critical_total} pasados")
        
        # Veredicto final
        print("\n" + "="*100)
        if passed == total and critical_passed == critical_total:
            print("🎉 ¡ÉXITO TOTAL! Todos los tests pasaron")
            print("   El sistema está listo para producción")
        elif critical_passed == critical_total:
            print("✅ Tests críticos pasados")
            print("   Sistema funcional, algunos tests no críticos fallaron")
        elif critical_passed >= critical_total * 0.8:
            print("⚠️  ATENCIÓN: Algunos tests críticos fallaron")
            print("   Revisar problemas antes de ir a producción")
        else:
            print("🚨 FALLO CRÍTICO: Múltiples tests críticos fallaron")
            print("   Sistema NO listo para producción")
        print("="*100 + "\n")
        
        # Guardar reporte
        self.save_report()
    
    def save_report(self):
        """Guarda el reporte en un archivo"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = f"integration_tests/reports/test_report_{timestamp}.json"
        
        # Crear directorio si no existe
        os.makedirs('integration_tests/reports', exist_ok=True)
        
        import json
        report = {
            'timestamp': timestamp,
            'mode': 'fast' if self.fast_mode else 'complete',
            'duration': self.end_time - self.start_time,
            'results': self.results,
            'summary': {
                'total': len([r for r in self.results if r['status'] != 'SKIPPED']),
                'passed': len([r for r in self.results if r['status'] == 'PASS']),
                'failed': len([r for r in self.results if r['status'] == 'FAIL']),
                'errors': len([r for r in self.results if r['status'] == 'ERROR']),
                'timeouts': len([r for r in self.results if r['status'] == 'TIMEOUT'])
            }
        }
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"📄 Reporte guardado en: {report_file}\n")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Ejecuta la suite de tests de integración')
    parser.add_argument('--fast', action='store_true', help='Solo ejecutar tests críticos')
    parser.add_argument('--verbose', action='store_true', help='Mostrar logs detallados')
    
    args = parser.parse_args()
    
    runner = TestRunner(fast_mode=args.fast, verbose=args.verbose)
    runner.run_all()


if __name__ == "__main__":
    main()
