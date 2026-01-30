@echo off
REM ============================================================================
REM Script para iniciar el Frontend (Streamlit)
REM ============================================================================

echo.
echo ================================================================================
echo   Frontend - Streamlit (Puerto 8501)
echo ================================================================================
echo.

REM Activar entorno virtual
call venv\Scripts\activate.bat

REM Configurar encoding
set PYTHONIOENCODING=utf-8

echo Iniciando interfaz Streamlit...
echo URL: http://localhost:8501
echo.
echo Presiona Ctrl+C para detener
echo.

python -m streamlit run app_ui.py --server.port 8501
