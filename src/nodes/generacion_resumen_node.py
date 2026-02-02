"""
Nodo 6: Generación de Resúmenes (Auditoría)

Este nodo actúa como "auditor" de la sesión, transformando la conversación
cruda en una cápsula de conocimiento estructurado.

Responsabilidades:
- Extraer hechos, pendientes, perfil y estado
- Generar resumen ejecutivo (<100 palabras)
- Comportamiento especial para sesión expirada (retomar hilo)
- Incluir timestamp de Mexicali
- Preparar texto para Nodo 7 (persistencia pgvector)
"""

import logging
from typing import Dict, List, Any
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from src.utils.time_utils import get_current_time
import os
from dotenv import load_dotenv

# ✅ Imports para memoria semántica
from langgraph.store.base import BaseStore
from src.memory import update_semantic_memory
from langgraph.types import Command
from src.utils.logging_config import (
    log_separator,
    log_node_io
)

load_dotenv()

logger = logging.getLogger(__name__)

# LLM principal para auditoría
llm_primary = ChatOpenAI(
    model="deepseek-chat",
    temperature=0.2,
    max_tokens=120,
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1",
    timeout=10.0,  # ✅ Reducido de 15s a 10s
    max_retries=0
)

# Fallback: Claude Sonnet
llm_fallback = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    temperature=0.2,
    max_tokens=120,
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    timeout=10.0,  # ✅ Reducido de 15s a 10s
    max_retries=0
)

# Auditor con fallback automático
llm_auditor = llm_primary.with_fallbacks([llm_fallback])

# ==================== CONSTANTES ====================

# Estados conversacionales que requieren saltar resumen
ESTADOS_SIN_RESUMEN = [
    'esperando_confirmacion',
    'recolectando_datos',
    'procesando_pago'
]

# Categorías de resumen para clustering semántico
CATEGORIAS_RESUMEN = {
    'cita': ['agendar', 'cita', 'turno', 'horario', 'disponibilidad', 'reservar', 'consulta'],
    'sintoma': ['dolor', 'molestia', 'síntoma', 'malestar', 'fiebre', 'ardor', 'inflamación'],
    'recordatorio': ['recordatorio', 'confirmar', 'confirmó', 'asistir', 'llegará', 'vendrá'],
    'diagnostico': ['diagnóstico', 'resultado', 'examen', 'análisis', 'estudio', 'radiografía'],
    'tratamiento': ['medicamento', 'receta', 'tratamiento', 'indicaciones', 'dosis', 'pastilla'],
    'historial': ['historial', 'antecedentes', 'alergias', 'padecimiento', 'crónico'],
    'cancelacion': ['cancelar', 'canceló', 'reagendar', 'posponer', 'reprogramar'],
}


def clasificar_categoria(resumen: str) -> str:
    """
    Clasifica automáticamente la categoría del resumen basándose en palabras clave.
    
    Args:
        resumen: Texto del resumen a clasificar
        
    Returns:
        Categoría detectada o 'general' si no coincide ninguna
    """
    resumen_lower = resumen.lower()
    
    for categoria, palabras in CATEGORIAS_RESUMEN.items():
        for palabra in palabras:
            if palabra in resumen_lower:
                return categoria
    
    return 'general'


def extraer_fecha_evento(resumen: str) -> str:
    """
    Intenta extraer una fecha mencionada en el resumen.
    
    Args:
        resumen: Texto del resumen
        
    Returns:
        Fecha en formato YYYY-MM-DD o None
    """
    import re
    from datetime import datetime, timedelta
    
    resumen_lower = resumen.lower()
    
    # Patrones de fecha
    # "4 de febrero de 2025", "febrero 4, 2025"
    patron_fecha = r'(\d{1,2})\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+(?:de\s+)?(\d{4})'
    match = re.search(patron_fecha, resumen_lower)
    
    if match:
        meses = {
            'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
            'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
            'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
        }
        dia = int(match.group(1))
        mes = meses.get(match.group(2), 1)
        año = int(match.group(3))
        try:
            return datetime(año, mes, dia).strftime('%Y-%m-%d')
        except:
            pass
    
    # "mañana", "hoy"
    if 'mañana' in resumen_lower:
        return (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    if 'hoy' in resumen_lower:
        return datetime.now().strftime('%Y-%m-%d')
    
    return None


def extraer_mensajes_relevantes(messages: List[Any]) -> str:
    """
    Extrae y formatea los mensajes de la conversación excluyendo ruido.
    
    Args:
        messages: Lista de mensajes del state
        
    Returns:
        String con conversación formateada
    """
    conversacion = []
    
    for msg in messages:
        # Extraer contenido según tipo de mensaje
        if hasattr(msg, 'content'):
            contenido = msg.content
        elif isinstance(msg, dict) and 'content' in msg:
            contenido = msg['content']
        else:
            contenido = str(msg)
        
        # Extraer rol
        if hasattr(msg, 'role'):
            rol = msg.role
        elif isinstance(msg, dict) and 'role' in msg:
            rol = msg['role']
        elif hasattr(msg, '__class__'):
            rol = 'ai' if 'AI' in msg.__class__.__name__ else 'user'
        else:
            rol = 'desconocido'
        
        # Filtrar mensajes vacíos o muy cortos
        if contenido and len(contenido.strip()) > 2:
            conversacion.append(f"{rol.upper()}: {contenido}")
    
    return "\n".join(conversacion) if conversacion else ""


def construir_prompt_auditoria(
    conversacion: str,
    contexto_episodico: Any,
    sesion_expirada: bool
) -> str:
    """
    Construye el prompt de auditoría para el LLM según el contexto.
    
    Args:
        conversacion: Conversación formateada
        contexto_episodico: Memoria de conversaciones previas
        sesion_expirada: Si la sesión fue interrumpida por timeout
        
    Returns:
        Prompt estructurado para el auditor
    """
    timestamp = get_current_time().format('dddd, DD [de] MMMM [de] YYYY [a las] HH:mm', locale='es')
    
    # Extraer contexto previo si existe
    contexto_previo = ""
    if contexto_episodico and isinstance(contexto_episodico, dict):
        if 'resumen' in contexto_episodico:
            contexto_previo = f"\nCONTEXTO PREVIO:\n{contexto_episodico['resumen']}\n"
    
    # Instrucción especial para sesión expirada
    enfoque_especial = ""
    if sesion_expirada:
        enfoque_especial = """
⚠️ IMPORTANTE: Esta sesión fue interrumpida hace 24 horas por timeout.
Tu resumen debe permitir retomar la conversación EXACTAMENTE donde se quedó.
Prioriza:
- Estado específico de la tarea (completada/pendiente/interrumpida)
- Última petición del usuario que quedó sin resolver
- Contexto necesario para continuar sin repetir información
"""
    
    prompt = f"""Genera un resumen NARRATIVO de esta conversación médica.

FECHA: {timestamp}
{contexto_previo}
CONVERSACIÓN:
{conversacion}
{enfoque_especial}

INSTRUCCIONES:
1. Escribe en TERCERA PERSONA como si narraras lo que sucedió
2. Incluye: qué informó/preguntó el paciente, qué se le indicó/respondió
3. Si hay cita, incluye fecha y hora específica
4. Máximo 2-3 oraciones concisas

EJEMPLOS DE FORMATO CORRECTO:
- "El paciente informó que le dolía la uña del pie izquierdo y se le indicó que no usara calcetines hasta su cita del 4 de febrero de 2025"
- "Se envió recordatorio al paciente para su cita, quien confirmó que asistiría mañana 4 de febrero de 2025"
- "El paciente consultó sobre disponibilidad y se le agendó cita con Dr. García para el lunes 10 a las 3pm"

Respuesta en UNA línea, sin bullets ni markdown.
Si no hay info médica relevante: "Sin cambios médicos relevantes"

RESUMEN:"""
    
    return prompt


def nodo_generacion_resumen(state: Dict[str, Any], store: BaseStore) -> Command:
    """
    Nodo 6: Genera resumen ejecutivo de la sesión para memoria a largo plazo.
    
    MEJORAS APLICADAS:
    ✅ Command pattern con routing directo
    ✅ Detección de estado conversacional
    ✅ Timeout reducido (10s)
    ✅ Logging estructurado
    
    Returns:
        Command con update y goto
    """
    log_separator(logger, "NODO_6_GENERACION_RESUMEN", "INICIO")
    
    messages = state.get('messages', [])
    contexto_episodico = state.get('contexto_episodico')
    sesion_expirada = state.get('sesion_expirada', False)
    user_id = state.get('user_id', 'default_user')
    estado_conversacion = state.get('estado_conversacion', 'inicial')
    
    # Log del input
    input_data = f"messages: {len(messages)}\nsesion_expirada: {sesion_expirada}\nestado: {estado_conversacion}"
    log_node_io(logger, "INPUT", "NODO_6_RESUMEN", input_data)
    
    logger.info(f"    📋 Mensajes a resumir: {len(messages)}")
    logger.info(f"    {'⏰' if sesion_expirada else '✅'} Modo: {'RECUPERACIÓN' if sesion_expirada else 'NORMAL'}")
    logger.info(f"    🔄 Estado: {estado_conversacion}")
    
    # ✅ NUEVA VALIDACIÓN: Detectar estado conversacional
    if estado_conversacion in ESTADOS_SIN_RESUMEN:
        logger.info(f"   🔄 Estado {estado_conversacion} - Saltando generación de resumen")
        return Command(
            update={'resumen_actual': "Conversación en progreso"},
            goto="persistencia_episodica"
        )
    
    # Validar mensajes suficientes
    if len(messages) < 2:
        logger.info("    ⚠️  Pocos mensajes para generar resumen")
        return Command(
            update={'resumen_actual': "Sin cambios relevantes"},
            goto="persistencia_episodica"
        )
    
    # Extraer conversación
    conversacion = extraer_mensajes_relevantes(messages)
    
    if not conversacion or len(conversacion.strip()) < 10:
        logger.info("    ⚠️  No hay contenido relevante")
        return Command(
            update={'resumen_actual': "Sin cambios relevantes"},
            goto="persistencia_episodica"
        )
    
    logger.info(f"    📊 Caracteres a auditar: {len(conversacion)}")
    
    # Construir prompt
    prompt = construir_prompt_auditoria(
        conversacion=conversacion,
        contexto_episodico=contexto_episodico,
        sesion_expirada=sesion_expirada
    )
    
    try:
        # Invocar LLM
        logger.info("    🤖 Invocando auditor LLM...")
        respuesta = llm_auditor.invoke(prompt)
        resumen = respuesta.content.strip()
        
        # Timestamp
        timestamp = get_current_time().format('DD/MM/YYYY HH:mm', locale='es')
        resumen_con_fecha = f"[{timestamp}] {resumen}"
        
        logger.info(f"    ✅ Resumen: '{resumen[:80]}...'")
        logger.info(f"    📊 Longitud: {len(resumen)} caracteres")
        
        # Actualizar preferencias
        try:
            logger.info("    🧠 Actualizando preferencias...")
            update_semantic_memory(
                state=state,
                store=store,
                user_id=user_id,
                llm=llm_auditor
            )
            logger.info("    ✅ Preferencias procesadas")
        except Exception as pref_error:
            logger.error(f"    ❌ Error preferencias: {pref_error}")
        
        # ✅ Clasificar categoría automáticamente
        categoria = clasificar_categoria(resumen)
        fecha_evento = extraer_fecha_evento(resumen)
        
        logger.info(f"    🏷️  Categoría: {categoria}")
        if fecha_evento:
            logger.info(f"    📅 Fecha evento: {fecha_evento}")
        
        # Log de output
        output_data = f"resumen_chars: {len(resumen)} | categoria: {categoria}"
        log_node_io(logger, "OUTPUT", "NODO_6_RESUMEN", output_data)
        log_separator(logger, "NODO_6_GENERACION_RESUMEN", "FIN")
        
        # ✅ Retornar Command con metadata adicional
        return Command(
            update={
                'resumen_actual': resumen_con_fecha,
                'resumen_categoria': categoria,
                'resumen_fecha_evento': fecha_evento
            },
            goto="persistencia_episodica"
        )
        
    except Exception as e:
        logger.error(f"    ❌ Error generando resumen: {e}")
        
        # Fallback
        timestamp = get_current_time().format('DD/MM/YYYY HH:mm', locale='es')
        resumen_fallback = f"[{timestamp}] Conversación con {len(messages)} mensajes."
        
        log_separator(logger, "NODO_6_GENERACION_RESUMEN", "FIN")
        
        return Command(
            update={'resumen_actual': resumen_fallback},
            goto="persistencia_episodica"
        )


def nodo_generacion_resumen_wrapper(state: Dict[str, Any], store: BaseStore) -> Command:
    """Wrapper para LangGraph - retorna Command directamente."""
    return nodo_generacion_resumen(state, store)


if __name__ == "__main__":
    """
    Test standalone del nodo de auditoría.
    """
    print("\n🧪 Test del Nodo 6: Generación de Resúmenes\n")
    
    # Test 1: Conversación normal con agendamiento
    print("Test 1: Conversación con agendamiento")
    state_test1 = {
        'messages': [
            {'role': 'user', 'content': 'Necesito agendar una reunión para mañana'},
            {'role': 'ai', 'content': '¿A qué hora te gustaría agendar?'},
            {'role': 'user', 'content': 'A las 3 de la tarde'},
            {'role': 'ai', 'content': 'Perfecto, agendé tu reunión para mañana a las 15:00'}
        ],
        'user_id': 'test_user',
        'session_id': 'session_test1',
        'contexto_episodico': None,
        'sesion_expirada': False
    }
    
    resultado1 = nodo_generacion_resumen(state_test1)
    print(f"✅ Resumen: {resultado1['resumen_actual']}\n")
    
    # Test 2: Sesión expirada con tarea pendiente
    print("Test 2: Sesión expirada (recuperación)")
    state_test2 = {
        'messages': [
            {'role': 'user', 'content': 'Ponme una cita para el miércoles pero déjame confirmar el lugar'},
            {'role': 'ai', 'content': 'Ok, ¿a qué hora?'},
            {'role': 'user', 'content': 'A las 10 am'}
        ],
        'user_id': 'test_user',
        'session_id': 'session_test2',
        'contexto_episodico': {
            'resumen': 'Usuario prefiere reuniones por la mañana'
        },
        'sesion_expirada': True
    }
    
    resultado2 = nodo_generacion_resumen(state_test2)
    print(f"✅ Resumen: {resultado2['resumen_actual']}\n")
    
    # Test 3: Conversación sin contenido relevante
    print("Test 3: Sin contenido relevante")
    state_test3 = {
        'messages': [
            {'role': 'user', 'content': 'Hola'},
            {'role': 'ai', 'content': '¡Hola! ¿En qué puedo ayudarte?'}
        ],
        'user_id': 'test_user',
        'session_id': 'session_test3',
        'contexto_episodico': None,
        'sesion_expirada': False
    }
    
    resultado3 = nodo_generacion_resumen(state_test3)
    print(f"✅ Resumen: {resultado3['resumen_actual']}\n")
    
    print("🎉 Tests completados")
