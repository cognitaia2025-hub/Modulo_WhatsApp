"""
Tests para Nodo N6R: Recepcionista

✅ Command pattern
✅ Pydantic extraction
✅ Flujo multi-turno
"""

import pytest
from unittest.mock import patch, Mock, MagicMock
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.types import Command

from src.nodes.recepcionista_node import (
    nodo_recepcionista,
    extraer_nombre_con_llm,
    extraer_fecha_con_llm,
    extraer_ultimo_mensaje_usuario,
    formatear_slots_para_whatsapp,
    ESTADOS_RECEPCIONISTA,
    ExtraccionNombre,
    ExtraccionFecha,
    SeleccionSlot
)


# ==================== FIXTURES ====================

@pytest.fixture
def state_base():
    """Estado base para pruebas"""
    return {
        'user_id': '+526861234567',
        'tipo_usuario': 'paciente_externo',
        'estado_conversacion': 'inicial',
        'messages': [],
        'datos_temporales': {}
    }


@pytest.fixture
def mock_paciente_existente():
    """Mock de paciente existente"""
    return {
        'id': 1,
        'phone_number': '+526861234567',
        'nombre_completo': 'Juan Pérez',
        'email': 'juan@example.com'
    }


@pytest.fixture
def mock_slots_disponibles():
    """Mock de slots disponibles"""
    return [
        {
            'fecha': '2026-02-05',
            'hora_inicio': '09:00',
            'hora_fin': '09:30',
            'doctor_asignado_id': 1,
            'doctor_nombre': 'Dr. García'
        },
        {
            'fecha': '2026-02-05',
            'hora_inicio': '10:00',
            'hora_fin': '10:30',
            'doctor_asignado_id': 1,
            'doctor_nombre': 'Dr. García'
        },
        {
            'fecha': '2026-02-06',
            'hora_inicio': '15:00',
            'hora_fin': '15:30',
            'doctor_asignado_id': 2,
            'doctor_nombre': 'Dr. López'
        }
    ]


# ==================== TESTS DE CONSTANTES ====================

def test_estados_recepcionista_definidos():
    """Verifica que todos los estados estén definidos."""
    assert 'inicial' in ESTADOS_RECEPCIONISTA
    assert 'solicitando_nombre' in ESTADOS_RECEPCIONISTA
    assert 'solicitando_fecha' in ESTADOS_RECEPCIONISTA
    assert 'mostrando_slots' in ESTADOS_RECEPCIONISTA
    assert 'confirmando_cita' in ESTADOS_RECEPCIONISTA
    assert 'completado' in ESTADOS_RECEPCIONISTA
    assert 'cancelado' in ESTADOS_RECEPCIONISTA


# ==================== TESTS DE FUNCIONES DE UTILIDAD ====================

def test_extraer_ultimo_mensaje_usuario_con_mensaje_humano():
    """Extrae correctamente mensaje de HumanMessage."""
    state = {
        'messages': [
            AIMessage(content="Hola"),
            HumanMessage(content="Quiero una cita")
        ]
    }
    
    resultado = extraer_ultimo_mensaje_usuario(state)
    assert resultado == "Quiero una cita"


def test_extraer_ultimo_mensaje_usuario_sin_mensajes():
    """Retorna string vacío si no hay mensajes."""
    state = {'messages': []}
    
    resultado = extraer_ultimo_mensaje_usuario(state)
    assert resultado == ""


def test_formatear_slots_para_whatsapp(mock_slots_disponibles):
    """Formatea correctamente los slots para WhatsApp."""
    resultado = formatear_slots_para_whatsapp(mock_slots_disponibles)
    
    assert "Horarios disponibles" in resultado
    assert "A)" in resultado
    assert "B)" in resultado
    assert "C)" in resultado
    assert "09:00" in resultado
    assert "¿Cuál prefieres?" in resultado


# ==================== TESTS DE EXTRACCIÓN PYDANTIC ====================

@patch('src.nodes.recepcionista_node.llm_extractor')
def test_extraer_nombre_exitoso(mock_llm):
    """Extrae nombre con alta confianza."""
    mock_structured = Mock()
    mock_structured.invoke.return_value = ExtraccionNombre(
        nombre_completo="María González",
        confianza="alta"
    )
    mock_llm.with_structured_output.return_value = mock_structured
    
    resultado = extraer_nombre_con_llm("Me llamo María González")
    
    assert resultado == "María González"
    mock_structured.invoke.assert_called_once()


@patch('src.nodes.recepcionista_node.llm_extractor')
def test_extraer_nombre_baja_confianza(mock_llm):
    """No retorna nombre con baja confianza."""
    mock_structured = Mock()
    mock_structured.invoke.return_value = ExtraccionNombre(
        nombre_completo="xyz",
        confianza="baja"
    )
    mock_llm.with_structured_output.return_value = mock_structured
    
    resultado = extraer_nombre_con_llm("xyz abc")
    
    assert resultado is None


@patch('src.nodes.recepcionista_node.llm_extractor')
def test_extraer_fecha_exitoso(mock_llm):
    """Extrae fecha correctamente."""
    mock_structured = Mock()
    mock_structured.invoke.return_value = ExtraccionFecha(
        fecha="2026-02-10",
        es_flexible=False
    )
    mock_llm.with_structured_output.return_value = mock_structured
    
    resultado = extraer_fecha_con_llm("El 10 de febrero", "Hoy es 1 de febrero de 2026")
    
    assert resultado == "2026-02-10"
    mock_structured.invoke.assert_called_once()


# ==================== TESTS DE FLUJO PRINCIPAL ====================

@patch('src.nodes.recepcionista_node.get_paciente_by_phone')
def test_flujo_inicial_paciente_nuevo(mock_get_paciente, state_base):
    """Estado inicial con paciente nuevo solicita nombre."""
    mock_get_paciente.return_value = None
    
    state_base['messages'] = [HumanMessage(content="Quiero una cita")]
    
    resultado = nodo_recepcionista(state_base)
    
    assert isinstance(resultado, Command)
    assert resultado.goto == "END"
    assert resultado.update['estado_conversacion'] == 'solicitando_nombre'
    assert "nombre" in resultado.update['messages'][0].content.lower()


@patch('src.nodes.recepcionista_node.get_paciente_by_phone')
def test_flujo_inicial_paciente_existente(mock_get_paciente, state_base, mock_paciente_existente):
    """Estado inicial con paciente existente solicita fecha."""
    mock_get_paciente.return_value = mock_paciente_existente
    
    state_base['messages'] = [HumanMessage(content="Quiero una cita")]
    
    resultado = nodo_recepcionista(state_base)
    
    assert isinstance(resultado, Command)
    assert resultado.goto == "END"
    assert resultado.update['estado_conversacion'] == 'solicitando_fecha'
    assert "Juan Pérez" in resultado.update['messages'][0].content
    assert "día" in resultado.update['messages'][0].content.lower()


@patch('src.nodes.recepcionista_node.registrar_paciente_externo')
@patch('src.nodes.recepcionista_node.extraer_nombre_con_llm')
def test_flujo_solicitando_nombre_exitoso(mock_extraer, mock_registrar, state_base):
    """Extrae nombre y avanza a siguiente estado."""
    mock_extraer.return_value = "Carlos Ramírez"
    mock_registrar.return_value = {"id": 2, "nombre": "Carlos Ramírez"}
    
    state_base['estado_conversacion'] = 'solicitando_nombre'
    state_base['messages'] = [HumanMessage(content="Me llamo Carlos Ramírez")]
    
    resultado = nodo_recepcionista(state_base)
    
    assert resultado.update['estado_conversacion'] == 'solicitando_fecha'
    assert resultado.update['datos_temporales']['nombre_paciente'] == "Carlos Ramírez"
    assert "Carlos Ramírez" in resultado.update['messages'][0].content


@patch('src.nodes.recepcionista_node.extraer_nombre_con_llm')
def test_flujo_solicitando_nombre_falla(mock_extraer, state_base):
    """Solicita nombre nuevamente si extracción falla."""
    mock_extraer.return_value = None
    
    state_base['estado_conversacion'] = 'solicitando_nombre'
    state_base['messages'] = [HumanMessage(content="xyz abc")]
    
    resultado = nodo_recepcionista(state_base)
    
    assert resultado.update['estado_conversacion'] == 'solicitando_nombre'
    assert "nombre completo" in resultado.update['messages'][0].content.lower()


@patch('src.nodes.recepcionista_node.generar_slots_con_turnos')
@patch('src.nodes.recepcionista_node.extraer_fecha_con_llm')
def test_flujo_solicitando_fecha_exitoso(mock_extraer_fecha, mock_generar_slots, state_base, mock_slots_disponibles):
    """Extrae fecha y muestra slots disponibles."""
    mock_extraer_fecha.return_value = "2026-02-10"
    mock_generar_slots.return_value = mock_slots_disponibles
    
    state_base['estado_conversacion'] = 'solicitando_fecha'
    state_base['messages'] = [HumanMessage(content="El 10 de febrero")]
    state_base['datos_temporales'] = {'nombre_paciente': 'Juan Pérez'}
    
    resultado = nodo_recepcionista(state_base)
    
    assert resultado.update['estado_conversacion'] == 'mostrando_slots'
    assert len(resultado.update['datos_temporales']['slots_disponibles']) == 3  # Mock returns 3 slots
    assert "Horarios disponibles" in resultado.update['messages'][0].content


@patch('src.nodes.recepcionista_node.extraer_fecha_con_llm')
def test_flujo_solicitando_fecha_sin_fecha(mock_extraer, state_base):
    """Solicita fecha nuevamente si no se puede extraer."""
    mock_extraer.return_value = None
    
    state_base['estado_conversacion'] = 'solicitando_fecha'
    state_base['messages'] = [HumanMessage(content="No sé")]
    
    resultado = nodo_recepcionista(state_base)
    
    assert resultado.update['estado_conversacion'] == 'solicitando_fecha'
    assert "fecha" in resultado.update['messages'][0].content.lower()


@patch('src.nodes.recepcionista_node.llm_extractor')
def test_flujo_mostrando_slots_seleccion_valida(mock_llm, state_base, mock_slots_disponibles):
    """Procesa selección válida de slot."""
    mock_structured = Mock()
    mock_structured.invoke.return_value = SeleccionSlot(
        opcion_seleccionada=2,
        confirmado=True
    )
    mock_llm.with_structured_output.return_value = mock_structured
    
    state_base['estado_conversacion'] = 'mostrando_slots'
    state_base['messages'] = [HumanMessage(content="La opción B")]
    state_base['datos_temporales'] = {
        'nombre_paciente': 'Juan Pérez',
        'slots_disponibles': mock_slots_disponibles
    }
    
    resultado = nodo_recepcionista(state_base)
    
    assert resultado.update['estado_conversacion'] == 'confirmando_cita'
    assert "Perfecto, confirmo tu cita" in resultado.update['messages'][0].content
    assert resultado.update['datos_temporales']['slot_final'] == mock_slots_disponibles[1]


@patch('src.nodes.recepcionista_node.agendar_cita_simple')
@patch('src.nodes.recepcionista_node.get_paciente_by_phone')
def test_flujo_confirmando_cita_aceptado(mock_get_paciente, mock_agendar, state_base, mock_slots_disponibles, mock_paciente_existente):
    """Agenda cita cuando usuario confirma."""
    mock_get_paciente.return_value = mock_paciente_existente
    mock_agendar.return_value = 123  # ID de cita creada
    
    state_base['estado_conversacion'] = 'confirmando_cita'
    state_base['messages'] = [HumanMessage(content="Sí, confirmo")]
    state_base['datos_temporales'] = {
        'nombre_paciente': 'Juan Pérez',
        'slot_final': mock_slots_disponibles[0]
    }
    
    resultado = nodo_recepcionista(state_base)
    
    assert resultado.update['estado_conversacion'] == 'completado'
    assert "✅" in resultado.update['messages'][0].content
    assert "agendada exitosamente" in resultado.update['messages'][0].content.lower()
    assert resultado.goto == "sincronizador_hibrido"


def test_flujo_confirmando_cita_rechazado(state_base, mock_slots_disponibles):
    """Cancela proceso cuando usuario rechaza."""
    state_base['estado_conversacion'] = 'confirmando_cita'
    state_base['messages'] = [HumanMessage(content="No, cancelar")]
    state_base['datos_temporales'] = {
        'nombre_paciente': 'Juan Pérez',
        'slot_final': mock_slots_disponibles[0]
    }
    
    resultado = nodo_recepcionista(state_base)
    
    assert resultado.update['estado_conversacion'] == 'inicial'
    assert "cancelé" in resultado.update['messages'][0].content.lower()


def test_flujo_estado_no_manejado(state_base):
    """Maneja estados no reconocidos con fallback."""
    state_base['estado_conversacion'] = 'estado_invalido'
    state_base['messages'] = [HumanMessage(content="Hola")]
    
    resultado = nodo_recepcionista(state_base)
    
    assert isinstance(resultado, Command)
    assert resultado.update['estado_conversacion'] == 'inicial'
    assert "error" in resultado.update['messages'][0].content.lower()


# ==================== TESTS DEL WRAPPER ====================

@patch('src.nodes.recepcionista_node.nodo_recepcionista')
def test_wrapper_llama_nodo_principal(mock_nodo, state_base):
    """Wrapper llama correctamente al nodo principal."""
    from src.nodes.recepcionista_node import nodo_recepcionista_wrapper
    
    mock_command = Command(
        update={'messages': [AIMessage(content="Test")]},
        goto="END"
    )
    mock_nodo.return_value = mock_command
    
    resultado = nodo_recepcionista_wrapper(state_base)
    
    assert resultado == mock_command
    mock_nodo.assert_called_once_with(state_base)


@patch('src.nodes.recepcionista_node.nodo_recepcionista')
def test_wrapper_maneja_errores(mock_nodo, state_base):
    """Wrapper maneja errores gracefully."""
    from src.nodes.recepcionista_node import nodo_recepcionista_wrapper
    
    mock_nodo.side_effect = Exception("Error de prueba")
    
    resultado = nodo_recepcionista_wrapper(state_base)
    
    assert isinstance(resultado, Command)
    assert resultado.goto == "END"
    assert "error" in resultado.update['messages'][0].content.lower()
    assert resultado.update['estado_conversacion'] == 'inicial'


# ==================== TESTS DE INTEGRACIÓN ====================

@patch('src.nodes.recepcionista_node.agendar_cita_simple')
@patch('src.nodes.recepcionista_node.generar_slots_con_turnos')
@patch('src.nodes.recepcionista_node.registrar_paciente_externo')
@patch('src.nodes.recepcionista_node.get_paciente_by_phone')
@patch('src.nodes.recepcionista_node.extraer_fecha_con_llm')
@patch('src.nodes.recepcionista_node.extraer_nombre_con_llm')
def test_flujo_completo_paciente_nuevo(
    mock_nombre, mock_fecha, mock_get_paciente, mock_registrar,
    mock_generar, mock_agendar, state_base, mock_slots_disponibles
):
    """Test de flujo completo desde paciente nuevo hasta cita agendada."""
    # Setup
    mock_get_paciente.return_value = None
    mock_nombre.return_value = "Ana Torres"
    mock_registrar.return_value = {"id": 3, "nombre": "Ana Torres"}
    mock_fecha.return_value = "2026-02-15"
    mock_generar.return_value = mock_slots_disponibles
    mock_agendar.return_value = 456
    
    # 1. Estado inicial - pedir nombre
    state_base['messages'] = [HumanMessage(content="Quiero una cita")]
    resultado1 = nodo_recepcionista(state_base)
    assert resultado1.update['estado_conversacion'] == 'solicitando_nombre'
    
    # 2. Proporcionar nombre
    state_base['estado_conversacion'] = 'solicitando_nombre'
    state_base['messages'] = [HumanMessage(content="Me llamo Ana Torres")]
    resultado2 = nodo_recepcionista(state_base)
    assert resultado2.update['estado_conversacion'] == 'solicitando_fecha'
    
    # 3. Proporcionar fecha
    state_base['estado_conversacion'] = 'solicitando_fecha'
    state_base['datos_temporales'] = resultado2.update['datos_temporales']
    state_base['messages'] = [HumanMessage(content="El 15 de febrero")]
    resultado3 = nodo_recepcionista(state_base)
    assert resultado3.update['estado_conversacion'] == 'mostrando_slots'
    
    # Verificar que todos los mocks fueron llamados correctamente
    mock_nombre.assert_called_once()
    mock_registrar.assert_called_once()
    mock_fecha.assert_called_once()
    mock_generar.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
