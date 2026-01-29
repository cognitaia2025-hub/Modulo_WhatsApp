"""
TEST 1: test_filtrado_inteligente.py
Pruebas del nodo de filtrado inteligente con LLM

20 tests que validan:
- Clasificación correcta de mensajes
- Fallback DeepSeek → Claude
- Validación de permisos por tipo usuario
- Registro en BD
"""

import pytest
from unittest.mock import Mock, patch
from src.nodes.filtrado_inteligente_node import (
    nodo_filtrado_inteligente,
    construir_prompt_clasificacion,
    parsear_respuesta_llm,
    validar_clasificacion_por_tipo_usuario
)


# ============================================================================
# TESTS: Clasificación de Mensajes
# ============================================================================

def test_clasificar_solicitud_medica_doctor(estado_con_doctor, mock_llm_clasificacion, mock_registrar_clasificacion):
    """Test 1.1: Doctor dice 'mi paciente Juan' → clasificacion='medica'"""
    resultado = nodo_filtrado_inteligente(estado_con_doctor)
    
    assert resultado["clasificacion_mensaje"] == "medica"
    assert resultado["confianza_clasificacion"] >= 0.5


def test_clasificar_solicitud_personal(estado_con_paciente, mock_llm_clasificacion, mock_registrar_clasificacion):
    """Test 1.2: Usuario dice 'mi cumpleaños' → clasificacion='personal'"""
    mock_llm_clasificacion.invoke.return_value.content = '{"clasificacion": "personal", "confianza": 0.9}'
    
    estado = estado_con_paciente.copy()
    estado["messages"][0].content = "Recordarme mi cumpleaños mañana"
    
    resultado = nodo_filtrado_inteligente(estado)
    # Se corrige a solicitud_cita por ser paciente externo
    assert resultado["clasificacion_mensaje"] == "solicitud_cita_paciente"


def test_clasificar_chat_casual(estado_con_mensaje_chat, mock_llm_clasificacion, mock_registrar_clasificacion):
    """Test 1.3: Usuario dice 'hola' → clasificacion='chat'"""
    mock_llm_clasificacion.invoke.return_value.content = '{"clasificacion": "chat", "confianza": 0.99}'
    
    resultado = nodo_filtrado_inteligente(estado_con_mensaje_chat)
    
    assert resultado["clasificacion_mensaje"] == "chat"


def test_paciente_externo_solo_solicitud_cita(estado_con_paciente, mock_llm_clasificacion, mock_registrar_clasificacion):
    """Test 1.4: Paciente externo → siempre 'solicitud_cita_paciente'"""
    # LLM responde 'medica' pero se debe corregir
    mock_llm_clasificacion.invoke.return_value.content = '{"clasificacion": "medica", "confianza": 0.8}'
    
    resultado = nodo_filtrado_inteligente(estado_con_paciente)
    
    assert resultado["clasificacion_mensaje"] == "solicitud_cita_paciente"


def test_fallback_claude_si_deepseek_falla(estado_con_doctor, mocker, mock_registrar_clasificacion):
    """Test 1.5: Si DeepSeek falla → usar Claude automáticamente"""
    # Mock DeepSeek para fallar
    mock_deepseek = mocker.patch('src.nodes.filtrado_inteligente_node.llm_primary')
    mock_deepseek.invoke.side_effect = Exception("DeepSeek error")
    
    # Mock Claude para funcionar
    mock_claude = mocker.patch('src.nodes.filtrado_inteligente_node.llm_fallback')
    mock_claude.invoke.return_value.content = '{"clasificacion": "medica", "confianza": 0.9}'
    
    resultado = nodo_filtrado_inteligente(estado_con_doctor)
    
    assert resultado["clasificacion_mensaje"] == "medica"
    assert resultado["modelo_clasificacion_usado"] == "claude"


# ============================================================================
# TESTS: Parseo de Respuestas
# ============================================================================

def test_parsear_respuesta_json_valido():
    """Test 1.6: Parsea JSON válido correctamente"""
    respuesta = '{"clasificacion": "personal", "confianza": 0.95}'
    resultado = parsear_respuesta_llm(respuesta)
    
    assert resultado["clasificacion"] == "personal"
    assert resultado["confianza"] == 0.95


def test_parsear_respuesta_con_markdown():
    """Test 1.7: Parsea JSON envuelto en markdown"""
    respuesta = '```json\n{"clasificacion": "medica", "confianza": 0.9}\n```'
    resultado = parsear_respuesta_llm(respuesta)
    
    assert resultado["clasificacion"] == "medica"


def test_parsear_respuesta_invalida_fallback():
    """Test 1.8: Respuesta inválida → fallback a 'chat'"""
    respuesta = "esto no es JSON"
    resultado = parsear_respuesta_llm(respuesta)
    
    assert resultado["clasificacion"] == "chat"
    assert resultado["confianza"] == 0.5


def test_parsear_respuesta_sin_clasificacion():
    """Test 1.9: JSON sin campo 'clasificacion' → fallback"""
    respuesta = '{"confianza": 0.9}'
    resultado = parsear_respuesta_llm(respuesta)
    
    assert resultado["clasificacion"] == "chat"


# ============================================================================
# TESTS: Validación de Permisos
# ============================================================================

def test_validacion_paciente_no_puede_medica():
    """Test 1.10: Paciente externo no puede clasificarse como 'medica'"""
    clasificacion = validar_clasificacion_por_tipo_usuario("medica", "paciente_externo")
    
    assert clasificacion == "solicitud_cita_paciente"


def test_validacion_paciente_no_puede_personal():
    """Test 1.11: Paciente externo no puede clasificarse como 'personal'"""
    clasificacion = validar_clasificacion_por_tipo_usuario("personal", "paciente_externo")
    
    assert clasificacion == "solicitud_cita_paciente"


def test_validacion_doctor_mantiene_medica():
    """Test 1.12: Doctor puede mantener clasificación 'medica'"""
    clasificacion = validar_clasificacion_por_tipo_usuario("medica", "doctor")
    
    assert clasificacion == "medica"


def test_validacion_doctor_mantiene_personal():
    """Test 1.13: Doctor puede mantener clasificación 'personal'"""
    clasificacion = validar_clasificacion_por_tipo_usuario("personal", "doctor")
    
    assert clasificacion == "personal"


# ============================================================================
# TESTS: Construcción de Prompts
# ============================================================================

def test_construir_prompt_incluye_mensaje():
    """Test 1.14: Prompt incluye el mensaje del usuario"""
    mensaje = "Necesito una cita médica"
    prompt = construir_prompt_clasificacion(mensaje, "paciente_externo")
    
    assert len(prompt) == 2  # System + User
    assert mensaje in prompt[1].content


def test_construir_prompt_incluye_tipo_usuario():
    """Test 1.15: Prompt incluye el tipo de usuario"""
    mensaje = "Test"
    tipo = "doctor"
    prompt = construir_prompt_clasificacion(mensaje, tipo)
    
    assert tipo in prompt[1].content


# ============================================================================
# TESTS: Registro en BD
# ============================================================================

def test_registrar_clasificacion_en_bd(estado_con_doctor, mock_llm_clasificacion, mock_registrar_clasificacion):
    """Test 1.16: Clasificación se registra en BD"""
    nodo_filtrado_inteligente(estado_con_doctor)
    
    assert mock_registrar_clasificacion.called


def test_registro_incluye_tiempo_procesamiento(estado_con_doctor, mock_llm_clasificacion, mock_registrar_clasificacion):
    """Test 1.17: Registro incluye tiempo de procesamiento"""
    resultado = nodo_filtrado_inteligente(estado_con_doctor)
    
    assert "tiempo_clasificacion_ms" in resultado
    assert resultado["tiempo_clasificacion_ms"] > 0


# ============================================================================
# TESTS: Edge Cases
# ============================================================================

def test_mensaje_vacio_retorna_chat():
    """Test 1.18: Mensaje vacío → clasificación 'chat'"""
    estado = {
        "messages": [],
        "tipo_usuario": "paciente_externo",
        "user_id": "+526641234567"
    }
    
    resultado = nodo_filtrado_inteligente(estado)
    
    assert resultado["clasificacion_mensaje"] == "chat"


def test_ambos_llm_fallan_retorna_chat(estado_con_doctor, mocker, mock_registrar_clasificacion):
    """Test 1.19: Si ambos LLM fallan → clasificación 'chat'"""
    mocker.patch('src.nodes.filtrado_inteligente_node.llm_primary').invoke.side_effect = Exception()
    mocker.patch('src.nodes.filtrado_inteligente_node.llm_fallback').invoke.side_effect = Exception()
    
    resultado = nodo_filtrado_inteligente(estado_con_doctor)
    
    assert resultado["clasificacion_mensaje"] == "chat"
    assert resultado["confianza_clasificacion"] == 0.3


def test_timeout_llm_usa_fallback(estado_con_doctor, mocker, mock_registrar_clasificacion):
    """Test 1.20: Timeout de LLM → usa fallback automático"""
    mock_primary = mocker.patch('src.nodes.filtrado_inteligente_node.llm_primary')
    mock_primary.invoke.side_effect = TimeoutError("Timeout")
    
    mock_fallback = mocker.patch('src.nodes.filtrado_inteligente_node.llm_fallback')
    mock_fallback.invoke.return_value.content = '{"clasificacion": "medica", "confianza": 0.9}'
    
    resultado = nodo_filtrado_inteligente(estado_con_doctor)
    
    assert resultado["modelo_clasificacion_usado"] == "claude"
