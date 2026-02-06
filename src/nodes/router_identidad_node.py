"""
Router por Identidad - Routing instantáneo basado en tipo de usuario

Reemplaza el nodo de clasificación LLM para el 98% de casos.
Lógica:
- Paciente externo → recepcionista (siempre)
- Doctor/Admin → clasificar solo si necesario
- Saludo → respuesta casual
"""

import logging
from typing import Dict, Any, cast
from src.state.agent_state import WhatsAppAgentState

logger = logging.getLogger(__name__)


def nodo_router_identidad(state: WhatsAppAgentState) -> Dict[str, Any]:
    """
    Routing CERO-LATENCIA basado en tipo de usuario identificado.
    
    Args:
        state: Estado del grafo con tipo_usuario ya identificado en N0
        
    Returns:
        Dict con clasificacion_mensaje y ruta_siguiente
    """
    
    tipo_usuario = state.get('tipo_usuario', '')
    estado_actual = state.get('estado_conversacion', 'inicial') # ✅ Recuperar estado
    mensaje = _obtener_ultimo_mensaje(state)
    
    logger.info(f"🔀 ROUTER IDENTIDAD: tipo_usuario='{tipo_usuario}', estado='{estado_actual}'")
    logger.info(f"   Mensaje: '{mensaje[:50]}...'")
    
    # ========================================
    # PACIENTES: 70% de casos - RUTA DIRECTA
    # ========================================
    if tipo_usuario == 'paciente_externo':
        # ✅ Si ya está en un flujo de cita, NO clasificar como saludo
        if estado_actual in ['recolectando_slots', 'confirmando_cita', 'solicitando_nombre']:
            logger.info(f"   ♻️  Continuando flujo de cita en estado: {estado_actual}")
            return {
                'clasificacion_mensaje': 'solicitud_cita_paciente',
                'ruta_siguiente': 'recepcionista',
                'requiere_clasificacion_llm': False
            }
        
        # Solo permitir saludo si el estado es inicial
        if _es_saludo_inicial(mensaje) and estado_actual == 'inicial':
            ruta = 'respuesta_conversacional'
            clasificacion = 'chat'
            logger.info(f"   → RUTA: {ruta} (saludo paciente)")
        else:
            ruta = 'recepcionista'
            clasificacion = 'solicitud_cita_paciente'
            logger.info(f"   → RUTA: {ruta} (solicitud cita)")
        
        return {
            'clasificacion_mensaje': clasificacion,
            'ruta_siguiente': ruta,
            'requiere_clasificacion_llm': False,
            'confianza_clasificacion': 0.99  # Certeza total
        }
    
    # ========================================
    # DOCTORES: 25% de casos - CLASIFICACIÓN RÁPIDA
    # ========================================
    elif tipo_usuario == 'doctor':
        clasificacion = _clasificar_doctor_rapido(mensaje, state)
        
        if clasificacion in ['medica', 'personal']:
            # Clasificación exitosa sin LLM (90% de mensajes de doctores)
            logger.info(f"   → RUTA: {clasificacion} (clasificación rápida)")
            return {
                'clasificacion_mensaje': clasificacion,
                'ruta_siguiente': clasificacion,
                'requiere_clasificacion_llm': False,
                'confianza_clasificacion': 0.95
            }
        else:
            # Necesita LLM (10% de mensajes de doctores)
            logger.info(f"   → RUTA: clasificador_llm (mensaje ambiguo)")
            return {
                'ruta_siguiente': 'clasificador_llm',
                'requiere_clasificacion_llm': True
            }
    
    # ========================================
    # ADMIN: 5% de casos
    # ========================================
    elif tipo_usuario == 'admin' or state.get('es_admin'):
        # Detectar comandos administrativos
        if _es_comando_admin(mensaje):
            logger.info(f"   → RUTA: procesador_admin (comando admin)")
            return {
                'clasificacion_mensaje': 'administrativo',
                'ruta_siguiente': 'procesador_admin',
                'requiere_clasificacion_llm': False,
                'confianza_clasificacion': 0.98
            }
        else:
            # Clasificar como doctor (puede hacer personal + médico)
            clasificacion = _clasificar_doctor_rapido(mensaje, state)
            if clasificacion in ['medica', 'personal']:
                return {
                    'clasificacion_mensaje': clasificacion,
                    'ruta_siguiente': clasificacion,
                    'requiere_clasificacion_llm': False,
                    'confianza_clasificacion': 0.95
                }
            else:
                return {
                    'ruta_siguiente': 'clasificador_llm',
                    'requiere_clasificacion_llm': True
                }
    
    # ========================================
    # FALLBACK: Tipo de usuario desconocido
    # ========================================
    else:
        logger.warning(f"   ⚠️ Tipo de usuario desconocido: '{tipo_usuario}'")
        return {
            'ruta_siguiente': 'respuesta_conversacional',
            'clasificacion_mensaje': 'chat',
            'requiere_clasificacion_llm': False,
            'confianza_clasificacion': 0.50
        }


# ==================== FUNCIONES AUXILIARES ====================

def _obtener_ultimo_mensaje(state: WhatsAppAgentState) -> str:
    """Extrae el último mensaje del usuario del state."""
    from langchain_core.messages import BaseMessage
    
    messages = state.get('messages', [])
    
    for msg_item in reversed(messages):
        # Manejar BaseMessage de LangChain
        if isinstance(msg_item, BaseMessage) and msg_item.type == 'human':
            content = msg_item.content
            return str(content) if isinstance(content, str) else str(content[0]) if content else ""
        # Manejar diccionarios planos
        elif isinstance(msg_item, dict) and msg_item.get('role') == 'user':
            return str(msg_item.get('content', ''))
    
    return ""


def _es_saludo_inicial(mensaje: str) -> bool:
    """
    Detecta si es un saludo sin más contexto.
    
    Ejemplos que detecta:
    - "Hola"
    - "Buenos días"
    - "Hola buenos días"
    - "Hey"
    
    NO detecta (porque llevan acción):
    - "Hola, necesito una cita"
    - "Buenos días doctor, tengo una pregunta"
    """
    SALUDOS = {
        'hola', 'buenos días', 'buenas tardes', 'buenas noches',
        'buen día', 'qué tal', 'hey', 'saludos', 'holi'
    }
    
    mensaje_lower = mensaje.lower().strip()
    palabras = mensaje_lower.split()
    
    # Es saludo si:
    # 1. Tiene 3 palabras o menos
    # 2. Contiene una palabra de saludo
    # 3. NO contiene palabras de acción (cita, necesito, quiero)
    
    if len(palabras) > 3:
        return False
    
    tiene_saludo = any(saludo in mensaje_lower for saludo in SALUDOS)
    
    PALABRAS_ACCION = {'cita', 'necesito', 'quiero', 'agendar', 'solicitar', 'pedir'}
    tiene_accion = any(accion in mensaje_lower for accion in PALABRAS_ACCION)
    
    return tiene_saludo and not tiene_accion


def _clasificar_doctor_rapido(mensaje: str, state: WhatsAppAgentState) -> str:
    """
    Clasificación RÁPIDA para doctores sin LLM.
    
    Detecta contexto médico vs personal con palabras clave inequívocas.
    Solo retorna 'requiere_llm' si el mensaje es genuinamente ambiguo.
    
    Returns:
        'medica', 'personal', o 'requiere_llm'
    """
    
    # Palabras clave INEQUÍVOCAS de contexto médico
    MEDICO_KEYWORDS = {
        'paciente', 'pacientes', 'consulta', 'cita médica', 
        'historial', 'diagnóstico', 'tratamiento',
        'mi consultorio', 'citas del día', 'agenda médica',
        'consultorio', 'expediente', 'receta'
    }
    
    # Palabras clave INEQUÍVOCAS de contexto personal
    PERSONAL_KEYWORDS = {
        'mi cumpleaños', 'mi aniversario', 'evento personal',
        'recordarme', 'mi agenda personal', 'trámite',
        'cita personal', 'reunión familiar', 'vacaciones',
        'banco', 'comprar', 'pagar', 'mi esposa', 'mi hijo'
    }
    
    mensaje_lower = mensaje.lower()
    
    # ========================================
    # Fase 1: Detección inequívoca (90% casos)
    # ========================================
    
    # Contexto médico claro
    if any(kw in mensaje_lower for kw in MEDICO_KEYWORDS):
        logger.info(f"      ✓ Clasificación rápida: MEDICA (keyword match)")
        return 'medica'
    
    # Contexto personal claro
    if any(kw in mensaje_lower for kw in PERSONAL_KEYWORDS):
        logger.info(f"      ✓ Clasificación rápida: PERSONAL (keyword match)")
        return 'personal'
    
    # ========================================
    # Fase 2: Análisis de contexto (5% casos)
    # ========================================
    
    # "agendar cita" o "mi cita" → puede ser médico o personal
    # Usar contexto de conversación previa si está disponible
    if any(palabra in mensaje_lower for palabra in ['cita', 'agendar', 'programar']):
        # Revisar contexto episódico para desambiguar
        contexto_previo = state.get('contexto_episodico', {})
        if isinstance(contexto_previo, dict):
            resumen_previo = str(contexto_previo.get('resumen', ''))
            
            if 'paciente' in resumen_previo.lower():
                logger.info(f"      ✓ Clasificación por contexto: MEDICA")
                return 'medica'
            elif 'personal' in resumen_previo.lower():
                logger.info(f"      ✓ Clasificación por contexto: PERSONAL")
                return 'personal'
    
    # ========================================
    # Fase 3: Casos ambiguos → LLM (5% casos)
    # ========================================
    logger.info(f"      ? Clasificación ambigua → requiere LLM")
    return 'requiere_llm'


def _es_comando_admin(mensaje: str) -> bool:
    """
    Detecta comandos administrativos específicos.
    
    Ejemplos:
    - "Reporte de cancelaciones"
    - "Estadísticas de la semana"
    - "Dashboard de doctores"
    - "Listar todos los pacientes"
    """
    ADMIN_KEYWORDS = {
        'reporte', 'estadísticas', 'estadisticas', 'dashboard',
        'métricas', 'metricas', 'balance de carga',
        'listar doctores', 'crear doctor', 'desactivar doctor',
        'cancelaciones', 'actividad', 'resumen administrativo'
    }
    
    mensaje_lower = mensaje.lower()
    return any(kw in mensaje_lower for kw in ADMIN_KEYWORDS)


# ==================== WRAPPER PARA LANGGRAPH ====================

def nodo_router_identidad_wrapper(state: WhatsAppAgentState) -> WhatsAppAgentState:
    """
    Wrapper para que el nodo funcione con LangGraph.
    
    LangGraph requiere que los nodos retornen el state actualizado.
    """
    resultado = nodo_router_identidad(state)
    
    # Actualizar state con resultados del routing
    state_actualizado = dict(state)  # Copiar state original
    state_actualizado.update(resultado)  # Agregar campos nuevos
    
    return cast(WhatsAppAgentState, state_actualizado)
