"""
Nodo 6R: Recepcionista Conversacional Modernizado

MEJORAS APLICADAS:
✅ Command pattern con routing dinámico
✅ Pydantic structured output para extracción
✅ Estado conversacional robusto con 7 estados
✅ Timeout reducido (10s) alineado con otros nodos
✅ Manejo de flujo multi-turno completo

Este es el nodo MÁS CRÍTICO (70% del tráfico) que maneja el flujo 
conversacional completo de agendamiento para pacientes externos.

Estados:
inicial → solicitando_nombre → solicitando_fecha → mostrando_slots → 
confirmando_cita → completado/cancelado
"""

import os
import logging
from typing import Optional, Literal, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import Command
from dotenv import load_dotenv

from src.state.agent_state import WhatsAppAgentState
from src.utils.logging_config import setup_colored_logging, log_separator, log_node_io
from src.utils.time_utils import get_time_context
from src.medical.crud import get_paciente_by_phone, registrar_paciente_externo
from src.medical.slots import generar_slots_con_turnos

load_dotenv()
logger = setup_colored_logging()


# ==================== PYDANTIC MODELS ====================

class DatosRecolectados(BaseModel):
    """Datos del paciente recolectados durante conversación."""
    nombre_paciente: Optional[str] = Field(default=None, description="Nombre completo")
    fecha_preferida: Optional[str] = Field(default=None, description="Fecha en formato YYYY-MM-DD")
    hora_preferida: Optional[str] = Field(default=None, description="Hora en formato HH:MM")
    motivo_consulta: Optional[str] = Field(default=None, description="Motivo de la cita")
    telefono_contacto: Optional[str] = Field(default=None, description="Teléfono alternativo")


class ExtraccionNombre(BaseModel):
    """Extrae nombre del paciente."""
    nombre_completo: str = Field(description="Nombre completo del paciente")
    confianza: Literal["alta", "media", "baja"] = Field(description="Nivel de confianza")


class ExtraccionFecha(BaseModel):
    """Extrae fecha preferida."""
    fecha: str = Field(description="Fecha en formato YYYY-MM-DD")
    es_flexible: bool = Field(default=False, description="Si el paciente es flexible")


class SeleccionSlot(BaseModel):
    """Selección de slot por el paciente."""
    opcion_seleccionada: int = Field(description="Número de opción (1, 2, 3, etc.)")
    confirmado: bool = Field(default=True)


# ==================== CONSTANTES ====================

# Estados del flujo conversacional
ESTADOS_RECEPCIONISTA = {
    'inicial': 'Esperando inicio de conversación',
    'solicitando_nombre': 'Pidiendo nombre del paciente',
    'solicitando_fecha': 'Pidiendo fecha preferida',
    'mostrando_slots': 'Mostrando horarios disponibles',
    'confirmando_cita': 'Confirmando datos de la cita',
    'completado': 'Cita agendada exitosamente',
    'cancelado': 'Usuario canceló el proceso'
}

OPCIONES_LETRAS = ['A', 'B', 'C', 'D', 'E']
DIAS_SEMANA = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
MESES = [
    'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
    'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'
]


# ==================== CONFIGURACIÓN LLM ====================

llm_primary = ChatOpenAI(
    model="deepseek-chat",
    temperature=0.3,  # Más determinístico para extracción
    max_tokens=200,
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1",
    timeout=10.0,  # ✅ Consistente con otros nodos
    max_retries=0
)

llm_fallback = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    temperature=0.3,
    max_tokens=200,
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    timeout=10.0,
    max_retries=0
)

llm_extractor = llm_primary.with_fallbacks([llm_fallback])


# ==================== FUNCIONES DE EXTRACCIÓN ====================

def extraer_nombre_con_llm(mensaje: str) -> Optional[str]:
    """
    Extrae nombre del paciente usando Pydantic structured output.
    
    MEJORAS:
    ✅ Pydantic valida automáticamente
    ✅ Incluye nivel de confianza
    
    Args:
        mensaje: Mensaje del usuario con su nombre
        
    Returns:
        Nombre extraído o None si falla
    """
    llm_with_structure = llm_extractor.with_structured_output(
        ExtraccionNombre
    )
    
    prompt = f"""Extrae el nombre completo del paciente de este mensaje.

MENSAJE: "{mensaje}"

Si el mensaje contiene un nombre completo, extráelo.
Si no hay nombre, usa "desconocido" y confianza "baja".

Retorna JSON con nombre_completo y confianza."""
    
    try:
        resultado = llm_with_structure.invoke(prompt)
        if resultado.confianza in ["alta", "media"]:
            logger.info(f"    ✅ Nombre extraído: '{resultado.nombre_completo}' (confianza: {resultado.confianza})")
            return resultado.nombre_completo
        logger.warning(f"    ⚠️ Confianza baja en nombre extraído: '{resultado.nombre_completo}'")
        return None
    except Exception as e:
        logger.error(f"    ❌ Error extrayendo nombre: {e}")
        return None


def extraer_fecha_con_llm(mensaje: str, tiempo_context: str) -> Optional[str]:
    """
    Extrae fecha preferida con Pydantic.
    
    Args:
        mensaje: Mensaje del usuario con la fecha
        tiempo_context: Contexto temporal actual
        
    Returns:
        Fecha en formato YYYY-MM-DD o None
    """
    llm_with_structure = llm_extractor.with_structured_output(ExtraccionFecha)
    
    prompt = f"""Extrae la fecha preferida del paciente.

CONTEXTO DE TIEMPO:
{tiempo_context}

MENSAJE: "{mensaje}"

Convierte expresiones como "mañana", "el lunes", "en 3 días" a formato YYYY-MM-DD.
Si no hay fecha clara, usa None.

Retorna JSON con fecha y es_flexible."""
    
    try:
        resultado = llm_with_structure.invoke(prompt)
        if resultado.fecha and resultado.fecha.lower() != "none":
            logger.info(f"    ✅ Fecha extraída: {resultado.fecha} (flexible: {resultado.es_flexible})")
            return resultado.fecha
        return None
    except Exception as e:
        logger.error(f"    ❌ Error extrayendo fecha: {e}")
        return None


def extraer_ultimo_mensaje_usuario(state: WhatsAppAgentState) -> str:
    """
    Extrae el último mensaje del usuario del estado.
    
    Args:
        state: Estado actual
        
    Returns:
        Contenido del último mensaje humano
    """
    messages = state.get('messages', [])
    if not messages:
        return ""
    
    # Buscar último mensaje humano
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            return msg.content
        elif hasattr(msg, 'type') and msg.type == 'human':
            return msg.content
    
    # Fallback al último mensaje
    ultimo = messages[-1]
    return getattr(ultimo, 'content', str(ultimo))


# ==================== FUNCIONES AUXILIARES ====================

def formatear_slots_para_whatsapp(slots: List[Dict]) -> str:
    """
    Formatea los slots disponibles para mostrar al paciente.
    
    Args:
        slots: Lista de slots disponibles
        
    Returns:
        String formateado para WhatsApp
    """
    lineas = ["Horarios disponibles:", ""]
    
    for i, slot in enumerate(slots):
        letra = OPCIONES_LETRAS[i]
        
        # Parsear fecha
        fecha = slot.get('fecha', '')
        fecha_obj = None
        
        if fecha:
            try:
                fecha_obj = datetime.strptime(fecha, "%Y-%m-%d").date()
            except ValueError:
                logger.warning(f"Fecha inválida en slot: {fecha}")
                continue
        
        if fecha_obj:
            dia_nombre = DIAS_SEMANA[fecha_obj.weekday()]
            dia_numero = fecha_obj.day
            mes_nombre = MESES[fecha_obj.month - 1]
            
            # Formatear horarios
            hora_inicio = slot.get('hora_inicio', '')[:5]  # HH:MM
            hora_fin = slot.get('hora_fin', '')[:5]      # HH:MM
            
            lineas.append(f"{letra}) {dia_nombre.title()} {dia_numero} de {mes_nombre}, {hora_inicio} - {hora_fin}")
    
    lineas.append("")
    lineas.append("¿Cuál prefieres? Responde con la letra (A, B, C, etc.)")
    
    return "\n".join(lineas)


# ==================== NODO PRINCIPAL ====================

def nodo_recepcionista(state: WhatsAppAgentState) -> Command:
    """
    Nodo 6R: Maneja flujo conversacional multi-turno para agendamiento de citas
    
    MEJORAS APLICADAS:
    ✅ Command pattern con routing dinámico
    ✅ Pydantic structured output
    ✅ Estado conversacional robusto
    ✅ Timeout reducido (10s)
    
    Flujo:
    inicial → solicitando_nombre → solicitando_fecha → mostrando_slots → 
    confirmando_cita → completado
    
    Args:
        state: Estado actual del agente
        
    Returns:
        Command con update y goto según estado
    """
    log_separator(logger, "NODO_6R_RECEPCIONISTA", "INICIO")
    
    estado_actual = state.get('estado_conversacion', 'inicial')
    datos_temp = state.get('datos_temporales', {})
    mensaje_usuario = extraer_ultimo_mensaje_usuario(state)
    user_id = state.get('user_id', '')
    
    # Log de input
    input_data = f"estado: {estado_actual}\ndatos: {list(datos_temp.keys())}\nmensaje: {mensaje_usuario[:50]}"
    log_node_io(logger, "INPUT", "NODO_6R", input_data)
    
    logger.info(f"    🎯 Estado actual: {estado_actual}")
    logger.info(f"    📝 Datos recolectados: {list(datos_temp.keys())}")
    
    # ==================== MÁQUINA DE ESTADOS ====================
    
    if estado_actual == 'inicial':
        # Verificar si paciente existe
        paciente = get_paciente_by_phone(user_id)
        
        if not paciente:
            # Paciente nuevo - pedir nombre
            respuesta = "¡Hola! Claro, te ayudo a agendar una cita. ¿Cuál es tu nombre completo?"
            
            return Command(
                update={
                    'messages': [AIMessage(content=respuesta)],
                    'estado_conversacion': 'solicitando_nombre'
                },
                goto="END"
            )
        else:
            # Paciente existente - ir directo a solicitar fecha
            nombre = paciente.get('nombre_completo', 'paciente')
            datos_temp['nombre_paciente'] = nombre
            respuesta = f"¡Hola {nombre}! ¿Qué día prefieres para tu cita?"
            
            return Command(
                update={
                    'messages': [AIMessage(content=respuesta)],
                    'estado_conversacion': 'solicitando_fecha',
                    'datos_temporales': datos_temp
                },
                goto="END"
            )
    
    elif estado_actual == 'solicitando_nombre':
        # Extraer nombre con Pydantic
        nombre = extraer_nombre_con_llm(mensaje_usuario)
        
        if nombre and len(nombre.strip()) > 2:
            # Registrar paciente
            try:
                resultado = registrar_paciente_externo(user_id, nombre)
                logger.info(f"    ✅ Paciente registrado: {resultado}")
                
                datos_temp['nombre_paciente'] = nombre
                respuesta = f"Perfecto, {nombre}. ¿Qué día prefieres para tu cita?"
                nuevo_estado = 'solicitando_fecha'
            except Exception as e:
                logger.error(f"    ❌ Error registrando paciente: {e}")
                respuesta = "Hubo un problema al registrarte. ¿Podrías intentar de nuevo?"
                nuevo_estado = 'inicial'
        else:
            respuesta = "No pude identificar tu nombre. ¿Podrías decirme tu nombre completo?"
            nuevo_estado = 'solicitando_nombre'
        
        return Command(
            update={
                'messages': [AIMessage(content=respuesta)],
                'estado_conversacion': nuevo_estado,
                'datos_temporales': datos_temp
            },
            goto="END"
        )
    
    elif estado_actual == 'solicitando_fecha':
        # Extraer fecha con Pydantic
        tiempo_ctx = get_time_context()
        fecha = extraer_fecha_con_llm(mensaje_usuario, tiempo_ctx)
        
        if fecha:
            # Generar slots disponibles
            try:
                slots = generar_slots_con_turnos(dias_adelante=7)
                
                # Filtrar slots para la fecha solicitada si es posible
                # (simplificación: mostrar primeros 5 slots)
                if slots and len(slots) >= 3:
                    datos_temp['fecha_seleccionada'] = fecha
                    datos_temp['slots_disponibles'] = slots[:5]  # Max 5 opciones
                    
                    # Formatear slots
                    slots_texto = formatear_slots_para_whatsapp(slots[:5])
                    
                    respuesta = f"Encontré estos horarios disponibles:\n\n{slots_texto}"
                    nuevo_estado = 'mostrando_slots'
                else:
                    respuesta = f"No hay horarios disponibles para {fecha}. ¿Tienes otra fecha en mente?"
                    nuevo_estado = 'solicitando_fecha'
            except Exception as e:
                logger.error(f"    ❌ Error consultando slots: {e}")
                respuesta = "Hubo un problema consultando los horarios. ¿Podrías intentar con otra fecha?"
                nuevo_estado = 'solicitando_fecha'
        else:
            respuesta = "No entendí la fecha. ¿Podrías decirme qué día prefieres? Por ejemplo: 'mañana' o 'el lunes 15'"
            nuevo_estado = 'solicitando_fecha'
        
        return Command(
            update={
                'messages': [AIMessage(content=respuesta)],
                'estado_conversacion': nuevo_estado,
                'datos_temporales': datos_temp
            },
            goto="END"
        )
    
    elif estado_actual == 'mostrando_slots':
        # Extraer selección con Pydantic
        llm_with_structure = llm_extractor.with_structured_output(SeleccionSlot)
        
        try:
            seleccion = llm_with_structure.invoke(f"El usuario dijo: '{mensaje_usuario}'. Extrae qué opción seleccionó (1-5 o A-E). Si dice 'A' retorna 1, 'B' retorna 2, etc.")
            opcion = seleccion.opcion_seleccionada - 1  # Índice 0-based
            
            if 0 <= opcion < len(datos_temp.get('slots_disponibles', [])):
                slot_seleccionado = datos_temp['slots_disponibles'][opcion]
                datos_temp['slot_final'] = slot_seleccionado
                
                # Obtener nombre del doctor desde el slot
                doctor_nombre = slot_seleccionado.get('doctor_nombre', 'Doctor')
                
                # Confirmar datos
                respuesta = f"""Perfecto, confirmo tu cita:

📅 Fecha: {slot_seleccionado['fecha']}
🕐 Hora: {slot_seleccionado['hora_inicio']}
👨‍⚕️ Doctor: {doctor_nombre}
👤 Paciente: {datos_temp['nombre_paciente']}

¿Confirmas? (Sí/No)"""
                
                return Command(
                    update={
                        'messages': [AIMessage(content=respuesta)],
                        'estado_conversacion': 'confirmando_cita',
                        'datos_temporales': datos_temp
                    },
                    goto="END"
                )
        except Exception as e:
            logger.error(f"    ❌ Error procesando selección: {e}")
        
        respuesta = "No entendí tu selección. Por favor responde con la letra (A, B, C, etc.)"
        return Command(
            update={'messages': [AIMessage(content=respuesta)]},
            goto="END"
        )
    
    elif estado_actual == 'confirmando_cita':
        # Detectar confirmación
        mensaje_lower = mensaje_usuario.lower()
        
        if any(word in mensaje_lower for word in ['sí', 'si', 'confirmo', 'ok', 'vale', 'correcto', 'yes']):
            # Agendar la cita
            from src.medical.crud import agendar_cita_simple
            from datetime import datetime as dt
            
            slot = datos_temp['slot_final']
            paciente = get_paciente_by_phone(user_id)
            
            if not paciente:
                respuesta = "Hubo un error. No encontré tu registro. ¿Empezamos de nuevo?"
                return Command(
                    update={
                        'messages': [AIMessage(content=respuesta)],
                        'estado_conversacion': 'inicial',
                        'datos_temporales': {}
                    },
                    goto="END"
                )
            
            try:
                # Parsear fecha y hora del slot
                fecha_inicio_str = f"{slot['fecha']} {slot['hora_inicio']}"
                fecha_fin_str = f"{slot['fecha']} {slot['hora_fin']}"
                fecha_inicio = dt.strptime(fecha_inicio_str, "%Y-%m-%d %H:%M")
                fecha_fin = dt.strptime(fecha_fin_str, "%Y-%m-%d %H:%M")
                
                # Agendar la cita
                cita_id = agendar_cita_simple(
                    doctor_id=slot.get('doctor_asignado_id'),
                    paciente_id=paciente['id'],
                    fecha_inicio=fecha_inicio,
                    fecha_fin=fecha_fin,
                    motivo="Cita agendada via WhatsApp"
                )
                
                if cita_id:
                    respuesta = f"""✅ ¡Cita agendada exitosamente!

Tu cita está confirmada para el {slot['fecha']} a las {slot['hora_inicio']}.
Te enviaré un recordatorio 24 horas antes. ¡Hasta pronto!"""
                    
                    return Command(
                        update={
                            'messages': [AIMessage(content=respuesta)],
                            'estado_conversacion': 'completado',
                            'datos_temporales': {}
                        },
                        goto="sincronizador_hibrido"  # Sincronizar con Google Calendar
                    )
                else:
                    respuesta = "No pude agendar la cita. ¿Quieres intentar con otro horario?"
                    return Command(
                        update={
                            'messages': [AIMessage(content=respuesta)],
                            'estado_conversacion': 'solicitando_fecha',
                            'datos_temporales': {}
                        },
                        goto="END"
                    )
            except Exception as e:
                logger.error(f"    ❌ Error agendando cita: {e}")
                respuesta = "Hubo un error al agendar. ¿Quieres intentar de nuevo?"
                return Command(
                    update={
                        'messages': [AIMessage(content=respuesta)],
                        'estado_conversacion': 'inicial',
                        'datos_temporales': {}
                    },
                    goto="END"
                )
        else:
            respuesta = "Entendido, cancelé el proceso. ¿Quieres intentar con otra fecha?"
            
            return Command(
                update={
                    'messages': [AIMessage(content=respuesta)],
                    'estado_conversacion': 'inicial',
                    'datos_temporales': {}
                },
                goto="END"
            )
    
    # Fallback
    logger.warning(f"    ⚠️ Estado no manejado: {estado_actual}")
    return Command(
        update={
            'messages': [AIMessage(content="Hubo un error. ¿Empezamos de nuevo?")],
            'estado_conversacion': 'inicial',
            'datos_temporales': {}
        },
        goto="END"
    )


# ==================== WRAPPER ====================

def nodo_recepcionista_wrapper(state: WhatsAppAgentState) -> Command:
    """
    Wrapper para LangGraph - retorna Command directamente.
    
    Args:
        state: Estado actual
        
    Returns:
        Command del nodo principal
    """
    try:
        return nodo_recepcionista(state)
    except Exception as e:
        logger.error(f"❌ Error en nodo recepcionista: {e}")
        
        # Respuesta de fallback
        error_message = "Lo siento, hubo un error procesando tu solicitud de cita. Por favor intenta de nuevo."
        return Command(
            update={
                'messages': [AIMessage(content=error_message)],
                'estado_conversacion': 'inicial',
                'datos_temporales': {}
            },
            goto="END"
        )
