"""
Fixtures compartidas para tests de integración real.

Provee conexiones a BD, estados iniciales, y utilidades comunes.
"""

import os
import sys
import pytest
from datetime import datetime, timedelta
from typing import Dict, Any, Generator
from pathlib import Path
from unittest.mock import patch, MagicMock

import psycopg
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

# Agregar el directorio raíz al path
ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Cargar variables de entorno
load_dotenv(ROOT_DIR / ".env")

# Importar módulos del proyecto
from src.state.agent_state import WhatsAppAgentState


# ============================================================================
# CONFIGURACIÓN
# ============================================================================

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:password123@localhost:5434/agente_whatsapp")
GOOGLE_CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "primary")

# Teléfonos de prueba (deben existir en seed data)
TEST_PACIENTE_PHONE = "+526649876543"
TEST_DOCTOR_PHONE = "+526641111111"  # Dr. Santiago
TEST_ADMIN_PHONE = "+526641234567"
TEST_NUEVO_PHONE = "+526649999999"  # Usuario que no existe


# ============================================================================
# FIXTURES DE BASE DE DATOS
# ============================================================================

@pytest.fixture(scope="session")
def db_url() -> str:
    """URL de conexión a la base de datos."""
    return DATABASE_URL


@pytest.fixture(scope="function")
def db_connection(db_url: str) -> Generator[psycopg.Connection, None, None]:
    """Conexión a PostgreSQL para cada test."""
    conn = psycopg.connect(db_url)
    yield conn
    conn.close()


@pytest.fixture(scope="session")
def setup_test_data(db_url: str) -> None:
    """
    Asegura que existan datos de prueba en la BD.
    Se ejecuta una vez por sesión de tests.
    """
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            # Verificar si hay datos seed
            cur.execute("SELECT COUNT(*) FROM usuarios")
            count = cur.fetchone()[0]
            
            if count == 0:
                pytest.fail(
                    "Base de datos vacía. Ejecuta primero:\n"
                    "cd sql && python init_database_consolidated.py"
                )
            
            # Verificar doctores
            cur.execute("SELECT COUNT(*) FROM doctores")
            doctor_count = cur.fetchone()[0]
            
            if doctor_count == 0:
                pytest.fail(
                    "No hay doctores en la BD. Ejecuta seed_initial_data.sql"
                )


# ============================================================================
# FIXTURES DE ESTADO INICIAL
# ============================================================================

def crear_estado_base(
    user_id: str,
    mensaje: str,
    sender_name: str = "Test User"
) -> WhatsAppAgentState:
    """
    Crea un estado base para tests.
    
    Args:
        user_id: Número de teléfono del usuario
        mensaje: Mensaje del usuario
        sender_name: Nombre del remitente
    
    Returns:
        Estado inicial del agente
    """
    return WhatsAppAgentState(
        messages=[HumanMessage(content=mensaje)],
        user_id=user_id,
        session_id=f"test_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        es_admin=False,
        usuario_info={},
        usuario_registrado=False,
        tipo_usuario="",
        doctor_id=None,
        paciente_id=None,
        contexto_episodico=None,
        herramientas_seleccionadas=[],
        requiere_herramientas=False,
        resumen_actual=None,
        sesion_expirada=False,
        ultimo_listado=None,
        clasificacion_mensaje=None,
        confianza_clasificacion=None,
        modelo_clasificacion_usado=None,
        tiempo_clasificacion_ms=None,
        contexto_medico=None,
        estado_conversacion="inicial",
        slots_disponibles=[],
        paciente_nombre_temporal=None,
        timestamp=datetime.now().isoformat()
    )


@pytest.fixture
def estado_paciente() -> WhatsAppAgentState:
    """Estado inicial para test de paciente existente."""
    return crear_estado_base(
        user_id=TEST_PACIENTE_PHONE,
        mensaje="Hola, necesito agendar una cita para mañana",
        sender_name="Juan Pérez"
    )


@pytest.fixture
def estado_doctor() -> WhatsAppAgentState:
    """Estado inicial para test de doctor."""
    return crear_estado_base(
        user_id=TEST_DOCTOR_PHONE,
        mensaje="¿Cuántas citas tengo hoy?",
        sender_name="Dr. Santiago Ornelas"
    )


@pytest.fixture
def estado_admin() -> WhatsAppAgentState:
    """Estado inicial para test de admin."""
    return crear_estado_base(
        user_id=TEST_ADMIN_PHONE,
        mensaje="Dame un reporte de las citas de esta semana",
        sender_name="Administrador"
    )


@pytest.fixture
def estado_usuario_nuevo() -> WhatsAppAgentState:
    """Estado inicial para usuario que no existe (auto-registro)."""
    return crear_estado_base(
        user_id=TEST_NUEVO_PHONE,
        mensaje="Hola, soy nuevo paciente",
        sender_name="Nuevo Usuario"
    )


@pytest.fixture
def estado_calendario_personal() -> WhatsAppAgentState:
    """Estado para prueba de calendario personal."""
    return crear_estado_base(
        user_id=TEST_PACIENTE_PHONE,
        mensaje="Crea un evento llamado 'Reunión de trabajo' mañana a las 3pm",
        sender_name="Juan Pérez"
    )


@pytest.fixture
def estado_chat_casual() -> WhatsAppAgentState:
    """Estado para prueba de chat casual (sin herramientas)."""
    return crear_estado_base(
        user_id=TEST_PACIENTE_PHONE,
        mensaje="Hola, ¿cómo estás?",
        sender_name="Juan Pérez"
    )


@pytest.fixture
def estado_consulta_medica() -> WhatsAppAgentState:
    """Estado para consulta médica (doctor)."""
    return crear_estado_base(
        user_id=TEST_DOCTOR_PHONE,
        mensaje="Buscar historial del paciente Juan Pérez",
        sender_name="Dr. Santiago"
    )


@pytest.fixture
def estado_solicitud_cita() -> WhatsAppAgentState:
    """Estado para solicitud de cita (paciente)."""
    return crear_estado_base(
        user_id=TEST_PACIENTE_PHONE,
        mensaje="Necesito una cita médica para la próxima semana",
        sender_name="Juan Pérez"
    )


# ============================================================================
# FIXTURES DE GOOGLE CALENDAR
# ============================================================================

@pytest.fixture(scope="session")
def google_calendar_service():
    """
    Cliente de Google Calendar API para verificar eventos.
    Usa las credenciales del proyecto.
    """
    try:
        from src.utilities import build_calendar_service
        service = build_calendar_service()
        return service
    except Exception as e:
        pytest.skip(f"Google Calendar no disponible: {e}")


@pytest.fixture
def cleanup_test_events(google_calendar_service):
    """
    Fixture para limpiar eventos de prueba después del test.
    Elimina eventos con '[TEST]' en el título.
    """
    created_events = []
    
    yield created_events
    
    # Limpiar eventos creados
    if google_calendar_service and created_events:
        for event_id in created_events:
            try:
                google_calendar_service.events().delete(
                    calendarId=GOOGLE_CALENDAR_ID,
                    eventId=event_id
                ).execute()
                print(f"🧹 Evento de prueba eliminado: {event_id}")
            except Exception as e:
                print(f"⚠️ No se pudo eliminar evento {event_id}: {e}")


# ============================================================================
# FIXTURES DE NODOS
# ============================================================================

@pytest.fixture
def nodo_identificacion():
    """Importa el nodo de identificación."""
    from src.nodes.identificacion_usuario_node import nodo_identificacion_usuario_wrapper
    return nodo_identificacion_usuario_wrapper


@pytest.fixture
def nodo_cache():
    """Importa el nodo de caché."""
    from src.graph_whatsapp_etapa8 import nodo_cache_sesion
    return nodo_cache_sesion


@pytest.fixture
def nodo_clasificacion():
    """Importa el nodo de clasificación (usa LLM)."""
    from src.nodes.filtrado_inteligente_node import nodo_filtrado_inteligente_wrapper
    return nodo_filtrado_inteligente_wrapper


@pytest.fixture
def nodo_recuperacion_episodica():
    """Importa el nodo de recuperación episódica."""
    from src.nodes.recuperacion_episodica_node import nodo_recuperacion_episodica_wrapper
    return nodo_recuperacion_episodica_wrapper


@pytest.fixture
def nodo_recuperacion_medica():
    """Importa el nodo de recuperación médica."""
    from src.nodes.recuperacion_medica_node import nodo_recuperacion_medica_wrapper
    return nodo_recuperacion_medica_wrapper


@pytest.fixture
def nodo_seleccion():
    """Importa el nodo de selección de herramientas (usa LLM)."""
    from src.nodes.seleccion_herramientas_node import nodo_seleccion_herramientas_wrapper
    return nodo_seleccion_herramientas_wrapper


@pytest.fixture
def nodo_ejecucion_personal():
    """Importa el nodo de ejecución personal."""
    from src.nodes.ejecucion_herramientas_node import nodo_ejecucion_herramientas_wrapper
    return nodo_ejecucion_herramientas_wrapper


@pytest.fixture
def nodo_ejecucion_medica():
    """Importa el nodo de ejecución médica."""
    from src.nodes.ejecucion_medica_node import nodo_ejecucion_medica_wrapper
    return nodo_ejecucion_medica_wrapper


@pytest.fixture
def nodo_recepcionista():
    """Importa el nodo recepcionista (usa LLM)."""
    from src.nodes.recepcionista_node import nodo_recepcionista_wrapper
    return nodo_recepcionista_wrapper


@pytest.fixture
def nodo_generacion():
    """Importa el nodo de generación (usa LLM)."""
    from src.nodes.generacion_resumen_node import nodo_generacion_resumen_wrapper
    return nodo_generacion_resumen_wrapper


@pytest.fixture
def nodo_persistencia():
    """Importa el nodo de persistencia."""
    from src.nodes.persistencia_episodica_node import nodo_persistencia_episodica_wrapper
    return nodo_persistencia_episodica_wrapper


@pytest.fixture
def nodo_sincronizacion():
    """Importa el nodo de sincronización."""
    from src.nodes.sincronizador_hibrido_node import nodo_sincronizador_hibrido_wrapper
    return nodo_sincronizador_hibrido_wrapper


# ============================================================================
# FIXTURES DE GRAFO COMPLETO
# ============================================================================

@pytest.fixture
def grafo_completo():
    """
    Crea el grafo completo compilado.
    Útil para tests end-to-end.
    """
    from src.graph_whatsapp_etapa8 import crear_grafo_whatsapp
    return crear_grafo_whatsapp()


# ============================================================================
# UTILIDADES DE VALIDACIÓN
# ============================================================================

def validar_estado_post_identificacion(state: WhatsAppAgentState) -> None:
    """Valida que el estado sea correcto después del nodo de identificación."""
    assert state.get("user_id"), "user_id debe estar presente"
    assert state.get("tipo_usuario") in ["personal", "doctor", "paciente_externo", "admin"], \
        f"tipo_usuario inválido: {state.get('tipo_usuario')}"
    assert isinstance(state.get("es_admin"), bool), "es_admin debe ser booleano"
    assert isinstance(state.get("usuario_info"), dict), "usuario_info debe ser dict"


def validar_estado_post_clasificacion(state: WhatsAppAgentState) -> None:
    """Valida que el estado sea correcto después del nodo de clasificación."""
    clasificaciones_validas = ["personal", "medica", "solicitud_cita", "chat_casual", "consulta"]
    clasificacion = state.get("clasificacion") or state.get("clasificacion_mensaje")
    assert clasificacion in clasificaciones_validas, \
        f"clasificacion inválida: {clasificacion}"


def validar_respuesta_generada(state: WhatsAppAgentState) -> None:
    """Valida que se haya generado una respuesta."""
    # La respuesta puede estar en resumen_actual o en el último mensaje
    respuesta = state.get("resumen_actual") or ""
    messages = state.get("messages", [])
    
    # Buscar respuesta en mensajes
    for msg in reversed(messages):
        if hasattr(msg, "content") and msg.content:
            respuesta = msg.content
            break
    
    assert respuesta, "Debe haber una respuesta generada"
    assert len(respuesta) > 10, "La respuesta debe ser sustancial"


# Exportar utilidades
__all__ = [
    "crear_estado_base",
    "validar_estado_post_identificacion",
    "validar_estado_post_clasificacion",
    "validar_respuesta_generada",
    "TEST_PACIENTE_PHONE",
    "TEST_DOCTOR_PHONE",
    "TEST_ADMIN_PHONE",
    "TEST_NUEVO_PHONE",
]
