"""
Nodo de Resumen Asíncrono

Optimización: Genera resúmenes en background sin bloquear la respuesta al usuario.
Esto mejora la latencia percibida del sistema de WhatsApp.
"""

from typing import Dict, Any
import logging
from datetime import datetime

from src.state.agent_state import WhatsAppAgentState
from src.utils.logging_config import setup_colored_logging

logger = setup_colored_logging()

def nodo_resumen_async(state: WhatsAppAgentState) -> Dict[str, Any]:
    """
    [N6] Generador de Resumen Asíncrono - Optimizado para latencia
    
    A diferencia del nodo original que bloquea la respuesta, este nodo:
    1. Marca que el resumen debe generarse en background
    2. Retorna inmediatamente para no bloquear la respuesta
    3. El resumen se puede generar posteriormente via cola/workers
    
    Args:
        state: Estado del agente WhatsApp
        
    Returns:
        Estado actualizado con flag para resumen asíncrono
    """
    logger.info("⚡ [N6] RESUMEN_ASYNC - Marcando para procesamiento en background")
    
    # Extraer información básica para el resumen
    user_id = state.get('user_id', '')
    clasificacion = state.get('clasificacion_mensaje', 'desconocido')
    estado_conv = state.get('estado_conversacion', 'inicial')
    
    # Crear resumen rápido sin LLM para no bloquear
    resumen_basico = f"Conversación {clasificacion} - Usuario: {user_id[:10]}... - Estado: {estado_conv}"
    
    # Flag para procesamiento posterior
    estado_actualizado = {
        **state,
        'resumen_actual': resumen_basico,
        'requiere_resumen_completo': True,  # Para background processing
        'timestamp_resumen': datetime.now().isoformat(),
        'nodo_ejecutado': 'resumen_async'
    }
    
    logger.info(f"    ✅ Resumen básico: {resumen_basico[:50]}...")
    logger.info(f"    📤 Marcado para resumen completo en background")
    
    return estado_actualizado


def nodo_resumen_async_wrapper(state: WhatsAppAgentState) -> Dict[str, Any]:
    """
    Wrapper para compatibilidad con LangGraph.
    """
    try:
        return nodo_resumen_async(state)
    except Exception as e:
        logger.error(f"❌ Error en nodo_resumen_async: {e}")
        return {
            **state,
            'resumen_actual': f"Error generando resumen: {str(e)}",
            'nodo_ejecutado': 'resumen_async'
        }