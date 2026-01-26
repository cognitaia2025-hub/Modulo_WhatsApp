# 🧪 Tests de Integración - Orden Secuencial

Esta carpeta contiene tests de integración diseñados para ejecutarse en orden secuencial.
Cada test construye sobre el resultado del anterior.

## 📋 Orden de Ejecución

Ejecuta los tests en el siguiente orden:

1. `01_test_listar_inicial.py` - Ver estado inicial del calendario
2. `02_test_crear_evento.py` - Crear primera reunión
3. `03_test_verificar_creacion.py` - Verificar que se creó
4. `04_test_buscar_evento.py` - Buscar evento específico
5. `05_test_crear_segundo_evento.py` - Crear segundo evento
6. `06_test_actualizar_evento.py` - Modificar hora del primer evento
7. `07_test_verificar_actualizacion.py` - Verificar cambio aplicado
8. `08_test_buscar_rango.py` - Buscar por rango de fechas
9. `09_test_eliminar_evento.py` - Eliminar un evento
10. `10_test_verificar_eliminacion.py` - Confirmar eliminación
11. `11_test_sin_herramienta.py` - Conversación sin herramientas
12. `12_test_multiples_herramientas.py` - Múltiples acciones

## 🚀 Ejecución

### Ejecutar todos los tests en secuencia:
```bash
python run_all_tests.py
```

### Ejecutar un test individual:
```bash
python integration_tests/01_test_listar_inicial.py
```

## 📊 Registro de Resultados

Los tests generarán un archivo `test_results.json` con los resultados:

```json
{
  "01_test_listar_inicial": {
    "status": "PASSED",
    "herramienta_esperada": "list_calendar_events",
    "herramienta_detectada": "list_calendar_events",
    "timestamp": "2026-01-25T15:30:00"
  }
}
```

## ⚠️ Requisitos

- Backend debe estar corriendo en `http://localhost:8000`
- PostgreSQL debe estar activo
- Google Calendar debe estar autenticado

## 💡 Tips

- Si un test falla, revisa los logs del backend con colores
- Los tests limpian el calendario al final (opcional)
- Usa `--verbose` para ver logs detallados
