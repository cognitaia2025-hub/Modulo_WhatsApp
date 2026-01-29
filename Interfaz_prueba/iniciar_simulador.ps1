# ============================================================================
# Simulador Sistema Médico WhatsApp
# ============================================================================

Write-Host ""
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "  🏥 SIMULADOR SISTEMA MÉDICO WHATSAPP" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

# Verificar backend médico
Write-Host "🔍 Verificando backend médico..." -ForegroundColor Yellow

try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 3 -ErrorAction SilentlyContinue
    if ($response.StatusCode -eq 200) {
        Write-Host "✅ Backend médico CONECTADO (puerto 8000)" -ForegroundColor Green
        $backendStatus = "CONECTADO"
    }
} catch {
    Write-Host "❌ Backend médico NO DETECTADO" -ForegroundColor Red
    Write-Host ""
    Write-Host "💡 Para iniciar el sistema completo:" -ForegroundColor Yellow
    Write-Host "   1. Abre PowerShell en la raíz del proyecto" -ForegroundColor Gray
    Write-Host "   2. Ejecuta: .\start_project_whatsapp.ps1" -ForegroundColor Gray
    Write-Host ""
    Write-Host "⚠️  El simulador funcionará en modo offline hasta conectar" -ForegroundColor Yellow
    $backendStatus = "DESCONECTADO"
}

Write-Host ""

# Obtener ruta absoluta del archivo HTML
$htmlPath = Join-Path $PSScriptRoot "index.html"
$htmlUri = "file:///$($htmlPath -replace '\\\\', '/')"

Write-Host "🌐 Iniciando simulador..." -ForegroundColor Cyan
Write-Host "📱 Ruta: $htmlPath" -ForegroundColor Gray

# Abrir en navegador
Start-Process $htmlUri

Write-Host ""
Write-Host "================================================================================" -ForegroundColor Green
Write-Host "  ✅ SIMULADOR INICIADO" -ForegroundColor Green  
Write-Host "================================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "📊 ESTADO DEL SISTEMA:" -ForegroundColor Cyan
Write-Host "   🔹 Backend médico: $backendStatus" -ForegroundColor White
Write-Host "   🔹 Puerto esperado: 8000" -ForegroundColor White
Write-Host "   🔹 Endpoint: /api/whatsapp-agent/message" -ForegroundColor White
Write-Host ""
Write-Host "📋 INSTRUCCIONES DE USO:" -ForegroundColor Cyan
Write-Host "   1. 👩‍⚕️ Selecciona un tipo de usuario en el panel izquierdo" -ForegroundColor White
Write-Host "   2. 💬 Escribe mensajes como si fueras ese usuario" -ForegroundColor White
Write-Host "   3. 🤖 Observa las respuestas del sistema médico" -ForegroundColor White
Write-Host ""
Write-Host "🎯 CASOS DE PRUEBA RECOMENDADOS:" -ForegroundColor Yellow
Write-Host ""
Write-Host "   📱 COMO PACIENTE:" -ForegroundColor Magenta
Write-Host "     • 'Hola, necesito agendar una cita'" -ForegroundColor Gray
Write-Host "     • '¿Cuándo tienen disponibilidad?'" -ForegroundColor Gray
Write-Host "     • 'Quiero cancelar mi cita del martes'" -ForegroundColor Gray
Write-Host ""
Write-Host "   👨‍⚕️ COMO DOCTOR:" -ForegroundColor Blue
Write-Host "     • '¿Qué citas tengo hoy?'" -ForegroundColor Gray
Write-Host "     • 'Buscar paciente María López'" -ForegroundColor Gray
Write-Host "     • 'Dame un reporte de esta semana'" -ForegroundColor Gray
Write-Host ""
Write-Host "   ⚙️ COMO ADMINISTRADOR:" -ForegroundColor DarkYellow
Write-Host "     • 'Estadísticas de citas de hoy'" -ForegroundColor Gray
Write-Host "     • '¿Cuántos pacientes atendimos?'" -ForegroundColor Gray
Write-Host "     • 'Balance de carga de doctores'" -ForegroundColor Gray
Write-Host ""
Write-Host "🔧 FUNCIONES AVANZADAS:" -ForegroundColor Cyan
Write-Host "   🕐 Simulador temporal: Prueba citas en fechas específicas" -ForegroundColor White
Write-Host "   ⚡ Quick Replies: Mensajes predefinidos por tipo de usuario" -ForegroundColor White
Write-Host "   👥 Editor de usuarios: Personaliza pacientes y doctores" -ForegroundColor White
Write-Host "   📡 Monitor de conexión: Estado del backend en tiempo real" -ForegroundColor White
Write-Host ""
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

if ($backendStatus -eq "DESCONECTADO") {
    Write-Host "💡 RECORDATORIO: Para probar todas las funcionalidades," -ForegroundColor Yellow
    Write-Host "   ejecuta primero el backend médico completo." -ForegroundColor Yellow
    Write-Host ""
}

Write-Host "✨ ¡El simulador está listo en tu navegador!" -ForegroundColor Green
Write-Host "   Presiona cualquier tecla para cerrar este mensaje..." -ForegroundColor Gray
Write-Host ""

# Esperar tecla
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")