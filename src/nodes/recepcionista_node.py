"""
Nodo Recepcionista Conversacional - Etapa 4

Maneja el flujo conversacional completo para que pacientes externos 
agenden citas vía WhatsApp.

Estados de conversación:
- inicial: Primera interacción
- solicitando_nombre: Paciente nuevo sin registro
- mostrando_opciones: Se mostraron 3 slots disponibles  
- esperando_seleccion: Esperando que paciente elija A/B/C
- confirmando: Agendando cita en BD
- completado: Cita confirmada
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, date
from langchain_core.messages import AIMessage

from src.state.agent_state import WhatsAppAgentState
from src.utils.logging_config import setup_colored_logging
from src.utils.nlp_extractors import extraer_nombre_con_llm, extraer_seleccion
from src.medical.crud import get_paciente_by_phone, registrar_paciente_externo, get_doctor_by_id
from src.medical.slots import generar_slots_con_turnos

# Configurar logging
logger = setup_colored_logging()

# Configuración
OPCIONES_LETRAS = ['A', 'B', 'C', 'D', 'E']
DIAS_SEMANA = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
MESES = [
    'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
    'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'
]


def recepcionista_node(state: WhatsAppAgentState) -> Dict:
    """
    Nodo principal del flujo de recepcionista conversacional.
    
    Args:
        state: Estado del agente WhatsApp
        
    Returns:
        Estado actualizado con respuesta del recepcionista
    """
    logger.info("🏥 === NODO RECEPCIONISTA CONVERSACIONAL ===")
    
    # Obtener datos del estado
    estado_conv = state.get('estado_conversacion', 'inicial')
    messages = state.get('messages', [])
    paciente_phone = state.get('user_id', '')
    
    if not messages:
        logger.error("❌ No hay mensajes en el estado")
        return {**state, 'respuesta_recepcionista': "Error: No hay mensajes"}
    
    ultimo_mensaje = messages[-1]
    mensaje_contenido = getattr(ultimo_mensaje, 'content', '')
    
    logger.info(f"📱 Paciente: {paciente_phone}")
    logger.info(f"🔄 Estado conversación: {estado_conv}")
    logger.info(f"💬 Mensaje: {mensaje_contenido[:50]}...")
    
    respuesta = ""
    nuevo_estado = estado_conv
    slots_disponibles = state.get('slots_disponibles', [])
    
    try:
        if estado_conv == 'inicial':
            respuesta, nuevo_estado, slots_disponibles = _manejar_estado_inicial(
                paciente_phone, mensaje_contenido
            )
            
        elif estado_conv == 'solicitando_nombre':
            respuesta, nuevo_estado, slots_disponibles = _manejar_solicitar_nombre(
                paciente_phone, mensaje_contenido
            )
            
        elif estado_conv == 'esperando_seleccion':
            respuesta, nuevo_estado = _manejar_esperando_seleccion(
                paciente_phone, mensaje_contenido, slots_disponibles
            )
            
        else:
            # Estados terminales o no manejados
            respuesta = "¡Hola! ¿En qué puedo ayudarte hoy?"
            nuevo_estado = 'inicial'
            slots_disponibles = []
    
    except Exception as e:
        logger.error(f"❌ Error en recepcionista_node: {e}")
        respuesta = "Lo siento, ha ocurrido un error. ¿Podrías intentar de nuevo?"
        nuevo_estado = 'inicial'
        slots_disponibles = []
    
    # Agregar mensaje de respuesta a messages
    ai_message = AIMessage(content=respuesta)

    # Actualizar estado (solo retornar las actualizaciones necesarias)
    estado_actualizado = {
        'messages': [ai_message],  # Se agregará a messages gracias a add_messages
        'respuesta_recepcionista': respuesta,
        'estado_conversacion': nuevo_estado,
        'slots_disponibles': slots_disponibles,
        'timestamp': datetime.now().isoformat()
    }

    logger.info(f"✅ Respuesta generada ({len(respuesta)} chars)")
    logger.info(f"🔄 Nuevo estado: {nuevo_estado}")

    return estado_actualizado


def _manejar_estado_inicial(paciente_phone: str, mensaje: str) -> tuple[str, str, List[Dict]]:
    """
    Maneja el estado inicial de conversación.
    
    Returns:
        (respuesta, nuevo_estado, slots_disponibles)
    """
    logger.info("🟢 Manejando estado inicial")
    
    # 1. Verificar si paciente existe
    paciente = get_paciente_by_phone(paciente_phone)
    
    if not paciente:
        # Paciente nuevo - pedir nombre
        logger.info("🆕 Paciente nuevo detectado - solicitando nombre")
        respuesta = """¡Hola! 👋 

Veo que es tu primera vez. Para poder agendarte una cita, necesito tu nombre completo.

¿Cuál es tu nombre?"""
        
        return respuesta, 'solicitando_nombre', []
    
    else:
        # Paciente existente - mostrar opciones directamente
        nombre_paciente = paciente.get('nombre_completo', 'paciente')
        logger.info(f"✅ Paciente existente: {nombre_paciente}")
        
        # Generar slots disponibles
        slots = generar_slots_con_turnos(dias_adelante=7)
        
        if not slots or len(slots) < 3:
            respuesta = """¡Hola! 👋

Lo siento, no tenemos disponibilidad en los próximos días. 
¿Podrías intentar más tarde o contactarnos por teléfono?"""
            
            return respuesta, 'completado', []
        
        # Mostrar 3 opciones
        respuesta_slots = _formatear_opciones_slots(slots[:3])
        respuesta = f"""¡Hola {nombre_paciente}! 👋

{respuesta_slots}"""
        
        return respuesta, 'esperando_seleccion', slots[:3]


def _manejar_solicitar_nombre(paciente_phone: str, mensaje: str) -> tuple[str, str, List[Dict]]:
    """
    Maneja el estado de solicitar nombre.
    
    Returns:
        (respuesta, nuevo_estado, slots_disponibles)
    """
    logger.info("📝 Manejando solicitud de nombre")
    
    # Extraer nombre del mensaje
    nombre = extraer_nombre_con_llm(mensaje)
    
    if not nombre or len(nombre.strip()) < 2:
        logger.warning(f"Nombre extraído muy corto: '{nombre}'")
        respuesta = """No pude entender tu nombre correctamente. 

¿Podrías decírmelo de nuevo? Por ejemplo: "Mi nombre es Juan Pérez\""""
        
        return respuesta, 'solicitando_nombre', []
    
    # Registrar paciente
    try:
        resultado = registrar_paciente_externo(paciente_phone, nombre)
        logger.info(f"✅ Paciente registrado: {resultado}")
        
        # Generar slots disponibles
        slots = generar_slots_con_turnos(dias_adelante=7)
        
        if not slots or len(slots) < 3:
            respuesta = f"""¡Gracias {nombre}! 

Ya te registré en nuestro sistema. 
Sin embargo, no tenemos disponibilidad en los próximos días.

¿Podrías intentar más tarde o contactarnos por teléfono?"""
            
            return respuesta, 'completado', []
        
        # Mostrar opciones
        respuesta_slots = _formatear_opciones_slots(slots[:3])
        respuesta = f"""¡Gracias {nombre}! 😊

Ya te registré en nuestro sistema.

{respuesta_slots}"""
        
        return respuesta, 'esperando_seleccion', slots[:3]
        
    except Exception as e:
        logger.error(f"❌ Error registrando paciente: {e}")
        respuesta = """Ha ocurrido un problema al registrarte en el sistema.

¿Podrías intentar de nuevo más tarde o contactarnos por teléfono?"""
        
        return respuesta, 'inicial', []


def _manejar_esperando_seleccion(paciente_phone: str, mensaje: str, slots: List[Dict]) -> tuple[str, str]:
    """
    Maneja el estado de esperar selección.
    
    Returns:
        (respuesta, nuevo_estado)
    """
    logger.info("🎯 Manejando selección de slot")
    
    # Extraer selección
    seleccion = extraer_seleccion(mensaje)
    
    if seleccion is None:
        logger.warning(f"Selección no válida: '{mensaje}'")
        respuesta = """No pude entender tu selección. 

¿Podrías escribir la letra de la opción que prefieres? Por ejemplo: "A" o "Escojo la B\""""
        
        return respuesta, 'esperando_seleccion'
    
    # Validar que la selección esté en rango
    if seleccion < 0 or seleccion >= len(slots):
        logger.warning(f"Selección fuera de rango: {seleccion}, slots disponibles: {len(slots)}")
        respuesta = f"""Opción no válida. 

Por favor escoge una de las opciones disponibles: {', '.join(OPCIONES_LETRAS[:len(slots)])}"""
        
        return respuesta, 'esperando_seleccion'
    
    # Obtener slot seleccionado
    slot_elegido = slots[seleccion]
    
    # Intentar agendar la cita
    try:
        # Obtener datos del paciente
        paciente = get_paciente_by_phone(paciente_phone)
        if not paciente:
            logger.error("❌ Paciente no encontrado al agendar")
            respuesta = """Ha ocurrido un problema. ¿Podrías intentar de nuevo desde el inicio?"""
            return respuesta, 'inicial'
        
        logger.info(f"🎯 Agendando cita: paciente_id={paciente['id']}, slot={slot_elegido['fecha']} {slot_elegido['hora_inicio']}")
        
        # Agendar usando el doctor asignado en el slot
        # get_doctor_by_id retorna dict
        doctor = get_doctor_by_id(slot_elegido['doctor_asignado_id'])
        
        if not doctor:
            logger.error(f"❌ Doctor no encontrado: ID {slot_elegido['doctor_asignado_id']}")
            respuesta = """Ha ocurrido un problema con la asignación del doctor.

¿Podrías intentar de nuevo?"""
            return respuesta, 'inicial'
        
        # Agendar la cita usando función CRUD simplificada
        from src.medical.crud import agendar_cita_simple
        from datetime import datetime as dt
        
        # Parsear fecha y hora del slot
        fecha_inicio_str = f"{slot_elegido['fecha']} {slot_elegido['hora_inicio']}"
        fecha_fin_str = f"{slot_elegido['fecha']} {slot_elegido['hora_fin']}"
        fecha_inicio = dt.strptime(fecha_inicio_str, "%Y-%m-%d %H:%M")
        fecha_fin = dt.strptime(fecha_fin_str, "%Y-%m-%d %H:%M")
        
        # Agendar la cita
        cita_id = agendar_cita_simple(
            doctor_id=doctor['id'],
            paciente_id=paciente['id'],
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            motivo="Cita agendada via WhatsApp"
        )
        
        if cita_id:
            logger.info(f"✅ Cita agendada exitosamente (ID: {cita_id})")
            respuesta = f"""🎉 ¡Perfecto! Tu cita ha sido agendada.

📅 **Detalles de tu cita:**
{_formatear_detalle_slot_seleccionado(slot_elegido, doctor['nombre_completo'])}

📞 Si necesitas cancelar o reprogramar, contáctanos al teléfono de la clínica.

¡Te esperamos! 😊"""
        else:
            logger.error("❌ Error agendando cita")
            respuesta = """Lo siento, no pude agendar la cita en este momento.

¿Podrías intentar con otra opción o contactarnos por teléfono?"""
            return respuesta, 'esperando_seleccion'
            
    except Exception as e:
        logger.error(f"❌ Error crítico agendando cita: {e}")
        respuesta = """Ha ocurrido un problema al agendar la cita.

¿Podrías intentar de nuevo o contactarnos por teléfono?"""
        return respuesta, 'inicial'
    
    return respuesta, 'completado'


def _formatear_opciones_slots(slots: List[Dict]) -> str:
    """
    Formatea los slots disponibles para mostrar al paciente.
    NO menciona el doctor hasta la confirmación final.
    """
    respuesta = "🗓️ **Opciones disponibles:**\n\n"
    
    for i, slot in enumerate(slots):
        letra = OPCIONES_LETRAS[i]
        
        # Parsear fecha
        fecha_obj = date.fromisoformat(slot['fecha'])
        dia_nombre = DIAS_SEMANA[fecha_obj.weekday()]
        dia_numero = fecha_obj.day
        mes_nombre = MESES[fecha_obj.month - 1]
        
        # Formatear horarios
        hora_inicio = slot['hora_inicio'][:5]  # HH:MM
        hora_fin = slot['hora_fin'][:5]      # HH:MM
        
        respuesta += f"**{letra})** {dia_nombre.title()} {dia_numero} de {mes_nombre} - {hora_inicio} a {hora_fin}\n"
    
    respuesta += "\n¿Cuál te conviene más? Responde con la letra (A, B, C...)"
    
    return respuesta


def _formatear_detalle_slot_seleccionado(slot: Dict, doctor_nombre: str) -> str:
    """
    Formatea el detalle del slot seleccionado para confirmación.
    AQUÍ SÍ se revela el doctor asignado.
    """
    # Parsear fecha
    fecha_obj = date.fromisoformat(slot['fecha'])
    dia_nombre = DIAS_SEMANA[fecha_obj.weekday()]
    dia_numero = fecha_obj.day
    mes_nombre = MESES[fecha_obj.month - 1]
    
    # Formatear horarios
    hora_inicio = slot['hora_inicio'][:5]  # HH:MM
    hora_fin = slot['hora_fin'][:5]      # HH:MM
    
    detalle = f"""📅 Fecha: {dia_nombre.title()} {dia_numero} de {mes_nombre}
🕐 Hora: {hora_inicio} a {hora_fin}
👨‍⚕️ Doctor: {doctor_nombre}"""
    
    return detalle


# Testing function para desarrollo
def test_recepcionista_node():
    """Función de prueba para desarrollo local"""
    from langchain_core.messages import HumanMessage, AIMessage
    
    # Test 1: Paciente nuevo
    print("=== Test 1: Paciente nuevo ===")
    state_test = {
        'messages': [HumanMessage(content="Hola, quiero agendar una cita")],
        'user_id': '+521234567890',  # Número de prueba
        'estado_conversacion': 'inicial',
        'slots_disponibles': [],
        'timestamp': datetime.now().isoformat()
    }
    
    resultado = recepcionista_node(state_test)
    print(f"Respuesta: {resultado['respuesta_recepcionista']}")
    print(f"Nuevo estado: {resultado['estado_conversacion']}")
    
    # Test 2: Envío de nombre
    print("\n=== Test 2: Envío de nombre ===")
    state_test['estado_conversacion'] = 'solicitando_nombre'
    state_test['messages'].append(HumanMessage(content="Me llamo Juan Pérez"))
    
    resultado = recepcionista_node(state_test)
    print(f"Respuesta: {resultado['respuesta_recepcionista']}")
    print(f"Nuevo estado: {resultado['estado_conversacion']}")
    print(f"Slots disponibles: {len(resultado['slots_disponibles'])}")


# Wrapper para compatibilidad con grafo
def nodo_recepcionista_wrapper(state: WhatsAppAgentState) -> Dict:
    """
    Wrapper que mantiene la firma esperada por el grafo
    """
    try:
        # Llamar al nodo principal y retornar solo las actualizaciones
        return recepcionista_node(state)

    except Exception as e:
        logger.error(f"❌ Error en nodo recepcionista: {e}")

        # Respuesta de fallback
        error_message = "Lo siento, hubo un error procesando tu solicitud de cita. Por favor intenta de nuevo."
        return {
            'messages': [AIMessage(content=error_message)],
            'respuesta_recepcionista': error_message,
            'estado_conversacion': 'inicial'
        }


if __name__ == "__main__":
    test_recepcionista_node()