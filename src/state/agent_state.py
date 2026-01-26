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
        user_id: Identificador único del usuario
        session_id: ID de la sesión actual
        contexto_episodico: Resúmenes previos recuperados de pgvector
        herramientas_seleccionadas: IDs de herramientas a ejecutar
        cambio_de_tema: Indicador de cambio de tema detectado
        resumen_actual: Resumen generado de la conversación
        timestamp: Marca de tiempo de la interacción
    """
    # Conversación
    messages: Annotated[list[AnyMessage], add_messages]
    user_id: str
    session_id: str
    
    # Memoria Episódica (recuperada de pgvector)
    contexto_episodico: Optional[Dict[str, Any]]
    
    # Memoria Procedimental (consultada en PostgreSQL)
    herramientas_seleccionadas: List[str]
    
    # Control de flujo
    cambio_de_tema: bool
    resumen_actual: Optional[str]
    sesion_expirada: bool  # True si han pasado >24h desde último mensaje
    
    # Resultado de último listado de eventos (para contexto en delete/update)
    ultimo_listado: Optional[List[Dict[str, Any]]]
    
    # Metadata
    timestamp: str
