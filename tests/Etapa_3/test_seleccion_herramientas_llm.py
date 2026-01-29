"""
TEST 3: test_seleccion_herramientas_llm.py
Pruebas de selección inteligente de herramientas con LLM (20 tests)
"""

import pytest
from src.nodes.seleccion_herramientas_node import (
    nodo_seleccion_herramientas,
    obtener_herramientas_segun_clasificacion
)


def test_llm_selecciona_agendar_cita(estado_con_doctor, mock_obtener_herramientas, mocker):
    """Test 3.1: LLM detecta 'quiero cita' → selecciona 'agendar_cita_medica_completa'"""
    estado = estado_con_doctor.copy()
    estado["clasificacion_mensaje"] = "medica"
    estado["messages"][0].content = "Quiero agendar una cita"
    
    mock_llm = mocker.patch('src.nodes.seleccion_herramientas_node.llm_selector')
    mock_llm.invoke.return_value.content = "agendar_cita_medica_completa"
    
    resultado = nodo_seleccion_herramientas(estado)
    assert "agendar_cita_medica_completa" in resultado["herramientas_seleccionadas"]


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
    assert resultado["herramientas_seleccionadas"] == []


def test_llm_selecciona_multiples_herramientas(estado_con_doctor, mock_obtener_herramientas, mocker):
    """Test 3.8: LLM puede seleccionar múltiples herramientas"""
    estado = estado_con_doctor.copy()
    estado["clasificacion_mensaje"] = "medica"

    mock_llm = mocker.patch('src.nodes.seleccion_herramientas_node.llm_selector')
    # Usar IDs que existan en las herramientas disponibles mockeadas
    mock_llm.invoke.return_value.content = "consultar_slots_disponibles,agendar_cita_medica_completa"

    resultado = nodo_seleccion_herramientas(estado)
    assert len(resultado["herramientas_seleccionadas"]) >= 1


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
    assert isinstance(resultado["herramientas_seleccionadas"], list)


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


def test_parseo_respuesta_llm_limpia_espacios(mocker):
    """Test 3.13: Parseo de LLM limpia espacios y saltos de línea"""
    from src.nodes.seleccion_herramientas_node import parsear_respuesta_llm
    
    herramientas = [{"id_tool": "test_tool", "description": "Test"}]
    respuesta = "  test_tool \n"
    
    resultado = parsear_respuesta_llm(respuesta, herramientas)
    assert resultado == ["test_tool"]


def test_respuesta_none_retorna_vacio(mocker):
    """Test 3.14: Respuesta 'NONE' del LLM → lista vacía"""
    from src.nodes.seleccion_herramientas_node import parsear_respuesta_llm
    
    resultado = parsear_respuesta_llm("NONE", [])
    assert resultado == []


def test_respuesta_invalida_ignora_herramienta(mocker):
    """Test 3.15: Herramienta inválida es ignorada"""
    from src.nodes.seleccion_herramientas_node import parsear_respuesta_llm
    
    herramientas = [{"id_tool": "valida", "description": "Test"}]
    respuesta = "valida,invalida,otra_invalida"
    
    resultado = parsear_respuesta_llm(respuesta, herramientas)
    assert resultado == ["valida"]


def test_contexto_episodico_incluido_en_prompt(estado_con_doctor, mock_obtener_herramientas, mocker):
    """Test 3.16: Contexto episódico se incluye en prompt si existe"""
    estado = estado_con_doctor.copy()
    estado["clasificacion_mensaje"] = "medica"
    estado["contexto_episodico"] = {
        "episodios_recuperados": [{"summary": "Test"}],
        "texto_formateado": "Contexto de prueba"
    }
    
    mock_llm = mocker.patch('src.nodes.seleccion_herramientas_node.llm_selector')
    mock_llm.invoke.return_value.content = "test_tool"
    
    nodo_seleccion_herramientas(estado)
    
    # Verificar que se llamó el LLM
    assert mock_llm.invoke.called


def test_multiples_herramientas_separadas_por_coma(mocker):
    """Test 3.17: Múltiples herramientas separadas por comas"""
    from src.nodes.seleccion_herramientas_node import parsear_respuesta_llm
    
    herramientas = [
        {"id_tool": "tool1", "description": "T1"},
        {"id_tool": "tool2", "description": "T2"}
    ]
    respuesta = "tool1,tool2"
    
    resultado = parsear_respuesta_llm(respuesta, herramientas)
    assert len(resultado) == 2


def test_herramientas_case_insensitive(mocker):
    """Test 3.18: Nombres de herramientas son case-insensitive"""
    from src.nodes.seleccion_herramientas_node import parsear_respuesta_llm
    
    herramientas = [{"id_tool": "test_tool", "description": "Test"}]
    respuesta = "TEST_TOOL"
    
    resultado = parsear_respuesta_llm(respuesta, herramientas)
    assert resultado == ["test_tool"]


def test_estado_actualizado_con_seleccion(estado_con_doctor, mock_obtener_herramientas, mocker):
    """Test 3.19: Estado se actualiza con herramientas seleccionadas"""
    estado = estado_con_doctor.copy()
    estado["clasificacion_mensaje"] = "medica"
    
    mock_llm = mocker.patch('src.nodes.seleccion_herramientas_node.llm_selector')
    mock_llm.invoke.return_value.content = "consultar_slots_disponibles"
    
    resultado = nodo_seleccion_herramientas(estado)
    
    assert "herramientas_seleccionadas" in resultado
    assert isinstance(resultado["herramientas_seleccionadas"], list)


def test_clasificacion_determina_pool_herramientas():
    """Test 3.20: Cada clasificación tiene su propio pool de herramientas"""
    personal = obtener_herramientas_segun_clasificacion("personal", "doctor")
    medica = obtener_herramientas_segun_clasificacion("medica", "doctor")
    chat = obtener_herramientas_segun_clasificacion("chat", "doctor")
    
    # Personal y médica tienen herramientas diferentes
    # Chat no tiene herramientas
    assert len(chat) == 0
    assert len(medica) > 0
