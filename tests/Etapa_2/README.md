# Tests de ETAPA 2: Sistema de Turnos Automático

## 📋 Descripción General

Esta carpeta contiene **70 tests** de la **ETAPA 2** del sistema de calendario médico, que implementa el sistema de turnos rotativos automático entre Doctor Santiago y Doctora Joana.

## 🎯 Objetivo de la Etapa

Validar que el sistema de turnos automático funciona correctamente:
- Alternancia equitativa entre doctores (50%-50%)
- Validación de disponibilidad precisa
- Generación correcta de slots
- Privacidad del doctor hasta confirmación
- Fallback automático si doctor ocupado

## 📁 Archivos de Test

### 1. `test_turnos.py` (15 tests)
Pruebas del sistema de turnos rotativos.

**Valida:**
- ✅ Alternancia: NULL → Santiago → Joana → Santiago
- ✅ Actualización de contadores (citas_santiago, citas_joana)
- ✅ Estadísticas de turnos
- ✅ Función obtener_otro_doctor() (fallback)
- ✅ Manejo de errores

### 2. `test_disponibilidad.py` (15 tests)
Pruebas de validación de disponibilidad.

**Valida:**
- ✅ Días de atención (Jueves-Lunes)
- ✅ Días cerrados (Martes-Miércoles)
- ✅ Horarios válidos (8:30 AM - 6:30 PM)
- ✅ Detección de conflictos (overlaps)
- ✅ Timezone awareness (America/Tijuana)

### 3. `test_slots.py` (15 tests)
Pruebas de generación de slots.

**Valida:**
- ✅ Generación para N días adelante
- ✅ Filtrado de días cerrados
- ✅ Slots de 1 hora de duración
- ✅ Aplicación de turnos
- ✅ NO revelar doctor_id al frontend
- ✅ Funciones de formateo y agrupación

### 4. `test_agendamiento_turnos.py` (15 tests)
Pruebas de integración del agendamiento.

**Valida:**
- ✅ Agendamiento con doctor del turno
- ✅ Reasignación automática si ocupado
- ✅ Actualización de control_turnos
- ✅ Campos: `fue_asignacion_automatica`, `doctor_turno_original`, `razon_reasignacion`
- ✅ Índices y performance
- ✅ Citas canceladas no bloquean

### 5. `test_integration_etapa2.py` (10 tests)
Pruebas end-to-end del sistema completo.

**Valida:**
- ✅ Flujo completo: slots → selección → agendamiento
- ✅ Equidad perfecta en 10, 20, 100 citas
- ✅ Múltiples usuarios simultáneos
- ✅ Recuperación de errores
- ✅ Performance (<5s para 100 slots)

---

## 🚀 Ejecución de Tests

### Ejecutar todos los tests de ETAPA 2:
```bash
pytest tests/Etapa_2/ -v
```

### Ejecutar archivo específico:
```bash
pytest tests/Etapa_2/test_turnos.py -v
pytest tests/Etapa_2/test_disponibilidad.py -v
pytest tests/Etapa_2/test_slots.py -v
pytest tests/Etapa_2/test_agendamiento_turnos.py -v
pytest tests/Etapa_2/test_integration_etapa2.py -v
```

### Con coverage:
```bash
pytest tests/Etapa_2/ --cov=src.medical --cov-report=html
```

### Solo tests que fallen:
```bash
pytest tests/Etapa_2/ -x  # Detener al primer fallo
pytest tests/Etapa_2/ --lf  # Solo ejecutar últimos fallidos
```

### Ejecutar un test específico:
```bash
pytest tests/Etapa_2/test_turnos.py::test_alternancia_null_santiago -v
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
70 passed in X.XXs
========================================
```

---

## 🔧 Configuración Necesaria

### Variables de Entorno (.env):
```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5434/agente_whatsapp
```

### Base de Datos:
Asegurarse de que las siguientes tablas existan:
- ✅ `control_turnos` (con 1 registro inicial)
- ✅ `disponibilidad_medica` (con horarios configurados)
- ✅ `citas_medicas` (con columnas nuevas de ETAPA 2)
- ✅ `doctores` (con Santiago ID=1 y Joana ID=2)

**Ejecutar migración:**
```bash
python ejecutar_migracion_etapa2.py
```

---

## 🐛 Troubleshooting

### Error: "Requiere doctores 1 y 2"
```bash
# Verificar que existan los doctores
psql -h localhost -p 5434 -U postgres -d agente_whatsapp -c "SELECT id, nombre_completo FROM doctores WHERE id IN (1, 2);"
```

### Error: "control_turnos vacía"
```sql
-- Insertar registro inicial
INSERT INTO control_turnos (ultimo_doctor_id, citas_santiago, citas_joana)
VALUES (NULL, 0, 0);
```

### Tests fallan por datos previos
```bash
# Limpiar datos de prueba
psql -h localhost -p 5434 -U postgres -d agente_whatsapp -c "DELETE FROM citas_medicas WHERE fecha_hora_inicio > NOW() + INTERVAL '1 month';"
```

### Error: "Base de datos no disponible"
```bash
# Verificar que PostgreSQL está corriendo
docker ps | grep postgres

# O iniciar contenedor
docker-compose up -d postgres
```

---

## 📚 Referencia

- **Código probado:** `src/medical/`
- **Migración:** `sql/migrate_etapa_2_turnos.sql`
- **Documentación:** `docs/ETAPA_2_COMPLETADA.md`
- **Especificación:** `docs/PROMPT_ETAPA_2.md`

---

## ✅ Criterios de Aceptación

Para considerar ETAPA 2 completa:

1. ✅ Todos los tests pasan (70/70)
2. ✅ Cobertura >95% en código de src/medical/
3. ✅ Sistema alterna correctamente entre doctores
4. ✅ NO se revelan doctores antes de confirmación
5. ✅ Detección de conflictos funciona
6. ✅ Fallback automático opera correctamente

---

## 📈 Estadísticas

| Métrica | Valor |
|---------|-------|
| **Tests totales** | 70 |
| **test_turnos.py** | 15 |
| **test_disponibilidad.py** | 15 |
| **test_slots.py** | 15 |
| **test_agendamiento_turnos.py** | 15 |
| **test_integration_etapa2.py** | 10 |
| **Cobertura esperada** | >95% |

---

## 🎓 Reglas de Testing

Según especificación:

> Si test falla → reparar código, NO modificar tests

Los tests son la especificación. Si fallan, el código está mal, no los tests.

---

## 🔍 Qué se Prueba

### Sistema de Turnos
- Alternancia perfecta NULL → 1 → 2 → 1 → 2
- Contadores incrementan correctamente
- Estadísticas reflejan realidad
- Fallback funciona

### Disponibilidad
- Días: Solo Jueves-Lunes
- Horario: Solo 8:30-18:30
- Conflicts: Detecta overlaps
- Timezone: America/Tijuana

### Slots
- Generación: Para N días
- Duración: 1 hora cada uno
- Filtrado: Sin días cerrados
- Privacidad: Sin doctor_id al frontend

### Agendamiento
- Asignación: Con doctor del turno
- Reasignación: Si ocupado → otro doctor
- Tracking: Campos de auditoría
- Equidad: 50%-50% perfecto

### Integración
- Flujo completo: Funciona end-to-end
- Equidad: Se mantiene en 100 citas
- Concurrencia: Maneja múltiples usuarios
- Performance: <5s para 100 slots

---

**Autor:** Sistema de Testing - ETAPA 2  
**Versión:** 1.0.0  
**Última actualización:** 2026-01-28
