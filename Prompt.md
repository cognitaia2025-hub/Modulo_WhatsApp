
---

```
Crea un PR para implementar el Nodo 2B: Maya Detective de Intención para Doctores.

# Objetivo
Implementar asistente conversacional "Maya" para doctores que responde consultas básicas del día sin activar flujo completo. Similar a Maya Paciente (PR #3) pero con capacidades para responder estadísticas dinámicas del día actual.

# Diferencias clave vs Maya Paciente
- Información DINÁMICA: Query SQL que trae stats del día, próxima cita, lista de pacientes
- Responde: Stats del día, siguiente paciente, cuántos atendidos
- Escala a: "recuperacion_medica" (no "recepcionista")
- Restricción crítica: SOLO responde sobre HOY, otras fechas → ESCALA

# Archivos a crear

## 1. src/nodes/maya_detective_doctor_node.py

```python
"""
Nodo 2B: Maya - Detective de Intención para Doctores (OPTIMIZADO)

Asistente conversacional que maneja consultas básicas de doctores sin activar
flujo completo. Tiene acceso a estadísticas del día y puede responder preguntas
rápidas sin llamar a herramientas complejas.

TODO - OPTIMIZACIONES FUTURAS:
- [ ] Implementar connection pool para PostgreSQL (psycopg_pool)
- [ ] Mover queries a async con asyncpg para alta concurrencia
- [ ] Cachear resumen_dia por 5 minutos (Redis) para reducir queries

Actualmente usa psycopg síncrono directo. 
Esto es OK para <100 mensajes/min, pero necesitará pool para producción alta.
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

════════════════════════════════════════════════���══════════════
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
📊 USO DEL RESUMEN DEL DÍA
═══════════════════════════════════════════════════════════════

Usa los números tal cual, NO los recalcules:
• ESTADÍSTICAS: Usa completadas, pendientes, total directamente
• PRÓXIMA CITA: Usa el tiempo ya calculado ("en X min")
• PACIENTES DEL DÍA: Solo menciona si están en la lista visible

═══════════════════════════════════════════════════════════════
REGLAS DE CONVERSACIÓN
═══════════════════════════════════════════════════════════════

1. Personaliza con el nombre del doctor
2. Usa datos del RESUMEN DEL DÍA sin recalcular
3. Si no tienes la info en el resumen → ESCALA
4. Respuestas CORTAS: 3-4 líneas máx
5. Un emoji por mensaje (opcional)

═══════════════════════════════════════════════════════════════
MANEJO DE FLUJOS ACTIVOS
═══════════════════════════════════════════════════════════════

Estado: {estado_conversacion}

SI: ejecutando_herramienta, esperando_confirmacion, procesando
→ accion: "dejar_pasar"

SI: herramienta_completada, completado
→ accion: "responder_directo" (confirmar/despedir)

═══════════════════════════════════════════════════════════════
EJEMPLOS
═══════════════════════════════════════════════════════════════

Usuario: "Hola"
Maya: "Hola Dr. Santiago! Tienes 5 citas pendientes hoy 😊"

Usuario: "¿Cuántas tengo hoy?"
Maya: "Tienes 8 citas. Has completado 3 y te quedan 5"

Usuario: "¿Quién sigue?"
Maya: "María García a las 2:30pm (en 45 min)"

Usuario: "¿Cuántas tengo mañana?"
Maya: ESCALAR (fecha futura)

Usuario: "Busca a Juan Pérez"
Maya: ESCALAR (búsqueda específica)

Usuario: "¿Qué diagnóstico tiene María?"
Maya: ESCALAR (historial médico)

Usuario: "Cancela mi cita de las 5pm"
Maya: ESCALAR (modificar agenda)
"""


# ==================== FUNCIONES AUXILIARES ====================

def obtener_resumen_dia_doctor(doctor_id: int) -> str:
    """
    Obtiene resumen rápido del día del doctor.
    
    Query optimizada (~50ms) que trae:
    - Stats del día (total, completadas, pendientes, canceladas)
    - Próxima cita (paciente, hora, motivo)
    - Lista de pacientes del día con estado
    
    Args:
        doctor_id: ID del doctor
        
    Returns:
        String formateado con resumen del día
    """
    try:
        DATABASE_URL = os.getenv("DATABASE_URL")
        tz = pendulum.timezone('America/Tijuana')
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
    
    Flujo:
    1. Obtener info del doctor (nombre, especialidad)
    2. Obtener resumen del día (stats, próxima cita, lista pacientes)
    3. Obtener fecha/hora actual
    4. Construir prompt con toda la información
    5. Llamar LLM con structured output
    6. Retornar Command con update + goto
    
    Args:
        state: WhatsAppAgentState con doctor_id, messages, estado_conversacion
        
    Returns:
        Command con updates del state y siguiente nodo (goto)
    """
    logger.info("\n" + "=" * 70)
    logger.info("👨‍⚕️ NODO 2B: MAYA - DETECTIVE DOCTOR")
    logger.info("=" * 70)
    
    # Extraer datos del state
    doctor_id = state.get('doctor_id')
    mensaje_usuario = obtener_ultimo_mensaje(state)
    estado_conversacion = state.get('estado_conversacion', 'inicial')
    
    if not doctor_id:
        logger.warning("⚠️  No hay doctor_id - escalando a clasificador")
        return Command(
            update={'requiere_clasificacion_llm': True},
            goto="filtrado_inteligente"
        )
    
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
        # Fallback: responder con error genérico
        return Command(
            update={
                "messages": [AIMessage(content="Disculpa, ¿puedes repetir eso de otra forma?")],
                "clasificacion_mensaje": "chat"
            },
            goto="generacion_resumen"
        )


# ==================== WRAPPER ====================

def nodo_maya_detective_doctor_wrapper(state: WhatsAppAgentState) -> Command:
    """Wrapper para LangGraph - retorna Command directamente."""
    return nodo_maya_detective_doctor(state)
```

## 2. Modificar src/graph_whatsapp.py

- Importar nodo_maya_detective_doctor_wrapper
- Agregar nodo "maya_detective_doctor" después de router_identidad
- Modificar decidir_desde_router() para enviar doctores a Maya primero (similar a pacientes)
- Actualizar conditional_edges para incluir ruta "maya_detective_doctor"

Cambios específicos:

```python
# Import (después de maya_detective_paciente)
from src.nodes.maya_detective_doctor_node import nodo_maya_detective_doctor_wrapper

# Agregar nodo (después de maya_detective_paciente)
workflow.add_node("maya_detective_doctor", nodo_maya_detective_doctor_wrapper)

# Actualizar decidir_desde_router():
def decidir_desde_router(state: WhatsAppAgentState) -> Literal[...]:
    # ...código existente...
    
    # NUEVO: Doctores externos van primero a Maya
    if tipo_usuario == 'doctor' and ruta != 'recuperacion_medica':
        logger.info(f"   → Doctor: Maya Detective")
        return 'maya_detective_doctor'
    
    # ...resto del código...

# Actualizar conditional_edges:
workflow.add_conditional_edges(
    "router_identidad",
    decidir_desde_router,
    {
        "recepcionista": "recepcionista",
        "maya_detective_paciente": "maya_detective_paciente",
        "maya_detective_doctor": "maya_detective_doctor",  # NUEVO
        "filtrado_inteligente": "filtrado_inteligente",
        # ...resto...
    }
)
```

## 3. tests/test_maya_detective_doctor.py

Crear 18 tests similares a Maya Paciente:

```python
"""
Tests para Nodo 2B: Maya Detective de Intención - Doctores
"""

import pytest
from unittest.mock import Mock, patch
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
def mock_llm_response():
    """Mock de respuesta del LLM."""
    def _mock(accion, respuesta="", razon="test"):
        return MayaResponseDoctor(
            accion=accion,
            respuesta=respuesta,
            razon=razon
        )
    return _mock


# ==================== TESTS DE RESPONDER DIRECTO ====================

@patch('src.nodes.maya_detective_doctor_node.structured_llm_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_resumen_dia_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_info_doctor')
def test_maya_responde_saludo(mock_info, mock_resumen, mock_llm, estado_base_doctor, mock_llm_response):
    """Maya responde saludo con stats del día."""
    mock_info.return_value = {'nombre_completo': 'Dr. Santiago', 'especialidad': 'Podología'}
    mock_resumen.return_value = "📊 TUS ESTADÍSTICAS HOY:\n• Citas: 8\n• Pendientes: 5"
    mock_llm.invoke.return_value = mock_llm_response(
        accion="responder_directo",
        respuesta="Hola Dr. Santiago! Tienes 5 citas pendientes hoy 😊",
        razon="Saludo con stats"
    )
    
    resultado = nodo_maya_detective_doctor(estado_base_doctor)
    
    assert isinstance(resultado, Command)
    assert resultado.goto == "generacion_resumen"
    assert 'messages' in resultado.update


@patch('src.nodes.maya_detective_doctor_node.structured_llm_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_resumen_dia_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_info_doctor')
def test_maya_responde_cuantas_citas(mock_info, mock_resumen, mock_llm, estado_base_doctor, mock_llm_response):
    """Maya responde cuántas citas tiene el doctor."""
    estado_base_doctor['messages'] = [HumanMessage(content="¿Cuántas citas tengo?")]
    mock_info.return_value = {'nombre_completo': 'Dr. Santiago', 'especialidad': 'Podología'}
    mock_resumen.return_value = "📊 TUS ESTADÍSTICAS HOY:\n• Citas: 8\n• Completadas: 3\n• Pendientes: 5"
    mock_llm.invoke.return_value = mock_llm_response(
        accion="responder_directo",
        respuesta="Tienes 8 citas hoy. Has completado 3 y te quedan 5",
        razon="Stats del día"
    )
    
    resultado = nodo_maya_detective_doctor(estado_base_doctor)
    
    assert resultado.goto == "generacion_resumen"
    assert "8 citas" in resultado.update['messages'][0].content


@patch('src.nodes.maya_detective_doctor_node.structured_llm_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_resumen_dia_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_info_doctor')
def test_maya_responde_quien_sigue(mock_info, mock_resumen, mock_llm, estado_base_doctor, mock_llm_response):
    """Maya responde quién es el siguiente paciente."""
    estado_base_doctor['messages'] = [HumanMessage(content="¿Quién sigue?")]
    mock_info.return_value = {'nombre_completo': 'Dr. Santiago', 'especialidad': 'Podología'}
    mock_resumen.return_value = """📊 TUS ESTADÍSTICAS HOY:
• Citas: 8

🕐 PRÓXIMA CITA:
• Paciente: María García
• Hora: 2:30 PM (en 45 min)"""
    mock_llm.invoke.return_value = mock_llm_response(
        accion="responder_directo",
        respuesta="María García a las 2:30pm (en 45 min)",
        razon="Próxima cita disponible"
    )
    
    resultado = nodo_maya_detective_doctor(estado_base_doctor)
    
    assert resultado.goto == "generacion_resumen"
    assert "María García" in resultado.update['messages'][0].content


# ==================== TESTS DE ESCALAR ====================

@patch('src.nodes.maya_detective_doctor_node.structured_llm_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_resumen_dia_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_info_doctor')
def test_maya_escala_buscar_paciente(mock_info, mock_resumen, mock_llm, estado_base_doctor, mock_llm_response):
    """Maya escala cuando buscan paciente específico."""
    estado_base_doctor['messages'] = [HumanMessage(content="Busca a Juan Pérez")]
    mock_info.return_value = {'nombre_completo': 'Dr. Santiago', 'especialidad': 'Podología'}
    mock_resumen.return_value = "📊 TUS ESTADÍSTICAS HOY:\n• Citas: 8"
    mock_llm.invoke.return_value = mock_llm_response(
        accion="escalar_procedimental",
        razon="Búsqueda específica de paciente"
    )
    
    resultado = nodo_maya_detective_doctor(estado_base_doctor)
    
    assert resultado.goto == "recuperacion_medica"


@patch('src.nodes.maya_detective_doctor_node.structured_llm_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_resumen_dia_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_info_doctor')
def test_maya_escala_historial(mock_info, mock_resumen, mock_llm, estado_base_doctor, mock_llm_response):
    """Maya escala cuando piden historial médico."""
    estado_base_doctor['messages'] = [HumanMessage(content="¿Qué diagnóstico tiene María?")]
    mock_info.return_value = {'nombre_completo': 'Dr. Santiago', 'especialidad': 'Podología'}
    mock_resumen.return_value = "📊 TUS ESTADÍSTICAS HOY:\n• Citas: 8"
    mock_llm.invoke.return_value = mock_llm_response(
        accion="escalar_procedimental",
        razon="Consulta de historial médico"
    )
    
    resultado = nodo_maya_detective_doctor(estado_base_doctor)
    
    assert resultado.goto == "recuperacion_medica"


@patch('src.nodes.maya_detective_doctor_node.structured_llm_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_resumen_dia_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_info_doctor')
def test_maya_escala_fecha_futura(mock_info, mock_resumen, mock_llm, estado_base_doctor, mock_llm_response):
    """Maya escala cuando preguntan por fecha futura (CRÍTICO)."""
    estado_base_doctor['messages'] = [HumanMessage(content="¿Cuántas citas tengo mañana?")]
    mock_info.return_value = {'nombre_completo': 'Dr. Santiago', 'especialidad': 'Podología'}
    mock_resumen.return_value = "📊 TUS ESTADÍSTICAS HOY:\n• Citas: 8"
    mock_llm.invoke.return_value = mock_llm_response(
        accion="escalar_procedimental",
        razon="Pregunta por fecha futura - requiere herramientas"
    )
    
    resultado = nodo_maya_detective_doctor(estado_base_doctor)
    
    assert resultado.goto == "recuperacion_medica"
    assert resultado.update['clasificacion_mensaje'] == "medica"


@patch('src.nodes.maya_detective_doctor_node.structured_llm_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_resumen_dia_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_info_doctor')
def test_maya_escala_cancelar_cita(mock_info, mock_resumen, mock_llm, estado_base_doctor, mock_llm_response):
    """Maya escala cuando quieren cancelar cita."""
    estado_base_doctor['messages'] = [HumanMessage(content="Cancela mi cita de las 5pm")]
    mock_info.return_value = {'nombre_completo': 'Dr. Santiago', 'especialidad': 'Podología'}
    mock_resumen.return_value = "📊 TUS ESTADÍSTICAS HOY:\n• Citas: 8"
    mock_llm.invoke.return_value = mock_llm_response(
        accion="escalar_procedimental",
        razon="Modificar agenda requiere herramientas"
    )
    
    resultado = nodo_maya_detective_doctor(estado_base_doctor)
    
    assert resultado.goto == "recuperacion_medica"


# ==================== TESTS DE DEJAR PASAR ====================

@patch('src.nodes.maya_detective_doctor_node.structured_llm_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_resumen_dia_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_info_doctor')
def test_maya_deja_pasar_flujo_activo(mock_info, mock_resumen, mock_llm, estado_base_doctor, mock_llm_response):
    """Maya deja pasar cuando hay flujo activo."""
    estado_base_doctor['messages'] = [HumanMessage(content="Opción A")]
    estado_base_doctor['estado_conversacion'] = 'ejecutando_herramienta'
    mock_info.return_value = {'nombre_completo': 'Dr. Santiago', 'especialidad': 'Podología'}
    mock_resumen.return_value = "📊 TUS ESTADÍSTICAS HOY:\n• Citas: 8"
    mock_llm.invoke.return_value = mock_llm_response(
        accion="dejar_pasar",
        razon="Flujo activo - no interferir"
    )
    
    resultado = nodo_maya_detective_doctor(estado_base_doctor)
    
    assert resultado.goto == "seleccion_herramientas"


# ==================== TESTS DE MANEJO DE ERRORES ====================

def test_maya_sin_doctor_id():
    """Maya maneja gracefully si no hay doctor_id."""
    estado = {
        'messages': [HumanMessage(content="Hola")],
        'tipo_usuario': 'doctor'
    }
    
    resultado = nodo_maya_detective_doctor(estado)
    
    assert resultado.goto == "filtrado_inteligente"


@patch('src.nodes.maya_detective_doctor_node.structured_llm_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_resumen_dia_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_info_doctor')
def test_maya_maneja_error_llm(mock_info, mock_resumen, mock_llm, estado_base_doctor):
    """Maya maneja error si LLM falla."""
    mock_info.return_value = {'nombre_completo': 'Dr. Santiago', 'especialidad': 'Podología'}
    mock_resumen.return_value = "📊 TUS ESTADÍSTICAS HOY:\n• Citas: 8"
    mock_llm.invoke.side_effect = Exception("LLM timeout")
    
    resultado = nodo_maya_detective_doctor(estado_base_doctor)
    
    assert resultado.goto == "generacion_resumen"
    assert "repetir" in resultado.update['messages'][0].content.lower()


# ==================== TESTS DE FUNCIONES AUXILIARES ====================

@patch('src.nodes.maya_detective_doctor_node.psycopg.connect')
def test_obtener_resumen_dia_sin_citas(mock_connect):
    """Maneja correctamente día sin citas."""
    mock_cursor = Mock()
    mock_cursor.fetchone.return_value = (0, 0, 0, 0)
    mock_connect.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
    
    resumen = obtener_resumen_dia_doctor(1)
    
    assert "No tienes citas" in resumen


@patch('src.nodes.maya_detective_doctor_node.psycopg.connect')
def test_obtener_info_doctor(mock_connect):
    """Obtiene info del doctor correctamente."""
    mock_cursor = Mock()
    mock_cursor.fetchone.return_value = ('Dr. Juan Pérez', 'Podología')
    mock_connect.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
    
    info = obtener_info_doctor(1)
    
    assert info['nombre_completo'] == 'Dr. Juan Pérez'
    assert info['especialidad'] == 'Podología'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

# Optimizaciones clave aplicadas

1. **Restricción de fechas CRÍTICA**: Prompt explícito que Maya SOLO responde sobre HOY
2. **No recalcular tiempos**: Maya usa tiempos ya calculados en resumen_dia
3. **Regla de oro**: Si no está en el resumen → ESCALA
4. **Command pattern**: Update + goto en un solo paso
5. **Pydantic strict=True**: Garantiza formato válido
6. **DeepSeek + Claude fallback**: Robustez
7. **TODO comentado**: Pool de conexiones para optimización futura

# Impacto esperado

Doctores:
- 60% mensajes → Maya responde directo (<1 seg)
- 40% mensajes → Flujo completo (herramientas médicas)
- Latencia: 8 seg → 3 seg promedio
- Costo: -60% en llamadas LLM

# Criterios de aceptación

- Pydantic structured output funcionando
- Command pattern implementado
- 18 tests pasando
- Maya responde stats del día correctamente
- Maya ESCALA cuando preguntan por otra fecha (CRÍTICO)
- Maya ESCALA cuando buscan paciente específico
- Integrado al grafo correctamente
- Logs detallados

Repositorio: cognitaia2025-hub/Modulo_WhatsApp
```

---
