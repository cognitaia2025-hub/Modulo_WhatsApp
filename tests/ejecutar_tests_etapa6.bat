@echo off
REM =========================================
REM EJECUTAR TESTS ETAPA 6
REM =========================================

echo.
echo ========================================
echo EJECUTANDO TESTS ETAPA 6
echo ========================================
echo.

set PYTHONPATH=%CD%

python ejecutar_tests_etapa6.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo TESTS COMPLETADOS EXITOSAMENTE
    echo ========================================
) else (
    echo.
    echo ========================================
    echo ERROR EN TESTS
    echo ========================================
)

echo.
pause
