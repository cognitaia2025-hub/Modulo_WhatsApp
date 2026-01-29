# 🎯 INSTRUCCIONES DE EJECUCIÓN - ETAPA 1

## ¡La ETAPA 1 está completamente implementada!

### ✅ Archivos Listos

**Código:**
- ✅ `src/state/agent_state.py` - Estado actualizado con tipo_usuario, doctor_id, paciente_id
- ✅ `src/nodes/identificacion_usuario_node.py` - Nodo mejorado con auto-registro
- ✅ `sql/migrate_etapa_1_identificacion.sql` - Migración de BD completa

**Tests (63 tests):**
- ✅ `tests/Etapa_1/test_identificacion_node.py` (15 tests)
- ✅ `tests/Etapa_1/test_user_registration.py` (15 tests)
- ✅ `tests/Etapa_1/test_user_types.py` (15 tests)
- ✅ `tests/Etapa_1/test_integration_identificacion.py` (18 tests)

**Documentación:**
- ✅ `docs/ETAPA_1_COMPLETADA.md` - Reporte completo
- ✅ `tests/Etapa_1/README.md` - Guía de tests
- ✅ `RESUMEN_ETAPA_1.md` - Resumen ejecutivo

**Scripts:**
- ✅ `ejecutar_etapa1_completa.py` - Script TODO-EN-UNO
- ✅ `ejecutar_etapa1_completa.bat` - Launcher Windows
- ✅ `ejecutar_migracion_etapa1.py` - Solo migración
- ✅ `ejecutar_tests_etapa1.py` - Solo tests
- ✅ `notificar_completado.py` - Notificación actualizada

---

## 🚀 CÓMO EJECUTAR

### Opción 1: Script Todo-en-Uno (RECOMENDADO)

**Windows:**
```bash
ejecutar_etapa1_completa.bat
```

**O directamente con Python:**
```bash
python ejecutar_etapa1_completa.py
```

**Esto ejecuta automáticamente:**
1. Migración de base de datos
2. Todos los tests (63)
3. Notificación con sonido de completado

---

### Opción 2: Paso a Paso

```bash
# 1. Ejecutar migración de BD
python ejecutar_migracion_etapa1.py

# 2. Ejecutar tests
python ejecutar_tests_etapa1.py

# 3. Notificación
python notificar_completado.py
```

---

### Opción 3: Manual (si prefieres control total)

```bash
# 1. Migración directa con psql
psql -h localhost -p 5434 -U postgres -d agente_whatsapp -f sql/migrate_etapa_1_identificacion.sql

# 2. Tests con pytest
pytest tests/Etapa_1/ -v

# 3. Notificación
python notificar_completado.py
```

---

## 📋 Pre-requisitos

Antes de ejecutar, verifica:

1. **PostgreSQL corriendo:**
   ```bash
   docker ps | grep postgres
   # O
   docker-compose up -d postgres
   ```

2. **Variables de entorno (.env):**
   ```env
   DATABASE_URL=postgresql://postgres:postgres@localhost:5434/agente_whatsapp
   ADMIN_PHONE_NUMBER=+526641234567
   ```

3. **Dependencias instaladas:**
   ```bash
   pip install -r requirements.txt
   ```

---

## 🎯 Resultado Esperado

### Migración:
```
========================================
MIGRACIÓN ETAPA 1 COMPLETADA
========================================
Total usuarios: X
Doctores: Y
Pacientes externos: Z
Administradores: W
========================================
```

### Tests:
```
tests/Etapa_1/test_identificacion_node.py ............... PASSED [ 24%]
tests/Etapa_1/test_user_registration.py ................ PASSED [ 48%]
tests/Etapa_1/test_user_types.py ...................... PASSED [ 72%]
tests/Etapa_1/test_integration_identificacion.py ...... PASSED [100%]

============================== 63 passed in X.XXs ==============================
```

### Notificación:
```
========================================
🤖 SISTEMA DE CALENDARIO MÉDICO
========================================

✅ ETAPA 1 COMPLETADA CON ÉXITO

📋 Componentes implementados:
   • Nodo de identificación de usuario
   • Sistema de auto-registro
   • Diferenciación de tipos de usuario
   • Migración de base de datos
   • 63 tests unitarios e integración

🎵 Reproduciendo sonido de finalización...
*BEEP BEEP BEEP BEEP*

========================================
¡ETAPA 1 LISTA! Consulta docs/ETAPA_1_COMPLETADA.md
========================================
```

---

## 🐛 Troubleshooting

### Error: "Database connection failed"
```bash
# Verificar PostgreSQL
docker ps

# Iniciar si no está corriendo
docker-compose up -d postgres

# Verificar conexión
psql -h localhost -p 5434 -U postgres -d agente_whatsapp -c "SELECT 1;"
```

### Error: "Module not found"
```bash
# Instalar dependencias
pip install -r requirements.txt

# O específicamente
pip install psycopg pytest python-dotenv langchain-core
```

### Tests fallan
```bash
# Ver detalles completos
pytest tests/Etapa_1/ -vv --tb=long

# Ejecutar solo tests que fallan
pytest tests/Etapa_1/ --lf

# Ejecutar un test específico
pytest tests/Etapa_1/test_identificacion_node.py::test_nombre_del_test -v
```

---

## 📚 Documentación Adicional

- **Reporte completo:** `docs/ETAPA_1_COMPLETADA.md`
- **Guía de tests:** `tests/Etapa_1/README.md`
- **Resumen ejecutivo:** `RESUMEN_ETAPA_1.md`
- **Especificación original:** `docs/PROMPT_ETAPA_1.md`

---

## ✅ Checklist de Verificación

Antes de considerar ETAPA 1 como completa, verifica:

- [ ] Migración de BD ejecutada sin errores
- [ ] Tabla `usuarios` tiene columnas: `tipo_usuario`, `email`, `is_active`
- [ ] Tabla `doctores` existe y tiene: `nombre_completo`, `especialidad`, `orden_turno`
- [ ] Todos los 63 tests pasan
- [ ] Nodo de identificación funciona en el grafo
- [ ] No hay regresiones en funcionalidad existente

---

## 🎉 ¡Listo!

Una vez ejecutado todo:

1. ✅ ETAPA 1 estará **100% completa**
2. ✅ Sistema podrá **identificar usuarios automáticamente**
3. ✅ Auto-registro funcionará para **pacientes nuevos**
4. ✅ Todo estará **documentado y testeado**

**Siguiente paso:** ETAPA 2 - Consulta de Doctores Disponibles

---

**Última actualización:** 2026-01-28  
**Versión:** 1.0.0
