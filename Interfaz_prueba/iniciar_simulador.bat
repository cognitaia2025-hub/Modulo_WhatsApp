@echo off
chcp 65001 > nul
cls

echo ================================================================================
echo   🏥 SIMULADOR SISTEMA MÉDICO WHATSAPP
echo ================================================================================
echo.
echo 🔍 Verificando backend médico...

REM Verificar si el backend está corriendo
curl -s http://localhost:8000/health > nul 2>&1
if %errorlevel%==0 (
    echo ✅ Backend médico detectado en puerto 8000
) else (
    echo ❌ Backend médico NO detectado
    echo.
    echo 💡 Para iniciar el backend, ejecuta desde la raíz del proyecto:
    echo    .\start_project_whatsapp.ps1
    echo.
    echo ⚠️  El simulador funcionará en modo offline hasta que conectes el backend
)

echo.
echo 🌐 Abriendo simulador en el navegador...
echo 📱 URL: file://%~dp0index.html
echo.

REM Abrir en el navegador predeterminado
start "" "%~dp0index.html"

echo ================================================================================
echo   📋 INSTRUCCIONES DE USO:
echo ================================================================================
echo.
echo 1. 👩‍⚕️ Selecciona un usuario (Paciente/Doctor/Admin)
echo 2. 💬 Escribe un mensaje en el chat
echo 3. 🤖 El sistema médico responderá automáticamente
echo.
echo 🎯 CASOS DE PRUEBA SUGERIDOS:
echo    • Como paciente: "Necesito una cita"
echo    • Como doctor: "¿Qué citas tengo hoy?"
echo    • Como admin: "Reporte de esta semana"
echo.
echo 🔧 FUNCIONES AVANZADAS:
echo    • Simulador de fecha/hora para pruebas temporales
echo    • Quick replies con mensajes predefinidos
echo    • Editor de usuarios para personalizar
echo.
echo ✨ ¡El simulador está listo! Presiona cualquier tecla para continuar...
pause > nul