"""
Tests para validar que archivos sensibles no están trackeados.
"""

import subprocess
import pytest


class TestGitignoreValidation:
    """Tests de validación de .gitignore"""

    def run_git_command(self, command: str) -> str:
        """Ejecutar comando git"""
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.stdout

    def test_credentials_json_not_tracked(self):
        """Test: Archivos .json de credenciales no deben estar trackeados"""
        # Buscar archivos .json trackeados
        output = self.run_git_command('git ls-files | findstr /R "\\.json$"')

        # Filtrar package.json y similares (legítimos)
        legitimate_json = ["package.json", "package-lock.json", "tsconfig.json"]

        tracked_json = [
            f.strip()
            for f in output.strip().split("\n")
            if f.strip() and f.strip() not in legitimate_json
        ]

        # No debe haber archivos .json sensibles trackeados
        assert (
            len(tracked_json) == 0
        ), f"Archivos .json sensibles encontrados trackeados: {tracked_json}"

    def test_env_files_not_tracked(self):
        """Test: Archivos .env no deben estar trackeados"""
        output = self.run_git_command('git ls-files | findstr /R "\\.env"')

        # Solo .env.example está permitido
        tracked_env = [
            f.strip()
            for f in output.strip().split("\n")
            if f.strip() and f.strip() != ".env.example"
        ]

        assert (
            len(tracked_env) == 0
        ), f"Archivos .env encontrados trackeados: {tracked_env}"

    def test_log_files_not_tracked(self):
        """Test: Archivos de log no deben estar trackeados"""
        output = self.run_git_command('git ls-files | findstr /R "\\.log$"')

        tracked_logs = [f.strip() for f in output.strip().split("\n") if f.strip()]

        assert (
            len(tracked_logs) == 0
        ), f"Archivos .log encontrados trackeados: {tracked_logs}"

    def test_secrets_folder_not_tracked(self):
        """Test: Carpeta secrets/ no debe estar trackeada"""
        output = self.run_git_command('git ls-files | findstr "secrets/"')

        tracked_secrets = [f.strip() for f in output.strip().split("\n") if f.strip()]

        assert (
            len(tracked_secrets) == 0
        ), f"Archivos en secrets/ encontrados trackeados: {tracked_secrets}"

    def test_gitignore_exists(self):
        """Test: .gitignore debe existir"""
        import os

        assert os.path.exists(".gitignore"), ".gitignore no encontrado"

    def test_gitignore_contains_required_patterns(self):
        """Test: .gitignore debe contener patrones esenciales"""
        with open(".gitignore", "r") as f:
            gitignore_content = f.read()

        required_patterns = ["*.json", ".env", "secrets/", "*.log"]

        for pattern in required_patterns:
            assert (
                pattern in gitignore_content
            ), f"Patrón '{pattern}' faltante en .gitignore"
