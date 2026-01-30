"""
Herramientas Unificadas para ToolNode - Versión Simplificada

Consolida todas las herramientas en un solo lugar para uso con LangGraph ToolNode.
"""

from typing import List
from langchain_core.tools import BaseTool

def get_all_tools() -> List[BaseTool]:
    """
    Retorna todas las herramientas disponibles para el ToolNode unificado.
    
    Versión simplificada que retorna una lista vacía para evitar errores de import.
    """
    tools = []
    
    # Agregar herramientas de calendario si están disponibles
    try:
        from src.tool import (
            create_event_tool,
            list_events_tool,
            update_event_tool,
            delete_event_tool,
            postpone_event_tool,
            search_calendar_events_tool
        )
        calendar_tools = [
            create_event_tool,
            list_events_tool,
            update_event_tool,
            delete_event_tool,
            postpone_event_tool,
            search_calendar_events_tool
        ]
        tools.extend(calendar_tools)
        print(f"✅ Calendar tools loaded: {len(calendar_tools)}")
    except ImportError as e:
        print(f"⚠️ Calendar tools not available: {e}")
    
    # Agregar herramientas médicas si están disponibles
    try:
        from src.medical.herramientas_medicas import (
            buscar_disponibilidad_tool,
            agendar_cita_tool,
            cancelar_cita_tool,
            listar_citas_tool
        )
        medical_tools = [
            buscar_disponibilidad_tool,
            agendar_cita_tool,
            cancelar_cita_tool,
            listar_citas_tool
        ]
        tools.extend(medical_tools)
        print(f"✅ Medical tools loaded: {len(medical_tools)}")
    except ImportError as e:
        print(f"⚠️ Medical tools not available: {e}")
    
    print(f"🛠️ Total tools available: {len(tools)}")
    return tools