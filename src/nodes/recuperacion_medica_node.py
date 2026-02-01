"""
Nodo: Recuperación Médica (Sin LLM)

Recupera contexto médico relevante para doctores:
- Pacientes recientes (últimos 10)
- Citas del día actual
- Búsqueda semántica en historiales (con embeddings)
- Estadísticas del doctor

**Sin LLM:** Solo consultas SQL + búsqueda vectorial
"""

import logging
import psycopg
from typing import Dict, List, Optional
from datetime import datetime, date
import os
from dotenv import load_dotenv
import pytz

from src.state.agent_state import WhatsAppAgentState
from langgraph.types import Command
from sentence_transformers import SentenceTransformer

load_dotenv()
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5434/agente_whatsapp")
TIMEZONE = pytz.timezone("America/Tijuana")

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
        # Log truncated text for debugging
        texto_truncado = texto[:100] + "..." if len(texto) > 100 else texto
        logger.error(f"❌ Error generando embedding para texto: '{texto_truncado}'. Error: {e}")
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


def obtener_pacientes_recientes(doctor_id: int, limit: int = 10) -> List[Dict]:
    """
    Obtiene los últimos pacientes atendidos por el doctor
    
    Args:
        doctor_id: ID del doctor
        limit: Número máximo de pacientes a retornar
        
    Returns:
        Lista de diccionarios con info de pacientes
    """
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT DISTINCT ON (p.id)
                        p.id,
                        p.nombre_completo,
                        p.telefono,
                        p.email,
                        MAX(cm.fecha_hora_inicio) as ultima_cita,
                        COUNT(cm.id) as total_citas
                    FROM pacientes p
                    INNER JOIN citas_medicas cm ON p.id = cm.paciente_id
                    WHERE cm.doctor_id = %s
                        AND cm.estado IN ('confirmada', 'completada')
                    GROUP BY p.id, p.nombre_completo, p.telefono, p.email
                    ORDER BY ultima_cita DESC
                    LIMIT %s
                """, (doctor_id, limit))
                
                pacientes = []
                for row in cur.fetchall():
                    pacientes.append({
                        "id": row[0],
                        "nombre": row[1],
                        "telefono": row[2],
                        "email": row[3],
                        "ultima_cita": row[4].isoformat() if row[4] else None,
                        "total_citas": row[5]
                    })
                
                return pacientes
    
    except Exception as e:
        logger.error(f"❌ Error obteniendo pacientes recientes: {e}")
        return []


def obtener_citas_del_dia(doctor_id: int) -> List[Dict]:
    """
    Obtiene todas las citas del doctor para el día actual
    
    Args:
        doctor_id: ID del doctor
        
    Returns:
        Lista de diccionarios con info de citas
    """
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                # Fecha actual en timezone correcto
                hoy = datetime.now(TIMEZONE).date()
                
                cur.execute("""
                    SELECT 
                        cm.id,
                        cm.paciente_id,
                        p.nombre_completo as paciente_nombre,
                        cm.fecha_hora_inicio,
                        cm.fecha_hora_fin,
                        cm.estado,
                        cm.motivo,
                        cm.fue_asignacion_automatica
                    FROM citas_medicas cm
                    LEFT JOIN pacientes p ON cm.paciente_id = p.id
                    WHERE cm.doctor_id = %s
                        AND DATE(cm.fecha_hora_inicio AT TIME ZONE 'America/Tijuana') = %s
                    ORDER BY cm.fecha_hora_inicio ASC
                """, (doctor_id, hoy))
                
                citas = []
                for row in cur.fetchall():
                    citas.append({
                        "id": row[0],
                        "paciente_id": row[1],
                        "paciente_nombre": row[2],
                        "fecha_hora_inicio": row[3].isoformat() if row[3] else None,
                        "fecha_hora_fin": row[4].isoformat() if row[4] else None,
                        "estado": row[5],
                        "motivo": row[6],
                        "fue_asignacion_automatica": row[7]
                    })
                
                return citas
    
    except Exception as e:
        logger.error(f"❌ Error obteniendo citas del día: {e}")
        return []


def obtener_estadisticas_doctor(doctor_id: int) -> Dict:
    """
    Obtiene estadísticas generales del doctor
    
    Args:
        doctor_id: ID del doctor
        
    Returns:
        Diccionario con estadísticas
    """
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                # Usar función SQL si existe
                cur.execute("""
                    SELECT obtener_estadisticas_doctor_completas(%s)
                """, (doctor_id,))
                
                resultado = cur.fetchone()
                if resultado and resultado[0]:
                    return resultado[0]
                
                # Fallback: calcular manualmente
                cur.execute("""
                    SELECT 
                        COUNT(*) FILTER (WHERE DATE(fecha_hora_inicio AT TIME ZONE 'America/Tijuana') = CURRENT_DATE) as citas_hoy,
                        COUNT(*) FILTER (WHERE fecha_hora_inicio >= CURRENT_DATE AND fecha_hora_inicio < CURRENT_DATE + INTERVAL '7 days') as citas_semana,
                        COUNT(DISTINCT paciente_id) as pacientes_totales
                    FROM citas_medicas
                    WHERE doctor_id = %s
                """, (doctor_id,))
                
                row = cur.fetchone()
                return {
                    "doctor_id": doctor_id,
                    "citas_hoy": row[0],
                    "citas_semana": row[1],
                    "pacientes_totales": row[2],
                    "proxima_cita": None
                }
    
    except Exception as e:
        logger.error(f"❌ Error obteniendo estadísticas: {e}")
        return {
            "doctor_id": doctor_id,
            "citas_hoy": 0,
            "citas_semana": 0,
            "pacientes_totales": 0
        }


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


def formatear_contexto_medico(
    pacientes_recientes: List[Dict],
    citas_hoy: List[Dict],
    estadisticas: Dict,
    historiales: List[Dict]
) -> str:
    """
    Formatea contexto médico en string legible para logs/debugging
    
    Args:
        pacientes_recientes: Lista de pacientes
        citas_hoy: Lista de citas del día
        estadisticas: Estadísticas del doctor
        historiales: Historiales médicos relevantes
        
    Returns:
        String formateado
    """
    contexto = []
    
    # Estadísticas
    contexto.append("📊 ESTADÍSTICAS:")
    contexto.append(f"  • Citas hoy: {estadisticas.get('citas_hoy', 0)}")
    contexto.append(f"  • Citas esta semana: {estadisticas.get('citas_semana', 0)}")
    contexto.append(f"  • Pacientes totales: {estadisticas.get('pacientes_totales', 0)}")
    
    # Citas del día
    contexto.append(f"\n📅 CITAS HOY ({len(citas_hoy)}):")
    if citas_hoy:
        for cita in citas_hoy[:5]:  # Máximo 5
            hora = cita['fecha_hora_inicio'][:16] if cita['fecha_hora_inicio'] else "N/A"
            contexto.append(
                f"  • {hora} - {cita['paciente_nombre']} ({cita['estado']})"
            )
    else:
        contexto.append("  • Sin citas agendadas")
    
    # Pacientes recientes
    contexto.append(f"\n👥 PACIENTES RECIENTES ({len(pacientes_recientes)}):")
    if pacientes_recientes:
        for pac in pacientes_recientes[:5]:  # Máximo 5
            contexto.append(
                f"  • {pac['nombre']} - {pac['total_citas']} citas"
            )
    else:
        contexto.append("  • Sin pacientes recientes")
    
    # Historiales relevantes
    if historiales:
        contexto.append(f"\n📋 HISTORIALES RELEVANTES ({len(historiales)}):")
        for hist in historiales[:3]:  # Máximo 3
            nota = hist['nota'] or "Sin notas"
            nota_preview = nota[:80] + "..." if len(nota) > 80 else nota
            similitud_str = f"({hist['similitud']:.2f})" if hist['similitud'] else ""
            contexto.append(
                f"  • {hist['paciente_nombre']}: {nota_preview} {similitud_str}"
            )
    
    return "\n".join(contexto)


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


# Wrapper para compatibilidad con grafo
def nodo_recuperacion_medica_wrapper(state: WhatsAppAgentState) -> Command:
    """Wrapper para LangGraph - retorna Command directamente."""
    return nodo_recuperacion_medica(state)
