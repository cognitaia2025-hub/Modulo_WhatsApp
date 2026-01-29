#!/usr/bin/env python3
"""
EJECUTAR TESTS - ETAPA 2
Script para ejecutar los tests de la ETAPA 2 del sistema
"""

import subprocess
import sys
from pathlib import Path

def main():
    print("=" * 60)
    print("EJECUTANDO TESTS DE ETAPA 2")
    print("=" * 60)
    
    # Cambiar al directorio del script
    script_dir = Path(__file__).parent
    tests_dir = script_dir / "tests" / "Etapa_2"
    
    # Verificar que existe la carpeta de tests
    if not tests_dir.exists():
        print(f"❌ ERROR: No se encontró {tests_dir}")
        return 1
    
    print(f"\n📁 Carpeta de tests: {tests_dir}")
    print(f"🧪 Ejecutando pytest...\n")
    
    # Ejecutar pytest
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(tests_dir), "-v", "--tb=short"],
            cwd=str(script_dir)
        )
        
        print("\n" + "=" * 60)
        
        if result.returncode == 0:
            print("✅ TODOS LOS TESTS PASARON")
            print("=" * 60)
            return 0
        else:
            print("❌ ALGUNOS TESTS FALLARON")
            print("=" * 60)
            return 1
            
    except Exception as e:
        print(f"\n❌ ERROR al ejecutar tests: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
