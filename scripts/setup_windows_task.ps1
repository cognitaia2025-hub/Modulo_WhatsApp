# Script para configurar Task Scheduler en Windows
# Ejecuta limpieza de números temporales cada hora

$ProjectDir = "C:\Users\Salva\OneDrive\Escritorio\agent_calendar\Calender-agent"
$PythonExe = "$ProjectDir\venv\Scripts\python.exe"
$ScriptPath = "$ProjectDir\scripts\cleanup_numeros_temporales.py"
$LogDir = "$ProjectDir\logs"

# Crear directorio de logs si no existe
if (!(Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force
    Write-Host "✅ Directorio de logs creado: $LogDir"
}

# Configurar acción
$Action = New-ScheduledTaskAction -Execute $PythonExe -Argument $ScriptPath -WorkingDirectory $ProjectDir

# Configurar trigger (cada hora)
$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Hours 1) -RepetitionDuration ([TimeSpan]::MaxValue)

# Configurar principal (usuario actual)
$Principal = New-ScheduledTaskPrincipal -UserId "$env:USERNAME" -LogonType S4U -RunLevel Highest

# Configurar settings
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

# Registrar tarea
try {
    Register-ScheduledTask `
        -TaskName "CleanupNumerosTemporales" `
        -Action $Action `
        -Trigger $Trigger `
        -Principal $Principal `
        -Settings $Settings `
        -Description "Limpieza horaria de números temporales expirados para doctores" `
        -Force

    Write-Host ""
    Write-Host "✅ Tarea programada creada exitosamente" -ForegroundColor Green
    Write-Host ""
    Write-Host "📋 Detalles de la tarea:" -ForegroundColor Cyan
    Write-Host "   • Nombre: CleanupNumerosTemporales"
    Write-Host "   • Frecuencia: Cada hora"
    Write-Host "   • Script: $ScriptPath"
    Write-Host "   • Python: $PythonExe"
    Write-Host ""
    Write-Host "🔍 Para verificar la tarea:" -ForegroundColor Yellow
    Write-Host "   Get-ScheduledTask -TaskName 'CleanupNumerosTemporales'"
    Write-Host ""
    Write-Host "🗑️  Para eliminar la tarea:" -ForegroundColor Yellow
    Write-Host "   Unregister-ScheduledTask -TaskName 'CleanupNumerosTemporales' -Confirm:`$false"
    Write-Host ""
}
catch {
    Write-Host "❌ Error al crear la tarea programada: $_" -ForegroundColor Red
    exit 1
}
