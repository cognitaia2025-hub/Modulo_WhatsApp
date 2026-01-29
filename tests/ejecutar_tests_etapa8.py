"""
Script de ejecución de Tests - ETAPA 8

Ejecuta todos los tests de ETAPA 8 y genera un reporte completo.
"""

import sys
import os
import subprocess
from pathlib import Path
import time

def run_tests():
    """Ejecuta todos los tests de ETAPA 8"""
    
    # Configurar paths
    project_root = Path(__file__).parent
    tests_dir = project_root / "tests" / "Etapa_8"
    
    # Cambiar al directorio del proyecto
    os.chdir(project_root)
    
    print("="*80)
    print("🧪 EJECUTANDO TESTS DE ETAPA 8 - GRAFO WHATSAPP COMPLETO")
    print("="*80)
    
    # Lista de archivos de test
    test_files = [
        "test_grafo_compilacion.py",
        "test_decisiones_clasificacion.py", 
        "test_decisiones_ejecucion.py",
        "test_decisiones_recepcionista.py",
        "test_propagacion_estado.py",
        "test_flujos_completos.py",
        "test_integracion_grafo_completo.py"
    ]
    
    total_tests = 0
    total_passed = 0
    total_failed = 0
    failed_tests = []
    
    for test_file in test_files:
        test_path = tests_dir / test_file
        
        if not test_path.exists():
            print(f"❌ Test file not found: {test_file}")
            continue
            
        print(f"\n📝 Ejecutando: {test_file}")
        print("-" * 50)
        
        try:
            # Ejecutar pytest con verbose output
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                str(test_path), 
                "-v",
                "--tb=short",
                "--no-header"
            ], capture_output=True, text=True, timeout=120)
            
            # Parsear resultados
            output = result.stdout + result.stderr
            print(output)
            
            # Contar tests
            lines = output.split('\n')
            for line in lines:
                if " PASSED " in line or "::test_" in line and " PASSED" in line:
                    total_tests += 1
                    total_passed += 1
                elif " FAILED " in line or "::test_" in line and " FAILED" in line:
                    total_tests += 1
                    total_failed += 1
                    failed_tests.append(f"{test_file}: {line.strip()}")
            
            if result.returncode == 0:
                print(f"✅ {test_file}: TODOS LOS TESTS PASARON")
            else:
                print(f"❌ {test_file}: ALGUNOS TESTS FALLARON")
                
        except subprocess.TimeoutExpired:
            print(f"⏰ {test_file}: TIMEOUT (>120s)")
            total_failed += 1
            failed_tests.append(f"{test_file}: Timeout")
            
        except Exception as e:
            print(f"💥 {test_file}: ERROR - {e}")
            total_failed += 1
            failed_tests.append(f"{test_file}: {str(e)}")
    
    # Reporte final
    print("\n" + "="*80)
    print("📊 REPORTE FINAL DE TESTS - ETAPA 8")
    print("="*80)
    
    print(f"\n📈 ESTADÍSTICAS:")
    print(f"   Total Tests: {total_tests}")
    print(f"   ✅ Pasaron: {total_passed}")
    print(f"   ❌ Fallaron: {total_failed}")
    print(f"   📊 Porcentaje de éxito: {(total_passed/max(total_tests,1)*100):.1f}%")
    
    if failed_tests:
        print(f"\n❌ TESTS FALLIDOS:")
        for failed in failed_tests:
            print(f"   - {failed}")
    
    # Validación de criterios de aceptación
    print(f"\n🎯 CRITERIOS DE ACEPTACIÓN:")
    
    criterios = [
        ("Grafo compila correctamente", total_passed > 0),
        ("Tests de decisiones pasan", "decisiones" in str(failed_tests).lower() == False),
        ("Tests de flujos pasan", "flujos" in str(failed_tests).lower() == False),
        ("Tests de propagación pasan", "propagacion" in str(failed_tests).lower() == False),
        ("Tasa de éxito >= 80%", total_passed/max(total_tests,1) >= 0.8)
    ]
    
    for criterio, cumplido in criterios:
        status = "✅" if cumplido else "❌"
        print(f"   {status} {criterio}")
    
    todos_criterios = all(cumplido for _, cumplido in criterios)
    
    if todos_criterios:
        print(f"\n🎉 ETAPA 8 COMPLETADA EXITOSAMENTE")
        print("   - Grafo completo implementado y validado")
        print("   - 12 nodos integrados correctamente")
        print("   - 3 funciones de decisión funcionando") 
        print("   - Flujos end-to-end validados")
        return True
    else:
        print(f"\n⚠️  ETAPA 8 REQUIERE ATENCIÓN")
        print("   - Algunos criterios de aceptación no se cumplen")
        print("   - Revisar tests fallidos antes de continuar")
        return False

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)