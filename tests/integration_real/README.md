# Tests de Integración Real - Sistema Médico WhatsApp

Suite de tests incrementales que validan el funcionamiento de cada nodo del sistema
LangGraph, desde la identificación hasta la sincronización con Google Calendar.

## 🎯 Estrategia de Testing

Los tests son **incrementales**: cada archivo prueba todos los nodos anteriores más uno nuevo.

```
test_00 → Solo N0 (Identificación)
test_01 → N0 + N1 (+ Caché)
test_02 → N0 + N1 + N2 (+ Clasificación con LLM)
test_03 → N0 + N1 + N2 + N3 (+ Recuperación)
...
test_09 → Todos los nodos (flujo completo)
```

## 📁 Estructura de Archivos

```
tests/integration_real/
├── conftest.py                  # Fixtures compartidas (BD, LLM, estado)
├── test_00_identificacion.py    # N0: Solo identificación usuario
├── test_01_cache.py             # N0+N1: Identificación + Caché
├── test_02_clasificacion.py     # N0+N1+N2: + Clasificación (LLM)
├── test_03_recuperacion.py      # N0+N1+N2+N3: + Recuperación contexto
├── test_04_seleccion.py         # N0-N4: + Selección herramientas (LLM)
├── test_05_ejecucion.py         # N0-N5: + Ejecución (Calendar API)
├── test_06_recepcionista.py     # N0-N6R: + Recepcionista (LLM)
├── test_07_generacion.py        # N0-N6: + Generación respuesta (LLM)
├── test_08_memoria.py           # N0-N7: + Persistencia memoria
├── test_09_sincronizacion.py    # N0-N8: + Sync Google Calendar
└── README.md                    # Este archivo
```

## 🚀 Ejecución

### Prerequisitos

1. **Base de datos PostgreSQL corriendo:**
   ```bash
   docker-compose up -d postgres
   ```

2. **Variables de entorno configuradas:**
   - `DEEPSEEK_API_KEY`
   - `ANTHROPIC_API_KEY`
   - `DATABASE_URL`
   - `GOOGLE_SERVICE_ACCOUNT_FILE`
   - `GOOGLE_CALENDAR_ID`

3. **Schema de BD inicializado:**
   ```bash
   cd sql && python init_database_consolidated.py
   ```

### Ejecutar Tests

```bash
# Todos los tests
cd /workspaces/Modulo_WhatsApp
python -m pytest tests/integration_real/ -v --tb=short

# Un test específico
python -m pytest tests/integration_real/test_00_identificacion.py -v

# Tests hasta cierto nivel (por ejemplo, hasta N3)
python -m pytest tests/integration_real/test_0[0-3]*.py -v

# Con output detallado
python -m pytest tests/integration_real/ -v -s --log-cli-level=INFO

# Solo tests rápidos (sin LLM real)
python -m pytest tests/integration_real/ -v -m "not llm"

# Solo tests con LLM
python -m pytest tests/integration_real/ -v -m "llm"
```

## 📊 Escenarios de Prueba por Nodo

### N0: Identificación
- ✅ Usuario existente (paciente)
- ✅ Usuario existente (doctor)
- ✅ Usuario existente (admin)
- ✅ Usuario nuevo (auto-registro)
- ✅ Número de teléfono inválido
- ✅ Usuario desactivado

### N1: Caché
- ✅ Sesión activa (< 24h)
- ✅ Sesión expirada (> 24h)
- ✅ Primera sesión

### N2: Clasificación (LLM)
- ✅ Mensaje de calendario personal
- ✅ Solicitud de cita médica
- ✅ Consulta médica (doctor)
- ✅ Chat casual
- ✅ Mensaje ambiguo

### N3: Recuperación
- ✅ Con contexto previo
- ✅ Sin historial
- ✅ Múltiples memorias relevantes

### N4: Selección (LLM)
- ✅ Crear evento
- ✅ Listar eventos
- ✅ Actualizar evento
- ✅ Eliminar evento
- ✅ Consulta sin herramientas

### N5: Ejecución
- ✅ Crear evento en Google Calendar
- ✅ Listar eventos reales
- ✅ Actualizar evento existente
- ✅ Eliminar evento

### N6R: Recepcionista
- ✅ Nuevo paciente pide cita
- ✅ Paciente existente agenda
- ✅ Sin disponibilidad
- ✅ Confirmación de cita

### N6: Generación
- ✅ Respuesta informativa
- ✅ Respuesta con acción completada
- ✅ Manejo de errores amigable

### N7: Memoria
- ✅ Guardar conversación exitosa
- ✅ Embeddings generados correctamente

### N8: Sincronización
- ✅ Evento sincronizado a Google Calendar
- ✅ Verificación de evento creado
- ✅ Manejo de conflictos

## 🔧 Configuración de Fixtures

### `conftest.py` provee:

- `db_connection`: Conexión PostgreSQL real
- `test_state_paciente`: Estado inicial para paciente
- `test_state_doctor`: Estado inicial para doctor
- `test_state_admin`: Estado inicial para admin
- `google_calendar_client`: Cliente de Calendar API
- `cleanup_test_events`: Limpia eventos de prueba

## ⚠️ Notas Importantes

1. **Tests con LLM son lentos** (~1-3 segundos por llamada)
2. **Google Calendar requiere credenciales válidas**
3. **La BD debe tener datos seed iniciales**
4. **Los tests crean datos temporales que se limpian automáticamente**

## 📝 Marcadores de pytest

- `@pytest.mark.llm` - Requiere LLM real
- `@pytest.mark.calendar` - Requiere Google Calendar
- `@pytest.mark.slow` - Test lento (>5s)
- `@pytest.mark.db` - Requiere BD
