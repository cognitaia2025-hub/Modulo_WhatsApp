"""
Test de Google Calendar - Crear evento REAL

Este test crea un evento VISIBLE en el Google Calendar configurado
para verificar que la integración funciona correctamente.
"""

import pytest
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from google.oauth2 import service_account

# Configuración
SERVICE_ACCOUNT_FILE = "pro-core-466508-u7-76f56aed8c8b.json"
SCOPES = ["https://www.googleapis.com/auth/calendar"]
CALENDAR_ID = "92d85be088b1ee5c2c47b2bd38ad8631fe555ca46d2566f56089e8d17ed9de5d@group.calendar.google.com"


def crear_servicio_calendar():
    """Crea el servicio de Google Calendar."""
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return build('calendar', 'v3', credentials=credentials)


class TestGoogleCalendarReal:
    """Tests de integración real con Google Calendar."""

    def test_crear_evento_prueba(self):
        """
        Test: Crea un evento REAL en Google Calendar.
        
        Este evento será VISIBLE en tu calendario para confirmar
        que el sistema funciona correctamente.
        """
        service = crear_servicio_calendar()
        
        # Crear evento para mañana a las 10am
        manana = datetime.now() + timedelta(days=1)
        inicio = manana.replace(hour=10, minute=0, second=0, microsecond=0)
        fin = inicio + timedelta(hours=1)
        
        evento = {
            'summary': '✅ TEST - Sistema de Agendamiento Funciona',
            'description': (
                'Este evento fue creado automáticamente por el sistema de tests.\n\n'
                f'Fecha de creación: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n'
                'Sistema: Módulo WhatsApp - Agente de Citas Médicas\n\n'
                'Si ves este evento, significa que la integración con Google Calendar '
                'está funcionando correctamente. 🎉'
            ),
            'start': {
                'dateTime': inicio.isoformat(),
                'timeZone': 'America/Tijuana',
            },
            'end': {
                'dateTime': fin.isoformat(),
                'timeZone': 'America/Tijuana',
            },
            'colorId': '10',  # Verde
        }
        
        # Crear el evento
        evento_creado = service.events().insert(
            calendarId=CALENDAR_ID,
            body=evento
        ).execute()
        
        event_id = evento_creado.get('id')
        event_link = evento_creado.get('htmlLink')
        
        print(f"\n{'='*60}")
        print(f"✅ EVENTO CREADO EXITOSAMENTE EN GOOGLE CALENDAR")
        print(f"{'='*60}")
        print(f"📅 Título: {evento['summary']}")
        print(f"📆 Fecha: {inicio.strftime('%Y-%m-%d')}")
        print(f"⏰ Hora: {inicio.strftime('%H:%M')} - {fin.strftime('%H:%M')}")
        print(f"🔗 ID: {event_id}")
        print(f"🌐 Link: {event_link}")
        print(f"{'='*60}\n")
        
        # Verificar que se creó correctamente
        assert event_id is not None
        assert evento_creado.get('summary') == evento['summary']

    def test_listar_eventos_proximos(self):
        """
        Test: Lista los eventos próximos del calendario.
        """
        service = crear_servicio_calendar()
        
        ahora = datetime.utcnow().isoformat() + 'Z'
        
        eventos_result = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=ahora,
            maxResults=10,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        eventos = eventos_result.get('items', [])
        
        print(f"\n{'='*60}")
        print(f"📅 EVENTOS PRÓXIMOS EN EL CALENDARIO")
        print(f"{'='*60}")
        
        if not eventos:
            print("No hay eventos próximos.")
        else:
            for evento in eventos:
                start = evento['start'].get('dateTime', evento['start'].get('date'))
                print(f"• {start}: {evento['summary']}")
        
        print(f"{'='*60}\n")
        
        # El test pasa si no hay errores al listar
        assert isinstance(eventos, list)


if __name__ == "__main__":
    # Ejecutar directamente
    test = TestGoogleCalendarReal()
    test.test_crear_evento_prueba()
    test.test_listar_eventos_proximos()
