"""
Script simple para activar notificación de TESTS ETAPA 2 completados
"""
import subprocess
import sys

print("\n" + "=" * 70)
print("🎯 ACTIVANDO NOTIFICACIÓN: TESTS ETAPA 2 COMPLETADOS")
print("=" * 70 + "\n")

try:
    result = subprocess.run([sys.executable, "notificar_completado.py"], check=True)
    print("\n✅ Notificación ejecutada exitosamente\n")
    sys.exit(0)
except Exception as e:
    print(f"\n⚠️  Error al ejecutar notificación: {e}\n")
    sys.exit(1)
