# Tests de ETAPA 3: Flujo Inteligente con LLM

## 📋 Descripción

Esta carpeta contiene **80 tests** de la **ETAPA 3** del sistema de calendario médico, que implementa clasificación inteligente y manejo conversacional usando LLM.

## 🎯 Objetivo

Validar que el sistema de flujo inteligente funciona correctamente:
- Clasificación correcta de mensajes (personal/medica/chat/solicitud_cita_paciente)
- Fallback automático DeepSeek → Claude
- Validación de permisos por tipo de usuario
- Recuperación de contexto médico solo para doctores
- Selección inteligente de herramientas según clasificación
- Ejecución segura con validaciones

## 📁 Archivos de Test

### 1. `conftest.py`
Fixtures compartidos y mocks para todos los tests.

**Fixtures principales:**
- `mock_llm_clasificacion` - Mock de LLM para clasificación
- `estado_con_doctor` - Estado de grafo con usuario doctor
- `estado_con_paciente` - Estado con paciente externo
- `mock_db_connection` - Mock de base de datos
- `mock_herramientas_medicas` - Mock de herramientas

### 2. `test_filtrado_inteligente.py` (20 tests)
Pruebas del nodo de clasificación con LLM.

**Valida:**
- ✅ Clasificación de solicitudes médicas, personales, chat
- ✅ Paciente externo → solo solicitud_cita_paciente
- ✅ Fallback DeepSeek → Claude si falla
- ✅ Parseo robusto de respuestas JSON
- ✅ Validación de permisos post-LLM
- ✅ Registro en BD para auditoría

### 3. `test_recuperacion_medica.py` (15 tests)
Pruebas de recuperación de contexto médico.

**Valida:**
- ✅ Recuperación de pacientes recientes (últimos 10)
- ✅ Citas del día actual
- ✅ Estadísticas del doctor
- ✅ Búsqueda semántica con embeddings
- ✅ Formateo legible de contexto
- ✅ Solo doctores obtienen contexto médico

### 4. `test_seleccion_herramientas_llm.py` (20 tests)
Pruebas de selección inteligente de herramientas.

**Valida:**
- ✅ LLM selecciona herramientas correctas según contexto
- ✅ Pacientes externos: solo 2 herramientas
- ✅ Doctores: acceso completo (12 herramientas)
- ✅ Clasificación determina pool de herramientas
- ✅ Parseo robusto de respuestas del LLM
- ✅ Fallback si LLM falla

### 5. `test_ejecucion_medica.py` (15 tests)
Pruebas de ejecución de herramientas médicas.

**Valida:**
- ✅ Ejecución exitosa de herramientas
- ✅ Validación de permisos antes de ejecutar
- ✅ Inyección automática de doctor_phone
- ✅ Actualización de control_turnos después de agendar
- ✅ Manejo de errores sin detener otras herramientas
- ✅ Múltiples herramientas ejecutan secuencialmente

### 6. `test_integration_etapa3.py` (10 tests)
Pruebas end-to-end del sistema completo.

**Valida:**
- ✅ Flujo completo doctor: filtrado → recuperación → selección → ejecución
- ✅ Flujo completo paciente (sin recuperación médica)
- ✅ Fallback LLM funciona en todo el flujo
- ✅ Permisos se respetan en flujo completo
- ✅ Clasificación determina herramientas disponibles
- ✅ Performance del flujo completo

---

## 🚀 Ejecución de Tests

### Ejecutar todos los tests de ETAPA 3:
```bash
pytest tests/Etapa_3/ -v
```

### Ejecutar archivo específico:
```bash
pytest tests/Etapa_3/test_filtrado_inteligente.py -v
pytest tests/Etapa_3/test_recuperacion_medica.py -v
pytest tests/Etapa_3/test_seleccion_herramientas_llm.py -v
pytest tests/Etapa_3/test_ejecucion_medica.py -v
pytest tests/Etapa_3/test_integration_etapa3.py -v
```

### Con coverage:
```bash
pytest tests/Etapa_3/ --cov=src.nodes --cov-report=html
```

### Ejecutar un test específico:
```bash
pytest tests/Etapa_3/test_filtrado_inteligente.py::test_clasificar_solicitud_medica_doctor -v
```

---

## 📊 Resultado Esperado

```
========================================
tests/Etapa_3/test_filtrado_inteligente.py .......... (20 passed)
tests/Etapa_3/test_recuperacion_medica.py ........ (15 passed)
tests/Etapa_3/test_seleccion_herramientas_llm.py .. (20 passed)
tests/Etapa_3/test_ejecucion_medica.py ........... (15 passed)
tests/Etapa_3/test_integration_etapa3.py ......... (10 passed)
========================================
80 passed in X.XXs
========================================
```

---

## 🔧 Configuración Necesaria

### Variables de Entorno (.env):
```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5434/agente_whatsapp
DEEPSEEK_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

### Base de Datos:
Asegurarse de que las siguientes tablas existan:
- ✅ `clasificaciones_llm` (nueva en ETAPA 3)
- ✅ `historiales_medicos` con columna `embedding vector(384)`
- ✅ `control_turnos`, `disponibilidad_medica`, `citas_medicas`
- ✅ `doctores`, `pacientes`

**Ejecutar migración:**
```bash
python ejecutar_migracion_etapa3.py
```

---

## 🐛 Troubleshooting

### Error: "ImportError: No module named src.nodes"
```bash
# Asegurarse de estar en la raíz del proyecto
cd C:\Users\Salva\OneDrive\Escritorio\agent_calendar\Calender-agent

# Ejecutar tests
pytest tests/Etapa_3/ -v
```

### Error: "LLM API key not found"
```bash
# Verificar variables de entorno
echo %DEEPSEEK_API_KEY%
echo %ANTHROPIC_API_KEY%

# O agregar a .env
DEEPSEEK_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

### Tests fallan por datos previos
```sql
-- Limpiar clasificaciones de prueba
DELETE FROM clasificaciones_llm WHERE user_phone LIKE '%test%';
```

### Error: "Doctores no existen"
```sql
-- Verificar doctores
SELECT id, nombre_completo FROM doctores WHERE id IN (1, 2);

-- Crear si no existen
INSERT INTO doctores (id, nombre_completo, especialidad) 
VALUES (1, 'Dr. Santiago', 'Medicina General'), (2, 'Dra. Joana', 'Medicina General');
```

---

## 📚 Referencia

- **Código probado:** `src/nodes/` (filtrado_inteligente, recuperacion_medica, ejecucion_medica)
- **Herramientas:** `src/medical/tools.py` (12 herramientas)
- **Migración:** `sql/migrate_etapa_3_flujo_inteligente.sql`
- **Documentación:** `docs/ETAPA_3_COMPLETADA.md`
- **Especificación:** `docs/PROMPT_ETAPA_3.md`

---

## ✅ Criterios de Éxito

Para considerar ETAPA 3 completa:

1. ✅ 80 tests pasan (80/80)
2. ✅ Cobertura >95% en nodos nuevos
3. ✅ Clasificación funciona con fallback
4. ✅ Permisos validados correctamente
5. ✅ NO se usan API keys reales en tests (solo mocks)
6. ✅ Flujo completo funciona end-to-end

---

## 🎓 Reglas de Testing

Según especificación:

> Si test falla → reparar código, NO modificar tests

Los tests son la especificación. Si fallan, el código está mal, no los tests.

---

## 🔍 Qué se Prueba

### Filtrado Inteligente
- Clasificación correcta según mensaje
- Fallback automático DeepSeek → Claude
- Validación de permisos por tipo usuario
- Registro en BD para auditoría

### Recuperación Médica
- Pacientes recientes (últimos 10)
- Citas del día
- Estadísticas del doctor
- Solo para doctores

### Selección de Herramientas
- LLM selecciona herramientas correctas
- Pool determinado por clasificación
- Validación de permisos
- Parseo robusto

### Ejecución Médica
- Ejecución con validaciones
- Inyección de doctor_phone
- Actualización de turnos
- Manejo de errores

### Integración
- Flujo completo funciona
- Permisos se respetan
- Fallback LLM en todo el flujo
- Performance aceptable

---

**Autor:** Sistema de Testing - ETAPA 3  
**Versión:** 1.0.0  
**Última actualización:** 2026-01-28
