# 🔒 PROMPT PARA IMPLEMENTACIÓN - ETAPA 0: SEGURIDAD Y CORRECCIONES CRÍTICAS

**Prioridad:** 🔴 CRÍTICA
**Duración estimada:** 1-2 días
**Requisitos previos:** Ninguno
**Contexto del proyecto:** Sistema híbrido WhatsApp + LangGraph para calendario personal y gestión médica

---

## 🎯 OBJETIVO GENERAL

Corregir todas las vulnerabilidades de seguridad críticas identificadas en el code review antes de continuar con el desarrollo. Implementar sistema de configuración segura y protección contra exposición de credenciales.

**Problemas críticos a resolver:**
1. Credencial de Google Cloud expuesta en repositorio Git
2. Password de PostgreSQL hardcodeado con valor por defecto débil
3. API keys impresas en logs
4. CALENDAR_ID hardcodeado en múltiples archivos
5. Falta de rate limiting para APIs externas

---

## 📋 COMPONENTES A IMPLEMENTAR

### 🤖 Nodos Automatizados (Sin LLM)

#### N0.1 - Nodo de Configuración Segura
- **Estado:** 🟢 CREAR
- **Archivo:** `src/config/secure_config.py`
- **Responsabilidad:**
  - Cargar variables de entorno desde `.env`
  - Validar que todas las variables obligatorias existen
  - Lanzar excepciones claras si falta alguna configuración
  - Proporcionar acceso centralizado a configuraciones
- **Sin LLM:** Validación determinística

#### N0.2 - Nodo de Rate Limiting
- **Estado:** 🟢 CREAR
- **Archivo:** `src/middleware/rate_limiter.py`
- **Responsabilidad:**
  - Limitar llamadas a Google Calendar API (10 req/seg)
  - Limitar llamadas a DeepSeek API (20 req/min)
  - Limitar llamadas a Anthropic API (15 req/min)
  - Implementar backoff exponencial en caso de límites
- **Sin LLM:** Contadores y ventanas de tiempo

### 🔧 Herramientas Sistema

#### T0.1 - Script de Rotación de Credenciales
- **Estado:** 🟢 CREAR
- **Archivo:** `scripts/rotate_credentials.py`
- **Función:** Eliminar archivos de credenciales del historial Git

#### T0.2 - Script de Validación de .gitignore
- **Estado:** 🟢 CREAR
- **Archivo:** `scripts/validate_gitignore.py`
- **Función:** Verificar que archivos sensibles no estén trackeados

#### T0.3 - Decorador de Rate Limiting
- **Estado:** 🟢 CREAR
- **Archivo:** `src/decorators/rate_limit.py`
- **Función:** Decorator aplicable a cualquier función que llame APIs

### 🗄️ Bases de Datos

#### BD0.1 - Tabla de Configuración Segura
- **Estado:** 🟢 CREAR
- **Nombre:** `configuracion_sistema`
- **Uso:** Almacenar configuraciones sensibles encriptadas (futuro)

---

## 📝 ESPECIFICACIONES TÉCNICAS DETALLADAS

### 1. Configuración Segura (`src/config/secure_config.py`)

```python
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
        'POSTGRES_HOST',
        'POSTGRES_PORT',
        'POSTGRES_DB',
        'POSTGRES_USER',
        'POSTGRES_PASSWORD',
        'DEEPSEEK_API_KEY',
        'ANTHROPIC_API_KEY',
        'GOOGLE_SERVICE_ACCOUNT_FILE',
        'GOOGLE_CALENDAR_ID',
        'DEFAULT_TIMEZONE'
    ]

    def __init__(self):
        """Inicializar y validar configuración"""
        self._validate_required_vars()
        self._load_configuration()

    def _validate_required_vars(self):
        """Validar que todas las variables obligatorias existen"""
        missing_vars = []

        for var in self.REQUIRED_VARS:
            if not os.getenv(var):
                missing_vars.append(var)

        if missing_vars:
            raise ConfigurationError(
                f"Variables de entorno faltantes: {', '.join(missing_vars)}\n"
                f"Por favor configúralas en el archivo .env"
            )

    def _load_configuration(self):
        """Cargar configuración desde variables de entorno"""
        # Base de datos
        self.POSTGRES_HOST = os.getenv('POSTGRES_HOST')
        self.POSTGRES_PORT = int(os.getenv('POSTGRES_PORT', 5434))
        self.POSTGRES_DB = os.getenv('POSTGRES_DB')
        self.POSTGRES_USER = os.getenv('POSTGRES_USER')
        self.POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')

        # APIs LLM
        self.DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
        self.ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

        # Google
        self.GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE')
        self.GOOGLE_CALENDAR_ID = os.getenv('GOOGLE_CALENDAR_ID')

        # Sistema
        self.DEFAULT_TIMEZONE = os.getenv('DEFAULT_TIMEZONE', 'America/Tijuana')
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

    def get_database_url(self) -> str:
        """Construir URL de conexión a base de datos"""
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    def get_database_config(self) -> dict:
        """Obtener configuración de base de datos como dict"""
        return {
            'host': self.POSTGRES_HOST,
            'port': self.POSTGRES_PORT,
            'database': self.POSTGRES_DB,
            'user': self.POSTGRES_USER,
            'password': self.POSTGRES_PASSWORD
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
```

### 2. Rate Limiting (`src/middleware/rate_limiter.py`)

```python
"""
Middleware de rate limiting para APIs externas.
Previene exceder límites de llamadas a servicios externos.
"""
import time
import threading
from functools import wraps
from typing import Callable, Dict
from collections import deque
from datetime import datetime, timedelta

class RateLimiter:
    """Rate limiter con ventana deslizante"""

    def __init__(self, calls: int, period: int):
        """
        Args:
            calls: Número máximo de llamadas
            period: Período en segundos
        """
        self.calls = calls
        self.period = period
        self.timestamps: deque = deque()
        self.lock = threading.Lock()

    def _clean_old_timestamps(self):
        """Eliminar timestamps fuera de la ventana de tiempo"""
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.period)

        while self.timestamps and self.timestamps[0] < cutoff:
            self.timestamps.popleft()

    def acquire(self) -> bool:
        """
        Intentar adquirir permiso para ejecutar.
        Retorna True si se puede ejecutar, False si debe esperar.
        """
        with self.lock:
            self._clean_old_timestamps()

            if len(self.timestamps) < self.calls:
                self.timestamps.append(datetime.now())
                return True

            return False

    def wait_if_needed(self):
        """Esperar si es necesario para respetar el rate limit"""
        while not self.acquire():
            time.sleep(0.1)  # Esperar 100ms y reintentar

# Rate limiters globales para cada API
RATE_LIMITERS: Dict[str, RateLimiter] = {
    'google_calendar': RateLimiter(calls=10, period=1),      # 10 req/seg
    'deepseek': RateLimiter(calls=20, period=60),            # 20 req/min
    'anthropic': RateLimiter(calls=15, period=60),           # 15 req/min
    'whatsapp': RateLimiter(calls=80, period=1),             # 80 req/seg
}

def rate_limit(api_name: str):
    """
    Decorador para aplicar rate limiting a una función.

    Args:
        api_name: Nombre del API ('google_calendar', 'deepseek', etc.)

    Usage:
        @rate_limit('google_calendar')
        def call_google_api():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            limiter = RATE_LIMITERS.get(api_name)

            if limiter:
                limiter.wait_if_needed()

            return func(*args, **kwargs)

        return wrapper
    return decorator

# Versión asíncrona (para uso con asyncio)
def async_rate_limit(api_name: str):
    """
    Decorador para aplicar rate limiting a funciones async.

    Usage:
        @async_rate_limit('deepseek')
        async def call_deepseek_api():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            limiter = RATE_LIMITERS.get(api_name)

            if limiter:
                # Esperar de forma asíncrona
                while not limiter.acquire():
                    await asyncio.sleep(0.1)

            return await func(*args, **kwargs)

        return wrapper
    return decorator
```

### 3. Script de Rotación de Credenciales (`scripts/rotate_credentials.py`)

```python
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
        command,
        shell=True,
        capture_output=True,
        text=True,
        check=False
    )

    if check and result.returncode != 0:
        print(f"❌ Error: {result.stderr}")
        sys.exit(1)

    return result.returncode, result.stdout, result.stderr

def verify_git_repo():
    """Verificar que estamos en un repositorio Git"""
    if not os.path.exists('.git'):
        print("❌ Error: No estás en un repositorio Git")
        sys.exit(1)

def backup_repo():
    """Crear backup del repositorio actual"""
    print("📦 Creando backup del repositorio...")
    repo_path = Path.cwd()
    backup_path = repo_path.parent / f"{repo_path.name}_backup"

    run_command(f'cp -r "{repo_path}" "{backup_path}"')
    print(f"✅ Backup creado en: {backup_path}")

def remove_file_from_history(file_path: str):
    """Eliminar archivo del historial de Git"""
    print(f"\n🗑️  Eliminando '{file_path}' del historial de Git...")

    # Verificar que el archivo existe o existió
    code, _, _ = run_command(f'git log --all --full-history -- "{file_path}"', check=False)

    if code != 0:
        print(f"⚠️  Advertencia: '{file_path}' no encontrado en el historial")
        return

    # Eliminar del índice actual si existe
    run_command(f'git rm --cached --ignore-unmatch "{file_path}"', check=False)

    # Eliminar del historial usando filter-branch
    filter_command = (
        f'git filter-branch --force --index-filter '
        f'"git rm --cached --ignore-unmatch {file_path}" '
        f'--prune-empty --tag-name-filter cat -- --all'
    )

    run_command(filter_command)

    print(f"✅ '{file_path}' eliminado del historial")

def cleanup_git():
    """Limpiar referencias y recolectar basura"""
    print("\n🧹 Limpiando Git...")

    # Eliminar referencias del reflog
    run_command('git reflog expire --expire=now --all')

    # Recolectar basura
    run_command('git gc --prune=now --aggressive')

    print("✅ Limpieza completada")

def verify_removal(file_path: str):
    """Verificar que el archivo fue eliminado del historial"""
    print(f"\n🔍 Verificando eliminación de '{file_path}'...")

    code, output, _ = run_command(
        f'git log --all --full-history -- "{file_path}"',
        check=False
    )

    if code == 0 and output.strip():
        print(f"⚠️  ADVERTENCIA: '{file_path}' aún aparece en el historial")
        return False
    else:
        print(f"✅ '{file_path}' eliminado correctamente del historial")
        return True

def main():
    parser = argparse.ArgumentParser(
        description='Eliminar archivos de credenciales del historial de Git'
    )
    parser.add_argument(
        '--file',
        required=True,
        help='Ruta del archivo a eliminar del historial'
    )
    parser.add_argument(
        '--no-backup',
        action='store_true',
        help='No crear backup (no recomendado)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='No pedir confirmación'
    )

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
        if response != 'SI':
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
    print("   - Google Cloud: https://console.cloud.google.com/iam-admin/serviceaccounts")
    print("\n4. Agregar el archivo al .gitignore:")
    print(f"   echo '{args.file}' >> .gitignore")
    print("\n5. Mover credenciales a ubicación segura fuera del repo")

if __name__ == '__main__':
    main()
```

### 4. Crear `.env.example`

```bash
# .env.example - Plantilla de variables de entorno

# ==================== BASE DE DATOS ====================
POSTGRES_HOST=localhost
POSTGRES_PORT=5434
POSTGRES_DB=agente_whatsapp
POSTGRES_USER=admin
POSTGRES_PASSWORD=CAMBIAR_ESTE_PASSWORD_SEGURO

# ==================== APIs LLM ====================
DEEPSEEK_API_KEY=tu_api_key_aqui
ANTHROPIC_API_KEY=tu_api_key_aqui

# ==================== GOOGLE SERVICES ====================
GOOGLE_SERVICE_ACCOUNT_FILE=./secrets/credentials.json
GOOGLE_CALENDAR_ID=tu_calendar_id_aqui

# ==================== CONFIGURACIÓN SISTEMA ====================
DEFAULT_TIMEZONE=America/Tijuana
LOG_LEVEL=INFO

# ==================== SEGURIDAD ====================
# Agregar más variables según sea necesario
```

### 5. Actualizar `src/database/db_config.py`

**CAMBIAR:**
```python
password = os.getenv('POSTGRES_PASSWORD', 'admin')  # ❌ MAL
```

**POR:**
```python
from src.config.secure_config import get_config

config = get_config()

# Usar configuración centralizada
host = config.POSTGRES_HOST
port = config.POSTGRES_PORT
database = config.POSTGRES_DB
user = config.POSTGRES_USER
password = config.POSTGRES_PASSWORD  # Sin valor por defecto
```

### 6. Actualizar herramientas para usar rate limiting

**En `src/tool.py`:**

```python
from src.middleware.rate_limiter import rate_limit
from src.config.secure_config import get_config

config = get_config()

# Eliminar prints de API keys
# ANTES:
# print("DEEPSEEK_API_KEY:", DEEPSEEK_API_KEY[:10], "...")  # ❌

# DESPUÉS: Usar logger
logger.debug("DEEPSEEK_API_KEY configurado: %s", "Sí" if config.DEEPSEEK_API_KEY else "No")

# Aplicar rate limiting a herramientas de Google Calendar
@tool
@rate_limit('google_calendar')  # ✅ Agregar decorator
def list_events_tool(...):
    # ... código existente
```

### 7. Actualizar `.gitignore`

```gitignore
# Credenciales y secrets
*.json
!package.json
!package-lock.json
!tsconfig.json
.env
.env.local
.env.*.local
secrets/
credentials/
*.key
*.pem

# Archivos de configuración sensibles
config/local.py
config/production.py

# Logs con información sensible
logs/*.log
*.log

# Backups de base de datos
*.sql
*.dump
```

---

## 🧪 TESTS REQUERIDOS

### ⚠️ REGLA DE ORO: REPARAR CÓDIGO, NO TESTS

**CRÍTICO:** Si un test falla:
- ✅ **CORRECTO:** Reparar el código para que pase el test
- ❌ **INCORRECTO:** Modificar el test para que pase
- ⚖️ **ÚNICA EXCEPCIÓN:** Si el test tiene un error lógico evidente, documentar el por qué y corregir

### Tests Obligatorios

#### TEST 1: Configuración Segura (`tests/Etapa_0/test_secure_config.py`)

```python
"""
Tests para validar el sistema de configuración segura.
"""
import os
import pytest
from src.config.secure_config import SecureConfig, ConfigurationError, get_config

class TestSecureConfig:
    """Tests para SecureConfig"""

    def setup_method(self):
        """Configurar ambiente de prueba"""
        # Guardar variables originales
        self.original_env = os.environ.copy()

    def teardown_method(self):
        """Restaurar ambiente"""
        os.environ.clear()
        os.environ.update(self.original_env)

    def test_missing_required_vars_raises_error(self):
        """Test: Variables faltantes deben lanzar ConfigurationError"""
        # Limpiar todas las variables de entorno
        for var in SecureConfig.REQUIRED_VARS:
            os.environ.pop(var, None)

        # Intentar crear configuración
        with pytest.raises(ConfigurationError) as exc_info:
            SecureConfig()

        # Verificar mensaje de error
        error_message = str(exc_info.value)
        assert "Variables de entorno faltantes" in error_message
        assert "POSTGRES_PASSWORD" in error_message

    def test_all_required_vars_present_succeeds(self):
        """Test: Configuración exitosa con todas las variables"""
        # Configurar todas las variables requeridas
        test_vars = {
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_PORT': '5434',
            'POSTGRES_DB': 'test_db',
            'POSTGRES_USER': 'test_user',
            'POSTGRES_PASSWORD': 'secure_password_123',
            'DEEPSEEK_API_KEY': 'test_deepseek_key',
            'ANTHROPIC_API_KEY': 'test_anthropic_key',
            'GOOGLE_SERVICE_ACCOUNT_FILE': './test_credentials.json',
            'GOOGLE_CALENDAR_ID': 'test_calendar_id',
            'DEFAULT_TIMEZONE': 'America/Tijuana'
        }

        for key, value in test_vars.items():
            os.environ[key] = value

        # Crear configuración (no debe lanzar error)
        config = SecureConfig()

        # Verificar valores cargados
        assert config.POSTGRES_HOST == 'localhost'
        assert config.POSTGRES_PASSWORD == 'secure_password_123'
        assert config.DEEPSEEK_API_KEY == 'test_deepseek_key'

    def test_database_url_construction(self):
        """Test: Construcción correcta de URL de base de datos"""
        # Configurar variables
        os.environ.update({
            'POSTGRES_HOST': 'dbhost',
            'POSTGRES_PORT': '5432',
            'POSTGRES_DB': 'mydb',
            'POSTGRES_USER': 'myuser',
            'POSTGRES_PASSWORD': 'mypass',
            'DEEPSEEK_API_KEY': 'test',
            'ANTHROPIC_API_KEY': 'test',
            'GOOGLE_SERVICE_ACCOUNT_FILE': 'test.json',
            'GOOGLE_CALENDAR_ID': 'test',
            'DEFAULT_TIMEZONE': 'UTC'
        })

        config = SecureConfig()
        db_url = config.get_database_url()

        expected = "postgresql://myuser:mypass@dbhost:5432/mydb"
        assert db_url == expected

    def test_singleton_pattern(self):
        """Test: get_config() retorna la misma instancia"""
        # Configurar ambiente
        os.environ.update({
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_PORT': '5434',
            'POSTGRES_DB': 'test',
            'POSTGRES_USER': 'test',
            'POSTGRES_PASSWORD': 'test',
            'DEEPSEEK_API_KEY': 'test',
            'ANTHROPIC_API_KEY': 'test',
            'GOOGLE_SERVICE_ACCOUNT_FILE': 'test.json',
            'GOOGLE_CALENDAR_ID': 'test',
            'DEFAULT_TIMEZONE': 'UTC'
        })

        config1 = get_config()
        config2 = get_config()

        assert config1 is config2  # Misma instancia

    def test_no_default_password_allowed(self):
        """Test: No debe permitir usar passwords por defecto"""
        # Configurar todas las variables EXCEPTO password
        os.environ.update({
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_PORT': '5434',
            'POSTGRES_DB': 'test',
            'POSTGRES_USER': 'admin',
            # POSTGRES_PASSWORD NO está configurado
            'DEEPSEEK_API_KEY': 'test',
            'ANTHROPIC_API_KEY': 'test',
            'GOOGLE_SERVICE_ACCOUNT_FILE': 'test.json',
            'GOOGLE_CALENDAR_ID': 'test',
            'DEFAULT_TIMEZONE': 'UTC'
        })

        # Debe fallar porque falta POSTGRES_PASSWORD
        with pytest.raises(ConfigurationError):
            SecureConfig()
```

#### TEST 2: Rate Limiting (`tests/Etapa_0/test_rate_limiter.py`)

```python
"""
Tests para el sistema de rate limiting.
"""
import time
import pytest
from src.middleware.rate_limiter import RateLimiter, rate_limit

class TestRateLimiter:
    """Tests para RateLimiter"""

    def test_rate_limiter_allows_within_limit(self):
        """Test: Permite llamadas dentro del límite"""
        limiter = RateLimiter(calls=5, period=1)  # 5 llamadas por segundo

        # Debe permitir 5 llamadas
        for i in range(5):
            assert limiter.acquire() is True

    def test_rate_limiter_blocks_exceeding_limit(self):
        """Test: Bloquea llamadas que exceden el límite"""
        limiter = RateLimiter(calls=3, period=1)

        # Primeras 3 deben pasar
        for i in range(3):
            assert limiter.acquire() is True

        # La 4ta debe bloquearse
        assert limiter.acquire() is False

    def test_rate_limiter_resets_after_period(self):
        """Test: Se resetea después del período"""
        limiter = RateLimiter(calls=2, period=1)  # 2 llamadas por segundo

        # Primeras 2 pasan
        assert limiter.acquire() is True
        assert limiter.acquire() is True

        # 3ra se bloquea
        assert limiter.acquire() is False

        # Esperar 1 segundo
        time.sleep(1.1)

        # Ahora debe permitir de nuevo
        assert limiter.acquire() is True

    def test_rate_limit_decorator(self):
        """Test: Decorator funciona correctamente"""
        call_count = 0

        @rate_limit('google_calendar')
        def test_function():
            nonlocal call_count
            call_count += 1
            return "success"

        # Llamar varias veces
        for i in range(5):
            result = test_function()
            assert result == "success"

        # Debe haber ejecutado 5 veces
        assert call_count == 5

    def test_concurrent_calls_respect_limit(self):
        """Test: Llamadas concurrentes respetan el límite"""
        import threading

        limiter = RateLimiter(calls=10, period=1)
        success_count = 0
        lock = threading.Lock()

        def make_call():
            nonlocal success_count
            if limiter.acquire():
                with lock:
                    success_count += 1

        # Crear 20 threads simultáneos
        threads = []
        for i in range(20):
            t = threading.Thread(target=make_call)
            threads.append(t)
            t.start()

        # Esperar a que terminen
        for t in threads:
            t.join()

        # Solo 10 deben haber tenido éxito (el límite)
        assert success_count == 10
```

#### TEST 3: Validación de .gitignore (`tests/Etapa_0/test_gitignore_validation.py`)

```python
"""
Tests para validar que archivos sensibles no están trackeados.
"""
import subprocess
import pytest

class TestGitignoreValidation:
    """Tests de validación de .gitignore"""

    def run_git_command(self, command: str) -> str:
        """Ejecutar comando git"""
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True
        )
        return result.stdout

    def test_credentials_json_not_tracked(self):
        """Test: Archivos .json de credenciales no deben estar trackeados"""
        # Buscar archivos .json trackeados
        output = self.run_git_command('git ls-files | grep -E "\.json$"')

        # Filtrar package.json y similares (legítimos)
        legitimate_json = ['package.json', 'package-lock.json', 'tsconfig.json']

        tracked_json = [
            f for f in output.strip().split('\n')
            if f and f not in legitimate_json
        ]

        # No debe haber archivos .json sensibles trackeados
        assert len(tracked_json) == 0, (
            f"Archivos .json sensibles encontrados trackeados: {tracked_json}"
        )

    def test_env_files_not_tracked(self):
        """Test: Archivos .env no deben estar trackeados"""
        output = self.run_git_command('git ls-files | grep -E "\.env"')

        # Solo .env.example está permitido
        tracked_env = [
            f for f in output.strip().split('\n')
            if f and f != '.env.example'
        ]

        assert len(tracked_env) == 0, (
            f"Archivos .env encontrados trackeados: {tracked_env}"
        )

    def test_log_files_not_tracked(self):
        """Test: Archivos de log no deben estar trackeados"""
        output = self.run_git_command('git ls-files | grep -E "\.log$"')

        tracked_logs = [f for f in output.strip().split('\n') if f]

        assert len(tracked_logs) == 0, (
            f"Archivos .log encontrados trackeados: {tracked_logs}"
        )

    def test_secrets_folder_not_tracked(self):
        """Test: Carpeta secrets/ no debe estar trackeada"""
        output = self.run_git_command('git ls-files | grep "secrets/"')

        tracked_secrets = [f for f in output.strip().split('\n') if f]

        assert len(tracked_secrets) == 0, (
            f"Archivos en secrets/ encontrados trackeados: {tracked_secrets}"
        )

    def test_gitignore_exists(self):
        """Test: .gitignore debe existir"""
        import os
        assert os.path.exists('.gitignore'), ".gitignore no encontrado"

    def test_gitignore_contains_required_patterns(self):
        """Test: .gitignore debe contener patrones esenciales"""
        with open('.gitignore', 'r') as f:
            gitignore_content = f.read()

        required_patterns = [
            '*.json',
            '.env',
            'secrets/',
            '*.log'
        ]

        for pattern in required_patterns:
            assert pattern in gitignore_content, (
                f"Patrón '{pattern}' faltante en .gitignore"
            )
```

#### TEST 4: Integración de Seguridad (`tests/Etapa_0/test_security_integration.py`)

```python
"""
Tests de integración de seguridad end-to-end.
"""
import os
import pytest
from src.config.secure_config import get_config, ConfigurationError

class TestSecurityIntegration:
    """Tests de integración de seguridad"""

    def test_application_cannot_start_without_config(self):
        """Test: Aplicación no debe iniciar sin configuración válida"""
        # Limpiar variables de entorno
        original_env = os.environ.copy()

        try:
            os.environ.clear()

            # Intentar iniciar configuración
            with pytest.raises(ConfigurationError):
                get_config()

        finally:
            # Restaurar ambiente
            os.environ.clear()
            os.environ.update(original_env)

    def test_database_connection_uses_secure_config(self):
        """Test: Conexión a BD usa configuración segura"""
        from src.database.db_config import get_db_session

        # Verificar que NO hay passwords hardcodeados en el código
        import inspect
        source = inspect.getsource(db_config)

        # No debe contener password='admin' o similar
        assert "password='admin'" not in source.lower()
        assert 'password="admin"' not in source.lower()

    def test_no_api_keys_in_logs(self, caplog):
        """Test: API keys no deben aparecer en logs"""
        import logging
        from src.config.secure_config import get_config

        config = get_config()

        # Verificar que las API keys no se loguean
        for record in caplog.records:
            message = record.message.lower()
            # No debe contener fragmentos de keys
            assert config.DEEPSEEK_API_KEY[:5] not in message
            assert config.ANTHROPIC_API_KEY[:5] not in message

    def test_all_tools_use_rate_limiting(self):
        """Test: Todas las herramientas usan rate limiting"""
        import inspect
        from src import tool

        # Obtener todas las funciones de herramientas
        tools = [
            obj for name, obj in inspect.getmembers(tool)
            if inspect.isfunction(obj) and name.endswith('_tool')
        ]

        # Herramientas que llaman APIs externas
        external_api_tools = [
            'list_events_tool',
            'create_event_tool',
            'update_event_tool',
            'delete_event_tool',
            'search_events_tool',
            'postpone_event_tool'
        ]

        for tool_func in tools:
            if tool_func.__name__ in external_api_tools:
                # Verificar que tiene el decorator @rate_limit
                source = inspect.getsource(tool_func)
                assert '@rate_limit' in source, (
                    f"{tool_func.__name__} no usa @rate_limit"
                )
```

---

## ✅ CRITERIOS DE ACEPTACIÓN

Al finalizar la implementación, el sistema debe cumplir:

### Seguridad
- [ ] Ningún archivo de credenciales en el repositorio Git
- [ ] Ningún password hardcodeado en el código
- [ ] API keys NO se imprimen en logs
- [ ] Todas las configuraciones vienen de `.env`
- [ ] `.gitignore` correctamente configurado

### Funcionalidad
- [ ] `SecureConfig` carga y valida todas las variables
- [ ] `SecureConfig` lanza error claro si falta alguna variable
- [ ] Rate limiting funciona para todas las APIs
- [ ] Rate limiting respeta los límites configurados
- [ ] Decorator `@rate_limit` es aplicable a cualquier función

### Tests
- [ ] Todos los tests pasan al 100%
- [ ] Cobertura de tests >= 80%
- [ ] Tests validan casos exitosos y casos de error
- [ ] Tests son independientes y reproducibles

### Documentación
- [ ] `.env.example` con todas las variables documentadas
- [ ] README en `tests/Etapa_0/` explicando cada test
- [ ] Reporte de implementación en `docs/ETAPA_0_COMPLETADA.md`

---

## 📚 DOCUMENTACIÓN REQUERIDA

Al finalizar la etapa, crear:

### 1. `tests/Etapa_0/README.md`

```markdown
# Tests - ETAPA 0: Seguridad

## Descripción

Tests de seguridad para validar configuración segura, rate limiting y prevención de exposición de credenciales.

## Tests Implementados

### test_secure_config.py
- **Propósito:** Validar sistema de configuración centralizado
- **Casos:** 6 tests
- **Cobertura:** 95%

### test_rate_limiter.py
- **Propósito:** Validar rate limiting de APIs
- **Casos:** 5 tests
- **Cobertura:** 90%

### test_gitignore_validation.py
- **Propósito:** Validar que archivos sensibles no están trackeados
- **Casos:** 6 tests
- **Cobertura:** 100%

### test_security_integration.py
- **Propósito:** Tests de integración end-to-end de seguridad
- **Casos:** 4 tests
- **Cobertura:** 85%

## Ejecutar Tests

```bash
# Todos los tests de la etapa
pytest tests/Etapa_0/ -v

# Test específico
pytest tests/Etapa_0/test_secure_config.py -v

# Con cobertura
pytest tests/Etapa_0/ --cov=src/config --cov=src/middleware --cov-report=html
```

## Solución de Problemas

**Test falla: "Variables de entorno faltantes"**
- Copiar `.env.example` a `.env`
- Configurar todas las variables requeridas

**Test falla: "Archivos sensibles trackeados"**
- Ejecutar `scripts/rotate_credentials.py`
- Verificar .gitignore
```

### 2. `docs/ETAPA_0_COMPLETADA.md`

Template proporcionado en `.claude/CLAUDE.md`

---

## 🔍 CHECKLIST DE FINALIZACIÓN

Antes de marcar la etapa como completada, verificar:

- [ ] **Código Implementado**
  - [ ] `src/config/secure_config.py` creado y funcional
  - [ ] `src/middleware/rate_limiter.py` creado y funcional
  - [ ] `scripts/rotate_credentials.py` creado y probado
  - [ ] `scripts/validate_gitignore.py` creado y probado
  - [ ] `.env.example` creado con todas las variables
  - [ ] `src/database/db_config.py` actualizado sin passwords hardcodeados
  - [ ] `src/tool.py` actualizado con rate limiting y sin prints de API keys
  - [ ] `.gitignore` actualizado con todos los patrones necesarios

- [ ] **Seguridad Validada**
  - [ ] Credenciales rotadas en Google Cloud
  - [ ] Archivo `pro-core-466508-u7-76f56aed8c8b.json` eliminado del historial
  - [ ] No hay archivos sensibles trackeados en Git
  - [ ] Password de PostgreSQL en `.env` es fuerte y único
  - [ ] API keys no aparecen en logs

- [ ] **Tests**
  - [ ] `tests/Etapa_0/test_secure_config.py` - 6 tests pasando
  - [ ] `tests/Etapa_0/test_rate_limiter.py` - 5 tests pasando
  - [ ] `tests/Etapa_0/test_gitignore_validation.py` - 6 tests pasando
  - [ ] `tests/Etapa_0/test_security_integration.py` - 4 tests pasando
  - [ ] **TOTAL: 21/21 tests pasando (100%)**
  - [ ] Cobertura de código >= 80%
  - [ ] NO se modificaron tests para hacerlos pasar (salvo correcciones legítimas documentadas)

- [ ] **Documentación**
  - [ ] `tests/Etapa_0/README.md` creado
  - [ ] `docs/ETAPA_0_COMPLETADA.md` creado
  - [ ] `docs/PLAN_ESTRUCTURADO_IMPLEMENTACION.md` actualizado con checkmarks

- [ ] **Validación Manual**
  - [ ] Aplicación inicia correctamente con `.env` configurado
  - [ ] Aplicación falla con error claro si falta alguna variable
  - [ ] Rate limiting funciona en herramientas de Google Calendar
  - [ ] No hay warnings de seguridad en logs

---

## 🚀 COMANDOS DE EJECUCIÓN

### Configuración Inicial

```bash
# 1. Crear carpeta para tests
mkdir -p tests/Etapa_0

# 2. Copiar ejemplo de .env
cp .env.example .env

# 3. Editar .env con valores reales
# (Usar editor de texto)

# 4. Crear carpeta para credenciales
mkdir -p secrets

# 5. Mover credenciales a carpeta segura
mv pro-core-466508-u7-76f56aed8c8b.json secrets/credentials.json
```

### Rotación de Credenciales

```bash
# Ejecutar script de rotación
python scripts/rotate_credentials.py --file "pro-core-466508-u7-76f56aed8c8b.json"

# Validar que se eliminó del historial
git log --all --full-history -- "pro-core-466508-u7-76f56aed8c8b.json"

# (No debe mostrar nada)
```

### Validación de .gitignore

```bash
# Ejecutar script de validación
python scripts/validate_gitignore.py

# Ver archivos trackeados
git ls-files | grep -E "\.(json|env|log)$"

# (Solo debe mostrar package.json y archivos legítimos)
```

### Ejecución de Tests

```bash
# Instalar pytest si no está instalado
pip install pytest pytest-cov

# Ejecutar todos los tests de la etapa
pytest tests/Etapa_0/ -v

# Con cobertura
pytest tests/Etapa_0/ --cov=src/config --cov=src/middleware --cov-report=html

# Ver reporte de cobertura
# Abrir: htmlcov/index.html
```

### Validación de Integración

```bash
# Verificar que la aplicación inicia correctamente
python -c "from src.config.secure_config import get_config; get_config(); print('✅ Configuración OK')"

# Verificar que no hay prints de API keys
grep -r "print.*API_KEY" src/

# (No debe encontrar nada)

# Verificar que rate limiting está aplicado
grep -r "@rate_limit" src/tool.py

# (Debe encontrar decorators en herramientas)
```

---

## ⚠️ PROBLEMAS COMUNES Y SOLUCIONES

### Problema: "Variables de entorno faltantes"

**Causa:** No se configuró el archivo `.env`

**Solución:**
```bash
cp .env.example .env
# Editar .env con valores reales
```

### Problema: Tests fallan con "No such file or directory: .env"

**Causa:** Tests no encuentran el archivo .env

**Solución:**
```bash
# Opción 1: Crear .env en el directorio raíz
touch .env

# Opción 2: Usar variables de entorno en tests
export POSTGRES_PASSWORD="test_password"
# ... otras variables
pytest tests/Etapa_0/
```

### Problema: "git filter-branch" no elimina el archivo

**Causa:** Archivo aún está en alguna rama o tag

**Solución:**
```bash
# Eliminar de TODAS las ramas y tags
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch pro-core-466508-u7-76f56aed8c8b.json" \
  --prune-empty --tag-name-filter cat -- --all

# Forzar eliminación de reflog
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

### Problema: Rate limiter bloquea tests

**Causa:** Tests ejecutan muchas llamadas muy rápido

**Solución:**
```python
# En tests, usar mock o rate limiter más permisivo
from unittest.mock import patch

@patch('src.middleware.rate_limiter.RATE_LIMITERS')
def test_my_function(mock_limiters):
    # Test sin rate limiting
    result = my_function()
    assert result == expected
```

---

## 📊 MÉTRICAS DE ÉXITO

Al finalizar la etapa, reportar:

```markdown
## Métricas de ETAPA 0

### Tests
- Total: 21 tests
- Pasando: 21 (100%)
- Fallando: 0
- Cobertura: 87%

### Seguridad
- Credenciales expuestas: 0
- Passwords hardcodeados: 0
- API keys en logs: 0
- Archivos sensibles trackeados: 0

### Tiempo
- Estimado: 1-2 días
- Real: X días
- Variación: +/- X%

### Archivos
- Creados: 8
- Modificados: 4
- Eliminados del historial: 1
```

---

## 🎯 RESULTADO ESPERADO

Al completar esta etapa:

1. **Sistema 100% seguro** sin credenciales expuestas
2. **Configuración centralizada** en `secure_config.py`
3. **Rate limiting funcional** en todas las APIs externas
4. **Tests completos** validando seguridad
5. **Documentación clara** de implementación
6. **Base sólida** para continuar con ETAPA 1

---

**🚨 RECUERDA: Si un test falla, REPARAR EL CÓDIGO, NO EL TEST**

---

**Fecha de creación:** 27 de Enero de 2026
**Supervisor:** Claude Sonnet 4.5
**Próxima etapa:** ETAPA 1 - Identificación de Usuarios
