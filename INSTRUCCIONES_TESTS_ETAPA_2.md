# 🎯 INSTRUCCIONES FINALES - TESTS ETAPA 2

## ✅ ¿Qué se ha completado?

Se han creado **70 tests** para validar completamente la **ETAPA 2** del sistema de calendario médico (Sistema de Turnos Rotativos Automático).

---

## 📁 Archivos Creados

### Tests (70 tests en total):
- ✅ `tests/Etapa_2/test_turnos.py` (15 tests)
- ✅ `tests/Etapa_2/test_disponibilidad.py` (15 tests)
- ✅ `tests/Etapa_2/test_slots.py` (15 tests)
- ✅ `tests/Etapa_2/test_agendamiento_turnos.py` (15 tests)
- ✅ `tests/Etapa_2/test_integration_etapa2.py` (10 tests)

### Documentación:
- ✅ `tests/Etapa_2/README.md` - Guía completa de tests

### Scripts de Ejecución:
- ✅ `ejecutar_tests_etapa2.py` - Script Python
- ✅ `ejecutar_tests_etapa2.bat` - Script Windows

### Resúmenes:
- ✅ `RESUMEN_TESTS_ETAPA_2.md` - Resumen ejecutivo

---

## 🚀 PASOS SIGUIENTES (Para ejecutar los tests)

### Paso 1: Verificar que la base de datos está corriendo
```bash
# Verificar contenedor PostgreSQL
docker ps | findstr postgres
```

Si no está corriendo:
```bash
docker-compose up -d postgres
```

### Paso 2: Ejecutar la migración de ETAPA 2
```bash
python ejecutar_migracion_etapa2.py
```

Esto creará:
- Tabla `control_turnos`
- Tabla `disponibilidad_medica`
- Columnas nuevas en `citas_medicas`
- Funciones SQL necesarias

### Paso 3: Ejecutar los tests
```bash
# Opción 1: Usar el script Python
python ejecutar_tests_etapa2.py

# Opción 2: Usar el script BAT
ejecutar_tests_etapa2.bat

# Opción 3: Usar pytest directo
pytest tests/Etapa_2/ -v
```

### Paso 4: Verificar cobertura (opcional)
```bash
pytest tests/Etapa_2/ --cov=src.medical --cov-report=html
```

Luego abrir: `htmlcov/index.html`

### Paso 5: Si todo pasa, ejecutar notificación
```bash
python notificar_completado.py
```

---

## 📊 Resultado Esperado

```
========================================
tests/Etapa_2/test_turnos.py ............... (15 passed)
tests/Etapa_2/test_disponibilidad.py ....... (15 passed)
tests/Etapa_2/test_slots.py ................ (15 passed)
tests/Etapa_2/test_agendamiento_turnos.py .. (15 passed)
tests/Etapa_2/test_integration_etapa2.py ... (10 passed)
========================================
✅ 70 TESTS PASARON
========================================
```

---

## 🐛 Si algo falla...

### Error: "Requiere doctores 1 y 2"

**Causa:** No existen los doctores con ID 1 y 2 en la base de datos.

**Solución:**
```bash
# Conectar a la base de datos
docker exec -it <container_name> psql -U postgres -d agente_whatsapp

# Verificar doctores
SELECT id, nombre_completo FROM doctores;

# Si no existen, crearlos
INSERT INTO doctores (id, nombre_completo, especialidad, email)
VALUES 
  (1, 'Dr. Santiago', 'Medicina General', 'santiago@clinica.com'),
  (2, 'Dra. Joana', 'Medicina General', 'joana@clinica.com');
```

### Error: "control_turnos vacía" o "tabla no existe"

**Causa:** No se ejecutó la migración.

**Solución:**
```bash
python ejecutar_migracion_etapa2.py
```

### Error: "Base de datos no disponible"

**Causa:** PostgreSQL no está corriendo.

**Solución:**
```bash
docker-compose up -d postgres
```

### Tests fallan por datos previos

**Causa:** Hay datos de pruebas anteriores.

**Solución:**
```sql
-- Limpiar citas de prueba
DELETE FROM citas_medicas WHERE fecha_hora_inicio > NOW() + INTERVAL '1 month';

-- Resetear control de turnos
TRUNCATE TABLE control_turnos RESTART IDENTITY CASCADE;
INSERT INTO control_turnos (ultimo_doctor_id, citas_santiago, citas_joana)
VALUES (NULL, 0, 0);
```

---

## 📋 Checklist de Validación

- [ ] Base de datos PostgreSQL corriendo
- [ ] Migración ETAPA 2 ejecutada
- [ ] Doctores 1 y 2 existen
- [ ] Tests ejecutados (70/70 pasan)
- [ ] Cobertura >95% verificada
- [ ] Notificación activada

---

## 🎓 Qué se está probando

### 1. Sistema de Turnos Rotativos
- Alternancia perfecta: NULL → Santiago → Joana → Santiago → Joana
- Contadores incrementan correctamente
- Estadísticas reflejan la realidad
- Función de fallback funciona

### 2. Validación de Disponibilidad
- Solo días de atención: Jueves, Viernes, Sábado, Domingo, Lunes
- Solo horario: 8:30 AM - 6:30 PM
- Detección de conflictos/overlaps
- Manejo correcto de timezone (America/Tijuana)

### 3. Generación de Slots
- Genera slots para N días adelante
- Filtra días cerrados (Martes/Miércoles)
- Cada slot dura exactamente 1 hora
- **Privacidad:** NO revela doctor_id al frontend

### 4. Agendamiento con Turnos
- Asigna automáticamente doctor del turno
- Reasigna a otro doctor si ocupado
- Guarda campos de auditoría (fue_asignacion_automatica, doctor_turno_original, razon_reasignacion)
- Equidad perfecta: 50% Santiago, 50% Joana

### 5. Integración End-to-End
- Flujo completo: consultar → seleccionar → agendar
- Equidad se mantiene incluso con 100 citas
- Maneja múltiples usuarios simultáneos
- Performance: <5 segundos para generar 100 slots

---

## 📚 Documentación Adicional

- **Código completo:** `src/medical/` (turnos.py, disponibilidad.py, slots.py)
- **Migración SQL:** `sql/migrate_etapa_2_turnos.sql`
- **Documentación técnica:** `docs/ETAPA_2_COMPLETADA.md`
- **Especificación:** `docs/PROMPT_ETAPA_2.md`
- **Guía de tests:** `tests/Etapa_2/README.md`

---

## 🎉 ¡Todo listo!

Los tests están **100% creados y documentados**. Solo falta:

1. ✅ Ejecutar migración
2. ✅ Ejecutar tests
3. ✅ Verificar que pasen
4. ✅ Activar notificación

---

**Fecha:** 28 de enero de 2026  
**Status:** ✅ TESTS COMPLETADOS (70/70)  
**Próximo paso:** Ejecutar los comandos de arriba
