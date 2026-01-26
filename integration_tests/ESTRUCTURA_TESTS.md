# 📁 TESTS DE INTEGRACIÓN - ESTRUCTURA COMPLETA

## 🎯 Objetivo
Suite de 12 tests secuenciales que verifican el funcionamiento end-to-end del agente de calendario, probando cada herramienta y el flujo completo de operaciones.

---

## 📂 Estructura de Archivos

```
integration_tests/
├── README.md                           # Documentación principal
├── __init__.py                         # Módulo Python
├── test_base.py                        # Clase base reutilizable
├── run_all_tests.py                    # Ejecutor de todos los tests
│
├── 01_test_listar_inicial.py          # ✅ Listar eventos (estado inicial)
├── 02_test_crear_evento.py            # ✅ Crear evento (reunión equipo)
├── 03_test_verificar_creacion.py      # ✅ Verificar creación
├── 04_test_buscar_evento.py           # ✅ Buscar por palabra clave
├── 05_test_crear_segundo_evento.py    # ✅ Crear segundo evento (doctor)
├── 06_test_actualizar_evento.py       # ✅ Actualizar hora
├── 07_test_verificar_actualizacion.py # ✅ Verificar actualización
├── 08_test_buscar_rango.py            # ✅ Buscar por rango de fechas
├── 09_test_eliminar_evento.py         # ✅ Eliminar evento
├── 10_test_verificar_eliminacion.py   # ✅ Verificar eliminación
├── 11_test_sin_herramienta.py         # ✅ Sin herramienta necesaria
└── 12_test_multiples_herramientas.py  # ✅ Múltiples herramientas
```

---

## 🔢 Orden de Ejecución

### **Test 01: Listar eventos iniciales**
- **Mensaje**: "¿Qué eventos tengo hoy?"
- **Herramienta esperada**: `list_calendar_events`
- **Objetivo**: Ver el estado inicial del calendario

### **Test 02: Crear evento simple**
- **Mensaje**: "Agenda una reunión con el equipo mañana a las 10am"
- **Herramienta esperada**: `create_calendar_event`
- **Objetivo**: Crear primer evento

### **Test 03: Verificar creación**
- **Mensaje**: "Muéstrame mi agenda de mañana"
- **Herramienta esperada**: `list_calendar_events`
- **Objetivo**: Confirmar que el evento se creó

### **Test 04: Buscar evento específico**
- **Mensaje**: 'Busca eventos que tengan la palabra "reunión"'
- **Herramienta esperada**: `search_calendar_events`
- **Objetivo**: Encontrar el evento creado

### **Test 05: Crear segundo evento**
- **Mensaje**: 'Crea un evento llamado "Cita con el doctor" para pasado mañana a las 3pm'
- **Herramienta esperada**: `create_calendar_event`
- **Objetivo**: Crear segundo evento

### **Test 06: Actualizar evento**
- **Mensaje**: "Cambia la reunión del equipo para las 11am"
- **Herramienta esperada**: `update_calendar_event`
- **Objetivo**: Modificar hora del primer evento

### **Test 07: Verificar actualización**
- **Mensaje**: "¿Qué eventos tengo esta semana?"
- **Herramienta esperada**: `list_calendar_events`
- **Objetivo**: Confirmar que el cambio se aplicó

### **Test 08: Buscar con rango de fechas**
- **Mensaje**: "Busca eventos de la próxima semana"
- **Herramienta esperada**: `search_calendar_events`
- **Objetivo**: Probar búsqueda por rango

### **Test 09: Eliminar evento**
- **Mensaje**: "Elimina la cita con el doctor"
- **Herramienta esperada**: `delete_calendar_event`
- **Objetivo**: Probar eliminación

### **Test 10: Verificar eliminación**
- **Mensaje**: "Muéstrame todos mis eventos de los próximos 7 días"
- **Herramienta esperada**: `list_calendar_events`
- **Objetivo**: Confirmar que solo queda la reunión

### **Test 11: Sin herramienta necesaria**
- **Mensaje**: "Hola, ¿cómo estás?"
- **Herramienta esperada**: `NONE`
- **Objetivo**: Verificar que NO ejecuta herramientas innecesarias

### **Test 12: Múltiples herramientas**
- **Mensaje**: 'Crea un evento para mañana a las 2pm llamado "Gym" y luego muéstrame mi agenda de mañana'
- **Herramientas esperadas**: `create_calendar_event`, `list_calendar_events`
- **Objetivo**: Ejecutar múltiples herramientas en secuencia

---

## 🚀 Cómo Ejecutar

### **Opción 1: Ejecutar todos los tests**
```bash
cd integration_tests
python run_all_tests.py
```

### **Opción 2: Ejecutar un test individual**
```bash
cd integration_tests
python 01_test_listar_inicial.py
python 02_test_crear_evento.py
# etc...
```

---

## 📋 Requisitos Previos

1. **Backend corriendo**: El servidor debe estar activo en `http://localhost:8000`
   ```bash
   python app.py
   ```

2. **PostgreSQL activo**: Base de datos debe estar disponible

3. **Google Calendar autenticado**: Credenciales configuradas

4. **Dependencias instaladas**:
   ```bash
   pip install colorama requests
   ```

---

## 🎨 Características

### **Clase Base (`test_base.py`)**
- `IntegrationTestBase`: Clase reutilizable para todos los tests
- Métodos de impresión con colores (colorama)
- `send_message()`: Envía requests al backend
- `verify_tool_used()`: Verifica herramienta correcta (placeholder)
- `save_result()`: Guarda resultados en JSON

### **Ejecutor (`run_all_tests.py`)**
- Carga módulos dinámicamente (archivos empiezan con números)
- Ejecuta tests en secuencia
- Espera 3 segundos entre tests
- Muestra resumen final con estadísticas
- Usa colorama para output colorido

### **Tests Individuales**
- Cada test hereda de `IntegrationTestBase`
- Implementa método `run()`
- Imprime headers, pasos y resultados
- Guarda resultado en JSON

---

## 📊 Formato de Resultados

Los resultados se guardan en `test_results.json`:

```json
{
  "test_name": "Listar eventos iniciales",
  "test_number": 1,
  "timestamp": "2025-01-20T15:30:45",
  "passed": true,
  "details": {
    "response": "..."
  }
}
```

---

## 🔍 Debugging

### **Revisar logs del backend**
Los logs del backend (con colores) muestran:
- Herramientas seleccionadas
- Parámetros extraídos
- Resultados de ejecución

### **Verificar conexión**
Si un test falla con error de conexión:
```bash
# Verificar que el backend esté corriendo
curl http://localhost:8000/health
```

### **Ver resultados detallados**
```bash
# Ver resultados guardados
cat test_results.json
```

---

## 💡 Tips

1. **Ejecuta los tests en orden**: Cada test depende del anterior
2. **Revisa los logs del backend**: Ahí verás qué herramientas se ejecutan
3. **Espera entre tests**: Los 3 segundos de espera son importantes
4. **Verifica Google Calendar**: Puedes ver los eventos creados en tu calendario real
5. **Limpia el calendario**: Antes de ejecutar la suite completa, limpia los eventos de prueba anteriores

---

## 🎯 Cobertura de Tests

| Herramienta | Tests que la usan |
|-------------|-------------------|
| `list_calendar_events` | 01, 03, 07, 10, 12 |
| `create_calendar_event` | 02, 05, 12 |
| `search_calendar_events` | 04, 08 |
| `update_calendar_event` | 06 |
| `delete_calendar_event` | 09 |
| Ninguna | 11 |

---

## 📝 Próximos Pasos

1. **Implementar `verify_tool_used()`**: Parsear la respuesta del backend para verificar herramienta
2. **Agregar assertions**: Validar campos específicos en las respuestas
3. **Agregar CLI arguments**: `--verbose`, `--stop-on-fail`, `--skip-delays`
4. **Generar reporte HTML**: Visualización bonita de resultados
5. **Integrar con CI/CD**: Ejecutar automáticamente en cada commit

---

## ✅ Estado Actual

**COMPLETADO**: ✅
- Estructura de carpeta creada
- Clase base implementada
- 12 tests individuales creados
- Ejecutor completo implementado
- Documentación completa

**LISTO PARA USAR**: 🚀
```bash
python integration_tests/run_all_tests.py
```
