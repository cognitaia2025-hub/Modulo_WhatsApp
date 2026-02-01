```
Moderniza el nodo Recuperación Médica (N3B) para alinearlo con las mejores prácticas implementadas en Maya y Filtrado Inteligente: Command pattern, búsqueda semántica funcional con embeddings, y detección de estado conversacional.

# Objetivo
Mejorar robustez, activar búsqueda semántica real con pgvector, y alinear con patrones del sistema (Command, estado conversacional).

# Problemas actuales

1. Retorna Dict en lugar de Command - routing separado
2. Búsqueda semántica NUNCA se ejecuta - query_embedding siempre es None
3. No detecta estado_conversacion activo - puede hacer queries innecesarias
4. Sin tests unitarios (0 tests)
5. Formato de contexto no estructurado para LLM

# Cambios requeridos

## 1. Instalar dependencia para embeddings

Agregar a requirements.txt:

sentence-transformers==2.3.1

## 2. Agregar generación de embeddings en src/nodes/recuperacion_medica_node.py

Después de los imports (línea ~26), agregar:

from sentence_transformers import SentenceTransformer
from typing import Literal

# ==================== MODELO DE EMBEDDINGS ====================

# Cargar modelo una sola vez (singleton)
_embedding_model = None

def get_embedding_model():
    """Obtiene modelo de embeddings (singleton para no recargar)."""
    global _embedding_model
    if _embedding_model is None:
        logger.info("📦 Cargando modelo de embeddings (all-MiniLM-L6-v2)...")
        _embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("✅ Modelo de embeddings cargado")
    return _embedding_model


def generar_embedding(texto: str) -> List[float]:
    """
    Genera embedding de 384 dimensiones para búsqueda semántica.
    
    Args:
        texto: Texto a convertir en embedding
        
    Returns:
        Lista de 384 floats
    """
    try:
        model = get_embedding_model()
        embedding = model.encode(texto, show_progress_bar=False)
        return embedding.tolist()
    
    except Exception as e:
        logger.error(f"❌ Error generando embedding: {e}")
        return None


def obtener_ultimo_mensaje(state: Dict) -> str:
    """Extrae último mensaje del usuario del state."""
    messages = state.get('messages', [])
    
    for msg in reversed(messages):
        if hasattr(msg, 'type') and msg.type == 'human':
            return msg.content
        elif isinstance(msg, dict) and msg.get('role') == 'user':
            return msg.get('content', '')
    
    return ""


# ==================== CONSTANTES ====================

# Estados conversacionales que requieren saltar recuperación
ESTADOS_FLUJO_ACTIVO = [
    'ejecutando_herramienta',
    'esperando_confirmacion_medica',
    'procesando_resultado'
]

## 3. Actualizar función buscar_historiales_semantica

Reemplazar función buscar_historiales_semantica (líneas 188-276) con:

def buscar_historiales_semantica(
    doctor_id: int,
    query_embedding: Optional[List[float]] = None,
    limit: int = 5
) -> List[Dict]:
    """
    Búsqueda semántica en historiales médicos usando embeddings
    
    Args:
        doctor_id: ID del doctor
        query_embedding: Vector de embedding para búsqueda (384 dims)
        limit: Número máximo de resultados
        
    Returns:
        Lista de historiales con similitud
    """
    # ✅ CAMBIO: Si no hay embedding, intentar retornar vacío (no fallback)
    if not query_embedding:
        logger.info("   ℹ️ Sin embedding de búsqueda - Retornando lista vacía")
        return []
    
    # Búsqueda semántica con embeddings
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                # Convertir embedding a string de PostgreSQL
                embedding_str = f"[{','.join(map(str, query_embedding))}]"
                
                # ✅ MEJORADO: Query con JOIN explícito y filtros
                cur.execute("""
                    SELECT 
                        h.id,
                        h.paciente_id,
                        p.nombre_completo as paciente_nombre,
                        h.nota,
                        h.fecha,
                        ROUND((1 - (h.embedding <=> %s::vector))::NUMERIC, 4) as similitud
                    FROM historiales_medicos h
                    INNER JOIN pacientes p ON h.paciente_id = p.id
                    WHERE h.doctor_id = %s
                        AND h.embedding IS NOT NULL
                        AND h.nota IS NOT NULL
                        AND LENGTH(h.nota) > 10
                    ORDER BY h.embedding <=> %s::vector
                    LIMIT %s
                """, (embedding_str, doctor_id, embedding_str, limit))
                
                historiales = []
                for row in cur.fetchall():
                    similitud = float(row[5]) if row[5] else 0.0
                    
                    # Filtrar por similitud mínima (>0.5 = relevante)
                    if similitud >= 0.5:
                        historiales.append({
                            "id": row[0],
                            "paciente_id": row[1],
                            "paciente_nombre": row[2],
                            "nota": row[3],
                            "fecha": row[4].isoformat() if row[4] else None,
                            "similitud": similitud
                        })
                
                logger.info(f"   ✅ Búsqueda semántica: {len(historiales)} historiales relevantes")
                return historiales
    
    except Exception as e:
        logger.error(f"❌ Error en búsqueda semántica: {e}")
        return []

## 4. Actualizar nodo_recuperacion_medica para usar Command

Reemplazar función nodo_recuperacion_medica (líneas 338-407) con:

def nodo_recuperacion_medica(state: WhatsAppAgentState) -> Command:
    """
    Nodo de recuperación de contexto médico (Sin LLM)
    
    MEJORAS APLICADAS:
    ✅ Command pattern con routing directo
    ✅ Búsqueda semántica funcional con embeddings
    ✅ Detección de estado conversacional
    """
    logger.info("\n" + "=" * 70)
    logger.info("🏥 NODO: RECUPERACIÓN MÉDICA")
    logger.info("=" * 70)
    
    # ✅ NUEVA VALIDACIÓN: Si hay flujo activo, saltar recuperación
    estado_conversacion = state.get("estado_conversacion", "inicial")
    
    if estado_conversacion in ESTADOS_FLUJO_ACTIVO:
        logger.info(f"   🔄 Flujo activo detectado (estado: {estado_conversacion}) - Saltando recuperación")
        
        return Command(
            update={'contexto_medico': None},
            goto="seleccion_herramientas"
        )
    
    # Verificar que sea doctor
    tipo_usuario = state.get("tipo_usuario", "")
    doctor_id = state.get("doctor_id")
    
    if tipo_usuario != "doctor" or not doctor_id:
        logger.info("ℹ️  Usuario no es doctor, saltando recuperación médica")
        return Command(
            update={"contexto_medico": None},
            goto="generacion_resumen"
        )
    
    logger.info(f"👨‍⚕️ Doctor ID: {doctor_id}")
    
    # ✅ NUEVO: Generar embedding del mensaje para búsqueda semántica
    mensaje_usuario = obtener_ultimo_mensaje(state)
    query_embedding = None
    
    if mensaje_usuario:
        logger.info(f"📝 Mensaje: {mensaje_usuario[:100]}...")
        logger.info("🔍 Generando embedding para búsqueda semántica...")
        query_embedding = generar_embedding(mensaje_usuario)
        
        if query_embedding:
            logger.info(f"   ✅ Embedding generado: {len(query_embedding)} dimensiones")
        else:
            logger.warning("   ⚠️ No se pudo generar embedding")
    
    # Recuperar datos
    logger.info("📊 Recuperando estadísticas...")
    estadisticas = obtener_estadisticas_doctor(doctor_id)
    
    logger.info("👥 Recuperando pacientes recientes...")
    pacientes_recientes = obtener_pacientes_recientes(doctor_id, limit=10)
    
    logger.info("📅 Recuperando citas del día...")
    citas_hoy = obtener_citas_del_dia(doctor_id)
    
    logger.info("📋 Recuperando historiales relevantes...")
    historiales = buscar_historiales_semantica(
        doctor_id, 
        query_embedding=query_embedding,  # ✅ Ahora SÍ pasa el embedding
        limit=5
    )
    
    # Construir contexto médico estructurado
    contexto_medico = {
        "doctor_id": doctor_id,
        "mensaje_procesado": mensaje_usuario,
        "tiene_busqueda_semantica": query_embedding is not None,
        "estadisticas": estadisticas,
        "pacientes_recientes": pacientes_recientes,
        "citas_hoy": citas_hoy,
        "historiales_relevantes": historiales,
        "timestamp": datetime.now(TIMEZONE).isoformat()
    }
    
    # Formatear para logs
    contexto_formateado = formatear_contexto_medico(
        pacientes_recientes,
        citas_hoy,
        estadisticas,
        historiales
    )
    
    logger.info("\n" + contexto_formateado)
    logger.info("\n✅ Recuperación médica completada → Siguiente: seleccion_herramientas\n")
    
    # ✅ Retornar Command (no Dict)
    return Command(
        update={"contexto_medico": contexto_medico},
        goto="seleccion_herramientas"
    )

## 5. Actualizar wrapper function

Reemplazar nodo_recuperacion_medica_wrapper (líneas 410-414) con:

def nodo_recuperacion_medica_wrapper(state: WhatsAppAgentState) -> Command:
    """Wrapper para LangGraph - retorna Command directamente."""
    return nodo_recuperacion_medica(state)

## 6. Crear tests unitarios en tests/test_recuperacion_medica.py

Crear nuevo archivo con 15 tests:

"""
Tests para Nodo N3B: Recuperación Médica

✅ Usa CSV fixtures para tests rápidos
✅ Tests de búsqueda semántica con embeddings
✅ Tests de Command pattern
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from langchain_core.messages import HumanMessage
from langgraph.types import Command

from src.nodes.recuperacion_medica_node import (
    nodo_recuperacion_medica,
    obtener_pacientes_recientes,
    obtener_citas_del_dia,
    obtener_estadisticas_doctor,
    buscar_historiales_semantica,
    generar_embedding
)

# ==================== FIXTURES ====================

@pytest.fixture
def estado_base_doctor():
    """Estado base para tests de doctor."""
    return {
        'doctor_id': 1,
        'tipo_usuario': 'doctor',
        'messages': [HumanMessage(content="Busca a Juan Pérez")],
        'estado_conversacion': 'inicial'
    }

@pytest.fixture
def estado_no_doctor():
    """Estado de usuario que NO es doctor."""
    return {
        'tipo_usuario': 'paciente_externo',
        'messages': [HumanMessage(content="Hola")],
        'estado_conversacion': 'inicial'
    }

# ==================== TESTS BÁSICOS ====================

@patch('src.nodes.recuperacion_medica_node.obtener_estadisticas_doctor')
@patch('src.nodes.recuperacion_medica_node.obtener_pacientes_recientes')
@patch('src.nodes.recuperacion_medica_node.obtener_citas_del_dia')
@patch('src.nodes.recuperacion_medica_node.buscar_historiales_semantica')
@patch('src.nodes.recuperacion_medica_node.generar_embedding')
def test_recuperacion_medica_basica(mock_embed, mock_hist, mock_citas, mock_pac, mock_stats, estado_base_doctor):
    """Test básico: Recupera contexto médico correctamente."""
    mock_stats.return_value = {'citas_hoy': 5, 'citas_semana': 20}
    mock_pac.return_value = [{'id': 1, 'nombre': 'Juan Pérez'}]
    mock_citas.return_value = [{'id': 1, 'paciente_nombre': 'María'}]
    mock_hist.return_value = [{'id': 1, 'nota': 'Consulta general'}]
    mock_embed.return_value = [0.1] * 384
    
    resultado = nodo_recuperacion_medica(estado_base_doctor)
    
    assert isinstance(resultado, Command)
    assert resultado.goto == "seleccion_herramientas"
    assert 'contexto_medico' in resultado.update
    assert resultado.update['contexto_medico']['doctor_id'] == 1


def test_no_doctor_salta_recuperacion(estado_no_doctor):
    """Usuario que NO es doctor → salta recuperación."""
    resultado = nodo_recuperacion_medica(estado_no_doctor)
    
    assert isinstance(resultado, Command)
    assert resultado.goto == "generacion_resumen"
    assert resultado.update['contexto_medico'] is None


def test_detecta_estado_activo():
    """Detecta flujo activo y salta recuperación."""
    estado = {
        'doctor_id': 1,
        'tipo_usuario': 'doctor',
        'messages': [HumanMessage(content="Test")],
        'estado_conversacion': 'ejecutando_herramienta'
    }
    
    resultado = nodo_recuperacion_medica(estado)
    
    assert isinstance(resultado, Command)
    assert resultado.goto == "seleccion_herramientas"
    assert resultado.update['contexto_medico'] is None


# ==================== TESTS BÚSQUEDA SEMÁNTICA ====================

@patch('src.nodes.recuperacion_medica_node.psycopg.connect')
def test_busqueda_semantica_con_embedding(mock_connect):
    """Búsqueda semántica funciona con embedding."""
    mock_cursor = Mock()
    mock_cursor.fetchall.return_value = [
        (1, 101, 'Juan Pérez', 'Consulta general', '2026-01-15', 0.85)
    ]
    mock_connect.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
    
    embedding = [0.1] * 384
    historiales = buscar_historiales_semantica(1, query_embedding=embedding, limit=5)
    
    assert len(historiales) == 1
    assert historiales[0]['similitud'] == 0.85
    assert historiales[0]['paciente_nombre'] == 'Juan Pérez'


def test_busqueda_semantica_sin_embedding():
    """Sin embedding → retorna lista vacía."""
    historiales = buscar_historiales_semantica(1, query_embedding=None, limit=5)
    
    assert historiales == []


@patch('src.nodes.recuperacion_medica_node.get_embedding_model')
def test_generar_embedding_funciona(mock_model):
    """Genera embedding de 384 dimensiones."""
    mock_model.return_value.encode.return_value = Mock(tolist=lambda: [0.1] * 384)
    
    embedding = generar_embedding("Busca paciente Juan")
    
    assert embedding is not None
    assert len(embedding) == 384


@patch('src.nodes.recuperacion_medica_node.get_embedding_model')
def test_generar_embedding_maneja_error(mock_model):
    """Maneja error al generar embedding."""
    mock_model.side_effect = Exception("Model error")
    
    embedding = generar_embedding("Test")
    
    assert embedding is None


# ==================== TESTS FUNCIONES AUXILIARES ====================

@patch('src.nodes.recuperacion_medica_node.psycopg.connect')
def test_obtener_pacientes_recientes(mock_connect):
    """Obtiene últimos pacientes correctamente."""
    mock_cursor = Mock()
    mock_cursor.fetchall.return_value = [
        (1, 'Juan Pérez', '+526641234567', 'juan@test.com', '2026-01-31', 5)
    ]
    mock_connect.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
    
    pacientes = obtener_pacientes_recientes(1, limit=10)
    
    assert len(pacientes) == 1
    assert pacientes[0]['nombre'] == 'Juan Pérez'
    assert pacientes[0]['total_citas'] == 5


@patch('src.nodes.recuperacion_medica_node.psycopg.connect')
def test_obtener_citas_del_dia(mock_connect):
    """Obtiene citas del día correctamente."""
    mock_cursor = Mock()
    mock_cursor.fetchall.return_value = [
        (1, 'María García', '2026-01-31 09:00:00', 'agendada', 'Consulta')
    ]
    mock_connect.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
    
    citas = obtener_citas_del_dia(1)
    
    assert len(citas) == 1
    assert citas[0]['paciente_nombre'] == 'María García'


@patch('src.nodes.recuperacion_medica_node.psycopg.connect')
def test_obtener_estadisticas_doctor(mock_connect):
    """Obtiene estadísticas correctamente."""
    mock_cursor = Mock()
    mock_cursor.fetchone.side_effect = [
        ({'citas_hoy': 5, 'citas_semana': 20, 'pacientes_totales': 100},)
    ]
    mock_connect.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
    
    stats = obtener_estadisticas_doctor(1)
    
    assert stats['citas_hoy'] == 5
    assert stats['citas_semana'] == 20


# ==================== TESTS EDGE CASES ====================

def test_doctor_id_none():
    """doctor_id None → salta recuperación."""
    estado = {
        'doctor_id': None,
        'tipo_usuario': 'doctor',
        'messages': [HumanMessage(content="Test")]
    }
    
    resultado = nodo_recuperacion_medica(estado)
    
    assert isinstance(resultado, Command)
    assert resultado.update['contexto_medico'] is None


@patch('src.nodes.recuperacion_medica_node.obtener_estadisticas_doctor')
def test_error_en_query_no_rompe_flujo(mock_stats, estado_base_doctor):
    """Error en query no rompe el flujo."""
    mock_stats.side_effect = Exception("DB error")
    
    # Patch otras funciones para que funcionen
    with patch('src.nodes.recuperacion_medica_node.obtener_pacientes_recientes', return_value=[]):
        with patch('src.nodes.recuperacion_medica_node.obtener_citas_del_dia', return_value=[]):
            with patch('src.nodes.recuperacion_medica_node.buscar_historiales_semantica', return_value=[]):
                with patch('src.nodes.recuperacion_medica_node.generar_embedding', return_value=None):
                    resultado = nodo_recuperacion_medica(estado_base_doctor)
    
    assert isinstance(resultado, Command)
    assert resultado.goto == "seleccion_herramientas"


def test_mensaje_vacio_funciona():
    """Mensaje vacío no rompe generación de embedding."""
    estado = {
        'doctor_id': 1,
        'tipo_usuario': 'doctor',
        'messages': [],
        'estado_conversacion': 'inicial'
    }
    
    with patch('src.nodes.recuperacion_medica_node.obtener_estadisticas_doctor', return_value={}):
        with patch('src.nodes.recuperacion_medica_node.obtener_pacientes_recientes', return_value=[]):
            with patch('src.nodes.recuperacion_medica_node.obtener_citas_del_dia', return_value=[]):
                with patch('src.nodes.recuperacion_medica_node.buscar_historiales_semantica', return_value=[]):
                    resultado = nodo_recuperacion_medica(estado)
    
    assert isinstance(resultado, Command)

# Criterios de aceptación

- Command pattern implementado (retorna Command, no Dict)
- Búsqueda semántica funcional (genera embeddings reales)
- Detecta estado_conversacion activo y salta recuperación
- 15 tests pasando (búsqueda semántica, Command, edge cases)
- Embedding model se carga una sola vez (singleton)
- Contexto médico estructurado con flag tiene_busqueda_semantica
- Alineado con patrones de Maya/Filtrado

# Validación manual

Después de implementar, probar:

1. Doctor pregunta "Busca a Juan" → Genera embedding, busca historiales relevantes
2. Usuario no doctor → Salta recuperación, goto="generacion_resumen"
3. Estado activo → Salta recuperación, goto="seleccion_herramientas"
4. Query sin resultados → No rompe flujo, retorna contexto vacío

# Referencias

- PR #3: Maya Paciente (Command pattern)
- PR #10: Filtrado Inteligente (Command + estado)
- pgvector docs: Búsqueda vectorial con <=> operator
- sentence-transformers: all-MiniLM-L6-v2 (384 dims)

Repositorio: cognitaia2025-hub/Modulo_WhatsApp
```
