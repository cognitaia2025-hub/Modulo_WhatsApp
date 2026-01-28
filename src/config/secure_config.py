"""
Módulo de configuración segura del sistema.
Carga y valida todas las variables de entorno obligatorias.
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()


class ConfigurationError(Exception):
    """Error de configuración del sistema"""

    pass


class SecureConfig:
    """Configuración centralizada y segura"""

    # Variables obligatorias
    REQUIRED_VARS = [
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "DEEPSEEK_API_KEY",
        "ANTHROPIC_API_KEY",
        "GOOGLE_SERVICE_ACCOUNT_FILE",
        "GOOGLE_CALENDAR_ID",
        "DEFAULT_TIMEZONE",
    ]

    def __init__(self):
        """Inicializar y validar configuración"""
        self._validate_required_vars()
        self._load_configuration()

    def _validate_required_vars(self):
        """Validar que todas las variables obligatorias existen"""
        missing_vars = []

        for var in self.REQUIRED_VARS:
            val = os.getenv(var)
            # print(f"DEBUG: Checking {var}: {val}")
            if not val:
                missing_vars.append(var)

        if missing_vars:
            raise ConfigurationError(
                f"Variables de entorno faltantes: {', '.join(missing_vars)}\n"
                f"Por favor configúralas en el archivo .env"
            )

    def _load_configuration(self):
        """Cargar configuración desde variables de entorno"""
        # Base de datos
        self.POSTGRES_HOST = os.getenv("POSTGRES_HOST")
        self.POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", 5434))
        self.POSTGRES_DB = os.getenv("POSTGRES_DB")
        self.POSTGRES_USER = os.getenv("POSTGRES_USER")
        self.POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")

        # APIs LLM
        self.DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
        self.ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

        # Google
        self.GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
        self.GOOGLE_CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID")

        # Sistema
        self.DEFAULT_TIMEZONE = os.getenv("DEFAULT_TIMEZONE", "America/Tijuana")
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    def get_database_url(self) -> str:
        """Construir URL de conexión a base de datos"""
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    def get_database_config(self) -> dict:
        """Obtener configuración de base de datos como dict"""
        return {
            "host": self.POSTGRES_HOST,
            "port": self.POSTGRES_PORT,
            "database": self.POSTGRES_DB,
            "user": self.POSTGRES_USER,
            "password": self.POSTGRES_PASSWORD,
        }


# Instancia global (singleton)
config: Optional[SecureConfig] = None


def get_config() -> SecureConfig:
    """Obtener instancia de configuración (singleton)"""
    global config
    if config is None:
        config = SecureConfig()
    return config


# Para facilitar imports
def validate_configuration():
    """Validar configuración al inicio de la aplicación"""
    try:
        get_config()
        print("✅ Configuración validada correctamente")
        return True
    except ConfigurationError as e:
        print(f"❌ Error de configuración: {e}")
        return False
