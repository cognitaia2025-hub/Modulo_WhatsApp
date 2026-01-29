"""
Script para ejecutar tests de ETAPA 1
"""
import subprocess
import sys

print("=" * 70)
print("🧪 TESTS DE ETAPA 1: Sistema de Identificación de Usuarios")
print("=" * 70)
print()

# Ejecutar tests
result = subprocess.run(
    ["python", "-m", "pytest", "tests/Etapa_1/", "-v", "--tb=short"],
    capture_output=False
)

print()
print("=" * 70)

if result.returncode == 0:
    print("✅ TODOS LOS TESTS PASARON")
else:
    print("❌ ALGUNOS TESTS FALLARON")

print("=" * 70)

sys.exit(result.returncode)
