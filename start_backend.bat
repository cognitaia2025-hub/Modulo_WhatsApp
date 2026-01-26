@echo off
REM ============================================================================
REM Script para iniciar el Backend (FastAPI)
REM ============================================================================

echo.
echo ================================================================================
echo   Backend - FastAPI (Puerto 8000)
echo ================================================================================
echo.

REM Activar entorno virtual
call venv\Scripts\activate.bat

REM Configurar encoding
set PYTHONIOENCODING=utf-8

echo Iniciando servidor FastAPI...
echo URL: http://localhost:8000
echo Docs: http://localhost:8000/docs
echo.
echo Presiona Ctrl+C para detener
echo.

python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
