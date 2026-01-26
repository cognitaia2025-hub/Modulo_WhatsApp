# ⚡ Comandos Rápidos - Referencia

## 🚀 Inicio Rápido

```bash
# 1. Script interactivo (RECOMENDADO)
./quick_test.sh

# 2. Ejecutar todos los tests
python run_all_integration_tests.py

# 3. Solo tests críticos (más rápido)
python run_all_integration_tests.py --fast
```

---

## 🧪 Tests Individuales

```bash
# Test de actualización (NUEVO)
python integration_tests/06_test_actualizar_evento.py

# Test de eliminación con contexto (NUEVO)
python integration_tests/13_test_eliminar_con_contexto.py

# Test de memoria persistente (MÁS IMPORTANTE)
python integration_tests/14_test_memoria_persistente.py
```

---

## 🔍 Verificación del Sistema

```bash
# Health check del backend
curl http://localhost:8000/health

# Verificar PostgreSQL
docker ps | grep postgres

# Ver logs en tiempo real
tail -f logs/app.log

# Ver últimos errores
grep "ERROR" logs/app.log | tail -20
```

---

## 🛠️ Gestión de Servicios

```bash
# Iniciar backend
python app.py

# Iniciar PostgreSQL
docker-compose up -d postgres

# Reiniciar PostgreSQL
docker-compose restart postgres

# Ver logs de PostgreSQL
docker-compose logs -f postgres
```

---

## 📊 Reportes y Análisis

```bash
# Ver último reporte
ls -lht integration_tests/reports/ | head -2

# Ver resumen con jq (si está instalado)
cat integration_tests/reports/test_report_*.json | jq '.summary'

# Contar tests pasados
grep "PASS" integration_tests/reports/test_report_*.json | wc -l
```

---

## 🗄️ Base de Datos

```bash
# Conectar a PostgreSQL
psql -h localhost -p 5434 -U admin -d agente_whatsapp

# Ver tablas
psql -h localhost -p 5434 -U admin -d agente_whatsapp -c "\dt"

# Ver memoria episódica
psql -h localhost -p 5434 -U admin -d agente_whatsapp -c "SELECT COUNT(*) FROM memoria_episodica;"

# Limpiar datos de test
psql -h localhost -p 5434 -U admin -d agente_whatsapp -c "DELETE FROM memoria_episodica WHERE user_id LIKE 'test_%';"
```

---

## 📝 Variables de Entorno

```bash
# Verificar credenciales
cat .env | grep -E "DEEPSEEK|ANTHROPIC|DATABASE"

# Copiar .env de ejemplo
cp .env.example .env

# Editar .env
nano .env
```

---

## 🐛 Debugging

```bash
# Ver estado de herramientas
grep "herramientas_seleccionadas" logs/app.log | tail -10

# Ver recuperación episódica
grep "episodios_recuperados" logs/app.log | tail -10

# Ver errores de LLM
grep "Error.*LLM" logs/app.log | tail -20

# Ver errores de validación
grep "validation errors" logs/app.log | tail -20
```

---

## 📚 Documentación

```bash
# Ver resumen ejecutivo
cat RESUMEN_EJECUTIVO.md

# Ver análisis completo
cat ANALISIS_Y_MEJORAS_PRODUCCION.md

# Ver guía de deployment
cat GUIA_TESTS_Y_DEPLOYMENT.md
```

---

## 🔧 Solución Rápida de Problemas

### Problema: Backend no responde
```bash
# Verificar proceso
ps aux | grep "python app.py"

# Reiniciar
pkill -f "python app.py"
python app.py &
```

### Problema: Tests fallan con error de conexión
```bash
# Verificar que backend esté corriendo
curl http://localhost:8000/health

# Si no responde, iniciar backend
python app.py
```

### Problema: PostgreSQL no conecta
```bash
# Verificar contenedor
docker ps | grep postgres

# Si no está corriendo
docker-compose up -d postgres

# Ver logs
docker-compose logs postgres
```

### Problema: "Prompt must contain 'json'"
```bash
# Ya corregido en src/memory/semantic.py
# Verificar que tienes la última versión
grep "JSON" src/memory/semantic.py
```

---

## 🎯 Tests Críticos a Ejecutar

**Orden recomendado:**

1. **Verificar prerequisitos**
   ```bash
   ./quick_test.sh  # Opción 7
   ```

2. **Tests básicos (CRUD)**
   ```bash
   python integration_tests/01_test_listar_inicial.py
   python integration_tests/02_test_crear_evento.py
   ```

3. **Tests de nuevas funcionalidades**
   ```bash
   python integration_tests/06_test_actualizar_evento.py
   python integration_tests/13_test_eliminar_con_contexto.py
   ```

4. **Test más importante (memoria persistente)**
   ```bash
   python integration_tests/14_test_memoria_persistente.py
   ```

5. **Suite completa**
   ```bash
   python run_all_integration_tests.py
   ```

---

## ⚡ One-Liners Útiles

```bash
# Contar eventos en calendario (requiere listar primero)
curl -X POST http://localhost:8000/api/whatsapp-agent/message \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test_admin","message":"¿cuántos eventos tengo?"}' | jq .

# Limpiar todos los reportes de tests
rm integration_tests/reports/*.json

# Ver memoria episódica de un usuario
psql -h localhost -p 5434 -U admin -d agente_whatsapp \
  -c "SELECT id, resumen, tipo, similarity FROM memoria_episodica WHERE user_id='test_user' ORDER BY timestamp DESC LIMIT 5;"

# Backup rápido de la base de datos
pg_dump -h localhost -p 5434 -U admin agente_whatsapp > backup_$(date +%Y%m%d).sql

# Restaurar backup
psql -h localhost -p 5434 -U admin agente_whatsapp < backup_20260126.sql
```

---

## 📞 Ayuda Rápida

Si tienes problemas:

1. ✅ Verificar que el backend esté corriendo: `curl http://localhost:8000/health`
2. ✅ Verificar logs: `tail -f logs/app.log`
3. ✅ Revisar documentación: `cat RESUMEN_EJECUTIVO.md`
4. ✅ Ejecutar script interactivo: `./quick_test.sh`

---

**Última actualización:** 26 de enero de 2026
