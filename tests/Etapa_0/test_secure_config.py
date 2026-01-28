"""
Tests para validar el sistema de configuración segura.
"""

import os
import pytest
from unittest.mock import patch
from src.config.secure_config import SecureConfig, ConfigurationError, get_config


class TestSecureConfig:
    """Tests para SecureConfig"""

    def setup_method(self):
        """Configurar ambiente de prueba"""
        # Reset singleton explicitly
        import src.config.secure_config as sc

        sc.config = None

    def teardown_method(self):
        """Restaurar ambiente"""
        # Reset singleton
        import src.config.secure_config as sc

        sc.config = None

    def test_missing_required_vars_raises_error(self):
        """Test: Variables faltantes deben lanzar ConfigurationError"""
        # Use patch.dict to clear os.environ completely for this test block
        with patch.dict(os.environ, {}, clear=True):
            # Intentar crear configuración
            with pytest.raises(ConfigurationError) as exc_info:
                SecureConfig()

            # Verificar mensaje de error
            error_message = str(exc_info.value)
            assert "Variables de entorno faltantes" in error_message
            # POSTGRES_PASSWORD is one of the required vars, so it should be in the missing list
            assert "POSTGRES_PASSWORD" in error_message

    def test_all_required_vars_present_succeeds(self):
        """Test: Configuración exitosa con todas las variables"""
        test_vars = {
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5434",
            "POSTGRES_DB": "test_db",
            "POSTGRES_USER": "test_user",
            "POSTGRES_PASSWORD": "secure_password_123",
            "DEEPSEEK_API_KEY": "test_deepseek_key",
            "ANTHROPIC_API_KEY": "test_anthropic_key",
            "GOOGLE_SERVICE_ACCOUNT_FILE": "./test_credentials.json",
            "GOOGLE_CALENDAR_ID": "test_calendar_id",
            "DEFAULT_TIMEZONE": "America/Tijuana",
        }

        with patch.dict(os.environ, test_vars, clear=True):
            # Crear configuración (no debe lanzar error)
            config = SecureConfig()

            # Verificar valores cargados
            assert config.POSTGRES_HOST == "localhost"
            assert config.POSTGRES_PASSWORD == "secure_password_123"
            assert config.DEEPSEEK_API_KEY == "test_deepseek_key"

    def test_database_url_construction(self):
        """Test: Construcción correcta de URL de base de datos"""
        test_vars = {
            "POSTGRES_HOST": "dbhost",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "mydb",
            "POSTGRES_USER": "myuser",
            "POSTGRES_PASSWORD": "mypass",
            "DEEPSEEK_API_KEY": "test",
            "ANTHROPIC_API_KEY": "test",
            "GOOGLE_SERVICE_ACCOUNT_FILE": "test.json",
            "GOOGLE_CALENDAR_ID": "test",
            "DEFAULT_TIMEZONE": "UTC",
        }

        with patch.dict(os.environ, test_vars, clear=True):
            config = SecureConfig()
            db_url = config.get_database_url()

            expected = "postgresql://myuser:mypass@dbhost:5432/mydb"
            assert db_url == expected

    def test_singleton_pattern(self):
        """Test: get_config() retorna la misma instancia"""
        test_vars = {
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5434",
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "test",
            "POSTGRES_PASSWORD": "test",
            "DEEPSEEK_API_KEY": "test",
            "ANTHROPIC_API_KEY": "test",
            "GOOGLE_SERVICE_ACCOUNT_FILE": "test.json",
            "GOOGLE_CALENDAR_ID": "test",
            "DEFAULT_TIMEZONE": "UTC",
        }

        with patch.dict(os.environ, test_vars, clear=True):
            # Reset singleton
            import src.config.secure_config as sc

            sc.config = None

            config1 = get_config()
            config2 = get_config()

            assert config1 is config2  # Misma instancia

    def test_no_default_password_allowed(self):
        """Test: No debe permitir usar passwords por defecto"""
        test_vars = {
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5434",
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "admin",
            # POSTGRES_PASSWORD NO está configurado
            "DEEPSEEK_API_KEY": "test",
            "ANTHROPIC_API_KEY": "test",
            "GOOGLE_SERVICE_ACCOUNT_FILE": "test.json",
            "GOOGLE_CALENDAR_ID": "test",
            "DEFAULT_TIMEZONE": "UTC",
        }

        with patch.dict(os.environ, test_vars, clear=True):
            # Debe fallar porque falta POSTGRES_PASSWORD
            with pytest.raises(ConfigurationError):
                SecureConfig()
