@echo off
echo ===============================================================================
echo TESTS ETAPA 7: HERRAMIENTAS MEDICAS AVANZADAS
echo ===============================================================================
echo.

REM Configurar PYTHONPATH
set PYTHONPATH=%CD%

echo [INFO] Ejecutando tests de Etapa 7...
echo.

REM Ejecutar pytest con verbose
python -m pytest tests/Etapa_7/ -v --tb=short

echo.
echo ===============================================================================
echo FIN DE LOS TESTS
echo ===============================================================================

pause
