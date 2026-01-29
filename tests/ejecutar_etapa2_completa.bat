@echo off
echo ========================================
echo ETAPA 2: Sistema de Turnos Automático
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
echo Ejecutando proceso completo de ETAPA 2...
echo.

python ejecutar_etapa2_completa.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo ✅ ETAPA 2 COMPLETADA CON EXITO
    echo ========================================
) else (
    echo.
    echo ========================================
    echo ❌ ERROR EN ETAPA 2
    echo ========================================
)

echo.
pause
