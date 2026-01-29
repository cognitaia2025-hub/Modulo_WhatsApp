@echo off
REM Script para ejecutar tests de ETAPA 2

cd /d "%~dp0"

echo ============================================
echo EJECUTANDO TESTS DE ETAPA 2
echo ============================================

REM Activar virtual environment
call venv\Scripts\activate.bat

REM Ejecutar tests
python -m pytest tests\Etapa_2\ -v --tb=short

REM Verificar resultado
if %ERRORLEVEL% EQU 0 (
    echo.
    echo ============================================
    echo TESTS COMPLETADOS EXITOSAMENTE
    echo ============================================
) else (
    echo.
    echo ============================================
    echo ALGUNOS TESTS FALLARON
    echo ============================================
)

pause
