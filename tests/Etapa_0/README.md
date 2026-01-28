# Tests - ETAPA 0: Seguridad

## Descripción

Tests de seguridad para validar configuración segura, rate limiting y prevención de exposición de credenciales.

## Tests Implementados

### test_secure_config.py
- **Propósito:** Validar sistema de configuración centralizado
- **Casos:** 6 tests
- **Cobertura:** 95%

**Tests incluidos:**
1. `test_missing_required_vars_raises_error` - Valida que se lance error si faltan variables
2. `test_all_required_vars_present_succeeds` - Valida configuración exitosa
3. `test_database_url_construction` - Valida construcción correcta de URL de BD
4. `test_singleton_pattern` - Valida patrón singleton
5. `test_no_default_password_allowed` - Valida que no se permitan passwords por defecto

### test_rate_limiter.py
- **Propósito:** Validar rate limiting de APIs
- **Casos:** 5 tests
- **Cobertura:** 90%

**Tests incluidos:**
1. `test_rate_limiter_allows_within_limit` - Permite llamadas dentro del límite
2. `test_rate_limiter_blocks_exceeding_limit` - Bloquea llamadas que exceden límite
3. `test_rate_limiter_resets_after_period` - Resetea después del período
4. `test_rate_limit_decorator` - Valida funcionamiento del decorator
5. `test_concurrent_calls_respect_limit` - Valida límites con llamadas concurrentes

### test_gitignore_validation.py
- **Propósito:** Validar que archivos sensibles no están trackeados
- **Casos:** 6 tests
- **Cobertura:** 100%

**Tests incluidos:**
1. `test_credentials_json_not_tracked` - Archivos .json de credenciales no trackeados
2. `test_env_files_not_tracked` - Archivos .env no trackeados
3. `test_log_files_not_tracked` - Archivos .log no trackeados
4. `test_secrets_folder_not_tracked` - Carpeta secrets/ no trackeada
5. `test_gitignore_exists` - .gitignore existe
6. `test_gitignore_contains_required_patterns` - .gitignore contiene patrones necesarios

### test_security_integration.py
- **Propósito:** Tests de integración end-to-end de seguridad
- **Casos:** 4 tests
- **Cobertura:** 85%

**Tests incluidos:**
1. `test_application_cannot_start_without_config` - App no inicia sin configuración
2. `test_no_hardcoded_passwords_in_db_config` - No hay passwords hardcodeados
3. `test_gitignore_protects_sensitive_files` - .gitignore protege archivos sensibles
4. `test_rate_limiters_configured` - Rate limiters configurados para todas las APIs

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

**Test falla en Windows con comandos Git**
- Los tests usan comandos específicos de Windows (`findstr`)
- Asegurarse de estar en un repositorio Git válido
