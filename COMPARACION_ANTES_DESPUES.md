# Comparación Visual: N3A Antes vs Después

## 1. Command Pattern

### ❌ ANTES (retornaba Dict)
```python
def nodo_recuperacion_episodica(state: WhatsAppAgentState) -> Dict[str, Any]:
    """..."""
    return {
        'contexto_episodico': {
            'episodios_recuperados': len(episodios),
            'texto_formateado': texto_formateado,
            'timestamp_recuperacion': get_current_time().to_iso8601_string()
        }
    }

def nodo_recuperacion_episodica_wrapper(state: WhatsAppAgentState) -> WhatsAppAgentState:
    """Wrapper que mantiene la firma esperada por el grafo."""
    resultado = nodo_recuperacion_episodica(state)
    state['contexto_episodico'] = resultado['contexto_episodico']
    return state
```

### ✅ AHORA (retorna Command)
```python
def nodo_recuperacion_episodica(state: WhatsAppAgentState) -> Command:
    """
    MEJORAS APLICADAS:
    ✅ Command pattern con routing directo
    ✅ Detección de estado conversacional
    """
    return Command(
        update={
            'contexto_episodico': {
                'episodios_recuperados': len(episodios),
                'texto_formateado': texto_formateado,
                'timestamp_recuperacion': get_current_time().to_iso8601_string()
            }
        },
        goto="seleccion_herramientas"
    )

def nodo_recuperacion_episodica_wrapper(state: WhatsAppAgentState) -> Command:
    """Wrapper para LangGraph - retorna Command directamente."""
    return nodo_recuperacion_episodica(state)
```

---

## 2. Imports y Configuración

### ❌ ANTES (psycopg2)
```python
import psycopg2
from psycopg2.extras import RealDictCursor
from src.state.agent_state import WhatsAppAgentState
# ... otros imports

logger = logging.getLogger(__name__)
SIMILARITY_THRESHOLD = 0.5
MAX_EPISODIOS = 5
```

### ✅ AHORA (psycopg3 + env vars)
```python
import os
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv
from langgraph.types import Command
from src.state.agent_state import WhatsAppAgentState
# ... otros imports

load_dotenv()
logger = logging.getLogger(__name__)

# Configuración de base de datos
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5434/agente_whatsapp")

SIMILARITY_THRESHOLD = 0.5
MAX_EPISODIOS = 5

# ==================== CONSTANTES ====================

# Estados conversacionales que requieren saltar recuperación
ESTADOS_FLUJO_ACTIVO = [
    'ejecutando_herramienta',
    'esperando_confirmacion',
    'procesando_resultado',
    'recolectando_fecha',
    'recolectando_hora'
]
```

---

## 3. Búsqueda de Episodios

### ❌ ANTES (filtrado post-query en Python)
```python
def buscar_episodios_similares(...) -> List[Dict[str, Any]]:
    """Busca episodios similares en pgvector usando cosine similarity."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
            SELECT 
                resumen, metadata, timestamp,
                1 - (embedding <=> %s::vector) as similarity
            FROM memoria_episodica
            WHERE user_id = %s
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """
        
        cursor.execute(query, (embedding_str, user_id, embedding_str, max_results))
        resultados = cursor.fetchall()
        
        # ❌ INEFICIENTE: Filtrar en Python después
        episodios_filtrados = [
            dict(row) for row in resultados
            if row['similarity'] >= threshold
        ]
        
        cursor.close()
        conn.close()
        return episodios_filtrados
```

### ✅ AHORA (filtrado en SQL - más eficiente)
```python
def buscar_episodios_similares(...) -> List[Dict[str, Any]]:
    """
    MEJORAS:
    ✅ Filtro threshold en SQL (no post-query en Python)
    ✅ Usa psycopg3 (alineado con N3B)
    ✅ Más eficiente: BD filtra antes de retornar
    """
    try:
        # ✅ NUEVO: psycopg3 con dict_row
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                
                # ✅ MEJORADO: Filtro threshold en SQL
                query = """
                    SELECT 
                        resumen, metadata, timestamp,
                        1 - (embedding <=> %s::vector) as similarity
                    FROM memoria_episodica
                    WHERE user_id = %s
                      AND 1 - (embedding <=> %s::vector) >= %s
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                """
                
                cursor.execute(
                    query, 
                    (embedding_str, user_id, embedding_str, threshold, embedding_str, max_results)
                )
                
                resultados = cursor.fetchall()
                logger.info(f"📊 Encontrados {len(resultados)} episodios sobre threshold {threshold}")
                return resultados
```

---

## 4. Formateo de Contexto

### ❌ ANTES (sin truncamiento)
```python
def formatear_contexto_episodico(episodios: List[Dict[str, Any]]) -> str:
    """Formatea los episodios recuperados en texto legible para LLMs."""
    if not episodios:
        return "No hay conversaciones previas relevantes para este contexto."
    
    texto = "CONVERSACIONES PREVIAS RELEVANTES:\n\n"
    
    for i, episodio in enumerate(episodios, 1):
        resumen = episodio.get('resumen', 'Sin resumen')
        # ... formatear fecha ...
        
        # ❌ Sin límite de longitud
        texto += f"{i}. [{fecha_str}] (Relevancia: {similarity:.2f})\n"
        texto += f"   {resumen}\n"
```

### ✅ AHORA (con truncamiento automático)
```python
def formatear_contexto_episodico(episodios: List[Dict[str, Any]]) -> str:
    """
    MEJORAS:
    ✅ Trunca resúmenes largos (>200 chars)
    ✅ Formato más compacto
    """
    if not episodios:
        return "No hay conversaciones previas relevantes para este contexto."
    
    texto = "CONVERSACIONES PREVIAS RELEVANTES:\n\n"
    
    for i, episodio in enumerate(episodios, 1):
        resumen = episodio.get('resumen', 'Sin resumen')
        # ... formatear fecha ...
        
        # ✅ NUEVO: Truncar resúmenes muy largos
        MAX_RESUMEN_CHARS = 200
        if len(resumen) > MAX_RESUMEN_CHARS:
            resumen_truncado = resumen[:MAX_RESUMEN_CHARS - 3] + "..."
        else:
            resumen_truncado = resumen
        
        texto += f"{i}. [{fecha_str}] (Relevancia: {similarity:.2f})\n"
        texto += f"   {resumen_truncado}\n"
```

---

## 5. Detección de Estado Conversacional

### ❌ ANTES (no detectaba flujos activos)
```python
def nodo_recuperacion_episodica(state: WhatsAppAgentState) -> Dict[str, Any]:
    """..."""
    log_separator(logger, "NODO_3_RECUPERACION_EPISODICA", "INICIO")
    
    user_id = state.get('user_id')
    
    # ❌ No verifica estado conversacional
    if not user_id:
        logger.warning("Sin user_id...")
        return {'contexto_episodico': {...}}
    
    # Continúa con recuperación siempre...
```

### ✅ AHORA (detecta y salta si necesario)
```python
def nodo_recuperacion_episodica(state: WhatsAppAgentState) -> Command:
    """
    MEJORAS APLICADAS:
    ✅ Command pattern con routing directo
    ✅ Detección de estado conversacional
    """
    log_separator(logger, "NODO_3A_RECUPERACION_EPISODICA", "INICIO")
    
    user_id = state.get('user_id')
    estado_conversacion = state.get('estado_conversacion', 'inicial')
    
    logger.info(f"👤 User ID: {user_id}")
    logger.info(f"🔄 Estado: {estado_conversacion}")
    
    # ✅ NUEVA VALIDACIÓN: Si hay flujo activo, saltar recuperación
    if estado_conversacion in ESTADOS_FLUJO_ACTIVO:
        logger.info(f"🔄 Flujo activo detectado (estado: {estado_conversacion}) - Saltando recuperación")
        
        return Command(
            update={'contexto_episodico': None},
            goto="seleccion_herramientas"
        )
    
    # Solo recupera si no hay flujo activo...
```

---

## 6. Tests Unitarios

### ❌ ANTES
```
tests/test_recuperacion_episodica.py: NO EXISTE
```

### ✅ AHORA
```python
"""
Tests para Nodo N3A: Recuperación Episódica

✅ Command pattern
✅ psycopg3
✅ Estado conversacional
✅ Búsqueda semántica
"""

# 12 tests implementados:

def test_recuperacion_episodica_basica(...)
def test_sin_user_id(...)
def test_detecta_estado_activo(...)
def test_detecta_todos_estados_activos(...)  # parametrizado
def test_mensaje_vacio(...)
def test_buscar_episodios_con_resultados(...)
def test_buscar_episodios_sin_resultados(...)
def test_query_usa_threshold_en_sql(...)
def test_formatear_contexto_con_episodios(...)
def test_formatear_contexto_vacio(...)
def test_formatear_contexto_trunca_largos(...)
def test_error_embedding_no_rompe_flujo(...)
```

---

## Resumen de Mejoras

| Aspecto | Antes | Ahora |
|---------|-------|-------|
| Return type | Dict | Command |
| DB driver | psycopg2 | psycopg3 |
| Filtro threshold | Python (post-query) | SQL (pre-fetch) |
| Estado conversacional | No detecta | Detecta y salta |
| Truncamiento | Sin límite | 200 chars |
| Tests | 0 | 12 |
| Seguridad | Hardcoded creds | ENV var |
| Documentación | Inconsistente | Actualizada |

## Alineación con N3B

N3A ahora sigue el mismo patrón que N3B:
- ✅ Command pattern
- ✅ psycopg3 con dict_row
- ✅ ESTADOS_FLUJO_ACTIVO
- ✅ Detección estado conversacional
- ✅ DATABASE_URL desde env var
- ✅ Tests completos
