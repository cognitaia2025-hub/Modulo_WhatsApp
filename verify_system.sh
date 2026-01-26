#!/bin/bash

# ============================================================
# Script de Verificación Rápida del Sistema
# Agente WhatsApp Calendar - Post-Installation Check
# ============================================================

echo "========================================================"
echo "  🔍 VERIFICACIÓN RÁPIDA DEL SISTEMA"
echo "========================================================"
echo ""

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Contador de tests
PASS=0
FAIL=0

# Función para print con color
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ PASS${NC} - $2"
        ((PASS++))
    else
        echo -e "${RED}❌ FAIL${NC} - $2"
        ((FAIL++))
    fi
}

# Test 1: Docker está corriendo
echo "1️⃣  Verificando Docker..."
docker ps > /dev/null 2>&1
print_status $? "Docker está corriendo"

# Test 2: Contenedor de PostgreSQL está activo
echo "2️⃣  Verificando contenedor PostgreSQL..."
docker ps | grep -q agente-whatsapp-db
print_status $? "Contenedor agente-whatsapp-db está activo"

# Test 3: PostgreSQL acepta conexiones
echo "3️⃣  Verificando PostgreSQL..."
docker exec agente-whatsapp-db pg_isready -U admin -d agente_whatsapp > /dev/null 2>&1
print_status $? "PostgreSQL acepta conexiones"

# Test 4: Extensión pgvector instalada
echo "4️⃣  Verificando pgvector..."
docker exec agente-whatsapp-db psql -U admin -d agente_whatsapp -c "SELECT extname FROM pg_extension WHERE extname = 'vector';" | grep -q vector
print_status $? "Extensión pgvector instalada"

# Test 5: Tabla herramientas_disponibles existe
echo "5️⃣  Verificando tabla de herramientas..."
docker exec agente-whatsapp-db psql -U admin -d agente_whatsapp -c "\dt herramientas_disponibles" | grep -q herramientas_disponibles
print_status $? "Tabla herramientas_disponibles existe"

# Test 6: Tabla memoria_episodica existe
echo "6️⃣  Verificando tabla de memoria..."
docker exec agente-whatsapp-db psql -U admin -d agente_whatsapp -c "\dt memoria_episodica" | grep -q memoria_episodica
print_status $? "Tabla memoria_episodica existe"

# Test 7: Herramientas insertadas
echo "7️⃣  Verificando herramientas insertadas..."
COUNT=$(docker exec agente-whatsapp-db psql -U admin -d agente_whatsapp -t -c "SELECT COUNT(*) FROM herramientas_disponibles;" | tr -d ' ')
if [ "$COUNT" -eq 5 ]; then
    print_status 0 "5 herramientas insertadas"
else
    print_status 1 "Herramientas insertadas ($COUNT/5)"
fi

# Test 8: Archivo .env existe
echo "8️⃣  Verificando archivo .env..."
[ -f .env ]
print_status $? "Archivo .env existe"

# Test 9: Python puede importar módulos
echo "9️⃣  Verificando módulos Python..."
python -c "import psycopg2; import pendulum; import sentence_transformers" > /dev/null 2>&1
print_status $? "Módulos Python disponibles"

# Test 10: Tests de infraestructura existen
echo "🔟 Verificando archivos de tests..."
[ -f test_infrastructure.py ] && [ -f test_components.py ]
print_status $? "Archivos de tests disponibles"

# Resumen
echo ""
echo "========================================================"
echo "  📊 RESUMEN"
echo "========================================================"
TOTAL=$((PASS + FAIL))
echo -e "Tests ejecutados: ${TOTAL}"
echo -e "${GREEN}Exitosos: ${PASS}${NC}"
echo -e "${RED}Fallidos: ${FAIL}${NC}"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}🎉 ¡TODOS LOS TESTS PASARON!${NC}"
    echo "✅ El sistema está listo para uso"
    echo ""
    echo "Próximos pasos:"
    echo "  1. Ejecutar tests completos: python test_infrastructure.py"
    echo "  2. Ejecutar tests de componentes: python test_components.py"
    echo "  3. Leer documentación: cat REPORTE_EJECUCION_TESTS.md"
    exit 0
else
    echo -e "${RED}⚠️  ALGUNOS TESTS FALLARON${NC}"
    echo "❌ Revisar logs y configuración"
    echo ""
    echo "Comandos útiles:"
    echo "  - Ver logs: docker logs agente-whatsapp-db"
    echo "  - Reiniciar: docker-compose restart postgres"
    echo "  - Consultar BD: docker exec -it agente-whatsapp-db psql -U admin -d agente_whatsapp"
    exit 1
fi
