# 🔧 Setup de PostgreSQL + pgvector

Este documento explica cómo configurar la base de datos PostgreSQL con extensión pgvector para el Nodo 3 (Memoria Episódica) y Nodo 4 (Memoria Procedimental).

---

## 📦 Requisitos

- **PostgreSQL 12+** instalado localmente o en servidor
- **pgvector extension** para búsquedas de similitud vectorial
- Acceso con permisos para crear bases de datos y extensiones

---

## 🚀 Instalación Rápida

### Windows

1. **Descargar PostgreSQL:**
   ```
   https://www.postgresql.org/download/windows/
   ```
   Instala PostgreSQL con pgAdmin incluido.

2. **Instalar pgvector:**
   ```powershell
   # Descargar desde GitHub releases
   https://github.com/pgvector/pgvector/releases
   
   # O compilar desde fuente (requiere Visual Studio)
   git clone https://github.com/pgvector/pgvector.git
   cd pgvector
   nmake /F Makefile.win
   nmake /F Makefile.win install
   ```

### Linux/Mac

```bash
# Instalar PostgreSQL
sudo apt-get install postgresql postgresql-contrib  # Ubuntu/Debian
brew install postgresql  # macOS

# Instalar pgvector
git clone --branch v0.5.1 https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install
```

---

## 🗄️ Configuración de Base de Datos

### Paso 1: Crear Base de Datos

```bash
# Conectar como superusuario
psql -U postgres

# Crear base de datos
CREATE DATABASE calendar_agent;

# Conectar a la BD
\c calendar_agent

# Crear extensión pgvector
CREATE EXTENSION vector;

# Verificar instalación
\dx
```

Deberías ver `vector` en la lista de extensiones.

### Paso 2: Ejecutar Scripts SQL

```bash
# Desde la raíz del proyecto
psql -U postgres -d calendar_agent -f sql/setup_herramientas.sql
```

El script crea:
- Tabla `herramientas_disponibles` con 5 herramientas de Google Calendar
- Índices para búsqueda rápida
- Inserción de datos iniciales

### Paso 3: Verificar Tablas

```sql
-- Conectar a la BD
psql -U postgres -d calendar_agent

-- Listar tablas
\dt

-- Ver herramientas
SELECT id_tool, description, activa 
FROM herramientas_disponibles;
```

Salida esperada:
```
          id_tool          |                description                 | activa 
---------------------------+-------------------------------------------+--------
 create_calendar_event     | Crear nuevos eventos con título, fecha...  | t
 list_calendar_events      | Listar eventos para ver la agenda en...    | t
 update_calendar_event     | Modificar la hora, título o detalles...    | t
 delete_calendar_event     | Eliminar un evento específico del...       | t
 search_calendar_events    | Buscar eventos por palabras clave en...    | t
```

---

## ⚙️ Configurar Variables de Entorno

Copia `.env.example` a `.env` y configura:

```bash
cp .env.example .env
```

Edita `.env`:

```env
# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=calendar_agent
POSTGRES_USER=postgres
POSTGRES_PASSWORD=TU_PASSWORD_AQUI
```

---

## 🧪 Verificar Conexión

Ejecuta el test de conexión:

```bash
# Con entorno virtual activado
.\venv\Scripts\python.exe -c "from src.database import test_connection; test_connection()"
```

Salida esperada:
```
✅ Conexión a PostgreSQL exitosa
```

---

## 📊 Crear Tabla de Memoria Episódica (Opcional)

Para el Nodo 3 (búsquedas semánticas), crea la tabla de episodios:

```sql
-- Conectar a calendar_agent
psql -U postgres -d calendar_agent

-- Crear tabla memoria_episodica
CREATE TABLE memoria_episodica (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    session_id VARCHAR(255) NOT NULL,
    resumen TEXT NOT NULL,
    embedding vector(384),  -- pgvector: 384 dimensiones
    tipo VARCHAR(50) DEFAULT 'EPISODIO_NORMAL',
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB
);

-- Índice para búsqueda vectorial eficiente
CREATE INDEX idx_memoria_embedding 
ON memoria_episodica 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

-- Índice para filtrado por usuario
CREATE INDEX idx_memoria_user 
ON memoria_episodica(user_id);

-- Verificar
\d memoria_episodica
```

---

## 🔍 Query de Prueba (Búsqueda Vectorial)

```sql
-- Insertar un episodio de prueba (embedding dummy)
INSERT INTO memoria_episodica (user_id, session_id, resumen, embedding)
VALUES (
    'test_user',
    'session_001',
    'Usuario agendó reunión con equipo de ventas para el martes',
    '[0.1, 0.2, 0.3, ..., 0.4]'::vector(384)
);

-- Buscar episodios similares (ejemplo con vector dummy)
SELECT 
    id, 
    resumen, 
    timestamp,
    1 - (embedding <=> '[0.1, 0.2, ..., 0.4]'::vector(384)) AS similitud
FROM memoria_episodica
WHERE user_id = 'test_user'
  AND 1 - (embedding <=> '[0.1, 0.2, ..., 0.4]'::vector(384)) >= 0.7
ORDER BY embedding <=> '[0.1, 0.2, ..., 0.4]'::vector(384) ASC
LIMIT 3;
```

Nota: Los embeddings reales son generados por `sentence-transformers`.

---

## 🛠️ Troubleshooting

### Error: "connection refused"
```
❌ connection to server at "localhost", port 5432 failed
```

**Solución:**
1. Verificar que PostgreSQL está corriendo:
   ```bash
   # Windows
   Get-Service postgresql*
   
   # Linux
   sudo systemctl status postgresql
   ```

2. Iniciar servicio si está detenido:
   ```bash
   # Windows (como Admin)
   Start-Service postgresql-x64-15
   
   # Linux
   sudo systemctl start postgresql
   ```

### Error: "extension vector does not exist"
```
❌ ERROR: extension "vector" does not exist
```

**Solución:**
Instalar pgvector siguiendo pasos en sección de instalación.

### Error: "password authentication failed"
```
❌ FATAL: password authentication failed for user "postgres"
```

**Solución:**
1. Resetear password:
   ```bash
   # Windows (como Admin, en bin de PostgreSQL)
   psql -U postgres
   ALTER USER postgres PASSWORD 'nueva_password';
   
   # Linux
   sudo -u postgres psql
   ALTER USER postgres PASSWORD 'nueva_password';
   ```

2. Actualizar `.env` con la nueva password.

---

## 📈 Optimizaciones (Producción)

### 1. Connection Pooling
```python
# En src/database/db_procedimental.py
from psycopg2 import pool

connection_pool = pool.SimpleConnectionPool(
    minconn=1,
    maxconn=10,
    host=POSTGRES_HOST,
    ...
)
```

### 2. Índices Adicionales
```sql
-- Índice para búsquedas por timestamp
CREATE INDEX idx_memoria_timestamp 
ON memoria_episodica(timestamp DESC);

-- Índice compuesto para filtros frecuentes
CREATE INDEX idx_memoria_user_timestamp 
ON memoria_episodica(user_id, timestamp DESC);
```

### 3. Particionamiento (para alto volumen)
```sql
-- Particionar por mes
CREATE TABLE memoria_episodica_2026_01 PARTITION OF memoria_episodica
FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
```

---

## ✅ Verificación Final

Ejecuta el test completo del Nodo 4:

```bash
.\venv\Scripts\python.exe test_nodo4_seleccion.py
```

Si la conexión a PostgreSQL está configurada correctamente, deberías ver:
```
✅ Cargadas 5 herramientas desde PostgreSQL
```

En lugar de:
```
⚠️  Usando herramientas hardcoded (fallback)
```

---

## 📞 Soporte

Si tienes problemas con la instalación:
1. Verifica logs de PostgreSQL en `C:\Program Files\PostgreSQL\15\data\log\` (Windows)
2. Consulta documentación oficial: https://www.postgresql.org/docs/
3. pgvector GitHub: https://github.com/pgvector/pgvector

---

**Siguiente paso:** Una vez configurada la BD, el agente usará memoria procedimental real y podrás agregar/modificar herramientas desde SQL sin tocar código.
