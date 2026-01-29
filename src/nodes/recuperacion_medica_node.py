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

load_dotenv()
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5434/agente_whatsapp")
TIMEZONE = pytz.timezone("America/Tijuana")


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
                        p.nombre,
                        p.telefono,
                        p.email,
                        MAX(cm.fecha_hora_inicio) as ultima_cita,
                        COUNT(cm.id) as total_citas
                    FROM pacientes p
                    INNER JOIN citas_medicas cm ON p.id = cm.paciente_id
                    WHERE cm.doctor_id = %s
                        AND cm.estado IN ('confirmada', 'completada')
                    GROUP BY p.id, p.nombre, p.telefono, p.email
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
                        p.nombre as paciente_nombre,
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
    # Si no hay embedding, retornar historiales más recientes
    if not query_embedding:
        try:
            with psycopg.connect(DATABASE_URL) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT 
                            h.id,
                            h.paciente_id,
                            p.nombre as paciente_nombre,
                            h.nota,
                            h.fecha
                        FROM historiales_medicos h
                        LEFT JOIN pacientes p ON h.paciente_id = p.id
                        WHERE h.doctor_id = %s
                        ORDER BY h.fecha DESC
                        LIMIT %s
                    """, (doctor_id, limit))
                    
                    historiales = []
                    for row in cur.fetchall():
                        historiales.append({
                            "id": row[0],
                            "paciente_id": row[1],
                            "paciente_nombre": row[2],
                            "nota": row[3],
                            "fecha": row[4].isoformat() if row[4] else None,
                            "similitud": None
                        })
                    
                    return historiales
        
        except Exception as e:
            logger.error(f"❌ Error obteniendo historiales recientes: {e}")
            return []
    
    # Búsqueda semántica con embeddings
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                # Convertir embedding a string de PostgreSQL
                embedding_str = f"[{','.join(map(str, query_embedding))}]"
                
                cur.execute("""
                    SELECT 
                        h.id,
                        h.paciente_id,
                        p.nombre as paciente_nombre,
                        h.nota,
                        h.fecha,
                        ROUND((1 - (h.embedding <=> %s::vector))::NUMERIC, 4) as similitud
                    FROM historiales_medicos h
                    LEFT JOIN pacientes p ON h.paciente_id = p.id
                    WHERE h.doctor_id = %s
                        AND h.embedding IS NOT NULL
                    ORDER BY h.embedding <=> %s::vector
                    LIMIT %s
                """, (embedding_str, doctor_id, embedding_str, limit))
                
                historiales = []
                for row in cur.fetchall():
                    historiales.append({
                        "id": row[0],
                        "paciente_id": row[1],
                        "paciente_nombre": row[2],
                        "nota": row[3],
                        "fecha": row[4].isoformat() if row[4] else None,
                        "similitud": float(row[5]) if row[5] else None
                    })
                
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


def nodo_recuperacion_medica(state: WhatsAppAgentState) -> Dict:
    """
    Nodo de recuperación de contexto médico (Sin LLM)
    
    Flujo:
    1. Verifica que el usuario sea doctor
    2. Recupera pacientes recientes (últimos 10)
    3. Recupera citas del día actual
    4. Recupera estadísticas del doctor
    5. (Opcional) Búsqueda semántica en historiales
    6. Formatea y retorna contexto
    
    Args:
        state: WhatsAppAgentState
        
    Returns:
        Dict con actualizaciones del state
    """
    logger.info("\n" + "=" * 70)
    logger.info("🏥 NODO: RECUPERACIÓN MÉDICA")
    logger.info("=" * 70)
    
    # Verificar que sea doctor
    tipo_usuario = state.get("tipo_usuario", "")
    doctor_id = state.get("doctor_id")
    
    if tipo_usuario != "doctor" or not doctor_id:
        logger.info("ℹ️  Usuario no es doctor, saltando recuperación médica")
        return {
            "contexto_medico": None
        }
    
    logger.info(f"👨‍⚕️ Doctor ID: {doctor_id}")
    
    # Recuperar datos
    logger.info("📊 Recuperando estadísticas...")
    estadisticas = obtener_estadisticas_doctor(doctor_id)
    
    logger.info("👥 Recuperando pacientes recientes...")
    pacientes_recientes = obtener_pacientes_recientes(doctor_id, limit=10)
    
    logger.info("📅 Recuperando citas del día...")
    citas_hoy = obtener_citas_del_dia(doctor_id)
    
    logger.info("📋 Recuperando historiales relevantes...")
    historiales = buscar_historiales_semantica(doctor_id, limit=5)
    
    # Construir contexto médico
    contexto_medico = {
        "doctor_id": doctor_id,
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
    logger.info("\n✅ Recuperación médica completada\n")
    
    return {
        "contexto_medico": contexto_medico
    }


# Wrapper para compatibilidad con grafo
def nodo_recuperacion_medica_wrapper(state: WhatsAppAgentState) -> WhatsAppAgentState:
    """
    Wrapper que mantiene la firma esperada por el grafo
    """
    try:
        # Llamar al nodo principal
        resultado = nodo_recuperacion_medica(state)
        
        # Actualizar state con resultado
        state.update(resultado)
        
        # Retornar el estado completo
        return state
        
    except Exception as e:
        logger.error(f"❌ Error en nodo recuperación médica: {e}")
        
        # Respuesta de fallback
        state["contexto_medico"] = {
            "error": str(e),
            "fallback": True
        }
        
        return state
