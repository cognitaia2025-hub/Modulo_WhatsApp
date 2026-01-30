"""
Nodo de recepcionista optimizado con slot filling.

Este módulo implementa el patrón de slot filling para una experiencia
más natural en lugar de opciones rígidas A/B/C.
"""

from typing import Dict, Any, List, Optional
from langchain_core.messages import AIMessage
from datetime import datetime, timedelta, date
import re

# Imports internos
from src.state.agent_state import WhatsAppAgentState
from src.utils.logging_config import setup_colored_logging
from src.medical.crud import (
    get_paciente_by_phone, 
    registrar_paciente_externo,
    get_doctor_by_id
)
from src.utils.nlp_extractors import extraer_nombre_con_llm
from src.medical.slots import generar_slots_con_turnos

logger = setup_colored_logging()

# Configuración de slot filling
DIAS_SEMANA = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
MESES = [
    'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
    'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'
]

def recepcionista_optimizado_node(state: WhatsAppAgentState) -> Dict[str, Any]:
    """
    Nodo de recepcionista optimizado con slot filling.
    
    En lugar de mostrar opciones rígidas A/B/C, este nodo:
    1. Verifica qué datos faltan (fecha_deseada, hora_deseada)
    2. Los pide de forma natural
    3. Una vez obtenidos, busca slots disponibles
    4. Presenta confirmación natural en lugar de menú
    
    Args:
        state: Estado del agente WhatsApp
        
    Returns:
        Estado actualizado con flujo de slot filling
    """
    from src.utils.logging_config import log_separator
    
    # LOGGING DETALLADO - INICIO DEL NODO
    log_separator(logger, "RECEPCIONISTA_OPTIMIZADO", "INICIO")
    logger.debug("🏥 === NODO RECEPCIONISTA OPTIMIZADO (SLOT FILLING) ===")
    
    # Obtener datos del estado
    estado_conv = state.get('estado_conversacion', 'inicial')
    messages = state.get('messages', [])
    paciente_phone = state.get('user_id', '')
    fecha_deseada = state.get('fecha_deseada')
    hora_deseada = state.get('hora_deseada')
    intencion_confirmada = state.get('intencion_confirmada', False)
    
    # LOGGING DEL ESTADO ACTUAL
    logger.debug(f"📱 Paciente: {paciente_phone}")
    logger.debug(f"🔄 Estado conversacion: {estado_conv}")
    logger.debug(f"📅 Fecha deseada: {fecha_deseada}")
    logger.debug(f"⏰ Hora deseada: {hora_deseada}")
    logger.debug(f"✅ Intencion confirmada: {intencion_confirmada}")
    logger.debug(f"💌 Total mensajes: {len(messages)}")
    
    if not messages:
        logger.error("❌ No hay mensajes en el estado")
        log_separator(logger, "RECEPCIONISTA_OPTIMIZADO", "ERROR")
        return {**state, 'respuesta_recepcionista': "Error: No hay mensajes"}
    
    ultimo_mensaje = messages[-1]
    mensaje_contenido = getattr(ultimo_mensaje, 'content', '')
    
    logger.debug(f"💬 Último mensaje: '{mensaje_contenido}'")
    logger.debug(f"📝 Longitud mensaje: {len(mensaje_contenido)} chars")
    
    try:
        logger.debug(f"🎯 Determinando flujo para estado: {estado_conv}")
        
        if estado_conv == 'inicial':
            logger.debug("🟢 Ejecutando: _manejar_inicial_slot_filling")
            respuesta, nuevo_estado, slots, updates = _manejar_inicial_slot_filling(
                paciente_phone, mensaje_contenido, fecha_deseada, hora_deseada
            )
            
        elif estado_conv == 'solicitando_nombre':
            logger.debug("📝 Ejecutando: _manejar_solicitar_nombre_optimizado")
            respuesta, nuevo_estado, slots, updates = _manejar_solicitar_nombre_optimizado(
                paciente_phone, mensaje_contenido
            )
            
        elif estado_conv == 'recolectando_slots':
            logger.debug("📊 Ejecutando: _manejar_recoleccion_slots")
            respuesta, nuevo_estado, slots, updates = _manejar_recoleccion_slots(
                paciente_phone, mensaje_contenido, fecha_deseada, hora_deseada
            )
            
        elif estado_conv == 'confirmando_cita':
            logger.debug("✅ Ejecutando: _manejar_confirmacion_final")
            respuesta, nuevo_estado, slots, updates = _manejar_confirmacion_final(
                paciente_phone, mensaje_contenido, state.get('slots_disponibles', [])
            )
            
        else:
            # Estado desconocido, reiniciar
            logger.warning(f"⚠️ Estado desconocido: {estado_conv} - Reiniciando")
            respuesta = "Lo siento, algo salió mal. ¿Podrías decirme nuevamente qué necesitas?"
            nuevo_estado = 'inicial'
            slots = []
            updates = {'fecha_deseada': None, 'hora_deseada': None, 'intencion_confirmada': False}
    
    except Exception as e:
        logger.error(f"❌ Error en recepcionista optimizado: {e}")
        logger.exception("📋 Stack trace completo:")
        respuesta = "Lo siento, ha ocurrido un error. ¿Podrías intentar de nuevo?"
        nuevo_estado = 'inicial'
        slots = []
        updates = {}
    
    # LOGGING DEL RESULTADO
    logger.debug(f"📤 Respuesta generada: '{respuesta[:100]}...'")
    logger.debug(f"🔄 Nuevo estado: {nuevo_estado}")
    logger.debug(f"📋 Updates: {updates}")
    logger.debug(f"🎯 Slots encontrados: {len(slots)}")
    
    # Crear mensaje AI
    ai_message = AIMessage(content=respuesta)

    # Actualizar estado
    estado_actualizado = {
        **state,
        **updates,
        'messages': [ai_message],
        'respuesta_recepcionista': respuesta,
        'estado_conversacion': nuevo_estado,
        'slots_disponibles': slots,
        'timestamp': datetime.now().isoformat()
    }

    logger.info(f"✅ Respuesta generada ({len(respuesta)} chars)")
    logger.info(f"🔄 Nuevo estado: {nuevo_estado}")
    log_separator(logger, "RECEPCIONISTA_OPTIMIZADO", "FIN")

    return estado_actualizado


def _manejar_inicial_slot_filling(
    paciente_phone: str, 
    mensaje: str, 
    fecha_deseada: Optional[str], 
    hora_deseada: Optional[str]
) -> tuple[str, str, List[Dict], Dict[str, Any]]:
    """
    Maneja el estado inicial con slot filling.
    
    Returns:
        (respuesta, nuevo_estado, slots_disponibles, updates)
    """
    logger.debug("🟢 === MANEJANDO INICIAL SLOT FILLING ===")
    logger.debug(f"📱 Teléfono: {paciente_phone}")
    logger.debug(f"💬 Mensaje: '{mensaje}'")
    logger.debug(f"📅 Fecha actual: {fecha_deseada}")
    logger.debug(f"⏰ Hora actual: {hora_deseada}")
    
    # 1. Verificar si paciente existe
    logger.debug("🔍 Verificando si paciente existe...")
    paciente = get_paciente_by_phone(paciente_phone)
    
    if not paciente:
        logger.info("🆕 Paciente nuevo - solicitando nombre")
        respuesta = "Hola! Veo que es tu primera vez. Para agendarte una cita, necesito tu nombre completo. ¿Cómo te llamas?"
        return respuesta, 'solicitando_nombre', [], {}
    
    nombre_paciente = paciente.get('nombre_completo', 'paciente').replace(' (Test)', '')
    logger.debug(f"✅ Paciente existente: {nombre_paciente}")
    
    # 2. Extraer información de slot del mensaje actual
    logger.debug("🔍 Extrayendo información de slots del mensaje...")
    fecha_extraida = _extraer_fecha_del_mensaje(mensaje)
    hora_extraida = _extraer_hora_del_mensaje(mensaje)
    
    logger.debug(f"📅 Fecha extraída: {fecha_extraida}")
    logger.debug(f"⏰ Hora extraída: {hora_extraida}")
    
    # Actualizar slots con nueva información
    if fecha_extraida:
        fecha_deseada = fecha_extraida
        logger.debug(f"✅ Fecha actualizada: {fecha_deseada}")
    if hora_extraida:
        hora_deseada = hora_extraida
        logger.debug(f"✅ Hora actualizada: {hora_deseada}")
    
    # 3. Verificar qué información nos falta
    logger.debug("📊 Analizando información faltante...")
    logger.debug(f"📅 Fecha disponible: {bool(fecha_deseada)}")
    logger.debug(f"⏰ Hora disponible: {bool(hora_deseada)}")
    
    if not fecha_deseada:
        logger.debug("❌ Falta fecha - solicitando")
        respuesta = f"Hola {nombre_paciente}! ¿Para qué día te gustaría la cita? Puedes decirme 'mañana', 'el viernes', etc."
        updates = {'fecha_deseada': fecha_deseada, 'hora_deseada': hora_deseada}
        return respuesta, 'recolectando_slots', [], updates
    
    elif not hora_deseada:
        logger.debug("❌ Falta hora - solicitando")
        respuesta = f"Perfecto {nombre_paciente}, para {fecha_deseada}. ¿A qué hora prefieres? Puedes decir 'mañana', 'tarde', o una hora específica."
        updates = {'fecha_deseada': fecha_deseada, 'hora_deseada': hora_deseada}
        return respuesta, 'recolectando_slots', [], updates
    
    else:
        # Tenemos ambos datos, buscar slots y confirmar
        logger.debug("✅ Tenemos fecha y hora - buscando slots")
        slots = _buscar_slots_por_preferencias(fecha_deseada, hora_deseada)
        
        if not slots:
            logger.debug(f"❌ No hay slots disponibles para {fecha_deseada} {hora_deseada}")
            respuesta = f"Lo siento {nombre_paciente}. No tenemos disponibilidad para {fecha_deseada} {hora_deseada}. ¿Te funcionaría otro día u horario?"
            updates = {'fecha_deseada': None, 'hora_deseada': None}
            return respuesta, 'recolectando_slots', [], updates
        
        # Presentar confirmación natural (no menú A/B/C)
        mejor_slot = slots[0]  # Tomar el mejor match
        logger.debug(f"✅ Slot encontrado: {mejor_slot}")
        respuesta = f"Perfecto {nombre_paciente}! Encontré disponibilidad para: {_formatear_slot_natural(mejor_slot)} ¿Te confirmo esta cita?"
        
        updates = {
            'fecha_deseada': fecha_deseada, 
            'hora_deseada': hora_deseada,
            'intencion_confirmada': False
        }
        return respuesta, 'confirmando_cita', [mejor_slot], updates


def _manejar_recoleccion_slots(
    paciente_phone: str,
    mensaje: str, 
    fecha_deseada: Optional[str], 
    hora_deseada: Optional[str]
) -> tuple[str, str, List[Dict], Dict[str, Any]]:
    """
    Maneja la recolección de información de slot faltante.
    """
    logger.info("📝 Recolectando información de slot")
    
    # Extraer nueva información del mensaje
    fecha_extraida = _extraer_fecha_del_mensaje(mensaje)
    hora_extraida = _extraer_hora_del_mensaje(mensaje)
    
    # Actualizar con nueva información
    if fecha_extraida:
        fecha_deseada = fecha_extraida
    if hora_extraida:
        hora_deseada = hora_extraida
    
    paciente = get_paciente_by_phone(paciente_phone)
    nombre_paciente = paciente.get('nombre_completo', 'paciente').replace(' (Test)', '')
    
    # Verificar qué sigue faltando
    if not fecha_deseada:
        respuesta = "¿Para qué día te gustaría la cita? Puedes decirme 'mañana', 'el viernes', etc."
        updates = {'fecha_deseada': fecha_deseada, 'hora_deseada': hora_deseada}
        return respuesta, 'recolectando_slots', [], updates
    
    elif not hora_deseada:
        respuesta = f"Perfecto, para {fecha_deseada}. ¿A qué hora prefieres? Puedes decir 'mañana', 'tarde', etc."
        updates = {'fecha_deseada': fecha_deseada, 'hora_deseada': hora_deseada}
        return respuesta, 'recolectando_slots', [], updates
    
    else:
        # Ya tenemos todo, buscar y confirmar
        slots = _buscar_slots_por_preferencias(fecha_deseada, hora_deseada)
        
        if not slots:
            respuesta = f"Lo siento {nombre_paciente}. No hay disponibilidad para {fecha_deseada} {hora_deseada}. ¿Podrías intentar con otro día u horario?"
            updates = {'fecha_deseada': None, 'hora_deseada': None}
            return respuesta, 'recolectando_slots', [], updates
        
        mejor_slot = slots[0]
        respuesta = f"Excelente {nombre_paciente}! Tengo disponibilidad para: {_formatear_slot_natural(mejor_slot)} ¿Confirmo esta cita?"
        
        updates = {
            'fecha_deseada': fecha_deseada,
            'hora_deseada': hora_deseada,
            'intencion_confirmada': False
        }
        return respuesta, 'confirmando_cita', [mejor_slot], updates


def _manejar_confirmacion_final(
    paciente_phone: str,
    mensaje: str,
    slots_disponibles: List[Dict]
) -> tuple[str, str, List[Dict], Dict[str, Any]]:
    """
    Maneja la confirmación final de la cita.
    """
    logger.debug("✅ === CONFIRMACIÓN FINAL ===")
    logger.debug(f"📱 Teléfono: {paciente_phone}")
    logger.debug(f"💬 Mensaje: '{mensaje}'")
    logger.debug(f"📋 Slots disponibles: {len(slots_disponibles)}")
    
    if slots_disponibles:
        logger.debug(f"🎯 Primer slot: {slots_disponibles[0]}")
    
    mensaje_lower = mensaje.lower().strip()
    logger.debug(f"🔍 Mensaje normalizado: '{mensaje_lower}'")
    
    es_confirmacion = any(palabra in mensaje_lower for palabra in [
        'sí', 'si', 'confirmo', 'perfecto', 'ok', 'está bien', 'dale', 'confirma'
    ])
    es_negacion = any(palabra in mensaje_lower for palabra in [
        'no', 'cancel', 'cambiar', 'otro', 'diferente'
    ])
    
    logger.debug(f"✅ Es confirmación: {es_confirmacion}")
    logger.debug(f"❌ Es negación: {es_negacion}")
    
    if es_negacion:
        logger.debug("❌ Usuario rechazó la cita")
        respuesta = "No hay problema. ¿Prefieres otro día u horario? Dime cuándo te funcionaría mejor."
        updates = {
            'fecha_deseada': None,
            'hora_deseada': None,
            'intencion_confirmada': False
        }
        return respuesta, 'recolectando_slots', [], updates
    
    elif es_confirmacion and slots_disponibles:
        # Simulación de agendamiento exitoso
        slot_elegido = slots_disponibles[0]
        respuesta = f"¡Perfecto! Tu cita ha sido agendada para {_formatear_slot_natural(slot_elegido)}. Te esperamos!"
        
        updates = {'intencion_confirmada': True}
        return respuesta, 'completado', slots_disponibles, updates
    
    else:
        # Respuesta ambigua, pedir confirmación clara
        respuesta = "¿Confirmas la cita? Puedes responder 'sí, confirmo' o 'no, prefiero otro horario'."
        return respuesta, 'confirmando_cita', slots_disponibles, {}


def _manejar_solicitar_nombre_optimizado(
    paciente_phone: str,
    mensaje: str
) -> tuple[str, str, List[Dict], Dict[str, Any]]:
    """
    Maneja la solicitud de nombre optimizada.
    """
    logger.info("📝 Solicitando nombre optimizado")
    
    nombre = extraer_nombre_con_llm(mensaje)
    
    if not nombre or len(nombre.strip()) < 2:
        respuesta = "No pude entender tu nombre. ¿Podrías decírmelo de nuevo? Por ejemplo: 'Soy Juan Pérez'"
        return respuesta, 'solicitando_nombre', [], {}
    
    # Registrar paciente
    try:
        resultado = registrar_paciente_externo(paciente_phone, nombre)
        logger.info(f"✅ Paciente registrado: {resultado}")
        
        respuesta = f"Gracias {nombre}! Ya te registré en el sistema. ¿Para qué día te gustaría la cita?"
        return respuesta, 'recolectando_slots', [], {}
        
    except Exception as e:
        logger.error(f"❌ Error registrando paciente: {e}")
        respuesta = "Ha ocurrido un problema al registrarte. ¿Podrías intentar más tarde?"
        return respuesta, 'inicial', [], {}


# ==================== FUNCIONES AUXILIARES ====================

def _extraer_fecha_del_mensaje(mensaje: str) -> Optional[str]:
    """
    Extrae información de fecha del mensaje usando patrones simples.
    """
    mensaje_lower = mensaje.lower()
    logger.debug(f"🔍 Extrayendo fecha del mensaje: '{mensaje_lower}'")
    
    # Patrones básicos
    if 'mañana' in mensaje_lower:
        fecha = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        resultado = f"mañana ({fecha})"
        logger.debug(f"📅 Fecha extraída: {resultado}")
        return resultado
    
    elif 'pasado mañana' in mensaje_lower:
        fecha = (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')
        resultado = f"pasado mañana ({fecha})"
        logger.debug(f"📅 Fecha extraída: {resultado}")
        return resultado
    
    # Días de la semana
    for i, dia in enumerate(DIAS_SEMANA):
        if dia in mensaje_lower:
            # Calcular próximo día de la semana
            hoy = datetime.now().weekday()
            dias_hasta = (i - hoy) % 7
            if dias_hasta == 0:
                dias_hasta = 7  # Siguiente semana
            fecha = (datetime.now() + timedelta(days=dias_hasta)).strftime('%Y-%m-%d')
            resultado = f"{dia} ({fecha})"
            logger.debug(f"📅 Fecha extraída: {resultado}")
            return resultado
    
    logger.debug("❌ No se pudo extraer fecha")
    return None


def _extraer_hora_del_mensaje(mensaje: str) -> Optional[str]:
    """
    Extrae información de hora del mensaje.
    """
    mensaje_lower = mensaje.lower()
    logger.debug(f"🕐 Extrayendo hora del mensaje: '{mensaje_lower}'")
    
    # Patrones de hora - MEJORADOS para mejor detección
    if any(palabra in mensaje_lower for palabra in ['mañana', 'temprano', 'matutino', '8', '9', '10', '11']):
        resultado = "en la mañana"
        logger.debug(f"⏰ Hora extraída: {resultado}")
        return resultado
        
    elif any(palabra in mensaje_lower for palabra in ['tarde', 'después', 'vespertino', '12', '13', '14', '15', '16', '17', '2', '3', '4', '5']):
        resultado = "por la tarde"
        logger.debug(f"⏰ Hora extraída: {resultado}")
        return resultado
        
    elif any(palabra in mensaje_lower for palabra in ['noche', 'nocturno', '18', '19', '20', '6pm', '7pm', '8pm']):
        resultado = "en la noche"
        logger.debug(f"⏰ Hora extraída: {resultado}")
        return resultado
    
    # Horas específicas (básico)
    import re
    patron_hora = re.search(r'(\d{1,2})(?::\d{2})?\s*(?:am|pm|hrs?)?', mensaje_lower)
    if patron_hora:
        resultado = f"a las {patron_hora.group(0)}"
        logger.debug(f"⏰ Hora extraída: {resultado}")
        return resultado
    
    logger.debug("❌ No se pudo extraer hora")
    return None


def _buscar_slots_por_preferencias(fecha_deseada: str, hora_deseada: str) -> List[Dict]:
    """
    Busca slots disponibles según las preferencias del usuario.
    """
    logger.info(f"🔍 Buscando slots para: {fecha_deseada} {hora_deseada}")
    
    # Por ahora, usar generador existente y filtrar
    slots = generar_slots_con_turnos(dias_adelante=14)
    
    if not slots:
        return []
    
    # Filtrado básico por hora preferida
    slots_filtrados = []
    for slot in slots:
        hora_slot = slot.get('hora_inicio', '')
        
        if 'mañana' in hora_deseada.lower() and hora_slot < '12:00':
            slots_filtrados.append(slot)
        elif 'tarde' in hora_deseada.lower() and '12:00' <= hora_slot < '18:00':
            slots_filtrados.append(slot)
        elif 'noche' in hora_deseada.lower() and hora_slot >= '18:00':
            slots_filtrados.append(slot)
        else:
            # Si no hay filtro específico, incluir todos
            slots_filtrados.append(slot)
    
    # Retornar máximo 3 mejores opciones
    return slots_filtrados[:3] if slots_filtrados else slots[:3]


def _formatear_slot_natural(slot: Dict) -> str:
    """
    Formatea un slot de manera natural (no como opción A/B/C).
    """
    fecha_obj = date.fromisoformat(slot['fecha'])
    dia_nombre = DIAS_SEMANA[fecha_obj.weekday()]
    dia_numero = fecha_obj.day
    mes_nombre = MESES[fecha_obj.month - 1]
    
    hora_inicio = slot['hora_inicio'][:5]
    hora_fin = slot['hora_fin'][:5]
    
    return f"{dia_nombre.title()} {dia_numero} de {mes_nombre}, {hora_inicio} - {hora_fin}"


# Wrapper para compatibilidad
def nodo_recepcionista_optimizado_wrapper(state: WhatsAppAgentState) -> Dict[str, Any]:
    """
    Wrapper que mantiene la firma esperada por el grafo.
    """
    try:
        return recepcionista_optimizado_node(state)
    except Exception as e:
        logger.error(f"❌ Error en recepcionista optimizado: {e}")
        return {
            **state,
            'respuesta_recepcionista': "Error en el sistema de citas. Inténtalo más tarde.",
            'estado_conversacion': 'inicial'
        }