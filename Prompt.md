---

```
Crea un PR para implementar el Nodo 2B: Maya Detective de Intención para Doctores.

# Objetivo
Implementar asistente conversacional "Maya" para doctores que responde consultas básicas del día sin activar flujo completo. Reduce latencia de 8 seg a ~1 seg en 60% de mensajes de doctores.

# Contexto
Similar a Maya Paciente (PR #3) pero con diferencias clave:
- Maya Paciente: Info ESTÁTICA (horarios, ubicación)
- Maya Doctor: Info DINÁMICA (stats del día actual desde BD)

# Diferencias vs Maya Paciente

| Aspecto | Maya Paciente | Maya Doctor |
|---------|---------------|-------------|
| Datos | Estáticos (hardcoded) | Dinámicos (query SQL) |
| Responde | Horarios, ubicación | Stats día, próxima cita |
| Escala a | recepcionista | recuperacion_medica |
| Query | obtener_contexto_paciente() | obtener_resumen_dia_doctor() |
| Max tokens | 300 | 400 |

# Mejoras Técnicas Críticas (LangGraph Recommendations)

## 1. Validación Pre-vuelo de doctor_id
Verificar que doctor_id existe ANTES de llamar al LLM para evitar formateo fallido del prompt.

## 2. Bloqueo de Recálculo Estricto
Instrucción explícita en prompt para que Maya NO recalcule tiempos usando su "reloj interno".

## 3. Fixture de Tiempo para Tests
Permitir inyectar `ahora` en tests para que "quién sigue" no dependa de hora real del test.

## 4. Reseteo de Estado en Cache
El nodo cache_sesion debe resetear estado_conversacion='inicial' si sesión > 24h.

---

# Archivos a crear/modificar

## 1. src/nodes/maya_detective_doctor_node.py

```python
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
    """Respuesta estructurada de Maya para Doctores."""
    
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
    model="claude-3-5-haiku-20241022",
    temperature=0.7,
    max_tokens=400,
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    timeout=10.0,
    max_retries=0
)

llm_maya_doctor = llm_primary.with_fallbacks([llm_fallback])
structured_llm_doctor = llm_maya_doctor.with_structured_output(
    MayaResponseDoctor,
    method="json_schema",
    strict=True
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

══════════════════════���════════════════════════════════════════
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
                    
                    # Calcular tiempo restante
                    diferencia = hora - ahora
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
    """Obtiene información básica del doctor."""
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
        logger.error(f"❌ doctor_id inválido: {doctor_id} ({type(doctor_id)})")
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
```

## 2. Modificar src/nodes/cache_sesion_node.py

```python
# ✅ MEJORA 4: Resetear estado_conversacion si sesión expirada

def nodo_cache_sesion(state: WhatsAppAgentState, checkpointer=None) -> WhatsAppAgentState:
    """
    Nodo N1: Cache de Sesión con reseteo de estado.
    """
    logger.info("🗄️  [N1] CACHE_SESION - Verificando caché de sesión")
    
    user_id = state.get('user_id', '')
    
    # ... código existente de buscar sesión ...
    
    if sesion_activa and sesion_activa['hours_inactive'] < SESSION_TTL_HOURS:
        thread_id = sesion_activa['thread_id']
        logger.info(f"    ✅ SESIÓN ACTIVA - Thread: {thread_id}")
        
        # Recuperar mensajes y estado del checkpointer
        if checkpointer:
            mensajes_previos, estado_conversacion = recuperar_mensajes_checkpointer(thread_id, checkpointer)
            
            if mensajes_previos:
                state['messages'] = mensajes_previos + state.get('messages', [])
                logger.info(f"    📝 Contexto restaurado: {len(mensajes_previos)} mensajes")
            
            # Preservar estado conversacional si existe
            if estado_conversacion != 'inicial':
                state['estado_conversacion'] = estado_conversacion
                logger.info(f"    🔄 Estado conversacional restaurado: {estado_conversacion}")
        
        state['session_id'] = thread_id
        state['sesion_expirada'] = False
        actualizar_actividad_sesion(thread_id, user_id)
    
    else:
        # Sesión nueva o expirada
        logger.info(f"    🆕 SESIÓN NUEVA/EXPIRADA")
        thread_id = crear_nueva_sesion(user_id, user_id)
        
        state['session_id'] = thread_id
        state['sesion_expirada'] = True
        
        # ✅ MEJORA 4: Resetear estado_conversacion si sesión expiró
        state['estado_conversacion'] = 'inicial'
        logger.info(f"    🔄 Estado conversacional reseteado a 'inicial' (sesión expirada)")
        
        logger.info(f"    ✓ Nueva sesión: {thread_id}")
    
    state['timestamp'] = datetime.now().isoformat()
    
    logger.info(f"    ✅ Cache de sesión completado")
    return state
```

## 3. Modificar src/graph_whatsapp.py

```python
# Import
from src.nodes.maya_detective_doctor_node import nodo_maya_detective_doctor_wrapper

# Agregar nodo después de maya_detective_paciente
workflow.add_node("maya_detective_doctor", nodo_maya_detective_doctor_wrapper)

# Actualizar decidir_desde_router():
def decidir_desde_router(state: WhatsAppAgentState) -> Literal[...]:
    """
    Decide ruta según tipo de usuario.
    
    Prioridad:
    1. Pacientes externos → Maya Paciente
    2. Doctores → Maya Doctor
    3. Resto → Clasificador LLM
    """
    tipo_usuario = state.get('tipo_usuario', '')
    ruta = state.get('ruta_siguiente', '')
    
    logger.info(f"🔀 Router - tipo_usuario: {tipo_usuario}, ruta: {ruta}")
    
    # Pacientes externos → Maya Paciente
    if tipo_usuario == 'paciente_externo':
        logger.info("   → Paciente externo: Maya Detective Paciente")
        return 'maya_detective_paciente'
    
    # ✅ NUEVO: Doctores → Maya Doctor (excepto si ya viene de clasificador)
    if tipo_usuario == 'doctor' and ruta != 'clasificador_llm':
        logger.info("   → Doctor: Maya Detective Doctor")
        return 'maya_detective_doctor'
    
    # Recepcionista directo
    if tipo_usuario == 'recepcionista':
        logger.info("   → Recepcionista: Flujo directo")
        return 'recepcionista'
    
    # Admin o tipo desconocido → clasificador
    logger.info("   → Clasificador LLM")
    return 'filtrado_inteligente'

# Actualizar conditional_edges para incluir maya_detective_doctor
workflow.add_conditional_edges(
    "router_identidad",
    decidir_desde_router,
    {
        "recepcionista": "recepcionista",
        "maya_detective_paciente": "maya_detective_paciente",
        "maya_detective_doctor": "maya_detective_doctor",  # ✅ NUEVO
        "filtrado_inteligente": "filtrado_inteligente"
    }
)
```

## 4. Tests completos (tests/test_maya_detective_doctor.py)

Crear 18 tests mínimo usando CSV fixtures (PR #6):

```python
"""
Tests para Nodo 2B: Maya Detective de Intención - Doctores

✅ Usa CSV fixtures para tests rápidos
✅ Mock de tiempo inyectable
✅ Validación de doctor_id
"""

import pytest
import pendulum
from unittest.mock import patch, Mock
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.types import Command

from src.nodes.maya_detective_doctor_node import (
    nodo_maya_detective_doctor,
    obtener_resumen_dia_doctor,
    obtener_info_doctor,
    MayaResponseDoctor
)

# ==================== FIXTURES ====================

@pytest.fixture
def estado_base_doctor():
    """Estado base para tests de doctor."""
    return {
        'doctor_id': 1,
        'tipo_usuario': 'doctor',
        'messages': [HumanMessage(content="Hola")],
        'estado_conversacion': 'inicial'
    }

@pytest.fixture
def mock_tiempo_fijo():
    """Fixture de tiempo para tests consistentes."""
    tz = pendulum.timezone('America/Tijuana')
    # Fijar a 1:30 PM del 31 de enero 2026
    return pendulum.datetime(2026, 1, 31, 13, 30, tz=tz)


# ==================== TESTS RESPONDER DIRECTO ====================

@patch('src.nodes.maya_detective_doctor_node.structured_llm_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_resumen_dia_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_info_doctor')
def test_maya_responde_saludo(mock_info, mock_resumen, mock_llm, estado_base_doctor):
    """Maya responde saludo con stats del día."""
    mock_info.return_value = {'nombre_completo': 'Dr. Santiago', 'especialidad': 'Podología'}
    mock_resumen.return_value = "📊 TUS ESTADÍSTICAS HOY:\n• Citas: 8\n• Pendientes: 5"
    mock_llm.invoke.return_value = MayaResponseDoctor(
        accion="responder_directo",
        respuesta="Hola Dr. Santiago! Tienes 5 citas pendientes hoy 😊",
        razon="Saludo"
    )
    
    resultado = nodo_maya_detective_doctor(estado_base_doctor)
    
    assert isinstance(resultado, Command)
    assert resultado.goto == "generacion_resumen"
    assert 'messages' in resultado.update

# ... (más tests según PR #3 como referencia)

# ==================== TESTS DE VALIDACIÓN ====================

def test_maya_sin_doctor_id():
    """✅ MEJORA 1: Valida que doctor_id es requerido."""
    estado = {
        'messages': [HumanMessage(content="Hola")],
        'tipo_usuario': 'doctor'
        # doctor_id ausente
    }
    
    resultado = nodo_maya_detective_doctor(estado)
    
    assert resultado.goto == "filtrado_inteligente"
    assert resultado.update.get('requiere_clasificacion_llm') == True

def test_maya_doctor_id_invalido():
    """✅ MEJORA 1: Maneja doctor_id inválido."""
    estado = {
        'doctor_id': 'abc',  # String no convertible
        'messages': [HumanMessage(content="Hola")]
    }
    
    resultado = nodo_maya_detective_doctor(estado)
    
    assert resultado.goto == "filtrado_inteligente"

def test_maya_doctor_id_negativo():
    """✅ MEJORA 1: Rechaza doctor_id <= 0."""
    estado = {
        'doctor_id': -5,
        'messages': [HumanMessage(content="Hola")]
    }
    
    resultado = nodo_maya_detective_doctor(estado)
    
    assert resultado.goto == "filtrado_inteligente"


# ==================== TESTS DE TIEMPO INYECTABLE ====================

@patch('src.nodes.maya_detective_doctor_node.psycopg.connect')
def test_resumen_con_tiempo_inyectado(mock_connect, mock_tiempo_fijo):
    """✅ MEJORA 3: Tiempo inyectable para tests consistentes."""
    # Mock de BD
    mock_cursor = Mock()
    mock_cursor.fetchone.side_effect = [
        (8, 3, 5, 0),  # Stats
        ('María García', mock_tiempo_fijo.add(hours=1), 'Consulta'),  # Próxima (2:30pm)
        []  # Lista vacía
    ]
    mock_cursor.fetchall.return_value = []
    mock_connect.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
    
    # Llamar con tiempo fijo
    resumen = obtener_resumen_dia_doctor(1, ahora=mock_tiempo_fijo)
    
    # Verificar que el tiempo es "en 60 min" (no variable según hora real)
    assert "en 60 min" in resumen or "en 1h 0min" in resumen
```

# Optimizaciones clave aplicadas

1. ✅ **Validación pre-vuelo doctor_id** - Evita formateo fallido del prompt
2. ✅ **Bloqueo de recálculo estricto** - Instrucción explícita "NO RECALCULES"
3. ✅ **Tiempo inyectable** - Tests consistentes sin depender de hora real
4. ✅ **Reseteo de estado en cache** - Sesiones expiradas limpian estado_conversacion
5. ✅ **Command pattern** - Update + goto en un paso
6. ✅ **Pydantic strict=True** - Schema validation
7. ✅ **DeepSeek + Claude fallback** - Robustez

# Criterios de aceptación

- [x] Pydantic structured output funcionando
- [x] Command pattern implementado
- [x] Validación pre-vuelo de doctor_id
- [x] Maya responde stats del día correctamente
- [x] Maya NO recalcula tiempos (usa valores del resumen)
- [x] Maya ESCALA cuando preguntan por otra fecha
- [x] Cache resetea estado_conversacion en sesiones expiradas
- [x] 18+ tests pasando (incluyendo validaciones y tiempo inyectable)
- [x] Integrado al grafo correctamente
- [x] Logs detallados con stack traces en errores

# Referencias

- PR #3 (Maya Paciente) - Estructura base
- PR #2 (Cache Sesión) - Modificación estado_conversacion
- PR #6 (CSV Fixtures) - Tests rápidos
- LangGraph docs: Command routing, Unit testing

Repositorio: cognitaia2025-hub/Modulo_WhatsApp
```

---
