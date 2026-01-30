# ============================================================================
# Script para iniciar el proyecto completo con WhatsApp
# ============================================================================
#
# Inicia automáticamente:
# 1. Backend FastAPI (puerto 8000)
# 2. Servicio WhatsApp (puerto 3001)
#
# Uso: .\start_project_whatsapp.ps1
# ============================================================================

Write-Host ""
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "  🚀 INICIANDO CALENDAR AI AGENT - WHATSAPP" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

# Activar entorno virtual
$venvPath = ".\venv\Scripts\Activate.ps1"
if (Test-Path $venvPath) {
    Write-Host "✅ Activando entorno virtual..." -ForegroundColor Green
    & $venvPath
} else {
    Write-Host "⚠️  Entorno virtual no encontrado en $venvPath" -ForegroundColor Yellow
}

# Configurar encoding UTF-8
$env:PYTHONIOENCODING = 'utf-8'

Write-Host ""
Write-Host "🔧 Verificando configuración..." -ForegroundColor Yellow

# Verificar .env
if (Test-Path ".env") {
    Write-Host "  ✅ Archivo .env encontrado" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  Archivo .env no encontrado" -ForegroundColor Yellow
}

# Verificar .env de WhatsApp
if (Test-Path "whatsapp-service\.env") {
    Write-Host "  ✅ Archivo .env de WhatsApp encontrado" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  Archivo .env de WhatsApp no encontrado" -ForegroundColor Yellow
}

# Verificar PostgreSQL
$pgHost = $env:POSTGRES_HOST
if ($pgHost) {
    Write-Host "  ✅ PostgreSQL configurado: $pgHost" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  PostgreSQL no configurado (usará fallback)" -ForegroundColor Yellow
}

# Verificar Node.js
try {
    $nodeVersion = node --version
    Write-Host "  ✅ Node.js instalado: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "  ❌ Node.js no encontrado - Instala Node.js desde https://nodejs.org" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "  🌐 INICIANDO SERVICIOS" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

# Función para iniciar FastAPI en segundo plano
Write-Host "1️⃣  Iniciando Backend (FastAPI)..." -ForegroundColor Cyan
Write-Host "   Puerto: 8000" -ForegroundColor Gray
Write-Host "   URL: http://localhost:8000" -ForegroundColor Gray
Write-Host ""

$backendJob = Start-Job -ScriptBlock {
    param($projectPath)
    Set-Location $projectPath
    $env:PYTHONIOENCODING = 'utf-8'
    & ".\venv\Scripts\python.exe" -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
} -ArgumentList (Get-Location).Path

Start-Sleep -Seconds 5

# Verificar si el backend inició
$backendRunning = $false
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 2 -ErrorAction SilentlyContinue
    if ($response.StatusCode -eq 200) {
        $backendRunning = $true
        Write-Host "   ✅ Backend iniciado correctamente" -ForegroundColor Green
    }
} catch {
    Write-Host "   ⚠️  Backend iniciando... (puede tomar unos segundos)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "2️⃣  Iniciando Servicio WhatsApp..." -ForegroundColor Cyan
Write-Host "   Puerto: 3001" -ForegroundColor Gray
Write-Host "   URL Status: http://localhost:3001/status" -ForegroundColor Gray
Write-Host "   URL Health: http://localhost:3001/health" -ForegroundColor Gray
Write-Host ""

$whatsappJob = Start-Job -ScriptBlock {
    param($projectPath)
    Set-Location "$projectPath\whatsapp-service"
    node src/index.js
} -ArgumentList (Get-Location).Path

Start-Sleep -Seconds 5

# Verificar si WhatsApp inició
$whatsappRunning = $false
try {
    $response = Invoke-WebRequest -Uri "http://localhost:3001/health" -TimeoutSec 2 -ErrorAction SilentlyContinue
    if ($response.StatusCode -eq 200) {
        $whatsappRunning = $true
        Write-Host "   ✅ Servicio WhatsApp iniciado correctamente" -ForegroundColor Green
    }
} catch {
    Write-Host "   ⚠️  Servicio WhatsApp iniciando... (puede tomar unos segundos)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "================================================================================" -ForegroundColor Green
Write-Host "  ✅ SERVICIOS INICIADOS" -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "📋 URLs Disponibles:" -ForegroundColor Cyan
Write-Host "   🔧 Backend (FastAPI):     http://localhost:8000" -ForegroundColor White
Write-Host "   📄 API Docs (Swagger):    http://localhost:8000/docs" -ForegroundColor White
Write-Host "   📱 WhatsApp Status:       http://localhost:3001/status" -ForegroundColor White
Write-Host "   💚 WhatsApp Health:       http://localhost:3001/health" -ForegroundColor White
Write-Host ""
Write-Host "💡 Instrucciones:" -ForegroundColor Yellow
Write-Host "   1. Escanea el código QR que apareció arriba con WhatsApp" -ForegroundColor Gray
Write-Host "   2. Una vez conectado, envía mensajes desde WhatsApp" -ForegroundColor Gray
Write-Host "   3. El agente responderá automáticamente" -ForegroundColor Gray
Write-Host "   4. Presiona Ctrl+C para detener los servicios" -ForegroundColor Gray
Write-Host ""
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "📊 Monitoreando servicios (Presiona Ctrl+C para detener)..." -ForegroundColor Yellow
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

# Mantener el script corriendo y mostrar logs
try {
    while ($true) {
        # Verificar si los jobs están corriendo
        $backendStatus = Get-Job -Id $backendJob.Id
        $whatsappStatus = Get-Job -Id $whatsappJob.Id

        if ($backendStatus.State -eq "Failed" -or $backendStatus.State -eq "Stopped") {
            Write-Host ""
            Write-Host "❌ Backend se detuvo inesperadamente" -ForegroundColor Red
            Receive-Job -Id $backendJob.Id
            break
        }

        if ($whatsappStatus.State -eq "Failed" -or $whatsappStatus.State -eq "Stopped") {
            Write-Host ""
            Write-Host "❌ Servicio WhatsApp se detuvo inesperadamente" -ForegroundColor Red
            Receive-Job -Id $whatsappJob.Id
            break
        }

        # Mostrar logs del servicio WhatsApp cada 2 segundos
        $whatsappOutput = Receive-Job -Id $whatsappJob.Id
        if ($whatsappOutput) {
            Write-Host $whatsappOutput
        }

        Start-Sleep -Seconds 2
    }
} finally {
    # Cleanup al salir
    Write-Host ""
    Write-Host "================================================================================" -ForegroundColor Red
    Write-Host "  🛑 DETENIENDO SERVICIOS..." -ForegroundColor Red
    Write-Host "================================================================================" -ForegroundColor Red
    Write-Host ""

    Stop-Job -Id $backendJob.Id -ErrorAction SilentlyContinue
    Stop-Job -Id $whatsappJob.Id -ErrorAction SilentlyContinue
    Remove-Job -Id $backendJob.Id -ErrorAction SilentlyContinue
    Remove-Job -Id $whatsappJob.Id -ErrorAction SilentlyContinue

    Write-Host "✅ Servicios detenidos" -ForegroundColor Green
    Write-Host ""
}
