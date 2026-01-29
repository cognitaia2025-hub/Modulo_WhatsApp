@echo off
REM Script para ejecutar migración de ETAPA 1

echo ========================================
echo MIGRACION ETAPA 1: Identificacion de Usuarios
echo ========================================
echo.

REM Configurar variables
set PGPASSWORD=postgres
set PGHOST=localhost
set PGPORT=5434
set PGUSER=postgres
set PGDATABASE=agente_whatsapp

echo Ejecutando migracion SQL...
psql -h %PGHOST% -p %PGPORT% -U %PGUSER% -d %PGDATABASE% -f sql\migrate_etapa_1_identificacion.sql

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo MIGRACION COMPLETADA EXITOSAMENTE
    echo ========================================
) else (
    echo.
    echo ========================================
    echo ERROR EN MIGRACION
    echo ========================================
)

pause
