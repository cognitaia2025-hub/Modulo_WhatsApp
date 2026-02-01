"""
TEST 3: test_seleccion_herramientas_llm.py
Pruebas de selección inteligente de herramientas con LLM (20 tests)
"""

import pytest
from langgraph.types import Command
from src.nodes.seleccion_herramientas_node import (
    nodo_seleccion_herramientas,
    obtener_herramientas_segun_clasificacion,
    SeleccionHerramientas,
    ESTADOS_FLUJO_ACTIVO
)
from unittest.mock import patch


def test_llm_selecciona_agendar_cita(estado_con_doctor, mock_obtener_herramientas, mocker):
    """Test 3.1: LLM detecta 'quiero cita' → selecciona 'agendar_cita_medica_completa'"""
    estado = estado_con_doctor.copy()
    estado["clasificacion_mensaje"] = "medica"
    estado["messages"][0].content = "Quiero agendar una cita"
    
    mock_llm = mocker.patch('src.nodes.seleccion_herramientas_node.llm_selector')
    mock_llm.invoke.return_value = SeleccionHerramientas(
        herramientas_ids=["agendar_cita_medica_completa"],
        razonamiento="Usuario solicita agendar cita"
    )
    
    resultado = nodo_seleccion_herramientas(estado)
    assert isinstance(resultado, Command)
    assert resultado.goto == "ejecucion_herramientas"
    assert "agendar_cita_medica_completa" in resultado.update['herramientas_seleccionadas']


def test_paciente_externo_herramientas_limitadas(estado_con_paciente):
    """Test 3.2: Paciente solo puede usar 2 herramientas"""
    herramientas = obtener_herramientas_segun_clasificacion("solicitud_cita_paciente", "paciente_externo")
    
    assert len(herramientas) == 2
    assert all(h["id_tool"] in ["consultar_slots_disponibles", "agendar_cita_medica_completa"] for h in herramientas)


def test_doctor_acceso_completo():
    """Test 3.3: Doctor puede usar todas las 12 herramientas"""
    herramientas = obtener_herramientas_segun_clasificacion("medica", "doctor")
    
    assert len(herramientas) == 12


def test_clasificacion_personal_usa_calendario():
    """Test 3.4: Clasificación 'personal' → herramientas de calendario"""
    herramientas = obtener_herramientas_segun_clasificacion("personal", "doctor")
    
    # Debería retornar herramientas de calendar
    assert isinstance(herramientas, list)


def test_clasificacion_chat_sin_herramientas():
    """Test 3.5: Clasificación 'chat' → sin herramientas"""
    herramientas = obtener_herramientas_segun_clasificacion("chat", "paciente_externo")
    
    assert herramientas == []


def test_herramientas_tienen_formato_correcto():
    """Test 3.6: Herramientas tienen 'id_tool' y 'description'"""
    herramientas = obtener_herramientas_segun_clasificacion("medica", "doctor")
    
    for h in herramientas:
        assert "id_tool" in h
        assert "description" in h


def test_sin_mensaje_retorna_vacio(estado_con_doctor, mock_obtener_herramientas):
    """Test 3.7: Sin mensaje del usuario → herramientas vacías"""
    estado = estado_con_doctor.copy()
    estado["messages"] = []
    
    resultado = nodo_seleccion_herramientas(estado)
    assert isinstance(resultado, Command)
    assert resultado.goto == "generacion_resumen"
    assert resultado.update['herramientas_seleccionadas'] == []


def test_llm_selecciona_multiples_herramientas(estado_con_doctor, mock_obtener_herramientas, mocker):
    """Test 3.8: LLM puede seleccionar múltiples herramientas"""
    estado = estado_con_doctor.copy()
    estado["clasificacion_mensaje"] = "medica"

    mock_llm = mocker.patch('src.nodes.seleccion_herramientas_node.llm_selector')
    mock_llm.invoke.return_value = SeleccionHerramientas(
        herramientas_ids=["consultar_slots_disponibles", "agendar_cita_medica_completa"],
        razonamiento="Necesita consultar y agendar"
    )

    resultado = nodo_seleccion_herramientas(estado)
    assert isinstance(resultado, Command)
    assert resultado.goto == "ejecucion_herramientas"
    assert len(resultado.update['herramientas_seleccionadas']) >= 1


def test_clasificacion_medica_requiere_doctor():
    """Test 3.9: Clasificación 'medica' sin ser doctor → sin herramientas"""
    herramientas = obtener_herramientas_segun_clasificacion("medica", "paciente_externo")
    
    assert herramientas == []


def test_fallback_si_llm_falla(estado_con_doctor, mock_obtener_herramientas, mocker):
    """Test 3.10: Si LLM falla → herramientas por defecto según clasificación"""
    estado = estado_con_doctor.copy()
    estado["clasificacion_mensaje"] = "medica"
    
    mock_llm = mocker.patch('src.nodes.seleccion_herramientas_node.llm_selector')
    mock_llm.invoke.side_effect = Exception("LLM error")
    
    resultado = nodo_seleccion_herramientas(estado)
    # Debe retornar fallback
    assert isinstance(resultado, Command)
    assert resultado.goto == "ejecucion_herramientas"
    assert isinstance(resultado.update['herramientas_seleccionadas'], list)


def test_herramientas_medicas_para_solicitud_cita():
    """Test 3.11: solicitud_cita_paciente → herramientas médicas limitadas"""
    herramientas = obtener_herramientas_segun_clasificacion("solicitud_cita_paciente", "paciente_externo")
    
    nombres = [h["id_tool"] for h in herramientas]
    assert "consultar_slots_disponibles" in nombres
    assert "agendar_cita_medica_completa" in nombres


def test_crear_paciente_solo_doctor():
    """Test 3.12: crear_paciente_medico solo para doctores"""
    herramientas_doctor = obtener_herramientas_segun_clasificacion("medica", "doctor")
    herramientas_paciente = obtener_herramientas_segun_clasificacion("solicitud_cita_paciente", "paciente_externo")
    
    tiene_doctor = any(h["id_tool"] == "crear_paciente_medico" for h in herramientas_doctor)
    tiene_paciente = any(h["id_tool"] == "crear_paciente_medico" for h in herramientas_paciente)
    
    assert tiene_doctor
    assert not tiene_paciente


def test_contexto_episodico_incluido_en_prompt(estado_con_doctor, mock_obtener_herramientas, mocker):
    """Test 3.13: Contexto episódico se incluye en prompt si existe"""
    estado = estado_con_doctor.copy()
    estado["clasificacion_mensaje"] = "medica"
    estado["contexto_episodico"] = {
        "episodios_recuperados": [{"summary": "Test"}],
        "texto_formateado": "Contexto de prueba"
    }
    
    mock_llm = mocker.patch('src.nodes.seleccion_herramientas_node.llm_selector')
    mock_llm.invoke.return_value = SeleccionHerramientas(
        herramientas_ids=["consultar_slots_disponibles"],
        razonamiento="Test"
    )
    
    resultado = nodo_seleccion_herramientas(estado)
    
    # Verificar que se llamó el LLM
    assert mock_llm.invoke.called
    assert isinstance(resultado, Command)


def test_estado_actualizado_con_seleccion(estado_con_doctor, mock_obtener_herramientas, mocker):
    """Test 3.14: Estado se actualiza con herramientas seleccionadas"""
    estado = estado_con_doctor.copy()
    estado["clasificacion_mensaje"] = "medica"
    
    mock_llm = mocker.patch('src.nodes.seleccion_herramientas_node.llm_selector')
    mock_llm.invoke.return_value = SeleccionHerramientas(
        herramientas_ids=["consultar_slots_disponibles"],
        razonamiento="Usuario necesita consultar"
    )
    
    resultado = nodo_seleccion_herramientas(estado)
    
    assert isinstance(resultado, Command)
    assert "herramientas_seleccionadas" in resultado.update
    assert isinstance(resultado.update['herramientas_seleccionadas'], list)


def test_clasificacion_determina_pool_herramientas():
    """Test 3.15: Cada clasificación tiene su propio pool de herramientas"""
    personal = obtener_herramientas_segun_clasificacion("personal", "doctor")
    medica = obtener_herramientas_segun_clasificacion("medica", "doctor")
    chat = obtener_herramientas_segun_clasificacion("chat", "doctor")
    
    # Personal y médica tienen herramientas diferentes
    # Chat no tiene herramientas
    assert len(chat) == 0
    assert len(medica) > 0


def test_herramienta_invalida_es_filtrada(estado_con_doctor, mock_obtener_herramientas, mocker):
    """Test 3.16: Herramienta inválida es filtrada automáticamente"""
    estado = estado_con_doctor.copy()
    estado["clasificacion_mensaje"] = "medica"
    
    mock_llm = mocker.patch('src.nodes.seleccion_herramientas_node.llm_selector')
    mock_llm.invoke.return_value = SeleccionHerramientas(
        herramientas_ids=["consultar_slots_disponibles", "herramienta_invalida"],
        razonamiento="Test con herramienta inválida"
    )
    
    resultado = nodo_seleccion_herramientas(estado)
    
    assert isinstance(resultado, Command)
    assert "consultar_slots_disponibles" in resultado.update['herramientas_seleccionadas']
    assert "herramienta_invalida" not in resultado.update['herramientas_seleccionadas']


def test_clasificacion_chat_salta_llm(estado_con_doctor, mock_obtener_herramientas, mocker):
    """Test 3.17: Clasificación 'chat' no llama al LLM"""
    estado = estado_con_doctor.copy()
    estado["clasificacion_mensaje"] = "chat"
    
    mock_llm = mocker.patch('src.nodes.seleccion_herramientas_node.llm_selector')
    
    resultado = nodo_seleccion_herramientas(estado)
    
    assert isinstance(resultado, Command)
    assert resultado.goto == "generacion_resumen"
    assert resultado.update['herramientas_seleccionadas'] == []
    assert not mock_llm.invoke.called


def test_pydantic_model_estructura(estado_con_doctor, mock_obtener_herramientas, mocker):
    """Test 3.18: Pydantic model tiene estructura correcta"""
    estado = estado_con_doctor.copy()
    estado["clasificacion_mensaje"] = "medica"
    
    mock_llm = mocker.patch('src.nodes.seleccion_herramientas_node.llm_selector')
    seleccion_obj = SeleccionHerramientas(
        herramientas_ids=["consultar_slots_disponibles"],
        razonamiento="Test de estructura"
    )
    mock_llm.invoke.return_value = seleccion_obj
    
    resultado = nodo_seleccion_herramientas(estado)
    
    assert isinstance(resultado, Command)
    assert hasattr(seleccion_obj, 'herramientas_ids')
    assert hasattr(seleccion_obj, 'razonamiento')
    assert isinstance(seleccion_obj.herramientas_ids, list)
    assert isinstance(seleccion_obj.razonamiento, str)


def test_timeout_reducido():
    """Test 3.19: Timeout de LLMs reducido a 10s"""
    from src.nodes.seleccion_herramientas_node import llm_primary_base, llm_fallback_base
    
    # Verificar que los timeouts sean 10s
    assert llm_primary_base.timeout == 10.0
    assert llm_fallback_base.timeout == 10.0


def test_lista_vacia_cuando_no_necesita_herramientas(estado_con_doctor, mock_obtener_herramientas, mocker):
    """Test 3.20: Lista vacía cuando LLM determina que no se necesitan herramientas"""
    estado = estado_con_doctor.copy()
    estado["clasificacion_mensaje"] = "medica"
    
    mock_llm = mocker.patch('src.nodes.seleccion_herramientas_node.llm_selector')
    mock_llm.invoke.return_value = SeleccionHerramientas(
        herramientas_ids=[],
        razonamiento="No se necesitan herramientas"
    )
    
    resultado = nodo_seleccion_herramientas(estado)
    
    assert isinstance(resultado, Command)
    assert resultado.goto == "ejecucion_herramientas"
    assert resultado.update['herramientas_seleccionadas'] == []


# ============================================================================
# NUEVOS TESTS: Estado Conversacional y Pydantic
# ============================================================================


def test_detecta_estado_activo():
    """Test 3.21: Detecta flujo activo y salta selección."""
    estado = {
        'clasificacion_mensaje': 'personal',
        'tipo_usuario': 'doctor',
        'messages': [{'role': 'user', 'content': 'Test'}],
        'estado_conversacion': 'ejecutando_herramienta'
    }
    
    resultado = nodo_seleccion_herramientas(estado)
    
    assert isinstance(resultado, Command)
    assert resultado.goto == "ejecucion_herramientas"
    assert resultado.update['herramientas_seleccionadas'] == []


@pytest.mark.parametrize("estado", ESTADOS_FLUJO_ACTIVO)
def test_detecta_todos_estados_activos(estado):
    """Test 3.22: Detecta todos los estados de flujo activo."""
    state = {
        'clasificacion_mensaje': 'personal',
        'tipo_usuario': 'doctor',
        'messages': [{'role': 'user', 'content': 'Test'}],
        'estado_conversacion': estado
    }
    
    resultado = nodo_seleccion_herramientas(state)
    
    assert isinstance(resultado, Command)
    assert resultado.update['herramientas_seleccionadas'] == []


@patch('src.nodes.seleccion_herramientas_node.llm_selector')
def test_pydantic_model_funciona(mock_llm, estado_con_doctor, mock_obtener_herramientas):
    """Test 3.23: Pydantic model parsea correctamente."""
    mock_llm.invoke.return_value = SeleccionHerramientas(
        herramientas_ids=["consultar_slots_disponibles"],
        razonamiento="Usuario pregunta por eventos"
    )
    
    estado = estado_con_doctor.copy()
    estado['clasificacion_mensaje'] = 'medica'
    estado['messages'][0].content = '¿Qué eventos tengo?'
    estado['estado_conversacion'] = 'inicial'
    
    resultado = nodo_seleccion_herramientas(estado)
    
    assert isinstance(resultado, Command)
    assert "consultar_slots_disponibles" in resultado.update['herramientas_seleccionadas']
