"""
Herramientas Unificadas para ToolNode

Consolida todas las herramientas en un solo lugar para uso con LangGraph ToolNode.
Esto elimina la redundancia de múltiples nodos de ejecución.
"""

from typing import List
from langchain_core.tools import BaseTool

# Importar todas las herramientas disponibles
from src.tools.calendar_tools import (
    ListGoogleCalendarEvents,
    CreateGoogleCalendarEvent,
    DeleteGoogleCalendarEvent,
    PostponeGoogleCalendarEvent
)

from src.tools.medical_tools import (
    CreateCitaMedicaTool,
    ListCitasMedicasTool
)

def get_all_tools() -> List[BaseTool]:
    """
    Retorna todas las herramientas disponibles para el ToolNode unificado.
    
    Benefits:
    - Un solo punto de configuración
    - Eliminación de nodos de ejecución redundantes
    - El LLM decide qué herramienta usar basándose en el contexto
    - Mejor manejo de errores centralizado
    
    Returns:
        Lista de todas las herramientas disponibles
    """
    tools = []
    
    # Herramientas de Google Calendar (personales)
    try:
        tools.extend([
            ListGoogleCalendarEvents(),
            CreateGoogleCalendarEvent(),
            DeleteGoogleCalendarEvent(),
            PostponeGoogleCalendarEvent()
        ])
    except Exception as e:
        # En caso de error con Google Calendar, continuar con herramientas médicas
        print(f"⚠️ Google Calendar tools not available: {e}")
    
    # Herramientas médicas (base de datos)
    try:
        tools.extend([
            CreateCitaMedicaTool(),
            ListCitasMedicasTool()
        ])
    except Exception as e:
        print(f"⚠️ Medical tools not available: {e}")
    
    print(f"✅ Loaded {len(tools)} tools for unified ToolNode")
    
    return tools


def get_calendar_tools() -> List[BaseTool]:
    """
    Retorna solo herramientas de Google Calendar.
    Para uso específico cuando se sabe que solo se necesitan estas.
    """
    try:
        return [
            ListGoogleCalendarEvents(),
            CreateGoogleCalendarEvent(),
            DeleteGoogleCalendarEvent(),
            PostponeGoogleCalendarEvent()
        ]
    except Exception as e:
        print(f"⚠️ Google Calendar tools not available: {e}")
        return []


def get_medical_tools() -> List[BaseTool]:
    """
    Retorna solo herramientas médicas.
    Para uso específico cuando se sabe que solo se necesitan estas.
    """
    try:
        return [
            CreateCitaMedicaTool(),
            ListCitasMedicasTool()
        ]
    except Exception as e:
        print(f"⚠️ Medical tools not available: {e}")
        return []