import logging
from langchain.tools import tool
from .utilities import ListGoogleCalendarEvents, CreateGoogleCalendarEvent, DeleteGoogleCalendarEvent, PostponeGoogleCalendarEvent
from .utilities import api_resource
from typing import TypedDict, cast
from langchain_openai import ChatOpenAI


from dotenv import load_dotenv
load_dotenv()  # this will load variables from .env into environment

import os
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
print("DEEPSEEK_API_KEY:", DEEPSEEK_API_KEY[:10] if DEEPSEEK_API_KEY else "None", "...")  # for debug

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
for handler in logging.root.handlers:
    if isinstance(handler, logging.StreamHandler):
        handler.stream.reconfigure(encoding='utf-8')
logger = logging.getLogger(__name__)

llm = ChatOpenAI(
    model="deepseek-chat",
    openai_api_key=DEEPSEEK_API_KEY,
    openai_api_base="https://api.deepseek.com/v1",
    temperature=0.7,
    timeout=20.0,  # ⚠️ Timeout de 20 segundos
    max_retries=0  # ✅ Reintentos los maneja LangGraph
)

@tool
def create_event_tool(start_datetime, end_datetime, summary, location="", description="", ):
    """
    Create a Google Calendar event.

    Args:
        start_datetime (str): Start datetime (YYYY-MM-DDTHH:MM:SS).
        end_datetime (str): End datetime (YYYY-MM-DDTHH:MM:SS).
        summary (str): Event title.
        location (str, optional): Event location.
        description (str, optional): Event description.
        timezone (str): Timezone.

    Returns:
        str: Confirmation message with event link.
    """
    timezone="America/Tijuana"
    try:
        tool = CreateGoogleCalendarEvent(api_resource)
        result = tool._run(
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            summary=summary,
            location=location,
            description=description,
            timezone=timezone
        )
        logger.info(f"Created event: {summary} from {start_datetime} to {end_datetime}")
        return result
    except Exception as e:
        logger.error(f"Error creating event: {e}")
        return f"❌ Error creating event: {e}"

@tool
def list_events_tool(start_datetime, end_datetime, max_results=10,):
    """
    List Google Calendar events in a date range.

    Args:
        start_datetime (str): Start datetime (YYYY-MM-DDTHH:MM:SS).
        end_datetime (str): End datetime (YYYY-MM-DDTHH:MM:SS).
        max_results (int): Maximum results to return.
        timezone (str): Timezone.

    Returns:
        list: List of event dicts (each includes event ID, summary, times, etc.).
    """
    timezone="America/Tijuana"
    try:
        tool = ListGoogleCalendarEvents(api_resource)
        events = tool._run(
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            max_results=max_results,
            timezone=timezone
        )
        logger.info(f"Listed {len(events)} events from {start_datetime} to {end_datetime}")
        return events
    except Exception as e:
        logger.error(f"Error listing events: {e}")
        return []

@tool
def postpone_event_tool(
    start_datetime: str,
    end_datetime: str,
    user_query: str,
    new_start_datetime: str,
    new_end_datetime: str,
) -> str:
    """
    Postpone one or more Google Calendar events based on a natural language user query.
    Uses an LLM to select the correct event(s) if the reference is ambiguous.

    Args:
        start_datetime (str): Start datetime for search window.
        end_datetime (str): End datetime for search window.
        user_query (str): The user's original query or meeting description.
        new_start_datetime (str): New start datetime for the event(s).
        new_end_datetime (str): New end datetime for the event(s).

    Returns:
        str: Confirmation message(s) or clarification prompt.
    """
    timezone = "America/Tijuana"
    args = {
        "start_datetime": start_datetime,
        "end_datetime": end_datetime
    }

    logger.info(f"Postpone tool called with args: {args}")
    events = list_events_tool.invoke(args)
    logger.info(f"Events found: {events}")
    if not events:
        return "No events found in the specified time window."

    # Prepare event options for the LLM
    event_options = [
        f"{idx+1}. {e.get('summary', 'No Title')} at {e.get('start')} (ID: {e.get('id')})"
        for idx, e in enumerate(events)
    ]
    options_text = "\n".join(event_options)

    # Compose LLM prompt
    prompt = (
        f"User query: '{user_query}'\n"
        f"Here are the events found:\n{options_text}\n"
        "Based on the user's query, which event ID(s) best match the intent for postponement? "
        "Just reply with the event ID(s) as a list."
    )

    # Call the LLM to select the best event(s)
    class output(TypedDict):
        event_id: list[str]  # Use the same key as in your delete_event_tool

    llm_response = cast(output, llm.with_structured_output(output).invoke(prompt))
    selected_event_ids = llm_response.get('event_id')
    logger.info(f"Selected event IDs for postponement: {selected_event_ids}")

    postponed_events = []

    for event_id in selected_event_ids:
        event = next((e for e in events if e.get('id') == event_id), None)
        if not event:
            msg = f"❌ Event ID `{event_id}` not found."
            logger.warning(msg)
            postponed_events.append(msg)
            continue

        try:
            tool = PostponeGoogleCalendarEvent(api_resource)
            result = tool._run(
                event_id=str(event.get('id')),
                new_start_datetime=new_start_datetime,
                new_end_datetime=new_end_datetime,
                timezone=timezone
            )
            msg = f"✅ Postponed event: **{event.get('summary', 'No Title')}** (`{event_id}`) → {result}"
            logger.info(msg)
            postponed_events.append(msg)
        except Exception as e:
            msg = f"❌ Error postponing event `{event_id}`: {e}"
            logger.error(msg)
            postponed_events.append(msg)

    return "\n".join(postponed_events)


@tool
def update_event_tool(
    event_id: str,
    new_start_datetime: str,
    new_end_datetime: str = None,
    new_summary: str = None,
    new_location: str = None,
    new_description: str = None,
) -> str:
    """
    Update (modify) a Google Calendar event's time, title, location, or description.
    
    Args:
        event_id: ID of the event to update
        new_start_datetime: New start time (YYYY-MM-DDTHH:MM:SS)
        new_end_datetime: New end time (optional, calculated from start if not provided)
        new_summary: New title (optional)
        new_location: New location (optional)
        new_description: New description (optional)
    
    Returns:
        Confirmation message with updated event details
    """
    timezone = "America/Tijuana"
    
    try:
        # Si no hay new_end_datetime, calcular 1 hora después del inicio
        if not new_end_datetime:
            import pendulum
            start_dt = pendulum.parse(new_start_datetime, tz=timezone)
            end_dt = start_dt.add(hours=1)
            new_end_datetime = end_dt.format('YYYY-MM-DDTHH:mm:ss')
        
        # Obtener el evento actual
        from .utilities import api_resource
        calendar_id = "92d85be088b1ee5c2c47b2bd38ad8631fe555ca46d2566f56089e8d17ed9de5d@group.calendar.google.com"
        
        event = api_resource.events().get(
            calendarId=calendar_id,
            eventId=event_id
        ).execute()
        
        # Actualizar campos según lo proporcionado
        if new_start_datetime:
            import pendulum
            start = pendulum.parse(new_start_datetime, tz=timezone).isoformat()
            event['start']['dateTime'] = start
            event['start']['timeZone'] = timezone
        
        if new_end_datetime:
            import pendulum
            end = pendulum.parse(new_end_datetime, tz=timezone).isoformat()
            event['end']['dateTime'] = end
            event['end']['timeZone'] = timezone
        
        if new_summary:
            event['summary'] = new_summary
        
        if new_location:
            event['location'] = new_location
        
        if new_description:
            event['description'] = new_description
        
        # Aplicar la actualización
        updated_event = api_resource.events().update(
            calendarId=calendar_id,
            eventId=event_id,
            body=event
        ).execute()
        
        summary = updated_event.get('summary', 'Sin título')
        start_time = updated_event['start'].get('dateTime', updated_event['start'].get('date'))
        link = updated_event.get('htmlLink', '')
        
        logger.info(f"Evento actualizado: {summary} → {start_time}")
        return f"✅ Evento actualizado: {summary} el {start_time}. {link}"
        
    except Exception as e:
        logger.error(f"Error actualizando evento {event_id}: {e}")
        return f"❌ Error actualizando evento: {e}"


@tool
def delete_event_tool(
    event_id: str = None,
    event_description: str = None,
    start_datetime: str = None,
    end_datetime: str = None,
) -> str:
    """
    Delete a Google Calendar event by ID or description.
    
    Args:
        event_id: Direct event ID to delete (preferred)
        event_description: Description to search for event (requires start_datetime/end_datetime)
        start_datetime: Start datetime for search window (if using event_description)
        end_datetime: End datetime for search window (if using event_description)
    
    Returns:
        Confirmation message or error
    """
    # Caso 1: Tenemos event_id directamente (path rápido)
    if event_id:
        try:
            tool = DeleteGoogleCalendarEvent(api_resource)
            result = tool._run(
                event_id=str(event_id),
                calendar_id=None
            )
            msg = f"✅ Evento eliminado (ID: {event_id}): {result}"
            logger.info(msg)
            return msg
        except Exception as e:
            msg = f"❌ Error eliminando evento `{event_id}`: {e}"
            logger.error(msg)
            return msg
    
    # Caso 2: Buscar evento por descripción (requiere ventana de tiempo)
    if not event_description or not start_datetime or not end_datetime:
        return "❌ Necesito el ID del evento o una descripción con rango de fechas para eliminarlo."
    
    args = {
        "start_datetime": start_datetime,
        "end_datetime": end_datetime
    }
    logger.info(f"Delete tool buscando evento: {event_description} en {args}")
    events = list_events_tool.invoke(args)
    
    if not events:
        return "❌ No se encontraron eventos en el rango especificado."

    # Preparar opciones para el LLM
    event_options = [
        f"{idx+1}. {e.get('summary', 'Sin título')} el {e.get('start')} (ID: {e.get('id')})"
        for idx, e in enumerate(events)
    ]
    options_text = "\n".join(event_options)

    # Prompt para el LLM
    prompt = (
        f"Descripción del usuario: '{event_description}'\n"
        f"Eventos encontrados:\n{options_text}\n"
        "¿Qué evento(s) coincide(n) mejor con la descripción del usuario? "
        "Responde SOLO con los event ID(s) como lista."
    )

    # Llamar al LLM para seleccionar el evento
    class output(TypedDict):
        event_id: list[str]

    llm_response = cast(output, llm.with_structured_output(output).invoke(prompt))
    selected_event_ids = llm_response.get('event_id')
    logger.info(f"Event IDs seleccionados para eliminación: {selected_event_ids}")

    # Eliminar cada evento seleccionado
    deleted_events = []
    for eid in selected_event_ids:
        event = next((e for e in events if e.get('id') == eid), None)
        if not event:
            msg = f"❌ Evento `{eid}` no encontrado."
            logger.warning(msg)
            deleted_events.append(msg)
            continue

        try:
            tool = DeleteGoogleCalendarEvent(api_resource)
            result = tool._run(event_id=str(eid), calendar_id=None)
            msg = f"✅ Eliminado: {event.get('summary', 'Sin título')} ({eid})"
            logger.info(msg)
            deleted_events.append(msg)
        except Exception as e:
            msg = f"❌ Error eliminando `{eid}`: {e}"
            logger.error(msg)
            deleted_events.append(msg)

    return "\n".join(deleted_events)

calendar_tools = [
    create_event_tool,
    list_events_tool,
    postpone_event_tool,
    update_event_tool,
    delete_event_tool
]

if __name__ == '__main__':
    logger.info("Tool file")
    result = postpone_event_tool.invoke({
        "start_datetime": "2025-07-07T17:00:00",        # Today, 5:00 PM
        "end_datetime": "2025-07-07T18:00:00",          # Today, 6:00 PM (assuming 1-hour meeting)
        "user_query": "postpone today's 5 pm meeting to tomorrow 10 am",
        "new_start_datetime": "2025-07-08T10:00:00",    # Tomorrow, 10:00 AM
        "new_end_datetime": "2025-07-08T11:00:00"       # Tomorrow, 11:00 AM
    })
    print(result)
