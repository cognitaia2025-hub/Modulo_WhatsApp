#!/usr/bin/env python3
"""
EJECUTAR TESTS - ETAPA 6
Script para ejecutar los tests de la Etapa 6: Recordatorios Automáticos
"""

import subprocess
import sys
import time
from pathlib import Path

def main():
    print("=" * 70)
    print("🧪 EJECUTANDO TESTS ETAPA 6 - RECORDATORIOS AUTOMÁTICOS")
    print("=" * 70)
    print()
    
    # Ruta al directorio de tests
    script_dir = Path(__file__).parent
    tests_dir = script_dir / "tests" / "Etapa_6"
    
    if not tests_dir.exists():
        print(f"❌ ERROR: No se encontró el directorio {tests_dir}")
        return 1
    
    print(f"📁 Directorio de tests: {tests_dir}")
    print()
    print("⏳ Ejecutando tests...")
    print()
    
    inicio = time.time()
    
    try:
        # Ejecutar pytest
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(tests_dir), "-v", "--tb=short"],
            capture_output=True,
            text=True
        )
        
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        
        fin = time.time()
        tiempo_total = fin - inicio
        
        print()
        print("=" * 70)
        if result.returncode == 0:
            print("✅ TODOS LOS TESTS PASARON")
        else:
            print("❌ ALGUNOS TESTS FALLARON")
        print("=" * 70)
        print()
        print(f"⏱️  Tiempo total: {tiempo_total:.2f}s")
        print()
        
        return result.returncode
    
    except Exception as e:
        print(f"❌ ERROR al ejecutar tests: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
