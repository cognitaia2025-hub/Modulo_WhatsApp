# ⚡ Optimización de Embeddings - Singleton Pattern

## 🎯 Problema Identificado

Antes de esta optimización, el agente tenía una **latencia de ~7 segundos adicionales** en cada mensaje:
- **Nodo 3 (Recuperación Episódica)**: ~4 segundos cargando el modelo
- **Nodo 7 (Persistencia Episódica)**: ~3 segundos cargando el modelo

**Causa:** El modelo `paraphrase-multilingual-MiniLM-L12-v2` (384 dims, ~120MB) se cargaba desde disco en **cada invocación**.

---

## ✅ Solución Implementada

### 1. **Singleton Thread-Safe** en `src/embeddings/local_embedder.py`

```python
# Variables globales con thread-safety
_model_instance: Optional[SentenceTransformer] = None
_model_lock = threading.Lock()
_model_loaded = False

def get_embedder() -> SentenceTransformer:
    """Carga el modelo UNA SOLA VEZ en memoria"""
    global _model_instance, _model_loaded
    
    # Double-checked locking
    if not _model_loaded:
        with _model_lock:
            if not _model_loaded:
                logger.info("🚀 [INIT] Cargando modelo...")
                _model_instance = SentenceTransformer(...)
                _model_loaded = True
    
    return _model_instance
```

**Características:**
- ✅ Thread-safe con `threading.Lock()`
- ✅ Double-checked locking para performance
- ✅ Log solo en primera carga
- ✅ Función `warmup_embedder()` para pre-carga

### 2. **Pre-carga en Startup** en `app.py`

```python
@app.on_event("startup")
async def startup_event():
    """Pre-carga el modelo al iniciar el servidor"""
    logger.info("🚀 Iniciando servidor FastAPI...")
    logger.info("📦 Pre-cargando modelo de embeddings...")
    
    warmup_embedder()
    logger.info("✅ Servidor listo - Modelo en memoria")
```

**Resultado:** Cuando llega el primer mensaje de WhatsApp, el modelo ya está "caliente" en RAM.

### 3. **Actualización de Nodo 7** en `src/nodes/persistencia_episodica_node.py`

**Antes:**
```python
# ❌ Cargaba su propia instancia
embedding_model = None
def get_embedding_model():
    global embedding_model
    if embedding_model is None:
        embedding_model = SentenceTransformer(MODEL_NAME)
```

**Después:**
```python
# ✅ Usa el singleton centralizado
from src.embeddings.local_embedder import generate_embedding, is_model_loaded

# Uso directo
embedding = generate_embedding(resumen)
```

---

## 📊 Resultados Esperados

### Antes de la Optimización
```
Usuario envía mensaje:
  ├─ Nodo 3: ~4000ms (carga modelo + genera embedding)
  ├─ Nodo 4: ~200ms
  ├─ Nodo 5: ~1000ms
  ├─ Nodo 6: ~500ms
  └─ Nodo 7: ~3000ms (carga modelo + guarda embedding)
  
Total: ~8700ms (~9 segundos)
```

### Después de la Optimización
```
Startup del servidor:
  └─ Warmup: ~4000ms (UNA SOLA VEZ)

Usuario envía mensaje:
  ├─ Nodo 3: ~50ms (embedding instantáneo)
  ├─ Nodo 4: ~200ms
  ├─ Nodo 5: ~1000ms
  ├─ Nodo 6: ~500ms
  └─ Nodo 7: ~50ms (embedding instantáneo)
  
Total: ~1800ms (~2 segundos)
```

**Ganancia:** ~7 segundos por mensaje = **4.8x más rápido** 🚀

---

## 🧪 Verificación

### Ejecutar Test de Singleton

```bash
python test_embeddings_singleton.py
```

**Salida esperada:**
```
🚀 [INIT] Cargando modelo de embeddings en memoria...
✅ Modelo cargado exitosamente en 3.84s
⚡ Las siguientes invocaciones serán instantáneas

Invocación #1: 45.23ms
Invocación #2: 38.91ms
Invocación #3: 42.17ms

✅ EXCELENTE - Tiempo promedio: 42.10ms
✅ Reducción de ~4000ms a ~42ms = 95x más rápido
```

### Logs en Producción

**Primera vez (startup):**
```
🚀 Iniciando servidor FastAPI...
📦 Pre-cargando modelo de embeddings...
🚀 [INIT] Cargando modelo de embeddings en memoria por primera y única vez...
   📦 Modelo: paraphrase-multilingual-MiniLM-L12-v2
   📏 Dimensiones: 384
   💻 Dispositivo: CPU
✅ Modelo cargado exitosamente en 3.92s
⚡ Las siguientes invocaciones serán instantáneas
```

**Mensajes subsiguientes:**
```
📖 [3] NODO_RECUPERACION_EPISODICA - Buscando memoria relevante
    🔢 Generando embedding (384 dims)...
    ✅ Embedding generado: [0.1234, 0.5678, ...]
    # ⚠️ NO aparece "Cargando modelo..."
```

---

## 🔍 Debugging

### Verificar si el modelo está cargado

```python
from src.embeddings.local_embedder import is_model_loaded

if is_model_loaded():
    print("✅ Modelo en memoria")
else:
    print("⚠️  Modelo NO cargado (se cargará bajo demanda)")
```

### Logs importantes

- ✅ **`[INIT] Cargando modelo...`** → Solo debe aparecer UNA VEZ al inicio
- ❌ Si aparece múltiples veces → El singleton no está funcionando
- ⚠️ **`Modelo no pre-cargado, se cargará bajo demanda`** → Verifica el `@app.on_event("startup")`

---

## 🎛️ Configuración

### Variables de entorno (opcional)

Si deseas forzar un modelo diferente o dispositivo:

```bash
# .env
EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2  # Modelo a usar
EMBEDDING_DEVICE=cpu  # cpu o cuda
```

### Desactivar pre-carga (no recomendado)

Si por alguna razón quieres desactivar el warmup:

```python
# En app.py, comenta:
# @app.on_event("startup")
# async def startup_event():
#     warmup_embedder()
```

**Nota:** El modelo se cargará bajo demanda en el primer mensaje (añadiendo ~4s de latencia).

---

## 📝 Archivos Modificados

### Creados:
- ✨ `test_embeddings_singleton.py` - Test de verificación

### Modificados:
- 🔧 `src/embeddings/local_embedder.py` - Singleton thread-safe + warmup
- 🔧 `src/nodes/persistencia_episodica_node.py` - Usa singleton centralizado
- 🔧 `app.py` - Pre-carga en startup event

### Sin cambios:
- ✅ `src/nodes/recuperacion_episodica_node.py` - Ya usaba el singleton correctamente

---

## 💡 Mejores Prácticas

### ✅ DO:
- Pre-cargar el modelo en el startup
- Usar `warmup_embedder()` antes del primer request
- Verificar logs para confirmar carga única
- Ejecutar `test_embeddings_singleton.py` después de desplegar

### ❌ DON'T:
- No crear nuevas instancias de `SentenceTransformer` en otros nodos
- No llamar `get_embedder()` sin necesidad
- No desactivar el warmup en producción

---

## 🚀 Próximos Pasos (Opcional)

### Optimizaciones Adicionales

1. **Cuantización del Modelo**
   - Reducir de float32 a float16
   - Ganancia: ~50% menos RAM, ~20% más rápido

2. **Caché de Embeddings Frecuentes**
   - Cachear embeddings de queries comunes
   - Ejemplo: "¿Qué eventos tengo hoy?" → embedding pre-calculado

3. **Batching de Embeddings**
   - Procesar múltiples textos en un batch
   - Útil si se procesan N mensajes simultáneos

---

## 📚 Referencias

- [SentenceTransformers Documentation](https://www.sbert.net/)
- [FastAPI Startup Events](https://fastapi.tiangolo.com/advanced/events/)
- [Python Singleton Pattern](https://refactoring.guru/design-patterns/singleton/python/example)
- [Thread-Safe Singleton](https://python-patterns.guide/gang-of-four/singleton/)

---

## ✅ Checklist de Verificación

- [x] Singleton implementado con thread-safety
- [x] Función `warmup_embedder()` creada
- [x] Startup event configurado en `app.py`
- [x] Nodo 7 actualizado para usar singleton
- [x] Test de verificación creado
- [x] Logs verifican carga única
- [x] Documentación completa

**Estado:** ✅ **Optimización Completa y Lista para Producción**
