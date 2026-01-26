#!/bin/bash
# Script de inicio rápido para tests del sistema

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║                                                                      ║"
echo "║          🚀 SISTEMA DE TESTS - MÓDULO WHATSAPP CALENDAR             ║"
echo "║                                                                      ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Función para mostrar menú
show_menu() {
    echo ""
    echo "Selecciona una opción:"
    echo ""
    echo "  1) 🧪 Ejecutar TODOS los tests (15-20 min)"
    echo "  2) ⚡ Ejecutar solo tests CRÍTICOS (8-10 min)"
    echo "  3) 📊 Ejecutar tests con logs VERBOSE"
    echo "  4) 🔍 Ejecutar test específico"
    echo "  5) 📈 Ver último reporte de tests"
    echo "  6) 🗑️  Limpiar reportes antiguos"
    echo "  7) 🔧 Verificar prerequisitos"
    echo "  8) 🚀 Iniciar backend (app.py)"
    echo "  0) ❌ Salir"
    echo ""
    read -p "Opción: " option
    echo ""
}

# Función para verificar prerequisitos
check_prerequisites() {
    echo -e "${YELLOW}🔍 Verificando prerequisitos...${NC}"
    echo ""
    
    # Verificar Python
    if command -v python &> /dev/null; then
        PYTHON_VERSION=$(python --version 2>&1)
        echo -e "${GREEN}✅ Python encontrado: $PYTHON_VERSION${NC}"
    else
        echo -e "${RED}❌ Python no encontrado${NC}"
        return 1
    fi
    
    # Verificar que el backend está corriendo
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Backend corriendo en http://localhost:8000${NC}"
    else
        echo -e "${RED}❌ Backend NO está corriendo${NC}"
        echo -e "${YELLOW}   Ejecuta: python app.py${NC}"
    fi
    
    # Verificar PostgreSQL
    if docker ps | grep postgres > /dev/null 2>&1; then
        echo -e "${GREEN}✅ PostgreSQL corriendo (Docker)${NC}"
    else
        echo -e "${RED}❌ PostgreSQL NO está corriendo${NC}"
        echo -e "${YELLOW}   Ejecuta: docker-compose up -d postgres${NC}"
    fi
    
    # Verificar .env
    if [ -f .env ]; then
        echo -e "${GREEN}✅ Archivo .env encontrado${NC}"
        
        # Verificar credenciales clave
        if grep -q "DEEPSEEK_API_KEY=sk-" .env; then
            echo -e "${GREEN}   ✅ DEEPSEEK_API_KEY configurado${NC}"
        else
            echo -e "${RED}   ❌ DEEPSEEK_API_KEY no configurado${NC}"
        fi
        
        if grep -q "ANTHROPIC_API_KEY=sk-" .env; then
            echo -e "${GREEN}   ✅ ANTHROPIC_API_KEY configurado${NC}"
        else
            echo -e "${RED}   ❌ ANTHROPIC_API_KEY no configurado${NC}"
        fi
        
        if grep -q "DATABASE_URL=postgresql://" .env; then
            echo -e "${GREEN}   ✅ DATABASE_URL configurado${NC}"
        else
            echo -e "${RED}   ❌ DATABASE_URL no configurado${NC}"
        fi
    else
        echo -e "${RED}❌ Archivo .env no encontrado${NC}"
    fi
    
    echo ""
}

# Función para ejecutar todos los tests
run_all_tests() {
    echo -e "${GREEN}🧪 Ejecutando TODOS los tests...${NC}"
    echo ""
    python run_all_integration_tests.py
}

# Función para ejecutar tests críticos
run_critical_tests() {
    echo -e "${GREEN}⚡ Ejecutando tests CRÍTICOS...${NC}"
    echo ""
    python run_all_integration_tests.py --fast
}

# Función para ejecutar tests con verbose
run_verbose_tests() {
    echo -e "${GREEN}📊 Ejecutando tests con logs VERBOSE...${NC}"
    echo ""
    python run_all_integration_tests.py --verbose
}

# Función para ejecutar test específico
run_specific_test() {
    echo "Tests disponibles:"
    echo ""
    echo "  01) Listar Inicial"
    echo "  02) Crear Evento"
    echo "  03) Verificar Creación"
    echo "  04) Buscar Evento"
    echo "  05) Crear Segundo Evento"
    echo "  06) Actualizar Evento (NUEVO) ⭐"
    echo "  07) Verificar Actualización"
    echo "  08) Buscar Rango"
    echo "  09) Eliminar Evento (MEJORADO) ⭐"
    echo "  10) Verificar Eliminación"
    echo "  11) Sin Herramienta"
    echo "  12) Múltiples Herramientas"
    echo "  13) Eliminar con Contexto (NUEVO) ⭐"
    echo "  14) Memoria Persistente (NUEVO) ⭐⭐⭐"
    echo ""
    read -p "Número de test (01-14): " test_num
    
    test_file="integration_tests/${test_num}_test_*.py"
    
    if ls $test_file 1> /dev/null 2>&1; then
        echo -e "${GREEN}▶️  Ejecutando test ${test_num}...${NC}"
        echo ""
        python $test_file
    else
        echo -e "${RED}❌ Test no encontrado: ${test_num}${NC}"
    fi
}

# Función para ver último reporte
view_last_report() {
    echo -e "${GREEN}📈 Último reporte de tests:${NC}"
    echo ""
    
    last_report=$(ls -t integration_tests/reports/test_report_*.json 2>/dev/null | head -1)
    
    if [ -f "$last_report" ]; then
        echo "Archivo: $last_report"
        echo ""
        
        # Si tiene jq instalado, mostrar resumen bonito
        if command -v jq &> /dev/null; then
            echo "Resumen:"
            jq '.summary' "$last_report"
            echo ""
            echo "Tests:"
            jq -r '.results[] | "\(.id) - \(.name): \(.status) (\(.duration)s)"' "$last_report"
        else
            # Si no tiene jq, mostrar raw
            cat "$last_report"
        fi
    else
        echo -e "${YELLOW}⚠️  No se encontraron reportes${NC}"
        echo "   Ejecuta tests primero"
    fi
    
    echo ""
}

# Función para limpiar reportes antiguos
clean_old_reports() {
    echo -e "${YELLOW}🗑️  Limpiando reportes antiguos...${NC}"
    
    report_count=$(ls integration_tests/reports/test_report_*.json 2>/dev/null | wc -l)
    
    if [ $report_count -gt 0 ]; then
        echo "Se encontraron $report_count reportes"
        read -p "¿Deseas eliminarlos? (s/n): " confirm
        
        if [ "$confirm" == "s" ] || [ "$confirm" == "S" ]; then
            rm integration_tests/reports/test_report_*.json
            echo -e "${GREEN}✅ Reportes eliminados${NC}"
        else
            echo "Operación cancelada"
        fi
    else
        echo "No hay reportes para eliminar"
    fi
    
    echo ""
}

# Función para iniciar backend
start_backend() {
    echo -e "${GREEN}🚀 Iniciando backend...${NC}"
    echo ""
    
    # Verificar que no esté corriendo ya
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  Backend ya está corriendo${NC}"
        read -p "¿Deseas reiniciarlo? (s/n): " confirm
        
        if [ "$confirm" != "s" ] && [ "$confirm" != "S" ]; then
            return
        fi
        
        # Buscar y matar proceso
        echo "Matando proceso anterior..."
        pkill -f "python app.py"
        sleep 2
    fi
    
    echo "Iniciando app.py..."
    python app.py &
    
    echo ""
    echo -e "${GREEN}✅ Backend iniciado${NC}"
    echo "   Accede a: http://localhost:8000"
    echo "   Health check: http://localhost:8000/health"
    echo ""
}

# Loop principal
while true; do
    show_menu
    
    case $option in
        1)
            run_all_tests
            read -p "Presiona Enter para continuar..."
            ;;
        2)
            run_critical_tests
            read -p "Presiona Enter para continuar..."
            ;;
        3)
            run_verbose_tests
            read -p "Presiona Enter para continuar..."
            ;;
        4)
            run_specific_test
            read -p "Presiona Enter para continuar..."
            ;;
        5)
            view_last_report
            read -p "Presiona Enter para continuar..."
            ;;
        6)
            clean_old_reports
            read -p "Presiona Enter para continuar..."
            ;;
        7)
            check_prerequisites
            read -p "Presiona Enter para continuar..."
            ;;
        8)
            start_backend
            read -p "Presiona Enter para continuar..."
            ;;
        0)
            echo "¡Hasta luego! 👋"
            exit 0
            ;;
        *)
            echo -e "${RED}❌ Opción inválida${NC}"
            read -p "Presiona Enter para continuar..."
            ;;
    esac
done
