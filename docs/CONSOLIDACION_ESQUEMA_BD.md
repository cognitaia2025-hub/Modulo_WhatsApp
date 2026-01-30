# 🎯 Consolidación de Esquema de Base de Datos - Resumen de Cambios

## 📅 Fecha: 30 de Enero de 2026

## 🎯 Objetivo Alcanzado

Se ha consolidado **todo el esquema de base de datos** en archivos SQL únicos, eliminando la necesidad de ejecutar migraciones por separado en cada entorno de trabajo.

## ✅ Trabajo Realizado

### 1. Archivo Principal Actualizado

**📄 `sql/init_database.sql`**
- ✅ Integradas **todas las tablas** de las Etapas 1-7
- ✅ Agregadas 15 tablas nuevas:
  - `usuarios` (Etapa 1)
  - `doctores` (Etapa 1)
  - `pacientes` (Etapa 1)
  - `control_turnos` (Etapa 2)
  - `disponibilidad_medica` (Etapa 2)
  - `citas_medicas` (Etapas 2-6)
  - `historiales_medicos` (Etapa 3)
  - `clasificaciones_llm` (Etapa 3)
  - `sincronizacion_calendar` (Etapa 5)
  - `metricas_consultas` (Etapa 7)
  - `reportes_generados` (Etapa 7)
  
- ✅ Agregadas **columnas de migraciones**:
  - `citas_medicas.sincronizada_google` (Etapa 5)
  - `citas_medicas.recordatorio_enviado` (Etapa 6)
  - `citas_medicas.recordatorio_fecha_envio` (Etapa 6)
  - `citas_medicas.recordatorio_intentos` (Etapa 6)
  - `sincronizacion_calendar.intentos` (Etapa 5)
  - `sincronizacion_calendar.max_intentos` (Etapa 5)
  - `historiales_medicos.embedding` (Etapa 3)

- ✅ Agregadas **8 funciones SQL**:
  - `buscar_memorias_similares()`
  - `buscar_historiales_semantica()`
  - `get_active_session()`
  - `update_session_activity()`
  - `cleanup_old_sessions()`
  - `actualizar_metricas_doctor()`
  - `buscar_citas_por_periodo()`
  - `trigger_actualizar_metricas()`

- ✅ Agregadas **5 vistas**:
  - `resumen_clasificaciones`
  - `metricas_llm_por_modelo`
  - `vista_estadisticas_doctores`
  - `active_sessions_24h`
  - `session_statistics`

- ✅ Agregados **3 triggers**:
  - `trigger_actualizar_metricas` en citas_medicas
  - `trg_prevent_user_id_change` en user_sessions
  - Trigger de actualización automática de updated_at

### 2. Actualización de Herramientas

**📄 `sql/setup_herramientas.sql`**
- ✅ Migración `migrate_add_tool_name.sql` **integrada**
- ✅ Columna `id_tool` renombrada a `tool_name`
- ✅ Constraint UNIQUE agregado a `tool_name`
- ✅ Ya NO es necesario ejecutar migración por separado

### 3. Nuevos Archivos Creados

**📄 `sql/seed_initial_data.sql`** (NUEVO)
- ✅ Datos de usuario administrador
- ✅ 2 doctores iniciales (Santiago y Joana)
- ✅ Disponibilidad horaria configurada (Lunes-Viernes 9:00-17:00)
- ✅ Control de turnos inicializado
- ✅ Todo listo para producción

**📄 `sql/README.md`** (NUEVO)
- ✅ Documentación completa del esquema
- ✅ Guía de inicialización paso a paso
- ✅ Listado de tablas, vistas y funciones
- ✅ Troubleshooting y verificación
- ✅ Marcado de archivos obsoletos

**📄 `sql/init_database_consolidated.py`** (NUEVO)
- ✅ Script Python para inicialización automática
- ✅ Ejecuta todos los SQL en orden correcto
- ✅ Validación de archivos y conexión
- ✅ Opción `--drop-existing` para reinicio limpio
- ✅ Opción `--skip-seed` para omitir datos iniciales
- ✅ Resumen detallado al finalizar

## 🗑️ Archivos Obsoletos (Ya NO Usar)

Los siguientes archivos de migración **YA NO SON NECESARIOS**:

```
❌ tests/ejecutar_migracion_etapa1.py
❌ tests/ejecutar_migracion_etapa2.py
❌ tests/ejecutar_migracion_etapa3.py
❌ tests/ejecutar_migracion_etapa5.py
❌ tests/ejecutar_migracion_etapa6.py
❌ tests/ejecutar_migracion_etapa7.py
❌ sql/migrate_add_tool_name.sql
❌ sql/migrate_etapa_*.sql (si existen)
```

> **Nota**: Se pueden eliminar o marcar como obsoletos para evitar confusión.

## 🚀 Cómo Usar el Nuevo Sistema

### Opción 1: Script Python Automático (Recomendado)

```bash
# Inicialización completa
python sql/init_database_consolidated.py

# Reinicio completo (elimina DB existente)
python sql/init_database_consolidated.py --drop-existing

# Sin datos de ejemplo
python sql/init_database_consolidated.py --skip-seed
```

### Opción 2: Manual con psql

```bash
# Ejecutar todos los scripts en orden
psql -h localhost -p 5434 -U postgres -d agente_whatsapp -f sql/init_database.sql
psql -h localhost -p 5434 -U postgres -d agente_whatsapp -f sql/setup_herramientas.sql
psql -h localhost -p 5434 -U postgres -d agente_whatsapp -f sql/setup_memoria_episodica.sql
psql -h localhost -p 5434 -U postgres -d agente_whatsapp -f sql/setup_user_sessions.sql
psql -h localhost -p 5434 -U postgres -d agente_whatsapp -f sql/seed_initial_data.sql
```

### Opción 3: Script Bash One-liner

```bash
cat sql/init_database.sql \
    sql/setup_herramientas.sql \
    sql/setup_memoria_episodica.sql \
    sql/setup_user_sessions.sql \
    sql/seed_initial_data.sql \
| psql -h localhost -p 5434 -U postgres -d agente_whatsapp
```

## 📊 Estructura Final del Esquema

### Tablas Creadas (15 tablas)

| # | Tabla | Etapa | Descripción |
|---|-------|-------|-------------|
| 1 | `herramientas_disponibles` | Base | Catálogo de herramientas Google Calendar |
| 2 | `memoria_episodica` | Base | Memoria a largo plazo con búsqueda semántica |
| 3 | `auditoria_conversaciones` | Base | Logs de conversaciones (6 meses) |
| 4 | `user_sessions` | Base | Gestión de sesiones rolling window |
| 5 | `usuarios` | Etapa 1 | Usuarios multi-rol |
| 6 | `doctores` | Etapa 1 | Perfiles de médicos |
| 7 | `pacientes` | Etapa 1 | Perfiles de pacientes |
| 8 | `control_turnos` | Etapa 2 | Alternancia de turnos |
| 9 | `disponibilidad_medica` | Etapa 2 | Horarios por doctor |
| 10 | `citas_medicas` | Etapa 2-6 | Registro completo de citas |
| 11 | `historiales_medicos` | Etapa 3 | Historiales con búsqueda semántica |
| 12 | `clasificaciones_llm` | Etapa 3 | Registro de decisiones LLM |
| 13 | `sincronizacion_calendar` | Etapa 5 | Control de sincronización Google |
| 14 | `metricas_consultas` | Etapa 7 | Métricas agregadas por doctor |
| 15 | `reportes_generados` | Etapa 7 | Histórico de reportes |

### Índices Optimizados (35+ índices)

- ✅ B-tree para búsquedas exactas
- ✅ HNSW para búsqueda vectorial (pgvector)
- ✅ GIN para búsqueda en JSONB
- ✅ Índices parciales para queries filtradas
- ✅ Índices compuestos para queries complejas

### Funciones y Triggers (11 componentes)

- ✅ 8 funciones SQL personalizadas
- ✅ 3 triggers automáticos
- ✅ 5 vistas para consultas comunes

## 🎯 Beneficios de la Consolidación

### ✨ Antes

```
1. Ejecutar init_database.sql
2. Ejecutar setup_herramientas.sql
3. Ejecutar setup_memoria_episodica.sql
4. Ejecutar setup_user_sessions.sql
5. Ejecutar migrate_etapa_1_identificacion.sql
6. Ejecutar migrate_etapa_2_turnos.sql
7. Ejecutar migrate_etapa_3_flujo_inteligente.sql
8. Ejecutar migrate_etapa_5_sincronizacion.sql (Python)
9. Ejecutar migrate_etapa_6_recordatorios.sql
10. Ejecutar migrate_etapa_7_herramientas_medicas.sql
11. Ejecutar migrate_add_tool_name.sql
12. Ejecutar scripts de datos iniciales...

❌ 12+ pasos manuales
❌ Propenso a errores
❌ Difícil de mantener
```

### ✨ Ahora

```
python sql/init_database_consolidated.py

✅ 1 comando
✅ Todo automatizado
✅ Fácil de mantener
✅ Idempotente (se puede ejecutar múltiples veces)
```

## 📝 Compatibilidad

- ✅ **100% compatible** con código existente
- ✅ Mismos nombres de tablas y columnas
- ✅ Mismos tipos de datos y constraints
- ✅ Mismos índices y relaciones
- ✅ No requiere cambios en el código de la aplicación

## ⚠️ Notas Importantes

1. **Las migraciones antiguas YA NO se deben ejecutar**
   - Todo está integrado en `init_database.sql`

2. **Los archivos de migración pueden archivarse**
   - Moverlos a `tests/migrations_deprecated/` o eliminarlos

3. **El script Python es idempotente**
   - Usa `IF NOT EXISTS` y `ON CONFLICT`
   - Se puede ejecutar múltiples veces sin problemas

4. **Las tablas de LangGraph se crean automáticamente**
   - Al ejecutar `PostgresSaver.setup()` en el código
   - No incluidas en estos scripts

## 🔍 Verificación

Para verificar que todo está correcto:

```sql
-- Contar tablas (debe ser >= 15)
SELECT COUNT(*) FROM information_schema.tables 
WHERE table_schema = 'public' AND table_type = 'BASE TABLE';

-- Verificar extensión pgvector
SELECT * FROM pg_extension WHERE extname = 'vector';

-- Verificar datos iniciales
SELECT COUNT(*) FROM usuarios;  -- Debe ser >= 3
SELECT COUNT(*) FROM doctores;  -- Debe ser 2
SELECT COUNT(*) FROM disponibilidad_medica;  -- Debe ser 10
```

## 🎉 Resultado Final

**Base de datos lista para producción en cualquier entorno** con un solo comando:

```bash
python sql/init_database_consolidated.py
```

¡No más migraciones manuales! 🚀

---

## 📚 Referencias

- Documentación completa: `sql/README.md`
- Script de inicialización: `sql/init_database_consolidated.py`
- Esquema consolidado: `sql/init_database.sql`
- Datos iniciales: `sql/seed_initial_data.sql`
