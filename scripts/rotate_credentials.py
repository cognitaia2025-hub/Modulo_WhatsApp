#!/usr/bin/env python3
"""
Script para eliminar archivos de credenciales del historial de Git.
ADVERTENCIA: Este script reescribe el historial de Git.
"""
import os
import sys
import subprocess
import argparse
from pathlib import Path


def run_command(command: str, check: bool = True) -> tuple:
    """Ejecutar comando de shell"""
    print(f"🔧 Ejecutando: {command}")
    result = subprocess.run(
        command, shell=True, capture_output=True, text=True, check=False
    )

    if check and result.returncode != 0:
        print(f"❌ Error: {result.stderr}")
        sys.exit(1)

    return result.returncode, result.stdout, result.stderr


def verify_git_repo():
    """Verificar que estamos en un repositorio Git"""
    if not os.path.exists(".git"):
        print("❌ Error: No estás en un repositorio Git")
        sys.exit(1)


def backup_repo():
    """Crear backup del repositorio actual"""
    print("📦 Creando backup del repositorio...")
    repo_path = Path.cwd()
    backup_path = repo_path.parent / f"{repo_path.name}_backup"

    # En Windows usamos xcopy en lugar de cp
    if os.name == "nt":
        run_command(f'xcopy /E /I /H /Y "{repo_path}" "{backup_path}"')
    else:
        run_command(f'cp -r "{repo_path}" "{backup_path}"')

    print(f"✅ Backup creado en: {backup_path}")


def remove_file_from_history(file_path: str):
    """Eliminar archivo del historial de Git"""
    print(f"\n🗑️  Eliminando '{file_path}' del historial de Git...")

    # Verificar que el archivo existe o existió
    code, _, _ = run_command(
        f'git log --all --full-history -- "{file_path}"', check=False
    )

    if code != 0:
        print(f"⚠️  Advertencia: '{file_path}' no encontrado en el historial")
        return

    # Eliminar del índice actual si existe
    run_command(f'git rm --cached --ignore-unmatch "{file_path}"', check=False)

    # Eliminar del historial usando filter-branch
    filter_command = (
        f"git filter-branch --force --index-filter "
        f'"git rm --cached --ignore-unmatch {file_path}" '
        f"--prune-empty --tag-name-filter cat -- --all"
    )

    run_command(filter_command)

    print(f"✅ '{file_path}' eliminado del historial")


def cleanup_git():
    """Limpiar referencias y recolectar basura"""
    print("\n🧹 Limpiando Git...")

    # Eliminar referencias del reflog
    run_command("git reflog expire --expire=now --all")

    # Recolectar basura
    run_command("git gc --prune=now --aggressive")

    print("✅ Limpieza completada")


def verify_removal(file_path: str):
    """Verificar que el archivo fue eliminado del historial"""
    print(f"\n🔍 Verificando eliminación de '{file_path}'...")

    code, output, _ = run_command(
        f'git log --all --full-history -- "{file_path}"', check=False
    )

    if code == 0 and output.strip():
        print(f"⚠️  ADVERTENCIA: '{file_path}' aún aparece en el historial")
        return False
    else:
        print(f"✅ '{file_path}' eliminado correctamente del historial")
        return True


def main():
    parser = argparse.ArgumentParser(
        description="Eliminar archivos de credenciales del historial de Git"
    )
    parser.add_argument(
        "--file", required=True, help="Ruta del archivo a eliminar del historial"
    )
    parser.add_argument(
        "--no-backup", action="store_true", help="No crear backup (no recomendado)"
    )
    parser.add_argument("--force", action="store_true", help="No pedir confirmación")

    args = parser.parse_args()

    print("=" * 60)
    print("🔒 ROTACIÓN DE CREDENCIALES - Eliminación de Historial Git")
    print("=" * 60)

    # Verificaciones
    verify_git_repo()

    # Advertencia
    print(f"\n⚠️  ADVERTENCIA: Este script va a:")
    print(f"   1. Eliminar '{args.file}' del historial de Git")
    print(f"   2. Reescribir el historial completo del repositorio")
    print(f"   3. Requerir un force push si el repo está en remoto")

    if not args.no_backup:
        print(f"   4. Crear un backup del repositorio actual")

    if not args.force:
        response = input("\n¿Deseas continuar? (escribe 'SI' para confirmar): ")
        if response != "SI":
            print("❌ Operación cancelada")
            sys.exit(0)

    # Crear backup
    if not args.no_backup:
        backup_repo()

    # Eliminar archivo del historial
    remove_file_from_history(args.file)

    # Limpiar Git
    cleanup_git()

    # Verificar eliminación
    verify_removal(args.file)

    # Instrucciones finales
    print("\n" + "=" * 60)
    print("✅ PROCESO COMPLETADO")
    print("=" * 60)
    print("\n📝 PRÓXIMOS PASOS:")
    print("\n1. Verificar que el archivo fue eliminado:")
    print(f"   git log --all --full-history -- {args.file}")
    print("\n2. Si el repositorio tiene remoto, hacer force push:")
    print("   git push origin --force --all")
    print("   git push origin --force --tags")
    print("\n3. ⚠️  IMPORTANTE: Rotar las credenciales en el servicio:")
    print(
        "   - Google Cloud: https://console.cloud.google.com/iam-admin/serviceaccounts"
    )
    print("\n4. Agregar el archivo al .gitignore:")
    print(f"   echo '{args.file}' >> .gitignore")
    print("\n5. Mover credenciales a ubicación segura fuera del repo")


if __name__ == "__main__":
    main()
