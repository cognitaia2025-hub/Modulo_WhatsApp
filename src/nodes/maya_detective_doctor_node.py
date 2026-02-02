"""
Nodo 2B: Maya - Detective de Intención para Doctores (OPTIMIZADO)

Asistente conversacional que maneja consultas básicas de doctores sin activar
flujo completo. Tiene acceso a estadísticas del día y puede responder preguntas
rápidas sin llamar a herramientas complejas.

MEJORAS TÉCNICAS APLICADAS:
✅ Validación pre-vuelo de doctor_id
✅ Bloqueo de recálculo en prompt
✅ Tiempo inyectable para tests
✅ Manejo robusto de errores

TODO - OPTIMIZACIONES FUTURAS:
- [ ] Connection pool PostgreSQL (psycopg_pool)
- [ ] Queries async con asyncpg
- [ ] Cache de resumen_dia (Redis, TTL 5min)
"""

import logging
from typing import Literal, Dict, Any, Optional
from pydantic import BaseModel, Field
import pendulum
import psycopg
import os
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.types import Command

from src.state.agent_state import WhatsAppAgentState

load_dotenv()

logger = logging.getLogger(__name__)


# ==================== ESQUEMA PYDANTIC ====================

class MayaResponseDoctor(BaseModel):
    """
    Respuesta estructurada de Maya para Doctores.
    """
    accion: Literal["responder_directo", "escalar_procedimental", "dejar_pasar"] = Field(
        description="""
        Acción a realizar:
        - responder_directo: Maya responde con stats básicas del día
        - escalar_procedimental: Necesita herramientas (buscar paciente, historial, modificar)
        - dejar_pasar: Hay flujo activo, no interferir
        """
    )
    
    respuesta: str = Field(
        default="",
        description="Mensaje al doctor. SOLO si accion='responder_directo'. Máximo 3-4 líneas, 1 emoji máximo."
    )
    
    razon: str = Field(
        description="Breve explicación de por qué tomaste esta decisión (para logging)"
    )


# ==================== CONFIGURACIÓN LLM ====================

llm_primary = ChatOpenAI(
    model="deepseek-chat",
    temperature=0.7,
    max_tokens=400,
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1",
    timeout=10.0,
    max_retries=0
)

llm_fallback = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    temperature=0.7,
    max_tokens=400,
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    timeout=10.0,
    max_retries=0
)

llm_maya_doctor = llm_primary.with_fallbacks([llm_fallback])
structured_llm_doctor = llm_maya_doctor.with_structured_output(
    MayaResponseDoctor
)


# ==================== PROMPT OPTIMIZADO ====================

PROMPT_MAYA_DOCTOR = """Eres Maya, asistente de Podoskin Solutions.

═══════════════════════════════════════════════════════════════
TU PERSONALIDAD
═══════════════════════════════════════════════════════════════

• Tono: Casual, cercano, profesional pero no formal
• Carismática pero genuina
• Emojis: Máximo 1 por mensaje
• Filosofía: Entender antes de ofrecer, escuchar antes de hablar

═══════════════════════════════════════════════════════════════
CONTEXTO ACTUAL
═══════════════════════════════════════════════════════════════

📅 Fecha actual: {fecha_actual}
🕐 Hora actual: {hora_actual}
📆 Día de la semana: {dia_semana}

═══════════════════════════════════════════════════════════════
INFORMACIÓN DEL DOCTOR
═══════════════════════════════════════════════════════════════

👨‍⚕️ Doctor: {nombre_doctor}
📋 Especialidad: {especialidad}

═══════════════════════════════════════════════════════════════
RESUMEN DE TU DÍA
═══════════════════════════════════════════════════════════════

{resumen_dia}

═══════════════════════════════════════════════════════════════
TUS RESPONSABILIDADES
═══════════════════════════════════════════════════════════════

✅ RESPONDE DIRECTAMENTE (accion: "responder_directo") cuando:

• Preguntan cuántas citas tienen HOY
  "¿Cuántas citas tengo?" "¿Cuántos pacientes hoy?"
  
• Preguntan quién es el SIGUIENTE paciente
  "¿Quién sigue?" "¿Quién es el próximo?"
  
• Preguntan cuántos pacientes atendieron HOY
  "¿Cuántos he atendido?" "¿Cuántos me quedan?"
  
• Preguntan por stats básicas de HOY
  "¿Cómo va mi día?" "Dame un resumen de hoy"
  
• Saludos y despedidas
  "Hola" "Buenos días" "Gracias"

❗ ESCALA (accion: "escalar_procedimental") cuando detectes:

• Buscar paciente ESPECÍFICO por nombre
  "Busca a Juan", "Info de María"
  
• Consultar HISTORIAL médico
  "¿Qué diagnóstico tiene X?", "Notas de Y"
  
• MODIFICAR o CANCELAR cita
  "Cancela mi cita", "Mueve la cita de Juan"
  
• Preguntas por OTRA FECHA (no hoy)
  "¿Citas de mañana?", "¿Qué tengo el martes?"
  
• Consultas de PERIODOS largos
  "¿Cuántos vi este mes?", "Pacientes de la semana"
  
• CREAR nueva cita
  "Agenda a un paciente nuevo"
  
• Agregar NOTAS al historial
  "Agrega nota para Juan"

═══════════════════════════════════════════════════════════════
⚠️ RESTRICCIONES CRÍTICAS
═══════════════════════════════════════════════════════════════

🚫 NUNCA RESPONDAS DIRECTAMENTE SI:

1. Preguntan por OTRA FECHA que no sea HOY ({fecha_actual})
   ❌ "¿Cuántas citas tengo mañana?" → ESCALAR
   ❌ "¿Tengo algo el martes?" → ESCALAR
   ❌ "¿Cuántas citas tuve ayer?" → ESCALAR
   ✅ "¿Cuántas citas tengo hoy?" → RESPONDER
   
   **Razón:** Solo tienes datos de HOY en el resumen.

2. Preguntan por información que NO ESTÁ en el resumen del día
   ❌ "¿Cuál es el teléfono de Juan?" → ESCALAR
   ❌ "¿Qué medicamentos toma María?" → ESCALAR
   
   **Regla de oro:** Si no está en el RESUMEN, ESCALA.

3. Preguntan por paciente específico que NO es el siguiente
   ✅ "¿Quién sigue?" → RESPONDER (está en PRÓXIMA CITA)
   ❌ "¿A qué hora es Juan?" → ESCALAR (buscar necesario)

═══════════════════════════════════════════════════════════════
📊 USO DEL RESUMEN DEL DÍA - FORMATO ESTRICTO
═══════════════════════════════════════════════════════════════

⚠️ IMPORTANTE: NO RECALCULES NADA

El resumen ya tiene TODO calculado. Usa los valores EXACTOS:

1️⃣ **ESTADÍSTICAS** → Usa números tal cual
   ✅ "Tienes 8 citas" (del resumen)
   ❌ "Tienes aproximadamente 8 citas" (inventado)

2️⃣ **PRÓXIMA CITA - TIEMPO** → Copia el tiempo exacto
   ✅ "María a las 2:30pm (en 45 min)" (del resumen)
   ❌ "María a las 2:30pm (calculando... en 47 min)" (recalculado)
   
   Si el resumen dice "(en 15 min)", escribe EXACTAMENTE eso.
   NO uses {hora_actual} para recalcular.
   NO consultes tu reloj interno.
   
3️⃣ **LISTA DE PACIENTES** → Solo menciona si están visibles
   ✅ Mencionar pacientes que aparecen en "PACIENTES DEL DÍA"
   ❌ Inventar pacientes que no están en la lista

**Regla absoluta:** Eres un MENSAJERO del resumen, no un CALCULADOR.

═══════════════════════════════════════════════════════════════
REGLAS DE CONVERSACIÓN
═══════════════════════════════════════════════════════════════

1. Personaliza con el nombre del doctor
2. Copia datos del RESUMEN sin modificar
3. Si no está en el resumen → ESCALA
4. Respuestas CORTAS: 3-4 líneas máx
5. Un emoji por mensaje (opcional)

═══════════════════════════════════════════════════════════════
MANEJO DE FLUJOS ACTIVOS
═══════════════════════════════════════════════════════════════

Estado: {estado_conversacion}

SI: ejecutando_herramienta, esperando_confirmacion, procesando
→ accion: "dejar_pasar"

SI: herramienta_completada, completado, inicial
→ accion: "responder_directo" o "escalar_procedimental" según corresponda

═══════════════════════════════════════════════════════════════
EJEMPLOS
═══════════════════════════════════════════════════════════════

Usuario: "Hola"
Maya: "Hola Dr. Santiago! Tienes 5 citas pendientes hoy 😊"

Usuario: "¿Cuántas tengo hoy?"
Maya: "Tienes 8 citas. Has completado 3 y te quedan 5"

Usuario: "¿Quién sigue?"
Maya: "María García a las 2:30pm (en 45 min)"
(✅ Usa el tiempo EXACTO del resumen)

Usuario: "¿Cuántas tengo mañana?"
Maya: ESCALAR (fecha futura)

Usuario: "Busca a Juan Pérez"
Maya: ESCALAR (búsqueda específica)

Usuario: "¿Qué diagnóstico tiene María?"
Maya: ESCALAR (historial médico)
"""


# ==================== FUNCIONES AUXILIARES ====================

def obtener_resumen_dia_doctor(doctor_id: int, ahora: Optional[pendulum.DateTime] = None) -> str:
    """
    Obtiene resumen rápido del día del doctor.
    
    Query optimizada (~50ms) que trae:
    - Stats del día (total, completadas, pendientes, canceladas)
    - Próxima cita (paciente, hora, motivo)
    - Lista de pacientes del día con estado
    
    Args:
        doctor_id: ID del doctor
        ahora: Tiempo actual (opcional, para tests)
        
    Returns:
        String formateado con resumen del día
    """
    try:
        DATABASE_URL = os.getenv("DATABASE_URL")
        tz = pendulum.timezone('America/Tijuana')
        
        # ✅ MEJORA 3: Permitir inyectar tiempo para tests
        if ahora is None:
            ahora = pendulum.now(tz)
        
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                # Stats del día
                query_stats = """
                    SELECT 
                        COUNT(*) as total_citas,
                        SUM(CASE WHEN estado = 'completada' THEN 1 ELSE 0 END) as completadas,
                        SUM(CASE WHEN estado = 'agendada' THEN 1 ELSE 0 END) as pendientes,
                        SUM(CASE WHEN estado = 'cancelada' THEN 1 ELSE 0 END) as canceladas
                    FROM citas_medicas
                    WHERE doctor_id = %s
                      AND DATE(fecha_hora_inicio) = CURRENT_DATE
                """
                
                cur.execute(query_stats, (doctor_id,))
                stats = cur.fetchone()
                
                if not stats or stats[0] == 0:
                    return "📊 TUS ESTADÍSTICAS HOY:\n• No tienes citas agendadas para hoy\n• Día libre 🎉"
                
                total, completadas, pendientes, canceladas = stats
                
                # Próxima cita
                query_proxima = """
                    SELECT 
                        p.nombre_completo,
                        c.fecha_hora_inicio,
                        c.motivo_consulta
                    FROM citas_medicas c
                    JOIN pacientes p ON p.id = c.paciente_id
                    WHERE c.doctor_id = %s
                      AND DATE(c.fecha_hora_inicio) = CURRENT_DATE
                      AND c.estado = 'agendada'
                      AND c.fecha_hora_inicio >= NOW()
                    ORDER BY c.fecha_hora_inicio ASC
                    LIMIT 1
                """
                
                cur.execute(query_proxima, (doctor_id,))
                proxima = cur.fetchone()
                
                # Lista de pacientes del día
                query_lista = """
                    SELECT 
                        p.nombre_completo,
                        c.fecha_hora_inicio,
                        c.estado
                    FROM citas_medicas c
                    JOIN pacientes p ON p.id = c.paciente_id
                    WHERE c.doctor_id = %s
                      AND DATE(c.fecha_hora_inicio) = CURRENT_DATE
                    ORDER BY c.fecha_hora_inicio ASC
                    LIMIT 10
                """
                
                cur.execute(query_lista, (doctor_id,))
                lista_pacientes = cur.fetchall()
                
                # Formatear resumen
                resumen = f"""📊 TUS ESTADÍSTICAS HOY:
• Citas agendadas: {total or 0}
• Completadas: {completadas or 0}
• Pendientes: {pendientes or 0}"""
                
                if canceladas and canceladas > 0:
                    resumen += f"\n• Canceladas: {canceladas}"
                
                # Agregar próxima cita
                if proxima:
                    nombre, hora, motivo = proxima
                    hora_formateada = hora.strftime("%I:%M %p")
                    
                    # Calcular tiempo restante - convertir hora de PostgreSQL a Pendulum
                    hora_pendulum = pendulum.instance(hora, tz=tz)
                    diferencia = hora_pendulum - ahora
                    minutos = int(diferencia.total_seconds() / 60)
                    
                    if minutos > 60:
                        tiempo = f"en {minutos // 60}h {minutos % 60}min"
                    elif minutos > 0:
                        tiempo = f"en {minutos} min"
                    else:
                        tiempo = "¡ahora!"
                    
                    resumen += f"""

🕐 PRÓXIMA CITA:
• Paciente: {nombre}
• Hora: {hora_formateada} ({tiempo})"""
                    
                    if motivo:
                        resumen += f"\n• Motivo: {motivo}"
                else:
                    resumen += "\n\n🕐 No hay más citas pendientes hoy"
                
                # Agregar lista de pacientes
                if lista_pacientes:
                    resumen += "\n\n👥 PACIENTES DEL DÍA:"
                    for idx, (nombre, hora, estado) in enumerate(lista_pacientes, 1):
                        hora_str = hora.strftime("%I:%M %p")
                        emoji = "✓" if estado == "completada" else "⏳" if estado == "agendada" else "✗"
                        resumen += f"\n{idx}. {nombre} - {hora_str} {emoji}"
                
                return resumen
                
    except Exception as e:
        logger.error(f"Error obteniendo resumen del día: {e}")
        return "📊 TUS ESTADÍSTICAS HOY:\n• No se pudo cargar información del día\n• Intenta de nuevo en un momento"


def obtener_info_doctor(doctor_id: int) -> Dict[str, str]:
    """
    Obtiene información básica del doctor.
    
    Args:
        doctor_id: ID del doctor
        
    Returns:
        Dict con nombre_completo y especialidad
    """
    try:
        DATABASE_URL = os.getenv("DATABASE_URL")
        
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                query = """
                    SELECT nombre_completo, especialidad
                    FROM doctores
                    WHERE id = %s
                """
                
                cur.execute(query, (doctor_id,))
                result = cur.fetchone()
                
                if result:
                    return {
                        'nombre_completo': result[0],
                        'especialidad': result[1] or 'Medicina General'
                    }
                else:
                    return {
                        'nombre_completo': 'Doctor',
                        'especialidad': 'Medicina General'
                    }
                    
    except Exception as e:
        logger.error(f"Error obteniendo info doctor: {e}")
        return {
            'nombre_completo': 'Doctor',
            'especialidad': 'Medicina General'
        }


def obtener_fecha_hora_actual() -> tuple:
    """Obtiene fecha/hora en timezone Mexicali."""
    tz = pendulum.timezone('America/Tijuana')
    ahora = pendulum.now(tz)
    
    fecha = ahora.format('dddd D [de] MMMM, YYYY', locale='es')
    hora = ahora.format('h:mm A')
    dia = ahora.format('dddd', locale='es').capitalize()
    
    return fecha, hora, dia


def obtener_ultimo_mensaje(state: Dict[str, Any]) -> str:
    """Extrae último mensaje del usuario del state."""
    messages = state.get('messages', [])
    
    for msg in reversed(messages):
        if hasattr(msg, 'type') and msg.type == 'human':
            return msg.content
        elif isinstance(msg, dict) and msg.get('role') == 'user':
            return msg.get('content', '')
    
    return ""


# ==================== NODO PRINCIPAL ====================

def nodo_maya_detective_doctor(state: WhatsAppAgentState) -> Command:
    """
    Nodo 2B: Maya Detective de Intención para Doctores.
    
    Similar a Maya Paciente pero con capacidades para responder
    stats del día sin activar herramientas complejas.
    
    MEJORAS APLICADAS:
    ✅ Validación pre-vuelo de doctor_id
    ✅ Manejo robusto de errores
    ✅ Logging detallado
    """
    logger.info("\n" + "=" * 70)
    logger.info("👨‍⚕️ NODO 2B: MAYA - DETECTIVE DOCTOR")
    logger.info("=" * 70)
    
    # ✅ MEJORA 1: Validación pre-vuelo de doctor_id
    doctor_id = state.get('doctor_id')
    
    if doctor_id is None:
        logger.error("❌ ERROR CRÍTICO: doctor_id es None - No se puede continuar")
        logger.error("   Estado recibido: %s", {k: v for k, v in state.items() if k != 'messages'})
        return Command(
            update={
                'requiere_clasificacion_llm': True,
                'error_maya': 'doctor_id_missing'
            },
            goto="filtrado_inteligente"
        )
    
    # Validar que sea un ID válido (entero > 0)
    try:
        doctor_id = int(doctor_id)
        if doctor_id <= 0:
            raise ValueError("doctor_id debe ser > 0")
    except (ValueError, TypeError) as e:
        logger.error(f"❌ doctor_id inválido: {doctor_id} (tipo: {type(doctor_id).__name__}). Error: {e}")
        return Command(
            update={'requiere_clasificacion_llm': True},
            goto="filtrado_inteligente"
        )
    
    # Extraer mensaje
    mensaje_usuario = obtener_ultimo_mensaje(state)
    estado_conversacion = state.get('estado_conversacion', 'inicial')
    
    if not mensaje_usuario:
        logger.warning("⚠️  Sin mensaje del usuario")
        return Command(goto="generacion_resumen")
    
    logger.info(f"📝 Mensaje: {mensaje_usuario[:100]}...")
    logger.info(f"📊 Estado conversación: {estado_conversacion}")
    logger.info(f"👨‍⚕️ Doctor ID: {doctor_id}")
    
    # Obtener info del doctor
    info_doctor = obtener_info_doctor(doctor_id)
    
    # Obtener resumen del día
    resumen_dia = obtener_resumen_dia_doctor(doctor_id)
    
    # Obtener fecha/hora actual
    fecha_actual, hora_actual, dia_semana = obtener_fecha_hora_actual()
    
    # Construir prompt
    prompt_completo = PROMPT_MAYA_DOCTOR.format(
        fecha_actual=fecha_actual,
        hora_actual=hora_actual,
        dia_semana=dia_semana,
        nombre_doctor=info_doctor['nombre_completo'],
        especialidad=info_doctor['especialidad'],
        resumen_dia=resumen_dia,
        estado_conversacion=estado_conversacion
    )
    
    # Llamar LLM con structured output
    try:
        logger.info("🤖 Llamando a Maya Doctor (DeepSeek → Claude fallback)...")
        
        resultado: MayaResponseDoctor = structured_llm_doctor.invoke([
            SystemMessage(content=prompt_completo),
            HumanMessage(content=mensaje_usuario)
        ])
        
        logger.info(f"✅ Acción decidida: {resultado.accion}")
        logger.info(f"📋 Razón: {resultado.razon}")
        
        # Mapear acciones a nodos destino
        destinos = {
            "responder_directo": "generacion_resumen",
            "escalar_procedimental": "recuperacion_medica",
            "dejar_pasar": "seleccion_herramientas"
        }
        
        goto = destinos.get(resultado.accion, "generacion_resumen")
        
        # Preparar updates según acción
        updates = {}
        
        if resultado.accion == "responder_directo":
            logger.info(f"💬 Respuesta directa: {resultado.respuesta}")
            updates = {
                "messages": [AIMessage(content=resultado.respuesta)],
                "clasificacion_mensaje": "chat",
                "requiere_clasificacion_llm": False
            }
        
        elif resultado.accion == "escalar_procedimental":
            logger.info(f"⬆️  Escalando a recuperación médica")
            updates = {
                "clasificacion_mensaje": "medica",
                "requiere_clasificacion_llm": False
            }
        
        elif resultado.accion == "dejar_pasar":
            logger.info(f"➡️  Dejando pasar mensaje (flujo activo)")
            updates = {
                "requiere_clasificacion_llm": False
            }
        
        # Retornar Command con update y goto
        return Command(
            update=updates,
            goto=goto
        )
        
    except Exception as e:
        logger.error(f"❌ Error en Maya Detective Doctor: {e}")
        logger.exception("Stack trace completo:")
        return Command(
            update={
                "messages": [AIMessage(content="Disculpa, ¿puedes repetir eso de otra forma?")],
                "clasificacion_mensaje": "chat",
                "error_maya": str(e)
            },
            goto="generacion_resumen"
        )


# ==================== WRAPPER ====================

def nodo_maya_detective_doctor_wrapper(state: WhatsAppAgentState) -> Command:
    """Wrapper para LangGraph - retorna Command directamente."""
    return nodo_maya_detective_doctor(state)
