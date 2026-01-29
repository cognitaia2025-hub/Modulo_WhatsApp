@echo off
REM Script para ejecutar migración ETAPA 3

cd /d "%~dp0"

echo ============================================
echo EJECUTANDO MIGRACION ETAPA 3
echo ============================================

call venv\Scripts\activate.bat

python ejecutar_migracion_etapa3.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ============================================
    echo MIGRACION COMPLETADA EXITOSAMENTE
    echo ============================================
) else (
    echo.
    echo ============================================
    echo ERROR EN MIGRACION
    echo ============================================
)

pause
