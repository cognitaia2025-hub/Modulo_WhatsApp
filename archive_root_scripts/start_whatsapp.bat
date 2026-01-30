@echo off
chcp 65001 > nul
cls

echo ================================================================================
echo   WhatsApp Service (Puerto 3001)
echo ================================================================================
echo.
echo Iniciando servicio de WhatsApp...
echo URL Status: http://localhost:3001/status
echo URL Health: http://localhost:3001/health
echo.
echo Presiona Ctrl+C para detener
echo.

cd whatsapp-service
node src/index.js
