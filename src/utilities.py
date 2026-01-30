from google.oauth2 import service_account
from langchain_google_community import CalendarToolkit
from googleapiclient.discovery import build
from dateutil import parser, tz
from datetime import datetime
import pendulum
import os
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional, Type


#Path of service account JSON key
SERVICE_ACCOUNT_FILE = "pro-core-466508-u7-76f56aed8c8b.json"

#scope of calender access
SCOPES = ["https://www.googleapis.com/auth/calendar"]

#Test Calender ID (LangGraph Calendar)
CALENDAR_ID = "92d85be088b1ee5c2c47b2bd38ad8631fe555ca46d2566f56089e8d17ed9de5d@group.calendar.google.com"

# Inicialización lazy de credenciales de Google Calendar
_credentials = None
_api_resource = None
_toolkit = None


def _is_credentials_file_valid() -> bool:
    """Verifica si el archivo de credenciales existe y no está vacío."""
    return os.path.exists(SERVICE_ACCOUNT_FILE) and os.path.getsize(SERVICE_ACCOUNT_FILE) > 10


def get_credentials():
    """Obtiene las credenciales de Google Calendar de forma lazy."""
    global _credentials
    if _credentials is None:
        if not _is_credentials_file_valid():
            raise ValueError(
                f"Archivo de credenciales '{SERVICE_ACCOUNT_FILE}' no existe o está vacío. "
                "Por favor, proporcione un archivo de credenciales válido."
            )
        _credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
    return _credentials


def get_api_resource():
    """Obtiene el recurso de API de Google Calendar de forma lazy."""
    global _api_resource
    if _api_resource is None:
        _api_resource = build('calendar', 'v3', credentials=get_credentials())
    return _api_resource


def get_toolkit():
    """Obtiene el toolkit de Google Calendar de forma lazy."""
    global _toolkit
    if _toolkit is None:
        _toolkit = CalendarToolkit(api_resource=get_api_resource())
    return _toolkit


# Mantener compatibilidad con código existente que usa estas variables directamente
# Solo se inicializan si el archivo de credenciales es válido
if _is_credentials_file_valid():
    try:
        credentials = get_credentials()
        api_resource = get_api_resource()
        toolkit = get_toolkit()
    except Exception:
        credentials = None
        api_resource = None
        toolkit = None
else:
    credentials = None
    api_resource = None
    toolkit = None


class GoogleCalendarBaseTool:
    """Base class for Google Calendar tools using a service account."""
    api_resource = None

    def __init__(self, api_resource):
        self.api_resource = api_resource

    @classmethod
    def from_api_resource(cls, api_resource):
        return cls(api_resource=api_resource)


class GetEventsSchema(BaseModel):
    start_datetime: str = Field(..., description="Start datetime (YYYY-MM-DDTHH:MM:SS)")
    end_datetime: str = Field(..., description="End datetime (YYYY-MM-DDTHH:MM:SS)")
    max_results: int = Field(default=10, description="Max results to return")
    timezone: str = Field(default="America/Tijuana", description="Timezone (TZ database name)")

class ListGoogleCalendarEvents(GoogleCalendarBaseTool):
    def _parse_event(self, event, timezone):
        """
        Parsea un evento de Google Calendar manejando eventos de todo el día y eventos con hora
        """
        # Detectar si es evento de todo el día
        is_all_day = 'date' in event['start']  # Si tiene 'date' en vez de 'dateTime'
        
        if is_all_day:
            # Evento de todo el día
            start_date = event['start'].get('date')  # "2026-01-25"
            end_date = event['end'].get('date')      # "2026-01-26"
            
            event_parsed = {
                'start': start_date,
                'end': end_date,
                'is_all_day': True
            }
        else:
            # Evento con hora específica
            start = event['start'].get('dateTime')
            start = parser.parse(start).astimezone(tz.gettz(timezone)).strftime('%Y/%m/%d %H:%M:%S')
            end = event['end'].get('dateTime')
            end = parser.parse(end).astimezone(tz.gettz(timezone)).strftime('%Y/%m/%d %H:%M:%S')
            
            event_parsed = {
                'start': start,
                'end': end,
                'is_all_day': False
            }
        
        # Agregar campos comunes
        for field in ['summary', 'description', 'location', 'hangoutLink']:
            event_parsed[field] = event.get(field, None)
        event_parsed['id'] = event.get('id')
        
        return event_parsed


    def _run(self, start_datetime, end_datetime, max_results=10, timezone="America/Tijuana"):
        calendar_id = "92d85be088b1ee5c2c47b2bd38ad8631fe555ca46d2566f56089e8d17ed9de5d@group.calendar.google.com"
        events = []
        start = pendulum.parse(start_datetime, tz=timezone)
        start = start.isoformat()
        end = pendulum.parse(end_datetime, tz=timezone)
        end = end.isoformat()
        events_result = self.api_resource.events().list(
            calendarId=calendar_id,
            timeMin=start,
            timeMax=end,
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        cal_events = events_result.get('items', [])
        events.extend(cal_events)
        events = sorted(events, key=lambda x: x['start'].get('dateTime', x['start'].get('date')))
        return [self._parse_event(e, timezone) for e in events]
    


class CreateEventSchema(BaseModel):
    start_datetime: str = Field(..., description="Start datetime (YYYY-MM-DDTHH:MM:SS)")
    end_datetime: str = Field(..., description="End datetime (YYYY-MM-DDTHH:MM:SS)")
    summary: str = Field(..., description="Event title")
    location: Optional[str] = Field(default="", description="Event location")
    description: Optional[str] = Field(default="", description="Event description")
    timezone: str = Field(default="America/Tijuana", description="Timezone (TZ database name)")

class CreateGoogleCalendarEvent(GoogleCalendarBaseTool):
    def _run(self, start_datetime, end_datetime, summary, location="", description="", timezone="America/Tijuana"):
        calendar_id = "92d85be088b1ee5c2c47b2bd38ad8631fe555ca46d2566f56089e8d17ed9de5d@group.calendar.google.com"
        start = pendulum.parse(start_datetime, tz=timezone)
        start = start.isoformat()
        end = pendulum.parse(end_datetime, tz=timezone)
        end = end.isoformat()
        body = {
            'summary': summary,
            'start': {'dateTime': start},
            'end': {'dateTime': end}
        }
        if location:
            body['location'] = location
        if description:
            body['description'] = description
        event = self.api_resource.events().insert(calendarId=calendar_id, body=body).execute()
        return "Event created: " + event.get('htmlLink', 'Failed to create event')


class DeleteEventSchema(BaseModel):
    event_id: str = Field(..., description="The event ID to delete.")
    calendar_id: Optional[str] = Field(
        default=None, description="The calendar ID. Defaults to your test calendar."
    )

class DeleteGoogleCalendarEvent:
    """
    Delete an event from your Google Calendar.

    - Requires only the event ID.
    - Always uses your test calendar ID unless another is specified.
    """

    def __init__(self, api_resource):
        self.api_resource = api_resource
        self.calendar_id = "92d85be088b1ee5c2c47b2bd38ad8631fe555ca46d2566f56089e8d17ed9de5d@group.calendar.google.com"

    def _run(self, event_id, calendar_id=None):
        calendar_id = calendar_id or self.calendar_id
        try:
            self.api_resource.events().delete(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            return f"Event {event_id} deleted from calendar {calendar_id}."
        except Exception as e:
            return f"Failed to delete event: {e}"
        


class PostponeEventSchema(BaseModel):
    event_id: str = Field(..., description="The event ID to postpone.")
    new_start_datetime: str = Field(..., description="New start datetime (YYYY-MM-DDTHH:MM:SS)")
    new_end_datetime: str = Field(..., description="New end datetime (YYYY-MM-DDTHH:MM:SS)")
    timezone: str = Field(default="America/Tijuana", description="Timezone (TZ database name)")
    calendar_id: Optional[str] = Field(
        default=None, description="The calendar ID. Defaults to your test calendar."
    )

class PostponeGoogleCalendarEvent:
    """
    Postpone (reschedule) an event in your Google Calendar.

    - Requires event ID and new start/end datetimes.
    - Always uses your test calendar ID unless another is specified.
    """

    def __init__(self, api_resource):
        self.api_resource = api_resource
        self.calendar_id = "92d85be088b1ee5c2c47b2bd38ad8631fe555ca46d2566f56089e8d17ed9de5d@group.calendar.google.com"

    def _run(self, event_id, new_start_datetime, new_end_datetime, timezone="America/Tijuana", calendar_id=None):
        calendar_id = calendar_id or self.calendar_id
        try:
            # Get the existing event
            event = self.api_resource.events().get(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()

            # Format new times
            start = pendulum.parse(new_start_datetime, tz=timezone).isoformat()
            end = pendulum.parse(new_end_datetime, tz=timezone).isoformat()

            event['start']['dateTime'] = start
            event['end']['dateTime'] = end
            event['start']['timeZone'] = timezone
            event['end']['timeZone'] = timezone

            updated_event = self.api_resource.events().update(
                calendarId=calendar_id,
                eventId=event_id,
                body=event
            ).execute()

            return f"Event postponed: {updated_event.get('htmlLink', 'No link')}"
        except Exception as e:
            return f"Failed to postpone event: {e}"


class SearchEventSchema(BaseModel):
    """Schema para búsqueda de eventos por palabras clave."""
    start_datetime: str = Field(..., description="Start datetime (YYYY-MM-DDTHH:MM:SS)")
    end_datetime: str = Field(..., description="End datetime (YYYY-MM-DDTHH:MM:SS)")
    query: str = Field(..., description="Search keywords (e.g., patient name, event type)")
    max_results: int = Field(default=10, description="Max results to return")
    timezone: str = Field(default="America/Tijuana", description="Timezone (TZ database name)")


class SearchGoogleCalendarEvents(GoogleCalendarBaseTool):
    """
    Search events in Google Calendar by keywords.

    - Searches in event title and description.
    - Returns events matching the query within the specified time range.
    """

    def _parse_event(self, event, timezone):
        """
        Parsea un evento de Google Calendar manejando eventos de todo el día y eventos con hora.
        """
        is_all_day = 'date' in event['start']

        if is_all_day:
            event_parsed = {
                'start': event['start'].get('date'),
                'end': event['end'].get('date'),
                'is_all_day': True
            }
        else:
            start = event['start'].get('dateTime')
            start = parser.parse(start).astimezone(tz.gettz(timezone)).strftime('%Y/%m/%d %H:%M:%S')
            end = event['end'].get('dateTime')
            end = parser.parse(end).astimezone(tz.gettz(timezone)).strftime('%Y/%m/%d %H:%M:%S')

            event_parsed = {
                'start': start,
                'end': end,
                'is_all_day': False
            }

        for field in ['summary', 'description', 'location', 'hangoutLink']:
            event_parsed[field] = event.get(field, None)
        event_parsed['id'] = event.get('id')

        return event_parsed

    def _run(self, start_datetime, end_datetime, query, max_results=10, timezone="America/Tijuana"):
        """
        Busca eventos en Google Calendar por palabras clave.

        Args:
            start_datetime: Inicio del rango de búsqueda (YYYY-MM-DDTHH:MM:SS)
            end_datetime: Fin del rango de búsqueda (YYYY-MM-DDTHH:MM:SS)
            query: Palabras clave para buscar en título/descripción
            max_results: Máximo de resultados
            timezone: Zona horaria

        Returns:
            Lista de eventos que coinciden con la búsqueda
        """
        calendar_id = CALENDAR_ID

        start = pendulum.parse(start_datetime, tz=timezone)
        start = start.isoformat()
        end = pendulum.parse(end_datetime, tz=timezone)
        end = end.isoformat()

        events_result = self.api_resource.events().list(
            calendarId=calendar_id,
            timeMin=start,
            timeMax=end,
            q=query,  # Búsqueda por palabras clave
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        cal_events = events_result.get('items', [])
        events = sorted(cal_events, key=lambda x: x['start'].get('dateTime', x['start'].get('date')))

        return [self._parse_event(e, timezone) for e in events]


if __name__ == '__main__':
    print("All okay")
