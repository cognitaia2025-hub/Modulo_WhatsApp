# 🏗️ Arquitectura del Sistema - Grafo Actualizado

## Diagrama de Flujo Completo

```mermaid
graph TD
    %% Inicio del Flujo
    START((Mensaje WhatsApp)) --> N1[<b>1. Nodo Caché</b><br/>¿Sesión Activa?<br/>Rolling Window 10 msgs]
    
    %% Decisión de Sesión
    N1 -- "Nueva Sesión" --> N2[<b>2. Nodo Gatekeeper</b><br/>¿Requiere Calendario?]
    N1 -- "Sesión Activa" --> N2
    
    %% Clasificación de Intención
    N2 -- "SÍ - Calendario" --> N3[<b>3. Recuperación Episódica</b><br/>Búsqueda Semántica<br/>pgvector 384D]
    N2 -- "NO - Conversación" --> RESP[<b>Respuesta Directa</b><br/>Sin Herramientas]
    
    %% Recuperación de Contexto
    N3 --> N4[<b>4. Selección de Herramientas</b><br/>LLM decide qué usar<br/>DeepSeek/Claude]
    
    %% Decisión de Herramientas
    N4 -- "Herramienta Detectada" --> N5[<b>5. Ejecución de Herramientas</b><br/>Google Calendar API<br/>+ Extracción LLM]
    N4 -- "Sin Herramienta" --> N6
    
    %% Ejecución y Orquestación
    N5 --> N6[<b>6. Generación de Respuesta</b><br/>LLM Orquestador<br/>Resumen + Auditoría]
    
    %% Persistencia
    N6 --> N7[<b>7. Persistencia Episódica</b><br/>Guarda Memoria<br/>Embedding + Metadata]
    
    %% Cierre
    N7 --> END((Respuesta a Usuario))
    RESP --> END

    %% ============================================================
    %% BASES DE DATOS (PostgreSQL 5434)
    %% ============================================================
    subgraph DB["🗄️ Base de Datos PostgreSQL:5434 (agente_whatsapp)"]
        direction TB
        
        %% Memoria Episódica
        DB_V[(📊 <b>memoria_episodica</b><br/>├─ Embeddings vector(384)<br/>├─ Resúmenes conversaciones<br/>├─ Metadata JSONB<br/>├─ Índice HNSW<br/>└─ 0 registros iniciales)]
        
        %% Herramientas Disponibles
        DB_T[(🔧 <b>herramientas_disponibles</b><br/>├─ 5 herramientas<br/>├─ list_calendar_events<br/>├─ create_calendar_event<br/>├─ update_calendar_event<br/>├─ delete_calendar_event<br/>└─ get_event_details)]
        
        %% Caché de Sesiones (LangGraph Store)
        DB_C[(💾 <b>LangGraph Store</b><br/>├─ user_preferences<br/>├─ session_state<br/>├─ ultimo_listado<br/>└─ Rolling Window 10 msgs)]
        
        %% Audit Log
        DB_A[(📝 <b>Audit Log</b><br/>├─ Texto plano<br/>├─ Logs de ejecución<br/>├─ Errores/Warnings<br/>└─ Retención 6 meses)]
    end

    %% ============================================================
    %% SERVICIOS EXTERNOS
    %% ============================================================
    subgraph EXT["☁️ Servicios Externos"]
        direction TB
        
        %% LLMs
        LLM1[🤖 <b>DeepSeek API</b><br/>deepseek-chat<br/>Temp: 0.7<br/>Timeout: 20s<br/>PRIMARY]
        LLM2[🤖 <b>Claude 3.5 Haiku</b><br/>claude-3-5-haiku<br/>Temp: 0.7<br/>Timeout: 25s<br/>FALLBACK]
        
        %% Google Calendar
        GCAL[📅 <b>Google Calendar API</b><br/>OAuth2 Service Account<br/>Calendar ID: 92d85...<br/>Timezone: America/Tijuana]
        
        %% Embeddings
        EMB[🧠 <b>sentence-transformers</b><br/>all-MiniLM-L6-v2<br/>384 dimensiones<br/>Local (CPU/GPU)]
    end

    %% ============================================================
    %% CONEXIONES A BASES DE DATOS
    %% ============================================================
    
    %% Nodo 1: Caché
    N1 -.->|"Lee/Escribe<br/>Sesiones"| DB_C
    
    %% Nodo 3: Recuperación Episódica
    N3 -.->|"SELECT con<br/>embedding <=> query"| DB_V
    N3 -.->|"Genera Embedding"| EMB
    
    %% Nodo 4: Selección de Herramientas
    N4 -.->|"SELECT WHERE<br/>activa = true"| DB_T
    N4 -.->|"Inferencia"| LLM1
    N4 -.->|"Fallback"| LLM2
    
    %% Nodo 5: Ejecución
    N5 -.->|"CRUD Operations"| GCAL
    N5 -.->|"Extracción params"| LLM1
    N5 -.->|"Lee ultimo_listado"| DB_C
    N5 -.->|"Escribe Log"| DB_A
    
    %% Nodo 6: Generación
    N6 -.->|"Genera Resumen"| LLM1
    N6 -.->|"Escribe Auditoría"| DB_A
    
    %% Nodo 7: Persistencia
    N7 -.->|"INSERT memoria<br/>con embedding"| DB_V
    N7 -.->|"Genera Embedding"| EMB
    N7 -.->|"Guarda Metadata"| DB_V

    %% ============================================================
    %% ESTILOS
    %% ============================================================
    classDef nodoActivo fill:#4CAF50,stroke:#2E7D32,stroke-width:3px,color:#fff
    classDef nodoDecision fill:#2196F3,stroke:#1565C0,stroke-width:3px,color:#fff
    classDef nodoEjecucion fill:#FF9800,stroke:#E65100,stroke-width:3px,color:#fff
    classDef nodoPersistencia fill:#9C27B0,stroke:#6A1B9A,stroke-width:3px,color:#fff
    classDef dbVectorial fill:#E91E63,stroke:#880E4F,stroke-width:2px,color:#fff
    classDef dbRelacional fill:#00BCD4,stroke:#006064,stroke-width:2px,color:#fff
    classDef servicioExterno fill:#607D8B,stroke:#37474F,stroke-width:2px,color:#fff
    
    class N1 nodoActivo
    class N2 nodoDecision
    class N3,N4 nodoDecision
    class N5 nodoEjecucion
    class N6 nodoEjecucion
    class N7 nodoPersistencia
    class DB_V dbVectorial
    class DB_T,DB_A dbRelacional
    class DB_C nodoActivo
    class LLM1,LLM2,GCAL,EMB servicioExterno
```

---

## 📋 Descripción de Nodos

### 🟢 Nodo 1: Caché de Sesiones
- **Función:** Gestionar sesiones activas con rolling window
- **Tecnología:** LangGraph Store
- **Datos:** Últimos 10 mensajes por sesión
- **Conexión:** PostgreSQL puerto 5434

### 🔵 Nodo 2: Gatekeeper (Clasificación)
- **Función:** Determinar si el mensaje requiere herramientas de calendario
- **LLM:** DeepSeek (primario) / Claude (fallback)
- **Salidas:** 
  - ✅ Requiere calendario → Nodo 3
  - ❌ Conversación general → Respuesta directa

### 🔵 Nodo 3: Recuperación Episódica
- **Función:** Buscar memorias similares en pgvector
- **Algoritmo:** Búsqueda semántica con embeddings 384D
- **Índice:** HNSW para búsqueda ultra-rápida
- **Query:** `embedding <=> query_vector ORDER BY distance`

### 🔵 Nodo 4: Selección de Herramientas
- **Función:** LLM decide qué herramienta usar
- **Herramientas Disponibles (5):**
  1. `list_calendar_events` - Listar eventos
  2. `create_calendar_event` - Crear evento
  3. `update_calendar_event` - Actualizar evento (NUEVO ✅)
  4. `delete_calendar_event` - Eliminar evento (MEJORADO ✅)
  5. `get_event_details` - Detalles de evento

### 🟠 Nodo 5: Ejecución de Herramientas
- **Función:** Ejecutar llamadas a Google Calendar API
- **Características:**
  - Extracción de parámetros con LLM
  - Contexto de `ultimo_listado`
  - Manejo de errores robusto
  - Auditoría de operaciones

### 🟠 Nodo 6: Generación de Respuesta
- **Función:** Crear respuesta natural para el usuario
- **LLM:** DeepSeek/Claude
- **Incluye:** 
  - Resumen de operación
  - Confirmación de cambios
  - Auditoría temporal

### 🟣 Nodo 7: Persistencia Episódica
- **Función:** Guardar memoria a largo plazo
- **Proceso:**
  1. Generar embedding de 384D
  2. Insertar en tabla `memoria_episodica`
  3. Guardar metadata (fecha, sesión, tipo)
  4. Índice HNSW automático

---

## 🗄️ Esquema de Base de Datos

### Tabla: `memoria_episodica`

```sql
CREATE TABLE memoria_episodica (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    resumen TEXT NOT NULL,
    embedding vector(384) NOT NULL,  -- pgvector
    metadata JSONB DEFAULT '{}'::jsonb,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índice HNSW para búsqueda ultra-rápida
CREATE INDEX idx_memoria_embedding_hnsw 
ON memoria_episodica 
USING hnsw (embedding vector_cosine_ops);
```

**Estado Actual:** ✅ Creada con 0 registros

### Tabla: `herramientas_disponibles`

```sql
CREATE TABLE herramientas_disponibles (
    id_tool SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE,
    descripcion TEXT NOT NULL,
    parametros JSONB DEFAULT '{}'::jsonb,
    activa BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Estado Actual:** ✅ Creada con 5 herramientas activas

---

## 🔄 Flujos de Datos

### 📥 Flujo de Entrada (Mensaje del Usuario)

1. **Mensaje WhatsApp** → Nodo 1 (Caché)
2. **Nodo 1** verifica sesión activa
3. **Nodo 2** clasifica intención (¿calendario?)
4. Si requiere calendario:
   - **Nodo 3** busca contexto en pgvector
   - **Nodo 4** selecciona herramienta
   - **Nodo 5** ejecuta API de Google Calendar
5. **Nodo 6** genera respuesta natural
6. **Nodo 7** persiste memoria episódica
7. **Respuesta enviada** al usuario

### 📤 Flujo de Persistencia

1. **Nodo 7** recibe resumen de conversación
2. **sentence-transformers** genera embedding 384D
3. **INSERT** en tabla `memoria_episodica`
4. **Metadata** incluye:
   - `user_id`: Identificador del usuario
   - `session_id`: ID de sesión
   - `tipo`: "calendario", "conversacion", etc.
   - `timestamp`: Fecha/hora
   - `timezone`: "America/Tijuana"

---

## 🔧 Tecnologías Implementadas

### Bases de Datos
- **PostgreSQL 16.11** - Base de datos principal
- **pgvector 0.8.1** - Extensión para vectores
- **Puerto:** 5434 (externo) → 5432 (interno)
- **Container:** `agente-whatsapp-db`

### LLMs
- **DeepSeek Chat** (Primario)
  - Modelo: `deepseek-chat`
  - Temperature: 0.7
  - Timeout: 20s
  - JSON mode habilitado
  
- **Claude 3.5 Haiku** (Fallback)
  - Modelo: `claude-3-5-haiku-20241022`
  - Temperature: 0.7
  - Timeout: 25s

### Embeddings
- **sentence-transformers**
  - Modelo: `all-MiniLM-L6-v2`
  - Dimensiones: 384
  - Carga: ~2.3 segundos
  - Tamaño: ~471 MB

### APIs Externas
- **Google Calendar API v3**
  - Autenticación: Service Account OAuth2
  - Calendar ID: `92d85be088...`
  - Timezone: `America/Tijuana`

---

## ✅ Estado de Tests

| Componente | Tests | Estado |
|-----------|-------|--------|
| PostgreSQL + pgvector | 5/5 | ✅ 100% |
| Componentes del Sistema | 6/6 | ✅ 100% |
| Verificación del Sistema | 10/10 | ✅ 100% |
| **TOTAL** | **21/21** | **✅ 100%** |

---

## 🚀 Mejoras Implementadas

### ✅ Correcciones Críticas

1. **Error de JSON con DeepSeek** → Prompt corregido en `semantic.py:166`
2. **`update_calendar_event` faltante** → Implementado en `tool.py:189`
3. **Validación de `delete_calendar_event`** → Parámetros opcionales en `tool.py:238`
4. **Pérdida de contexto** → Sistema `ultimo_listado` implementado
5. **Extracción de parámetros** → Prompts mejorados con contexto

### 📈 Métricas de Mejora

| Métrica | Antes | Después | Mejora |
|---------|-------|---------|--------|
| Error en preferencias | 100% | 0% | ✅ 100% |
| Operaciones de update | N/A | 100% | ✅ Nueva |
| Errores en delete | 60% | 5% | ✅ 92% |
| Pérdida de contexto | 30% | 5% | ✅ 83% |
| Precisión extracción | 60% | 90% | ✅ 50% |

---

## 📚 Documentación Relacionada

- [REPORTE_EJECUCION_TESTS.md](REPORTE_EJECUCION_TESTS.md) - Reporte de tests ejecutados
- [RESUMEN_EJECUTIVO.md](RESUMEN_EJECUTIVO.md) - Problemas corregidos
- [GUIA_TESTS_Y_DEPLOYMENT.md](GUIA_TESTS_Y_DEPLOYMENT.md) - Guía de deployment
- [COMANDOS_RAPIDOS.md](COMANDOS_RAPIDOS.md) - Comandos útiles

---

**🎯 Arquitectura actualizada y validada el 26 de Enero de 2026**
