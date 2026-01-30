"""
Tests para Maya Detective de Intención para Pacientes (Nodo 2A)

Test suite completo con 18 tests que validan el comportamiento de Maya
en diferentes escenarios de interacción con pacientes.
"""

import pytest
from unittest.mock import patch, MagicMock
from langchain_core.messages import HumanMessage
from langgraph.types import Command

from src.nodes.maya_detective_paciente_node import (
    nodo_maya_detective_paciente,
    obtener_contexto_paciente,
    obtener_fecha_hora_actual,
    MayaResponse,
    CLINICA_INFO
)


# ==================== FIXTURES ====================

@pytest.fixture
def state_base():
    """Estado base para pruebas"""
    return {
        'user_id': '+526861234567',
        'tipo_usuario': 'paciente_externo',
        'estado_conversacion': 'inicial',
        'messages': []
    }


@pytest.fixture
def mock_maya_respuesta_directa():
    """Mock de respuesta directa de Maya"""
    return MayaResponse(
        accion="responder_directo",
        respuesta="¡Hola! 👋 Estoy aquí para ayudarte. ¿En qué puedo asistirte hoy?",
        razon="Saludo inicial del paciente"
    )


@pytest.fixture
def mock_maya_escalar():
    """Mock de respuesta de escalamiento"""
    return MayaResponse(
        accion="escalar_procedimental",
        respuesta="",
        razon="Paciente especifica día y hora para cita"
    )


@pytest.fixture
def mock_maya_dejar_pasar():
    """Mock de respuesta dejar pasar"""
    return MayaResponse(
        accion="dejar_pasar",
        respuesta="",
        razon="Flujo de conversación ya está activo"
    )


# ==================== TESTS DE RESPUESTA DIRECTA ====================

def test_maya_responde_saludo(state_base, mock_maya_respuesta_directa):
    """Test 1: Maya responde a un saludo simple"""
    state_base['messages'] = [HumanMessage(content="Hola")]
    
    with patch('src.nodes.maya_detective_paciente_node.llm_structured') as mock_llm:
        mock_llm.invoke.return_value = mock_maya_respuesta_directa
        
        resultado = nodo_maya_detective_paciente(state_base)
        
        assert isinstance(resultado, Command)
        assert resultado.goto == "generacion_resumen"
        assert resultado.update['clasificacion_mensaje'] == "maya_respuesta_directa"
        assert 'respuesta_maya' in resultado.update


def test_maya_responde_ubicacion(state_base):
    """Test 2: Maya responde pregunta sobre ubicación"""
    state_base['messages'] = [HumanMessage(content="¿Dónde están ubicados?")]
    
    maya_response = MayaResponse(
        accion="responder_directo",
        respuesta=f"📍 Nos encontramos en {CLINICA_INFO['ubicacion']}",
        razon="Pregunta sobre ubicación de la clínica"
    )
    
    with patch('src.nodes.maya_detective_paciente_node.llm_structured') as mock_llm:
        mock_llm.invoke.return_value = maya_response
        
        resultado = nodo_maya_detective_paciente(state_base)
        
        assert resultado.goto == "generacion_resumen"
        assert CLINICA_INFO['ubicacion'] in resultado.update['respuesta_maya']


def test_maya_responde_horario(state_base):
    """Test 3: Maya responde pregunta sobre horario"""
    state_base['messages'] = [HumanMessage(content="¿Cuál es su horario?")]
    
    maya_response = MayaResponse(
        accion="responder_directo",
        respuesta=f"🕒 Nuestro horario es: {CLINICA_INFO['horario_lv']}, {CLINICA_INFO['horario_sd']}",
        razon="Pregunta sobre horario de atención"
    )
    
    with patch('src.nodes.maya_detective_paciente_node.llm_structured') as mock_llm:
        mock_llm.invoke.return_value = maya_response
        
        resultado = nodo_maya_detective_paciente(state_base)
        
        assert resultado.goto == "generacion_resumen"
        assert 'respuesta_maya' in resultado.update


def test_maya_pregunta_cuando_agendar_incompleto(state_base):
    """Test 4: Maya pregunta cuándo si agendar está incompleto"""
    state_base['messages'] = [HumanMessage(content="Quiero agendar una cita")]
    
    maya_response = MayaResponse(
        accion="responder_directo",
        respuesta="¡Perfecto! 📅 ¿Para cuándo te gustaría agendar tu cita?",
        razon="Solicitud de cita sin especificar día/hora"
    )
    
    with patch('src.nodes.maya_detective_paciente_node.llm_structured') as mock_llm:
        mock_llm.invoke.return_value = maya_response
        
        resultado = nodo_maya_detective_paciente(state_base)
        
        assert resultado.goto == "generacion_resumen"
        assert resultado.update['clasificacion_mensaje'] == "maya_respuesta_directa"


# ==================== TESTS DE ESCALAMIENTO ====================

def test_maya_escala_agendar_completo(state_base, mock_maya_escalar):
    """Test 5: Maya escala cuando agendar especifica día+hora"""
    state_base['messages'] = [HumanMessage(content="Quiero una cita mañana a las 3pm")]
    
    with patch('src.nodes.maya_detective_paciente_node.llm_structured') as mock_llm:
        mock_llm.invoke.return_value = mock_maya_escalar
        
        resultado = nodo_maya_detective_paciente(state_base)
        
        assert resultado.goto == "recepcionista"
        assert resultado.update['clasificacion_mensaje'] == "solicitud_cita_paciente"
        assert resultado.update['ruta_siguiente'] == "recepcionista"


def test_maya_escala_cancelar(state_base):
    """Test 6: Maya escala solicitud de cancelación"""
    state_base['messages'] = [HumanMessage(content="Necesito cancelar mi cita")]
    
    maya_response = MayaResponse(
        accion="escalar_procedimental",
        respuesta="",
        razon="Solicitud de cancelación de cita"
    )
    
    with patch('src.nodes.maya_detective_paciente_node.llm_structured') as mock_llm:
        mock_llm.invoke.return_value = maya_response
        
        resultado = nodo_maya_detective_paciente(state_base)
        
        assert resultado.goto == "recepcionista"
        assert resultado.update['clasificacion_mensaje'] == "solicitud_cita_paciente"


def test_maya_escala_reagendar(state_base):
    """Test 7: Maya escala solicitud de reagendamiento"""
    state_base['messages'] = [HumanMessage(content="Quiero reagendar mi cita para el viernes")]
    
    maya_response = MayaResponse(
        accion="escalar_procedimental",
        respuesta="",
        razon="Solicitud de reagendamiento con fecha específica"
    )
    
    with patch('src.nodes.maya_detective_paciente_node.llm_structured') as mock_llm:
        mock_llm.invoke.return_value = maya_response
        
        resultado = nodo_maya_detective_paciente(state_base)
        
        assert resultado.goto == "recepcionista"


# ==================== TESTS DE DEJAR PASAR ====================

def test_maya_deja_pasar_flujo_activo(state_base, mock_maya_dejar_pasar):
    """Test 8: Maya deja pasar cuando hay flujo activo"""
    state_base['messages'] = [HumanMessage(content="Opción B")]
    state_base['estado_conversacion'] = 'esperando_seleccion'
    
    with patch('src.nodes.maya_detective_paciente_node.llm_structured') as mock_llm:
        mock_llm.invoke.return_value = mock_maya_dejar_pasar
        
        resultado = nodo_maya_detective_paciente(state_base)
        
        assert resultado.goto == "recepcionista"
        assert resultado.update['clasificacion_mensaje'] == "flujo_activo"


def test_maya_responde_despedida_post_cita(state_base):
    """Test 9: Maya responde despedida después de cita completada"""
    state_base['messages'] = [HumanMessage(content="Gracias, hasta luego")]
    state_base['estado_conversacion'] = 'completado'
    
    maya_response = MayaResponse(
        accion="responder_directo",
        respuesta="¡Hasta luego! 👋 Te esperamos en tu cita. Cuídate mucho.",
        razon="Despedida post-cita completada"
    )
    
    with patch('src.nodes.maya_detective_paciente_node.llm_structured') as mock_llm:
        mock_llm.invoke.return_value = maya_response
        
        resultado = nodo_maya_detective_paciente(state_base)
        
        assert resultado.goto == "generacion_resumen"


# ==================== TESTS DE MANEJO DE ERRORES ====================

def test_maya_maneja_error_llm(state_base):
    """Test 10: Maya maneja error del LLM correctamente"""
    state_base['messages'] = [HumanMessage(content="Hola")]
    
    with patch('src.nodes.maya_detective_paciente_node.llm_structured') as mock_llm:
        mock_llm.invoke.side_effect = Exception("Error de API")
        
        resultado = nodo_maya_detective_paciente(state_base)
        
        # En caso de error, debe escalar al flujo completo
        assert resultado.goto == "recepcionista"
        assert resultado.update['clasificacion_mensaje'] == "error_maya"
        assert 'error_maya' in resultado.update


def test_maya_sin_mensaje(state_base):
    """Test 11: Maya maneja estado sin mensajes"""
    state_base['messages'] = []
    
    resultado = nodo_maya_detective_paciente(state_base)
    
    assert resultado.goto == "generacion_resumen"
    assert resultado.update['clasificacion_mensaje'] == "error"


# ==================== TESTS DE PERSONALIZACIÓN ====================

def test_maya_personaliza_saludo_paciente_conocido(state_base):
    """Test 12: Maya personaliza saludo para paciente conocido"""
    state_base['messages'] = [HumanMessage(content="Hola")]
    
    # Mock de paciente conocido
    paciente_conocido = {
        "id": 123,
        "nombre_completo": "Juan Pérez",
        "telefono": state_base['user_id']
    }
    
    maya_response = MayaResponse(
        accion="responder_directo",
        respuesta="¡Hola Juan! 👋 ¿En qué puedo ayudarte hoy?",
        razon="Saludo personalizado para paciente conocido"
    )
    
    with patch('src.nodes.maya_detective_paciente_node.get_paciente_by_phone') as mock_db:
        mock_db.return_value = paciente_conocido
        
        with patch('src.nodes.maya_detective_paciente_node.llm_structured') as mock_llm:
            mock_llm.invoke.return_value = maya_response
            
            resultado = nodo_maya_detective_paciente(state_base)
            
            assert resultado.goto == "generacion_resumen"
            assert "Juan" in resultado.update['respuesta_maya']


# ==================== TESTS DE EDGE CASES ====================

def test_maya_responde_telefono(state_base):
    """Test 13: Maya responde pregunta sobre teléfono"""
    state_base['messages'] = [HumanMessage(content="¿Cuál es su número de teléfono?")]
    
    maya_response = MayaResponse(
        accion="responder_directo",
        respuesta=f"📞 Puedes llamarnos al {CLINICA_INFO['telefono']}",
        razon="Pregunta sobre número telefónico"
    )
    
    with patch('src.nodes.maya_detective_paciente_node.llm_structured') as mock_llm:
        mock_llm.invoke.return_value = maya_response
        
        resultado = nodo_maya_detective_paciente(state_base)
        
        assert resultado.goto == "generacion_resumen"


def test_maya_responde_dias_cerrados(state_base):
    """Test 14: Maya informa sobre días cerrados"""
    state_base['messages'] = [HumanMessage(content="¿Están abiertos el martes?")]
    
    maya_response = MayaResponse(
        accion="responder_directo",
        respuesta=f"No, estamos cerrados {CLINICA_INFO['cerrado']} 📅",
        razon="Pregunta sobre días cerrados"
    )
    
    with patch('src.nodes.maya_detective_paciente_node.llm_structured') as mock_llm:
        mock_llm.invoke.return_value = maya_response
        
        resultado = nodo_maya_detective_paciente(state_base)
        
        assert resultado.goto == "generacion_resumen"


def test_maya_confirma_cita_con_horarios(state_base):
    """Test 15: Maya escala cita con día de semana + horario específico"""
    state_base['messages'] = [HumanMessage(content="Quiero cita el lunes a las 10am")]
    
    maya_response = MayaResponse(
        accion="escalar_procedimental",
        respuesta="",
        razon="Día específico + hora especificada"
    )
    
    with patch('src.nodes.maya_detective_paciente_node.llm_structured') as mock_llm:
        mock_llm.invoke.return_value = maya_response
        
        resultado = nodo_maya_detective_paciente(state_base)
        
        assert resultado.goto == "recepcionista"


def test_maya_responde_mensaje_general(state_base):
    """Test 16: Maya responde mensaje general/casual"""
    state_base['messages'] = [HumanMessage(content="¿Cómo están?")]
    
    maya_response = MayaResponse(
        accion="responder_directo",
        respuesta="¡Muy bien, gracias por preguntar! 😊 ¿En qué puedo ayudarte?",
        razon="Mensaje casual de cortesía"
    )
    
    with patch('src.nodes.maya_detective_paciente_node.llm_structured') as mock_llm:
        mock_llm.invoke.return_value = maya_response
        
        resultado = nodo_maya_detective_paciente(state_base)
        
        assert resultado.goto == "generacion_resumen"


def test_maya_escala_modificar_cita(state_base):
    """Test 17: Maya escala solicitud de modificar cita"""
    state_base['messages'] = [HumanMessage(content="Quiero cambiar la hora de mi cita")]
    
    maya_response = MayaResponse(
        accion="escalar_procedimental",
        respuesta="",
        razon="Solicitud de modificación de cita existente"
    )
    
    with patch('src.nodes.maya_detective_paciente_node.llm_structured') as mock_llm:
        mock_llm.invoke.return_value = maya_response
        
        resultado = nodo_maya_detective_paciente(state_base)
        
        assert resultado.goto == "recepcionista"


def test_maya_latencia_bajo_1_segundo(state_base):
    """Test 18: Verifica que Maya responde en menos de 1 segundo (mock)"""
    state_base['messages'] = [HumanMessage(content="Hola")]
    
    maya_response = MayaResponse(
        accion="responder_directo",
        respuesta="¡Hola! 👋",
        razon="Test de latencia"
    )
    
    with patch('src.nodes.maya_detective_paciente_node.llm_structured') as mock_llm:
        mock_llm.invoke.return_value = maya_response
        
        resultado = nodo_maya_detective_paciente(state_base)
        
        # Verificar que se registra el tiempo
        assert 'tiempo_maya_ms' in resultado.update
        # En mock debería ser muy rápido (< 100ms)
        assert resultado.update['tiempo_maya_ms'] < 1000


# ==================== TESTS DE FUNCIONES AUXILIARES ====================

def test_obtener_fecha_hora_actual():
    """Test: Función obtener_fecha_hora_actual retorna string válido"""
    fecha_hora = obtener_fecha_hora_actual()
    
    assert isinstance(fecha_hora, str)
    assert len(fecha_hora) > 0
    # Debe contener algún día de la semana en español
    dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    assert any(dia in fecha_hora for dia in dias)


def test_obtener_contexto_paciente_nuevo():
    """Test: Contexto de paciente nuevo (no existe en BD)"""
    with patch('src.nodes.maya_detective_paciente_node.get_paciente_by_phone') as mock_db:
        mock_db.return_value = None
        
        contexto = obtener_contexto_paciente("+526861234567")
        
        assert contexto['es_conocido'] == False
        assert 'nombre' not in contexto or contexto.get('nombre') == ''


def test_obtener_contexto_paciente_existente():
    """Test: Contexto de paciente existente en BD"""
    paciente_mock = {
        "id": 456,
        "nombre_completo": "María García",
        "telefono": "+526861234567"
    }
    
    with patch('src.nodes.maya_detective_paciente_node.get_paciente_by_phone') as mock_db:
        mock_db.return_value = paciente_mock
        
        contexto = obtener_contexto_paciente("+526861234567")
        
        assert contexto['es_conocido'] == True
        assert contexto['nombre'] == "María García"
        assert contexto['paciente_id'] == 456


# ==================== TESTS DE INFORMACIÓN CLÍNICA ====================

def test_clinica_info_completo():
    """Test: Verificar que CLINICA_INFO tiene todos los campos necesarios"""
    assert 'ubicacion' in CLINICA_INFO
    assert 'telefono' in CLINICA_INFO
    assert 'horario_lv' in CLINICA_INFO
    assert 'horario_sd' in CLINICA_INFO
    assert 'cerrado' in CLINICA_INFO
    
    # Verificar valores específicos
    assert "Avenida Electricistas 1978" in CLINICA_INFO['ubicacion']
    assert "686 108 3647" in CLINICA_INFO['telefono']
    assert "Martes y Miércoles" in CLINICA_INFO['cerrado']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
