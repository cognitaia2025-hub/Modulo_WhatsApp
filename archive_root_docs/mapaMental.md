---
config:
  layout: elk
---
flowchart TB
 subgraph DB["Base de Datos PostgreSQL:5434 (agente_whatsapp)"]
    direction TB
        DB_V["(memoria_episodica)<br>Embeddings vector(384)<br>Resumenes conversaciones<br>Metadata JSONB<br>Indice HNSW<br>0 registros iniciales"]
        DB_T["(herramientas_disponibles)<br>5 herramientas<br>list_calendar_events<br>create_calendar_event<br>update_calendar_event<br>delete_calendar_event<br>get_event_details"]
        DB_C["(LangGraph Store)<br>user_preferences<br>session_state<br>ultimo_listado<br>Rolling Window 10 msgs"]
        DB_A["(Audit Log)<br>Texto plano<br>Logs de ejecucion<br>Errores/Warnings<br>Retencion 6 meses"]
  end
 subgraph EXT["Servicios Externos"]
    direction TB
        LLM1["DeepSeek API<br>deepseek-chat<br>Temp: 0.7<br>Timeout: 20s<br>PRIMARY"]
        LLM2["Claude 3.5 Haiku<br>claude-3-5-haiku<br>Temp: 0.7<br>Timeout: 25s<br>FALLBACK"]
        GCAL["Google Calendar API<br>OAuth2 Service Account<br>Calendar ID: 92d85...<br>Timezone: America/Tijuana"]
        EMB["sentence-transformers<br>all-MiniLM-L6-v2<br>384 dimensiones<br>Local (CPU/GPU)"]
  end
    START(("Mensaje WhatsApp")) --> N1["<b>1. Nodo Caché</b><br>¿Sesión Activa?<br>Rolling Window 10 msgs"]
    N1 -- Nueva Sesión --> N2["<b>2. Nodo Gatekeeper</b><br>¿Requiere Calendario?"]
    N1 -- Sesión Activa --> N2
    N2 -- "SÍ - Calendario" --> N3["<b>3. Recuperación Episódica</b><br>Búsqueda Semántica<br>pgvector 384D"]
    N2 -- "NO - Conversación" --> RESP["<b>Respuesta Directa</b><br>Sin Herramientas"]
    N3 --> N4["<b>4. Selección de Herramientas</b><br>LLM decide qué usar<br>DeepSeek/Claude"]
    N4 -- Herramienta Detectada --> N5["<b>5. Ejecución de Herramientas</b><br>Google Calendar API<br>+ Extracción LLM"]
    N4 -- Sin Herramienta --> N6["<b>6. Generación de Respuesta</b><br>LLM Orquestador<br>Resumen + Auditoría"]
    N5 --> N6
    N6 --> N7["<b>7. Persistencia Episódica</b><br>Guarda Memoria<br>Embedding + Metadata"]
    N7 --> END(("Respuesta a Usuario"))
    RESP --> END
    N1 -. Lee/Escribe<br>Sesiones .-> DB_C
    N3 -. SELECT con<br>embedding .-> DB_V
    N3 -. Genera Embedding .-> EMB
    N4 -. "SELECT WHERE<br>activa = true" .-> DB_T
    N4 -. Inferencia .-> LLM1
    N4 -. Fallback .-> LLM2
    N5 -. CRUD Operations .-> GCAL
    N5 -. Extraccion params .-> LLM1
    N5 -. Lee ultimo_listado .-> DB_C
    N5 -. Escribe Log .-> DB_A
    N6 -. Genera Resumen .-> LLM1
    N6 -. Escribe Auditoria .-> DB_A
    N7 -. INSERT memoria<br>con embedding .-> DB_V
    N7 -. Genera Embedding .-> EMB
    N7 -. Guarda Metadata .-> DB_V

     N1:::nodoActivo
     N2:::nodoDecision
     N3:::nodoDecision
     N4:::nodoDecision
     N5:::nodoEjecucion
     N6:::nodoEjecucion
     N7:::nodoPersistencia
     DB_V:::dbVectorial
     DB_T:::dbRelacional
     DB_C:::nodoActivo
     DB_A:::dbRelacional
     LLM1:::servicioExterno
     LLM2:::servicioExterno
     GCAL:::servicioExterno
     EMB:::servicioExterno
    classDef nodoActivo fill:#4CAF50,stroke:#2E7D32,stroke-width:3px,color:#fff
    classDef nodoDecision fill:#2196F3,stroke:#1565C0,stroke-width:3px,color:#fff
    classDef nodoEjecucion fill:#FF9800,stroke:#E65100,stroke-width:3px,color:#fff
    classDef nodoPersistencia fill:#9C27B0,stroke:#6A1B9A,stroke-width:3px,color:#fff
    classDef dbVectorial fill:#E91E63,stroke:#880E4F,stroke-width:2px,color:#fff
    classDef dbRelacional fill:#00BCD4,stroke:#006064,stroke-width:2px,color:#fff
    classDef servicioExterno fill:#607D8B,stroke:#37474F,stroke-width:2px,color:#fff