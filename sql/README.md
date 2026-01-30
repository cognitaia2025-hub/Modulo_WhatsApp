# 📊 Esquema de Base de Datos Consolidado

## 🎯 Resumen

Este directorio contiene el **esquema consolidado** de la base de datos del proyecto. **Ya no es necesario ejecutar migraciones por separado** - todos los cambios de las Etapas 1-7 están integrados en los scripts SQL base.

## 📁 Archivos Principales

### 🔧 Scripts de Inicialización

| Archivo | Descripción | Orden de Ejecución |
|---------|-------------|-------------------|
| `init_database.sql` | **Script maestro** con todas las tablas consolidadas | 1️⃣ |
| `setup_herramientas.sql` | Configuración de herramientas disponibles | 2️⃣ |
| `setup_memoria_episodica.sql` | Sistema de memoria a largo plazo | 3️⃣ |
| `setup_user_sessions.sql` | Gestión de sesiones con rolling window | 4️⃣ |
| `seed_initial_data.sql` | Datos iniciales (admin, doctores, disponibilidad) | 5️⃣ |

### 🗑️ Archivos Obsoletos (Ya NO usar)

| Archivo | Status | Razón |
|---------|--------|-------|
| `migrate_add_tool_name.sql` | ⚠️ **OBSOLETO** | Ya integrado en `setup_herramientas.sql` |
| Todos los `migrate_etapa_*.sql` | ⚠️ **OBSOLETOS** | Ya integrados en `init_database.sql` |

## 🗄️ Estructura del Esquema

### 1️⃣ Sistema Base (Original)
- `herramientas_disponibles` - Catálogo de herramientas de Google Calendar
- `memoria_episodica` - Memoria a largo plazo con búsqueda semántica (pgvector)
- `auditoria_conversaciones` - Logs de todas las conversaciones (6 meses)
- `user_sessions` - Control de sesiones con rolling window de 24h

### 2️⃣ Sistema de Usuarios (Etapa 1)
- `usuarios` - Tabla principal multi-rol (personal/doctor/paciente/admin)
- `doctores` - Perfiles especializados de médicos
- `pacientes` - Perfiles de pacientes con historial básico

### 3️⃣ Sistema de Turnos (Etapa 2)
- `control_turnos` - Alternancia equitativa entre doctores
- `disponibilidad_medica` - Horarios configurables por doctor

### 4️⃣ Sistema de Citas (Etapas 2-6)
- `citas_medicas` - Registro completo de citas médicas
  - Incluye campos de sincronización Google Calendar (Etapa 5)
  - Incluye campos de recordatorios (Etapa 6)

### 5️⃣ Sistema Médico Inteligente (Etapa 3)
- `historiales_medicos` - Historiales clínicos con búsqueda semántica
- `clasificaciones_llm` - Registro de decisiones del LLM
- Vistas:
  - `resumen_clasificaciones`
  - `metricas_llm_por_modelo`

### 6️⃣ Sistema de Sincronización (Etapa 5)
- `sincronizacion_calendar` - Control de sincronización bidireccional con Google Calendar
  - Incluye retry logic con backoff exponencial
  - Estados: pendiente, sincronizada, error, reintentando, error_permanente

### 7️⃣ Sistema de Métricas y Reportes (Etapa 7)
- `metricas_consultas` - Métricas diarias agregadas por doctor
- `reportes_generados` - Histórico de reportes generados
- Vista: `vista_estadisticas_doctores`

### 8️⃣ Tablas Internas LangGraph (Automáticas)
- `checkpoints` - Estado de sesiones
- `checkpoint_writes` - Escrituras pendientes
- `checkpoint_blobs` - Datos serializados grandes

> ⚠️ **Nota**: Las tablas de LangGraph se crean automáticamente al ejecutar `PostgresSaver.setup()`

## 🚀 Inicialización de Base de Datos Limpia

### Opción 1: Inicialización Completa (Recomendado)

```bash
# 1. Crear base de datos desde cero
psql -h localhost -p 5434 -U postgres -c "DROP DATABASE IF EXISTS agente_whatsapp;"
psql -h localhost -p 5434 -U postgres -c "CREATE DATABASE agente_whatsapp;"

# 2. Ejecutar esquema base
psql -h localhost -p 5434 -U postgres -d agente_whatsapp -f sql/init_database.sql

# 3. Configurar herramientas
psql -h localhost -p 5434 -U postgres -d agente_whatsapp -f sql/setup_herramientas.sql

# 4. Configurar memoria episódica
psql -h localhost -p 5434 -U postgres -d agente_whatsapp -f sql/setup_memoria_episodica.sql

# 5. Configurar sesiones
psql -h localhost -p 5434 -U postgres -d agente_whatsapp -f sql/setup_user_sessions.sql

# 6. Insertar datos iniciales
psql -h localhost -p 5434 -U postgres -d agente_whatsapp -f sql/seed_initial_data.sql
```

### Opción 2: Script Unificado (Más Rápido)

```bash
# Un solo comando que ejecuta todo en orden
cat sql/init_database.sql \
    sql/setup_herramientas.sql \
    sql/setup_memoria_episodica.sql \
    sql/setup_user_sessions.sql \
    sql/seed_initial_data.sql \
| psql -h localhost -p 5434 -U postgres -d agente_whatsapp
```

### Opción 3: Desde Python

```python
import psycopg
import os

DATABASE_URL = os.getenv("DATABASE_URL")

# Lista de archivos en orden
sql_files = [
    "sql/init_database.sql",
    "sql/setup_herramientas.sql",
    "sql/setup_memoria_episodica.sql",
    "sql/setup_user_sessions.sql",
    "sql/seed_initial_data.sql"
]

with psycopg.connect(DATABASE_URL) as conn:
    for sql_file in sql_files:
        print(f"Ejecutando {sql_file}...")
        with open(sql_file, 'r') as f:
            conn.execute(f.read())
        print(f"✅ {sql_file} completado")
    
    conn.commit()
    print("\n✅ Base de datos inicializada correctamente")
```

## 🔑 Funciones y Triggers Importantes

### Búsqueda Semántica
- `buscar_memorias_similares(user_id, embedding, limit)` - Busca memorias similares
- `buscar_historiales_semantica(paciente_id, embedding, limit)` - Busca historiales médicos

### Gestión de Sesiones
- `get_active_session(user_id)` - Obtiene sesión activa (<24h)
- `update_session_activity(user_id, thread_id)` - Actualiza timestamp
- `cleanup_old_sessions()` - Limpia sesiones antiguas (>30 días)

### Métricas y Reportes
- `actualizar_metricas_doctor(doctor_id, fecha)` - Actualiza métricas diarias
- `buscar_citas_por_periodo(doctor_id, fecha_inicio, fecha_fin)` - Busca citas

### Triggers Automáticos
- `trigger_actualizar_metricas` - Actualiza métricas al insertar/modificar citas
- `trg_prevent_user_id_change` - Previene cambios en user_id de sesiones

## 📊 Vistas Disponibles

| Vista | Descripción |
|-------|-------------|
| `auditoria_para_limpiar` | Registros >6 meses para limpieza |
| `active_sessions_24h` | Sesiones activas en las últimas 24h |
| `session_statistics` | Estadísticas generales de sesiones |
| `resumen_clasificaciones` | Resumen de clasificaciones LLM |
| `metricas_llm_por_modelo` | Métricas por modelo LLM |
| `vista_estadisticas_doctores` | Estadísticas completas por doctor |

## 🎯 Datos Iniciales Incluidos

Al ejecutar `seed_initial_data.sql` se crean:

### 👤 Usuario Administrador
- Phone: `+526641234567`
- Tipo: `admin`

### 👨‍⚕️ Doctores
| ID | Nombre | Teléfono | Especialidad |
|----|--------|----------|--------------|
| 1 | Dr. Santiago de Jesús Ornelas Reynoso | +526641111111 | Medicina General |
| 2 | Dra. Joana Ibeth Meraz Arregín | +526647654321 | Medicina General |

### ⏰ Disponibilidad
- **Horario**: Lunes-Viernes 9:00-17:00
- **Duración de cita**: 30 minutos
- **Capacidad**: 16 pacientes/día por doctor

## ⚠️ Migraciones Obsoletas

Los siguientes scripts **YA NO DEBEN USARSE** (ya están integrados):

```
tests/ejecutar_migracion_etapa1.py  ❌
tests/ejecutar_migracion_etapa2.py  ❌
tests/ejecutar_migracion_etapa3.py  ❌
tests/ejecutar_migracion_etapa5.py  ❌
tests/ejecutar_migracion_etapa6.py  ❌
tests/ejecutar_migracion_etapa7.py  ❌
```

## 🔍 Verificación del Esquema

Para verificar que todo está correctamente instalado:

```sql
-- Contar todas las tablas del sistema
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;

-- Verificar extensiones
SELECT * FROM pg_extension WHERE extname = 'vector';

-- Verificar funciones creadas
SELECT 
    proname AS function_name,
    pg_get_functiondef(oid) AS definition
FROM pg_proc
WHERE pronamespace = 'public'::regnamespace
    AND proname LIKE '%buscar%'
ORDER BY proname;
```

## 📝 Notas de Compatibilidad

- ✅ Compatible con PostgreSQL 14+
- ✅ Requiere extensión `pgvector`
- ✅ Todas las columnas agregadas en migraciones están incluidas
- ✅ Todos los índices optimizados están creados
- ✅ Todas las constraints y checks están configurados

## 🆘 Troubleshooting

### Error: "extension vector does not exist"
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### Error: "relation already exists"
- Normal si ejecutas los scripts múltiples veces
- Todos los scripts usan `IF NOT EXISTS` y `ON CONFLICT`

### Verificar versión de schema
```sql
SELECT 
    COUNT(DISTINCT table_name) as total_tablas,
    string_agg(DISTINCT table_name::text, ', ' ORDER BY table_name::text) as tablas
FROM information_schema.tables
WHERE table_schema = 'public' 
    AND table_type = 'BASE TABLE';
```

Deberías ver: `auditoria_conversaciones, citas_medicas, clasificaciones_llm, control_turnos, disponibilidad_medica, doctores, herramientas_disponibles, historiales_medicos, memoria_episodica, metricas_consultas, pacientes, reportes_generados, sincronizacion_calendar, user_sessions, usuarios`

## 🎉 Resumen

**Antes**: 7 migraciones separadas + scripts base = Configuración compleja

**Ahora**: 5 scripts SQL en orden = Base de datos lista ✨

¡No más migraciones! Todo está consolidado y listo para usar en cualquier ambiente.
