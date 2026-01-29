@echo off
echo ========================================
echo ETAPA 1: Sistema de Identificacion
echo ========================================
echo.

REM Activar entorno virtual si existe
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    echo ✓ Entorno virtual activado
) else (
    echo ⚠ Entorno virtual no encontrado, usando Python global
)

echo.
echo Ejecutando proceso completo de ETAPA 1...
echo.

python ejecutar_etapa1_completa.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo ✅ ETAPA 1 COMPLETADA CON EXITO
    echo ========================================
) else (
    echo.
    echo ========================================
    echo ❌ ERROR EN ETAPA 1
    echo ========================================
)

echo.
pause
