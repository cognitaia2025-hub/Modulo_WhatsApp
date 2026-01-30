@echo off
cls
echo ================================================================================
echo   🏥 SIMULADOR MÉDICO WHATSAPP - INTERFAZ WEB
echo ================================================================================
echo.
echo Iniciando servidor web del simulador...
echo URL: http://localhost:3002
echo.
echo Presiona Ctrl+C para detener
echo.

cd Interfaz_prueba
python -m http.server 3002