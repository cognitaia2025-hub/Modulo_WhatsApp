# ============================================================================
# Script para iniciar el proyecto completo
# ============================================================================
# 
# Inicia automáticamente:
# 1. Backend FastAPI (puerto 8000)
# 2. Frontend Streamlit (puerto 8501)
# 
# Uso: .\start_project.ps1
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

# Verificar PostgreSQL
$pgHost = $env:POSTGRES_HOST
if ($pgHost) {
    Write-Host "  ✅ PostgreSQL configurado: $pgHost" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  PostgreSQL no configurado (usará fallback)" -ForegroundColor Yellow
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

Start-Sleep -Seconds 3

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
Write-Host "2️⃣  Iniciando Frontend (Streamlit)..." -ForegroundColor Cyan
Write-Host "   Puerto: 8501" -ForegroundColor Gray
Write-Host "   URL: http://localhost:8501" -ForegroundColor Gray
Write-Host ""

$frontendJob = Start-Job -ScriptBlock {
    param($projectPath)
    Set-Location $projectPath
    $env:PYTHONIOENCODING = 'utf-8'
    & ".\venv\Scripts\python.exe" -m streamlit run app_ui.py --server.port 8501 --server.headless true
} -ArgumentList (Get-Location).Path

Start-Sleep -Seconds 5

Write-Host ""
Write-Host "================================================================================" -ForegroundColor Green
Write-Host "  ✅ SERVICIOS INICIADOS" -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "📋 URLs Disponibles:" -ForegroundColor Cyan
Write-Host "   🌐 Frontend (Streamlit):  http://localhost:8501" -ForegroundColor White
Write-Host "   🔧 Backend (FastAPI):     http://localhost:8000" -ForegroundColor White
Write-Host "   📄 API Docs (Swagger):    http://localhost:8000/docs" -ForegroundColor White
Write-Host ""
Write-Host "💡 Consejos:" -ForegroundColor Yellow
Write-Host "   - Abre http://localhost:8501 en tu navegador para usar el chat" -ForegroundColor Gray
Write-Host "   - Presiona Ctrl+C para detener los servicios" -ForegroundColor Gray
Write-Host "   - Los logs aparecerán en tiempo real abajo" -ForegroundColor Gray
Write-Host ""
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

# Abrir navegador automáticamente
Write-Host "🌐 Abriendo navegador..." -ForegroundColor Cyan
Start-Sleep -Seconds 2
Start-Process "http://localhost:8501"

Write-Host ""
Write-Host "📊 Monitoreando servicios (Presiona Ctrl+C para detener)..." -ForegroundColor Yellow
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

# Mantener el script corriendo y mostrar logs
try {
    while ($true) {
        # Verificar si los jobs están corriendo
        $backendStatus = Get-Job -Id $backendJob.Id
        $frontendStatus = Get-Job -Id $frontendJob.Id
        
        if ($backendStatus.State -eq "Failed" -or $backendStatus.State -eq "Stopped") {
            Write-Host ""
            Write-Host "❌ Backend se detuvo inesperadamente" -ForegroundColor Red
            Receive-Job -Id $backendJob.Id
            break
        }
        
        if ($frontendStatus.State -eq "Failed" -or $frontendStatus.State -eq "Stopped") {
            Write-Host ""
            Write-Host "❌ Frontend se detuvo inesperadamente" -ForegroundColor Red
            Receive-Job -Id $frontendJob.Id
            break
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
    Stop-Job -Id $frontendJob.Id -ErrorAction SilentlyContinue
    Remove-Job -Id $backendJob.Id -ErrorAction SilentlyContinue
    Remove-Job -Id $frontendJob.Id -ErrorAction SilentlyContinue
    
    Write-Host "✅ Servicios detenidos" -ForegroundColor Green
    Write-Host ""
}
