"""
Tests de integración de seguridad end-to-end.
"""

import os
import pytest
from unittest.mock import patch
from src.config.secure_config import get_config, ConfigurationError, SecureConfig


class TestSecurityIntegration:
    """Tests de integración de seguridad"""

    def test_application_cannot_start_without_config(self):
        """Test: Aplicación no debe iniciar sin configuración válida"""
        # Reset singleton to ensure get_config() tries to create new instance
        import src.config.secure_config as sc

        sc.config = None

        # Use patch.dict to modify environment safely
        with patch.dict(os.environ):
            for var in SecureConfig.REQUIRED_VARS:
                if var in os.environ:
                    del os.environ[var]

            # Reset singleton inside context
            sc.config = None

            # Intentar iniciar configuración
            try:
                get_config()
                pytest.fail("get_config() should have raised ConfigurationError")
            except Exception as e:
                # Validate it is the correct exception type
                assert isinstance(
                    e, ConfigurationError
                ), f"Expected ConfigurationError but got {type(e)}"

        # Reset singleton again
        sc.config = None

    def test_no_hardcoded_passwords_in_db_config(self):
        """Test: No debe haber passwords hardcodeados en db_config"""
        import inspect
        from src.database import db_config

        # Verificar que NO hay passwords hardcodeados en el código
        source = inspect.getsource(db_config)

        # No debe contener password='admin' o similar
        assert "password='admin'" not in source.lower()
        assert 'password="admin"' not in source.lower()
        assert "getenv('POSTGRES_PASSWORD', 'admin')" not in source

    def test_gitignore_protects_sensitive_files(self):
        """Test: .gitignore protege archivos sensibles"""
        # Ensure we are in the root
        if not os.path.exists(".gitignore"):
            pytest.skip(".gitignore not found")

        with open(".gitignore", "r") as f:
            gitignore_content = f.read()

        # Patrones críticos de seguridad
        critical_patterns = ["*.json", ".env", "secrets/", "*.log", "*.key", "*.pem"]

        for pattern in critical_patterns:
            assert (
                pattern in gitignore_content
            ), f"Patrón crítico '{pattern}' faltante en .gitignore"

    def test_rate_limiters_configured(self):
        """Test: Rate limiters están configurados para todas las APIs"""
        from src.middleware.rate_limiter import RATE_LIMITERS

        required_apis = ["google_calendar", "deepseek", "anthropic", "whatsapp"]

        for api in required_apis:
            assert api in RATE_LIMITERS, f"Rate limiter para '{api}' no configurado"
            assert RATE_LIMITERS[api].calls > 0
            assert RATE_LIMITERS[api].period > 0
