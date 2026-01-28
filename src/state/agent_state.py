"""
Estado del Agente de WhatsApp

Define la estructura de datos compartida que fluye a través del grafo.
"""

from typing import TypedDict, Optional, Annotated, Any, Dict, List
from langgraph.graph.message import add_messages
from langchain_core.messages import AnyMessage


class WhatsAppAgentState(TypedDict):
    """
    Estado compartido del agente que fluye a través de todos los nodos.
    
    Campos:
        messages: Historial de conversación
        user_id: Identificador único del usuario (número de teléfono)
        session_id: ID de la sesión actual
        es_admin: Indica si el usuario actual es administrador
        usuario_info: Diccionario con información completa del usuario desde BD
        usuario_registrado: True si ya existía, False si fue creado automáticamente
        contexto_episodico: Resúmenes previos recuperados de pgvector
        herramientas_seleccionadas: IDs de herramientas a ejecutar
        requiere_herramientas: Indica si se detectó intención de usar herramientas de calendario
        resumen_actual: Resumen generado de la conversación
        timestamp: Marca de tiempo de la interacción
    """
    # Conversación
    messages: Annotated[list[AnyMessage], add_messages]
    user_id: str  # Número de teléfono en formato internacional (+52664...)
    session_id: str
    
    # Identificación de Usuario (NUEVO)
    es_admin: bool  # True si es el administrador del sistema
    usuario_info: Dict[str, Any]  # Datos completos del usuario desde BD
    usuario_registrado: bool  # True si ya existía, False si fue auto-creado
    
    # Memoria Episódica (recuperada de pgvector)
    contexto_episodico: Optional[Dict[str, Any]]
    
    # Memoria Procedimental (consultada en PostgreSQL)
    herramientas_seleccionadas: List[str]
    
    # Control de flujo
    requiere_herramientas: bool  # True si se detectó intención de usar alguna de las 6 herramientas de calendario
    resumen_actual: Optional[str]
    sesion_expirada: bool  # True si han pasado >24h desde último mensaje
    
    # Resultado de último listado de eventos (para contexto en delete/update)
    ultimo_listado: Optional[List[Dict[str, Any]]]
    
    # Metadata
    timestamp: str
