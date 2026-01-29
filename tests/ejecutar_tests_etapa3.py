#!/usr/bin/env python3
"""
EJECUTAR TESTS - ETAPA 3
Script para ejecutar los 80 tests de la ETAPA 3
"""

import subprocess
import sys
from pathlib import Path

def main():
    print("=" * 70)
    print("🧪 EJECUTANDO TESTS DE ETAPA 3")
    print("=" * 70)
    print()
    
    script_dir = Path(__file__).parent
    tests_dir = script_dir / "tests" / "Etapa_3"
    
    if not tests_dir.exists():
        print(f"❌ ERROR: No se encontró {tests_dir}")
        return 1
    
    print(f"📁 Carpeta de tests: {tests_dir}")
    print(f"🧪 Ejecutando pytest...\n")
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(tests_dir), "-v", "--tb=short"],
            cwd=str(script_dir)
        )
        
        print("\n" + "=" * 70)
        
        if result.returncode == 0:
            print("✅ TODOS LOS TESTS PASARON (80/80)")
            print("=" * 70)
            print("\n🎉 ETAPA 3 VALIDADA EXITOSAMENTE")
            return 0
        else:
            print("❌ ALGUNOS TESTS FALLARON")
            print("=" * 70)
            return 1
    
    except Exception as e:
        print(f"\n❌ ERROR al ejecutar tests: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
