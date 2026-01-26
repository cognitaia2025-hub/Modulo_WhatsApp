# 🚀 Guía de Ejecución de Tests y Deployment

## 📋 Tabla de Contenidos
1. [Correcciones Implementadas](#correcciones-implementadas)
2. [Cómo Ejecutar los Tests](#cómo-ejecutar-los-tests)
3. [Estructura de Tests](#estructura-de-tests)
4. [Deployment a Producción](#deployment-a-producción)
5. [Monitoreo y Mantenimiento](#monitoreo-y-mantenimiento)

---

## ✅ Correcciones Implementadas

### 1. Error de Preferencias con DeepSeek (CRÍTICO) ✅
**Problema:** `Prompt must contain the word 'json' in some form`

**Solución:** 
- Modificado `src/memory/semantic.py` línea 166
- Agregada palabra "JSON" explícitamente en el prompt
- Ahora funciona correctamente con `json_mode`

**Archivo:** [src/memory/semantic.py](src/memory/semantic.py#L166)

### 2. Implementación de `update_calendar_event` ✅
**Problema:** Herramienta no implementada

**Solución:**
- Creada nueva tool `update_event_tool` en `src/tool.py`
- Permite actualizar: hora, título, ubicación, descripción
- Integrada en `TOOL_MAPPING` del nodo de ejecución

**Archivo:** [src/tool.py](src/tool.py#L189)

### 3. Validación de `delete_calendar_event` ✅
**Problema:** Requería parámetros innecesarios (start_datetime, end_datetime, user_query)

**Solución:**
- Refactorizada signatura para hacer parámetros opcionales
- Dos modos: directo con `event_id` o búsqueda con descripción
- Eliminada dependencia de campos no necesarios

**Archivo:** [src/tool.py](src/tool.py#L238)

### 4. Mejora de Extracción de Parámetros ✅
**Problema:** LLM no extraía correctamente parámetros incompletos

**Solución:**
- Mejorados prompts de extracción con contexto histórico
- Uso de `ultimo_listado` para referencias contextuales
- Validación robusta antes de ejecutar herramientas

**Archivo:** [src/nodes/ejecucion_herramientas_node.py](src/nodes/ejecucion_herramientas_node.py#L150)

---

## 🧪 Cómo Ejecutar los Tests

### Prerequisitos

```bash
# 1. Asegúrate de que el backend esté corriendo
cd /workspaces/Modulo_WhatsApp
python app.py

# En otra terminal:
# 2. Verifica que PostgreSQL esté activo
docker ps | grep postgres

# 3. Verifica las credenciales en .env
cat .env | grep -E "DEEPSEEK|ANTHROPIC|DATABASE"
```

### Ejecutar Suite Completa

```bash
# Todos los tests (toma ~15-20 minutos)
python run_all_integration_tests.py

# Solo tests críticos (toma ~8-10 minutos)
python run_all_integration_tests.py --fast

# Con logs detallados
python run_all_integration_tests.py --verbose
```

### Ejecutar Tests Individuales

```bash
# Test de actualización de eventos
python integration_tests/06_test_actualizar_evento.py

# Test de eliminación con contexto
python integration_tests/13_test_eliminar_con_contexto.py

# Test de memoria persistente (MÁS IMPORTANTE)
python integration_tests/14_test_memoria_persistente.py
```

### Verificar Resultados

```bash
# Ver reportes generados
ls -lh integration_tests/reports/

# Ver último reporte
cat integration_tests/reports/test_report_*.json | tail -1 | jq .
```

---

## 📂 Estructura de Tests

```
integration_tests/
├── 01_test_listar_inicial.py           # ✅ Listar eventos
├── 02_test_crear_evento.py             # ✅ Crear evento
├── 03_test_verificar_creacion.py       # ✅ Verificar creación
├── 04_test_buscar_evento.py            # ✅ Buscar específico
├── 05_test_crear_segundo_evento.py     # ✅ Múltiples eventos
├── 06_test_actualizar_evento.py        # 🆕 NUEVO - Update completo
├── 07_test_verificar_actualizacion.py  # 🆕 NUEVO - Verificación update
├── 08_test_buscar_rango.py             # ✅ Búsqueda por rango
├── 09_test_eliminar_evento.py          # 🆕 MEJORADO - Delete con event_id
├── 10_test_verificar_eliminacion.py    # ✅ Verificar eliminación
├── 11_test_sin_herramienta.py          # ✅ Conversacional
├── 12_test_multiples_herramientas.py   # ✅ Múltiples herramientas
├── 13_test_eliminar_con_contexto.py    # 🆕 NUEVO - Context-aware delete
└── 14_test_memoria_persistente.py      # 🆕 NUEVO - Memoria episódica

reports/                                 # Reportes JSON de ejecución
└── test_report_YYYYMMDD_HHMMSS.json
```

### Tests Críticos (⚡ Prioridad Alta)

1. **01_test_listar_inicial.py** - Base para todo
2. **02_test_crear_evento.py** - CRUD básico
3. **06_test_actualizar_evento.py** - Nueva funcionalidad
4. **09_test_eliminar_evento.py** - CRUD completo
5. **13_test_eliminar_con_contexto.py** - Inteligencia contextual
6. **14_test_memoria_persistente.py** - Memoria entre sesiones

---

## 🚢 Deployment a Producción

### 1. Verificar que Todos los Tests Pasan

```bash
# Ejecutar suite completa
python run_all_integration_tests.py

# Verificar que tests críticos pasan al 100%
# Buscar en el output: "🔴 TESTS CRÍTICOS: X/X pasados"
```

### 2. Configurar Variables de Entorno

```bash
# Copiar .env.example a .env
cp .env.example .env

# Editar con credenciales de producción
nano .env
```

**Variables Requeridas:**
```env
# LLM APIs
DEEPSEEK_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Base de datos
DATABASE_URL=postgresql://user:pass@host:port/db
POSTGRES_HOST=localhost
POSTGRES_PORT=5434
POSTGRES_DB=agente_whatsapp
POSTGRES_USER=admin
POSTGRES_PASSWORD=password123

# Google Calendar
GOOGLE_CALENDAR_CREDENTIALS=credentials.json
GOOGLE_CALENDAR_TOKEN=token.json

# Timezone
TZ=America/Tijuana
```

### 3. Inicializar Base de Datos

```bash
# Levantar PostgreSQL con pgvector
docker-compose up -d postgres

# Ejecutar migraciones
python setup_infrastructure.py
python setup_user_sessions_table.py

# Verificar tablas
psql -h localhost -p 5434 -U admin -d agente_whatsapp -c "\dt"
```

### 4. Iniciar Servicio

```bash
# Desarrollo
uvicorn app:app --reload --host 0.0.0.0 --port 8000

# Producción con Gunicorn
gunicorn app:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120 \
  --log-level info
```

### 5. Verificar Health Check

```bash
# Verificar que el servicio responde
curl http://localhost:8000/health

# Debería retornar:
# {"status": "healthy", "timestamp": "..."}
```

---

## 📊 Monitoreo y Mantenimiento

### Logs

```bash
# Ver logs en tiempo real
tail -f logs/app.log

# Buscar errores
grep "ERROR" logs/app.log | tail -20

# Contar operaciones de calendario
grep "calendar_operations" logs/app.log | wc -l
```

### Métricas Clave

1. **Tasa de Éxito de Herramientas**
   - Objetivo: > 95%
   - Monitorear: Errores en ejecución de herramientas

2. **Latencia de Respuesta**
   - Objetivo: p95 < 3 segundos
   - Monitorear: Tiempo de respuesta del LLM

3. **Memoria Episódica**
   - Objetivo: Recuperación exitosa > 90%
   - Monitorear: Fallos en búsqueda por similitud

### Limpieza de Datos

```bash
# Limpiar memoria episódica antigua (> 90 días)
python scripts/cleanup_old_memories.py

# Backup de base de datos
python scripts/backup_preferences.sh
```

### Actualización de Modelos

```python
# Actualizar embeddings si cambia el modelo
from src.embeddings import EmbeddingsManager

embeddings = EmbeddingsManager()
embeddings.regenerate_all()  # CUIDADO: Operación costosa
```

---

## 🐛 Troubleshooting

### Problema: "Prompt must contain the word 'json'"

**Solución:** Ya corregido en `src/memory/semantic.py`. Si persiste:
```bash
git pull
git stash  # Si tienes cambios locales
git checkout main
```

### Problema: "Herramienta update_calendar_event no implementada"

**Solución:** Ya implementado en `src/tool.py`. Verifica:
```bash
grep "def update_event_tool" src/tool.py
```

### Problema: "3 validation errors for delete_event_tool"

**Solución:** Ya corregido. `delete_event_tool` ahora acepta parámetros opcionales.

### Problema: Pérdida de contexto conversacional

**Verificar:**
1. Que `ultimo_listado` se guarda en el estado
2. Que `contexto_episodico` se recupera correctamente
3. Revisar logs de recuperación episódica

```bash
grep "episodios_recuperados" logs/app.log | tail -10
```

---

## 📚 Recursos Adicionales

- [Análisis y Mejoras Completo](ANALISIS_Y_MEJORAS_PRODUCCION.md)
- [Documentación de Arquitectura](planificaciones_md/ESTADO_DEL_PROYECTO.md)
- [PRD Original](planificaciones_md/PRD.md)

---

## 🎯 Próximos Pasos Recomendados

1. **Ejecutar tests completos:**
   ```bash
   python run_all_integration_tests.py
   ```

2. **Revisar reporte de tests:**
   ```bash
   cat integration_tests/reports/test_report_*.json | jq .summary
   ```

3. **Si todos pasan → Deployment a staging:**
   ```bash
   # Configurar entorno de staging
   export ENVIRONMENT=staging
   python app.py
   ```

4. **Monitorear métricas por 24 horas**

5. **Si todo OK → Deployment a producción**

---

**Autor:** GitHub Copilot  
**Fecha:** 26 de enero de 2026  
**Versión:** 1.0.0
