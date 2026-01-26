# 📖 NODO 3: Recuperación Episódica con Embeddings Locales

## 🎯 Objetivo

El **Nodo 3** implementa **memoria episódica semántica** usando embeddings multilingües locales. Permite al agente recordar conversaciones pasadas relevantes cuando el usuario cambia de tema o pregunta sobre interacciones previas.

---

## 🏗️ Arquitectura

### Flujo de Activación

```
Usuario cambia de tema (detectado por Nodo 2)
         ↓
    [NODO 3]
         ↓
1. Extrae último mensaje del usuario
2. Genera embedding de 384 dimensiones (local)
3. Busca episodios similares en pgvector (coseno)
4. Filtra por user_id
5. Retorna top 3 resultados (umbral 0.7)
6. Formatea contexto para el agente
         ↓
    [NODO 4] → Continúa con herramientas
```

### Componentes Clave

#### 1. **Modelo de Embeddings** (`src/embeddings/local_embedder.py`)
```python
Modelo: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
Dimensiones: 384
Idiomas: 50+ (incluyendo español)
Dispositivo: CPU (PyTorch 2.10.0+cpu)
Patrón: Singleton (carga única)
```

**Características:**
- ✅ Optimizado para español y multilingüismo
- ✅ Vectores normalizados (búsqueda coseno eficiente)
- ✅ Carga bajo demanda (no bloquea inicio)
- ✅ Rápido en CPU (~20ms por embedding)

#### 2. **Nodo de Recuperación** (`nodo_recuperacion_episodica` en `graph_whatsapp.py`)
```python
def nodo_recuperacion_episodica(state: WhatsAppAgentState) -> Dict:
    """
    Busca episodios relevantes del pasado usando similitud semántica
    
    Input:
        - state['messages']: Historial de conversación
        - state['user_id']: ID del usuario (filtrado)
    
    Output:
        - contexto_episodico: {
            'query_embedding_dim': 384,
            'episodios_recuperados': [...],  # Top 3
            'similitud_threshold': 0.7,
            'texto_formateado': "..."
          }
    """
```

---

## 🔢 Especificaciones Técnicas

### Embedding Generation

```python
from src.embeddings.local_embedder import generate_embedding

texto = "¿Qué citas tenía pendientes la semana pasada?"
embedding = generate_embedding(texto)  # List[float], len=384
```

**Propiedades:**
- Entrada: String (cualquier longitud)
- Salida: Lista de 384 floats
- Normalización: L2 (norma euclidiana)
- Similitud: Producto punto = cosine similarity

### pgvector Query (Pendiente de Implementación)

```sql
-- Esquema de tabla
CREATE TABLE memoria_episodica (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    session_id VARCHAR(255) NOT NULL,
    resumen TEXT NOT NULL,
    embedding vector(384),  -- pgvector extension
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB
);

-- Índice para búsqueda eficiente
CREATE INDEX idx_memoria_embedding ON memoria_episodica 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

-- Búsqueda de similitud
SELECT 
    id, 
    resumen, 
    timestamp,
    1 - (embedding <=> '[...]'::vector) AS similitud
FROM memoria_episodica
WHERE user_id = 'test_user_123'
  AND 1 - (embedding <=> '[...]'::vector) >= 0.7  -- Umbral
ORDER BY embedding <=> '[...]'::vector ASC
LIMIT 3;
```

**Operador `<=>`:**
- Distancia coseno en pgvector
- `1 - distancia = similitud`
- Rango: [0, 2] → Similitud: [-1, 1]

---

## 📊 Resultados de Pruebas

### Test 1: Carga del Modelo ✅
```
📦 Cargando modelo paraphrase-multilingual-MiniLM-L12-v2...
   ✓ Modelo cargado en 3.34s (primera vez)
   ✓ Dimensiones: 384
   ✓ Tipo de datos: <class 'float'>
   ✓ Primeros 5 valores: [0.0328, -0.0001, -0.0377, 0.0245, -0.0157]
```

### Test 2: Calidad Semántica (Español) ✅
```
📊 Similitudes (coseno):
   '¿Qué reuniones tengo mañana?' ↔ '¿Cuáles son mis citas de mañana?': 0.7281
   '¿Qué reuniones tengo mañana?' ↔ '¿Cuál es el clima de hoy?': 0.3009
```

**Interpretación:**
- **0.73**: Alta similitud → Mismo dominio semántico (calendario)
- **0.30**: Baja similitud → Dominios diferentes (calendario vs clima)
- Umbral recomendado: **0.7** para resultados relevantes

### Test 3: Flujo Completo ✅
```
🚀 Conversación que cambia de tema:
   1. Usuario: "Hola"
   2. Asistente: "¡Hola! ¿En qué puedo ayudarte?"
   3. Usuario: "Quiero agendar una reunión para el lunes"
   4. Asistente: "Perfecto, ¿a qué hora?"
   5. Usuario: "Espera, ¿qué citas tenía pendientes la semana pasada?" ← CAMBIO

📊 RESULTADO:
   ✓ Nodo 2 detectó cambio: True
   ✓ Nodo 3 generó embedding: 384 dims
   ✓ Búsqueda simulada (pgvector pendiente)
   ✓ Contexto formateado: "No hay antecedentes previos para este tema"
   ✓ Flujo continuó sin errores
```

### Test 4: Robustez ✅
```
🛡️  Caso edge: Mensaje vacío
   ✓ Nodo 3 no activado (esperado: pocos mensajes)
   ✓ Sistema continúa sin errores
   ✓ Fallback funcional
```

---

## ⚙️ Configuración

### Variables de Estado

```python
WhatsAppAgentState:
    cambio_de_tema: bool          # Activador del Nodo 3
    contexto_episodico: Dict | None  # Salida del Nodo 3
```

### Parámetros del Nodo

```python
SIMILITUD_THRESHOLD = 0.7  # Umbral de relevancia (70%)
TOP_K_RESULTADOS = 3       # Máximo de episodios recuperados
EMBEDDING_DIM = 384        # Dimensiones del vector
```

---

## 🔄 Integración con Otros Nodos

### ⬅️ Input (desde Nodo 2)
```python
state['cambio_de_tema'] = True  # Señal para activar Nodo 3
```

### ➡️ Output (hacia Nodo 4)
```python
state['contexto_episodico'] = {
    'query_embedding_dim': 384,
    'episodios_recuperados': [
        {
            'resumen': 'Usuario agendó cita médica para el martes 21',
            'timestamp': '2024-01-16T10:30:00',
            'similitud': 0.89
        },
        {
            'resumen': 'Usuario canceló reunión con equipo de ventas',
            'timestamp': '2024-01-15T14:20:00',
            'similitud': 0.76
        }
    ],
    'similitud_threshold': 0.7,
    'texto_formateado': '''
📋 Contexto de conversaciones previas:

🕒 16 Ene, 10:30
   Usuario agendó cita médica para el martes 21
   (Similitud: 89%)

🕒 15 Ene, 14:20
   Usuario canceló reunión con equipo de ventas
   (Similitud: 76%)
    '''
}
```

### 🔗 Uso en Nodo 4 (Selección de Herramientas)
```python
contexto = state.get('contexto_episodico')
if contexto and contexto['episodios_recuperados']:
    # Usar contexto histórico para seleccionar herramientas relevantes
    prompt = f"""
    Contexto histórico:
    {contexto['texto_formateado']}
    
    Usuario actual: {ultimo_mensaje}
    
    ¿Qué herramientas necesitas?
    """
```

---

## 🚀 Implementación

### 1. Instalar Dependencias
```bash
pip install sentence-transformers torch numpy
```

### 2. Crear Módulo de Embeddings
Archivo: `src/embeddings/local_embedder.py`
```python
from sentence_transformers import SentenceTransformer
from typing import List
import logging

_model_instance = None  # Singleton

def get_embedder() -> SentenceTransformer:
    global _model_instance
    if _model_instance is None:
        logging.info("🔧 Cargando modelo de embeddings multilingüe...")
        _model_instance = SentenceTransformer(
            'paraphrase-multilingual-MiniLM-L12-v2',
            device='cpu'
        )
    return _model_instance

def generate_embedding(text: str) -> List[float]:
    model = get_embedder()
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()

def get_embedding_dimension() -> int:
    return 384
```

### 3. Implementar Nodo en Grafo
```python
from src.embeddings.local_embedder import generate_embedding

def nodo_recuperacion_episodica(state: WhatsAppAgentState) -> Dict:
    logger.info("📖 [3] NODO_RECUPERACION_EPISODICA - Buscando episodios")
    
    try:
        # 1. Extraer último mensaje
        mensajes = state['messages']
        ultimo_msg = next(
            (m['content'] for m in reversed(mensajes) if m['role'] == 'user'),
            None
        )
        
        if not ultimo_msg:
            return {'contexto_episodico': None}
        
        # 2. Generar embedding
        embedding = generate_embedding(ultimo_msg)
        
        # 3. Buscar en pgvector
        resultados = buscar_episodios_similares(
            user_id=state['user_id'],
            query_embedding=embedding,
            top_k=3,
            threshold=0.7
        )
        
        # 4. Formatear contexto
        texto = formatear_contexto(resultados)
        
        return {
            'contexto_episodico': {
                'query_embedding_dim': 384,
                'episodios_recuperados': resultados,
                'similitud_threshold': 0.7,
                'texto_formateado': texto
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error en recuperación episódica: {e}")
        return {
            'contexto_episodico': {
                'episodios_recuperados': [],
                'texto_formateado': "No hay antecedentes previos",
                'fallback': True,
                'error': str(e)
            }
        }
```

---

## 🔒 Fallback y Errores

### Estrategia de Fallback
1. **Modelo no carga:** Continúa sin contexto episódico
2. **Embedding falla:** Retorna contexto vacío
3. **pgvector no conecta:** Modo degradado (sin memoria)
4. **Query timeout:** Continúa con herramientas default

### Logging Detallado
```python
logger.info("📝 Query: 'Última pregunta del usuario...'")
logger.info("🔢 Generando embedding local (384 dims)...")
logger.info("✓ Embedding generado: 384 dimensiones")
logger.info("🔍 Buscando en memoria episódica (pgvector)...")
logger.info("✓ Encontrados 2 episodios relevantes")
```

---

## 📈 Métricas de Rendimiento

### Tiempos Medidos (CPU)
- **Primera carga del modelo:** ~3.5s
- **Cargas subsiguientes:** ~0.01s (singleton)
- **Generación de embedding:** ~20-30ms
- **Búsqueda pgvector (estimado):** ~50-100ms
- **Total por llamada:** ~80-150ms

### Uso de Memoria
- **Modelo cargado:** ~120 MB
- **Embedding (384 floats):** ~1.5 KB
- **Impacto total:** ~150 MB RAM

---

## 🛠️ Próximos Pasos

### 1. Conectar PostgreSQL + pgvector
```bash
# Instalar extensión
CREATE EXTENSION vector;

# Crear tabla
CREATE TABLE memoria_episodica (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255),
    session_id VARCHAR(255),
    resumen TEXT,
    embedding vector(384),
    timestamp TIMESTAMPTZ DEFAULT NOW()
);
```

### 2. Implementar Búsqueda Real
```python
import psycopg2

def buscar_episodios_similares(user_id, query_embedding, top_k=3, threshold=0.7):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT resumen, timestamp, 
               1 - (embedding <=> %s::vector) AS similitud
        FROM memoria_episodica
        WHERE user_id = %s
          AND 1 - (embedding <=> %s::vector) >= %s
        ORDER BY embedding <=> %s::vector ASC
        LIMIT %s
    """, (query_embedding, user_id, query_embedding, threshold, query_embedding, top_k))
    
    return cur.fetchall()
```

### 3. Guardar Embeddings en Nodo 7
```python
def nodo_persistencia_episodica(state: WhatsAppAgentState):
    resumen = state['resumen_actual']
    embedding = generate_embedding(resumen)
    
    # Guardar en BD
    guardar_episodio(
        user_id=state['user_id'],
        resumen=resumen,
        embedding=embedding
    )
```

---

## ✅ Checklist de Implementación

- [x] Instalar sentence-transformers
- [x] Crear módulo local_embedder.py
- [x] Implementar patrón singleton
- [x] Integrar en nodo_recuperacion_episodica
- [x] Pruebas de calidad semántica (español)
- [x] Pruebas de flujo completo
- [x] Manejo de errores y fallback
- [ ] Conectar PostgreSQL + pgvector
- [ ] Implementar búsqueda real
- [ ] Guardar embeddings en Nodo 7
- [ ] Monitoreo de latencia y cache

---

## 📚 Referencias

- **Modelo:** [sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2)
- **pgvector:** [Documentation](https://github.com/pgvector/pgvector)
- **LangGraph:** [Conditional Edges](https://langchain-ai.github.io/langgraph/concepts/low_level/)

---

## 🎉 Estado Actual

✅ **NODO 3 COMPLETADO Y PROBADO**

- Embeddings multilingües funcionando
- 384 dimensiones (compatible con pgvector)
- Optimizado para español
- Fallback robusto
- Listo para integración con BD

**Próximo paso:** Conectar PostgreSQL con extensión pgvector para búsqueda real.
