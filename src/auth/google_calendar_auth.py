"""
Módulo de Autenticación para Google Calendar API

Gestiona el flujo OAuth2 para acceso a Google Calendar.
Busca credentials.json y genera/actualiza token.json.
"""

import os
import logging
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

# Scopes necesarios para Google Calendar
SCOPES = ['https://www.googleapis.com/auth/calendar']

# Rutas de archivos
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.json'


def get_credentials_path() -> Path:
    """Retorna la ruta absoluta al archivo credentials.json"""
    # Buscar en el directorio raíz del proyecto
    root_dir = Path(__file__).parent.parent.parent
    creds_path = root_dir / CREDENTIALS_FILE
    
    if not creds_path.exists():
        raise FileNotFoundError(
            f"❌ No se encontró {CREDENTIALS_FILE} en {root_dir}\n"
            "Descárgalo desde Google Cloud Console:\n"
            "https://console.cloud.google.com/apis/credentials"
        )
    
    return creds_path


def get_token_path() -> Path:
    """Retorna la ruta absoluta al archivo token.json"""
    root_dir = Path(__file__).parent.parent.parent
    return root_dir / TOKEN_FILE


def authenticate_google_calendar() -> Credentials:
    """
    Autentica con Google Calendar usando OAuth2
    
    Flujo:
    1. Busca token.json existente
    2. Si existe y es válido, lo usa
    3. Si expiró, lo refresca
    4. Si no existe, inicia flujo OAuth (abre navegador)
    5. Guarda el token para futuras ejecuciones
    
    Returns:
        Credentials: Credenciales autenticadas
        
    Raises:
        FileNotFoundError: Si no encuentra credentials.json
        Exception: Si falla la autenticación
    """
    creds = None
    token_path = get_token_path()
    
    # Paso 1: Verificar si existe token guardado
    if token_path.exists():
        logger.info("🔑 Token existente encontrado, validando...")
        try:
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        except Exception as e:
            logger.warning(f"⚠️  Error leyendo token: {e}")
            creds = None
    
    # Paso 2: Refrescar o crear credenciales
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Refrescar token expirado
            logger.info("🔄 Token expirado, refrescando...")
            try:
                creds.refresh(Request())
                logger.info("✅ Token refrescado exitosamente")
            except Exception as e:
                logger.error(f"❌ Error refrescando token: {e}")
                logger.info("🔓 Iniciando nuevo flujo de autenticación...")
                creds = None
        
        if not creds:
            # Iniciar flujo OAuth desde cero
            creds_path = get_credentials_path()
            logger.info("🔓 Iniciando flujo de autenticación OAuth2...")
            logger.info("   Se abrirá tu navegador para autorizar el acceso")
            
            flow = InstalledAppFlow.from_client_secrets_file(
                str(creds_path), 
                SCOPES
            )
            
            # Usar puerto específico para callback
            creds = flow.run_local_server(port=8090)
            
            logger.info("✅ Autenticación completada exitosamente")
        
        # Guardar credenciales para futuros usos
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
        logger.info(f"💾 Token guardado en: {token_path}")
    else:
        logger.info("✅ Token válido encontrado")
    
    return creds


def get_calendar_service():
    """
    Obtiene el servicio de Google Calendar autenticado
    
    Returns:
        googleapiclient.discovery.Resource: Servicio de Calendar API v3
        
    Example:
        service = get_calendar_service()
        events = service.events().list(calendarId='primary').execute()
    """
    try:
        creds = authenticate_google_calendar()
        service = build('calendar', 'v3', credentials=creds)
        logger.info("✅ Servicio de Google Calendar inicializado")
        return service
    except HttpError as error:
        logger.error(f"❌ Error de Google Calendar API: {error}")
        raise
    except Exception as e:
        logger.error(f"❌ Error inesperado: {e}")
        raise


def test_calendar_connection() -> bool:
    """
    Prueba la conexión con Google Calendar
    
    Returns:
        bool: True si la conexión es exitosa
    """
    try:
        logger.info("🧪 Probando conexión con Google Calendar...")
        service = get_calendar_service()
        
        # Hacer una llamada simple para verificar
        calendar_list = service.calendarList().list(maxResults=1).execute()
        
        logger.info(f"✅ Conexión exitosa! Calendarios disponibles: {len(calendar_list.get('items', []))}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en test de conexión: {e}")
        return False


if __name__ == "__main__":
    # Test de autenticación
    logging.basicConfig(level=logging.INFO)
    
    print("\n" + "="*70)
    print("🧪 TEST DE AUTENTICACIÓN DE GOOGLE CALENDAR")
    print("="*70 + "\n")
    
    try:
        # Intentar autenticar
        creds = authenticate_google_calendar()
        print("\n✅ Autenticación exitosa!")
        print(f"   Token válido: {creds.valid}")
        print(f"   Token expira: {creds.expiry}")
        
        # Probar conexión
        print("\n" + "-"*70)
        if test_calendar_connection():
            print("\n🎉 Google Calendar está listo para usar!")
        else:
            print("\n❌ Fallo en la prueba de conexión")
            
    except FileNotFoundError as e:
        print(f"\n❌ {e}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
