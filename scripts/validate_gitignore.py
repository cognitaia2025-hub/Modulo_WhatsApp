#!/usr/bin/env python3
"""
Script para validar que archivos sensibles no están trackeados en Git.
"""
import subprocess
import sys
from pathlib import Path


def run_git_command(command: str) -> str:
    """Ejecutar comando git"""
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return result.stdout


def check_tracked_files(pattern: str, allowed: list = None) -> list:
    """Verificar archivos trackeados que coinciden con un patrón"""
    if allowed is None:
        allowed = []

    output = run_git_command(f'git ls-files | findstr /R "{pattern}"')

    tracked = [
        f.strip()
        for f in output.strip().split("\n")
        if f.strip() and f.strip() not in allowed
    ]

    return tracked


def main():
    print("=" * 60)
    print("🔍 VALIDACIÓN DE .GITIGNORE")
    print("=" * 60)

    errors = []

    # Verificar que .gitignore existe
    if not Path(".gitignore").exists():
        print("❌ ERROR: .gitignore no encontrado")
        sys.exit(1)

    print("\n✅ .gitignore encontrado")

    # Leer contenido de .gitignore
    with open(".gitignore", "r") as f:
        gitignore_content = f.read()

    # Patrones requeridos
    required_patterns = [
        ("*.json", "Archivos JSON de credenciales"),
        (".env", "Archivos de entorno"),
        ("secrets/", "Carpeta de secretos"),
        ("*.log", "Archivos de log"),
    ]

    print("\n📋 Verificando patrones en .gitignore:")
    for pattern, description in required_patterns:
        if pattern in gitignore_content:
            print(f"   ✅ {pattern} - {description}")
        else:
            print(f"   ❌ {pattern} - {description} (FALTANTE)")
            errors.append(f"Patrón '{pattern}' faltante en .gitignore")

    # Verificar archivos trackeados
    print("\n🔍 Verificando archivos trackeados:")

    # Archivos .json (excepto legítimos)
    legitimate_json = ["package.json", "package-lock.json", "tsconfig.json"]
    tracked_json = check_tracked_files(r"\.json$", legitimate_json)

    if tracked_json:
        print(f"   ❌ Archivos .json sensibles trackeados: {tracked_json}")
        errors.append(f"Archivos .json sensibles trackeados: {tracked_json}")
    else:
        print("   ✅ No hay archivos .json sensibles trackeados")

    # Archivos .env (excepto .env.example)
    tracked_env = check_tracked_files(r"\.env", [".env.example"])

    if tracked_env:
        print(f"   ❌ Archivos .env trackeados: {tracked_env}")
        errors.append(f"Archivos .env trackeados: {tracked_env}")
    else:
        print("   ✅ No hay archivos .env trackeados")

    # Archivos .log
    tracked_logs = check_tracked_files(r"\.log$")

    if tracked_logs:
        print(f"   ❌ Archivos .log trackeados: {tracked_logs}")
        errors.append(f"Archivos .log trackeados: {tracked_logs}")
    else:
        print("   ✅ No hay archivos .log trackeados")

    # Carpeta secrets/
    output = run_git_command('git ls-files | findstr /R "secrets/"')
    tracked_secrets = [f.strip() for f in output.strip().split("\n") if f.strip()]

    if tracked_secrets:
        print(f"   ❌ Archivos en secrets/ trackeados: {tracked_secrets}")
        errors.append(f"Archivos en secrets/ trackeados: {tracked_secrets}")
    else:
        print("   ✅ No hay archivos en secrets/ trackeados")

    # Resultado final
    print("\n" + "=" * 60)
    if errors:
        print("❌ VALIDACIÓN FALLIDA")
        print("=" * 60)
        print("\nErrores encontrados:")
        for error in errors:
            print(f"  • {error}")
        print("\n💡 Acciones recomendadas:")
        print("  1. Actualizar .gitignore con los patrones faltantes")
        print("  2. Ejecutar: git rm --cached <archivo>")
        print("  3. Para archivos sensibles en historial: usar rotate_credentials.py")
        sys.exit(1)
    else:
        print("✅ VALIDACIÓN EXITOSA")
        print("=" * 60)
        print("\n🎉 Todos los archivos sensibles están protegidos")
        sys.exit(0)


if __name__ == "__main__":
    main()
