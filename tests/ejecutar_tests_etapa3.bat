@echo off
REM Script para ejecutar tests ETAPA 3

cd /d "%~dp0"

echo ============================================
echo EJECUTANDO TESTS DE ETAPA 3
echo ============================================

call venv\Scripts\activate.bat

python ejecutar_tests_etapa3.py

pause
