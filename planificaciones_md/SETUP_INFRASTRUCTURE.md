# 🚀 Guía de Inicialización - Infraestructura Completa

## 📋 Resumen

Esta guía te llevará desde **cero hasta producción** en 5 minutos.

Al finalizar tendrás:
- ✅ PostgreSQL 16 + pgvector corriendo en Docker (puerto 5434)
- ✅ 4 tablas configuradas (herramientas, memoria, auditoría, checkpoints)
- ✅ PostgresSaver de LangGraph activo (caché 24h)
- ✅ Agente listo para recordar conversaciones entre sesiones

---

## ⚡ Inicio Rápido (5 minutos)

### 1️⃣ Verificar Requisitos

```powershell
# Docker Desktop debe estar corriendo
docker --version
# Debe mostrar: Docker version 20.10+ 

# Python 3.12+ instalado
python --version
```

---

### 2️⃣ Ejecutar Script de Setup

```powershell
# Instalar dependencias primero
pip install -r requirements.txt

# Ejecutar setup automático
python setup_infrastructure.py
```

El script hará **TODO automáticamente**:
- ✅ Levanta Docker Compose
- ✅ Espera a que PostgreSQL esté listo
- ✅ Verifica que las 4 tablas se crearon
- ✅ Instala `langgraph-checkpoint-postgres` y `psycopg`
- ✅ Prueba conexión desde Python
- ✅ Configura PostgresSaver (crea tablas de LangGraph)

**Salida esperada:**
```
🚀 SETUP DE INFRAESTRUCTURA - AGENTE WHATSAPP
==============================================================================

🔹 Paso 1: Verificando Docker Desktop
   ✅ Docker instalado - OK
   ✅ Docker Desktop corriendo - OK

🔹 Paso 2: Levantando contenedor PostgreSQL + pgvector
   ✅ docker-compose up -d - OK
   ✅ Contenedor 'agente-whatsapp-db' corriendo

...

✅ INFRAESTRUCTURA LISTA
==============================================================================
```

---

### 3️⃣ Verificar Base de Datos

```powershell
# Entrar al contenedor PostgreSQL
docker exec -it agente-whatsapp-db psql -U admin -d agente_whatsapp

# Ver tablas creadas
\dt

# Salida esperada:
#  public | auditoria_conversaciones  | table | admin
#  public | checkpoint_blobs          | table | admin
#  public | checkpoint_writes         | table | admin
#  public | checkpoints               | table | admin
#  public | herramientas_disponibles  | table | admin
#  public | memoria_episodica         | table | admin

# Ver herramientas disponibles
SELECT nombre FROM herramientas_disponibles;

# Salir
\q
```

---

### 4️⃣ Ejecutar Test End-to-End

```powershell
# Ahora los tests usarán PostgreSQL real
python test_end_to_end.py
```

**Cambios esperados en el output:**
```diff
- [ERROR] Error conectando a PostgreSQL: connection refused
- [WARNING] Usando herramientas hardcoded (fallback)

+ [INFO] ✅ PostgresSaver configurado (checkpoints)
+ [INFO] Herramientas cargadas desde PostgreSQL: 5
+ [INFO] Resumen guardado en memoria_episodica (id=1)
```

---

## 🗂️ Estructura de Base de Datos

### Tabla 1: `herramientas_disponibles` (Memoria Procedimental)
```sql
CREATE TABLE herramientas_disponibles (
    id_tool SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE,
    descripcion TEXT NOT NULL,
    parametros JSONB DEFAULT '{}'::jsonb,
    activa BOOLEAN DEFAULT true
);

-- 5 herramientas pre-cargadas:
-- 1. list_calendar_events
-- 2. create_calendar_event
-- 3. update_calendar_event
-- 4. delete_calendar_event
-- 5. get_event_details
```

---

### Tabla 2: `memoria_episodica` (Memoria a Largo Plazo)
```sql
CREATE TABLE memoria_episodica (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    resumen TEXT NOT NULL,
    embedding vector(384) NOT NULL,  -- Embeddings de 384 dims
    metadata JSONB DEFAULT '{}'::jsonb,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índice HNSW para búsqueda semántica ultra-rápida
CREATE INDEX idx_memoria_embedding_hnsw 
ON memoria_episodica 
USING hnsw (embedding vector_cosine_ops);
```

**Función helper para búsqueda:**
```sql
SELECT * FROM buscar_memorias_similares(
    'user_123',                  -- user_id
    '[0.1, 0.2, ...]'::vector,  -- embedding del mensaje
    5                            -- top-5 resultados
);
```

---

### Tabla 3: `auditoria_conversaciones` (Logs Planos)
```sql
CREATE TABLE auditoria_conversaciones (
    id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    session_id VARCHAR(200) NOT NULL,
    rol VARCHAR(20) NOT NULL,  -- 'user', 'assistant', 'system'
    contenido TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Retención: 6 meses (limpieza manual)
-- Función: limpiar_auditoria_antigua()
```

---

### Tablas 4-6: LangGraph Checkpoints (Caché 24h)
```sql
-- Creadas automáticamente por PostgresSaver.setup()

checkpoints          -- Estado completo de cada sesión
checkpoint_writes    -- Escrituras pendientes
checkpoint_blobs     -- Datos grandes serializados
```

**TTL automático:** 24 horas (configurado en LangGraph)

---

## 🔧 Configuración Detallada

### Variables de Entorno (`.env`)
```bash
# LLMs
DEEPSEEK_API_KEY=sk-c6bd351...
ANTHROPIC_API_KEY=sk-ant-api03-...
TESTSPRITE_API_KEY=sk-user-aIJZe...

# PostgreSQL (Puerto 5434 = disponible)
DATABASE_URL=postgresql://admin:password123@localhost:5434/agente_whatsapp
POSTGRES_HOST=localhost
POSTGRES_PORT=5434
POSTGRES_DB=agente_whatsapp
POSTGRES_USER=admin
POSTGRES_PASSWORD=password123

# Google Calendar OAuth2
GOOGLE_CALENDAR_CREDENTIALS=credentials.json
GOOGLE_CALENDAR_TOKEN=token.json

# Timezone
TZ=America/Tijuana
```

---

### Docker Compose (puerto 5434)
```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16
    ports:
      - "5434:5432"  # EXTERNO:INTERNO
    environment:
      POSTGRES_DB: agente_whatsapp
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: password123
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./sql/init_database.sql:/docker-entrypoint-initdb.d/init_database.sql
```

**Script de inicialización:** `sql/init_database.sql` se ejecuta automáticamente al crear el contenedor.

---

## 📊 Integración con LangGraph

### Código en `graph_whatsapp.py`
```python
from langgraph.checkpoint.postgres import PostgresSaver
import psycopg

def crear_grafo():
    # ... construcción del grafo ...
    
    # Configurar PostgresSaver
    database_url = os.getenv("DATABASE_URL")
    conn = psycopg.connect(database_url)
    
    checkpointer = PostgresSaver(conn)
    checkpointer.setup()  # Crea tablas de LangGraph
    
    # Compilar con persistencia
    graph = builder.compile(checkpointer=checkpointer)
    
    return graph
```

---

### Comportamiento con Checkpointer

**ANTES (sin PostgreSQL):**
```python
graph.invoke(estado)
# Cada invocación es independiente
# Sin memoria entre ejecuciones
```

**AHORA (con PostgresSaver):**
```python
# Primera llamada
graph.invoke(estado, config={"configurable": {"thread_id": "user_123"}})
# Estado guardado en checkpoints

# Segunda llamada (recupera estado anterior)
graph.invoke(estado, config={"configurable": {"thread_id": "user_123"}})
# Continúa desde donde se quedó (memoria 24h)
```

---

## 🛠️ Comandos Útiles

### Docker
```powershell
# Ver logs en tiempo real
docker logs -f agente-whatsapp-db

# Detener contenedor
docker-compose down

# Reiniciar contenedor
docker-compose restart

# Eliminar TODO (incluyendo volumen)
docker-compose down -v
```

---

### PostgreSQL
```powershell
# Entrar a psql
docker exec -it agente-whatsapp-db psql -U admin -d agente_whatsapp

# Queries útiles:
\dt                          # Listar tablas
\d+ memoria_episodica        # Describir tabla
SELECT COUNT(*) FROM checkpoints;  # Ver sesiones guardadas
SELECT * FROM herramientas_disponibles;  # Ver herramientas

# Limpiar auditoría antigua (>6 meses)
SELECT limpiar_auditoria_antigua();
```

---

### Python
```powershell
# Test de conexión rápido
python -c "import psycopg; conn = psycopg.connect('postgresql://admin:password123@localhost:5434/agente_whatsapp'); print('✅ Conexión OK')"

# Ver tablas desde Python
python -c "
import psycopg
conn = psycopg.connect('postgresql://admin:password123@localhost:5434/agente_whatsapp')
cur = conn.cursor()
cur.execute('SELECT tablename FROM pg_tables WHERE schemaname=\'public\'')
print('\n'.join([t[0] for t in cur.fetchall()]))
"
```

---

## 🐛 Troubleshooting

### Error: "Port 5434 already in use"
```powershell
# Ver qué proceso usa el puerto
netstat -ano | findstr :5434

# Opción 1: Cambiar puerto en docker-compose.yaml
ports:
  - "5435:5432"  # Usar 5435 en vez de 5434

# Opción 2: Matar proceso que ocupa 5434
taskkill /PID <PID> /F
```

---

### Error: "Docker daemon not running"
```powershell
# Abrir Docker Desktop manualmente
# O desde PowerShell:
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
```

---

### Error: "Extension vector not found"
```powershell
# Verificar imagen correcta
docker exec agente-whatsapp-db psql -U admin -d agente_whatsapp -c "SELECT * FROM pg_available_extensions WHERE name='vector';"

# Si no aparece, usar imagen pgvector/pgvector:pg16
# Ya está configurado en docker-compose.yaml
```

---

### Error: "PostgresSaver setup failed"
```powershell
# Reinstalar dependencia
pip uninstall langgraph-checkpoint-postgres
pip install langgraph-checkpoint-postgres

# Verificar instalación
pip show langgraph-checkpoint-postgres
```

---

## 📈 Verificar que Todo Funciona

### Checklist Completo
```powershell
# ✅ 1. Docker corriendo
docker ps | findstr agente-whatsapp-db

# ✅ 2. PostgreSQL responde
docker exec agente-whatsapp-db pg_isready -U admin

# ✅ 3. Base de datos creada
docker exec agente-whatsapp-db psql -U admin -l | findstr agente_whatsapp

# ✅ 4. Extensión pgvector instalada
docker exec agente-whatsapp-db psql -U admin -d agente_whatsapp -c "SELECT extname FROM pg_extension WHERE extname='vector';"

# ✅ 5. Tablas creadas (6 tablas esperadas)
docker exec agente-whatsapp-db psql -U admin -d agente_whatsapp -c "\dt" | findstr /C:"public"

# ✅ 6. Herramientas cargadas (5 registros)
docker exec agente-whatsapp-db psql -U admin -d agente_whatsapp -c "SELECT COUNT(*) FROM herramientas_disponibles;"

# ✅ 7. Python puede conectar
python -c "import psycopg; psycopg.connect('postgresql://admin:password123@localhost:5434/agente_whatsapp'); print('✅ OK')"

# ✅ 8. Test end-to-end pasa
python test_end_to_end.py
```

Si **TODOS** los pasos muestran ✅, tu infraestructura está **100% funcional**.

---

## 🎯 Próximos Pasos

1. **Ejecutar Agente:**
   ```powershell
   python app.py
   # O interfaz web:
   streamlit run streamlit.py
   ```

2. **Integrar WhatsApp Business API:**
   - Ver `PRD.md` sección "F-005: Integración WhatsApp Business API"

3. **Monitoreo en Producción:**
   - Configurar pg_cron para limpieza automática
   - Configurar backups diarios
   - Agregar logging estructurado (Sentry, DataDog)

---

## 📚 Documentación Adicional

- **LangGraph Persistence:** https://langchain-ai.github.io/langgraph/how-tos/persistence/
- **pgvector GitHub:** https://github.com/pgvector/pgvector
- **PostgreSQL en Docker:** https://hub.docker.com/_/postgres

---

**¿Problemas?** Revisa `ANALISIS_TESTS.md` o abre un issue en el repo. 🚀
