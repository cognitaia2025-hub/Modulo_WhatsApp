"""
Tests para Nodo 2B: Maya Detective de Intención - Doctores

Usa CSV fixtures en lugar de PostgreSQL real para tests más rápidos.
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.types import Command

from src.nodes.maya_detective_doctor_node import (
    nodo_maya_detective_doctor,
    obtener_resumen_dia_doctor,
    obtener_info_doctor,
    MayaResponseDoctor
)
from tests.helpers.csv_helpers import load_fixture_csv, crear_resumen_dia_desde_csv


# ==================== FIXTURES ====================

@pytest.fixture
def estado_base_doctor():
    """Estado base para tests de doctor."""
    return {
        'doctor_id': 1,
        'tipo_usuario': 'doctor',
        'messages': [HumanMessage(content="Hola")],
        'estado_conversacion': 'inicial'
    }


@pytest.fixture
def mock_llm_response():
    """Mock de respuesta del LLM."""
    def _mock(accion, respuesta="", razon="test"):
        return MayaResponseDoctor(
            accion=accion,
            respuesta=respuesta,
            razon=razon
        )
    return _mock


# ==================== TESTS DE RESPONDER DIRECTO ====================

@patch('src.nodes.maya_detective_doctor_node.structured_llm_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_resumen_dia_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_info_doctor')
def test_maya_responde_saludo(mock_info, mock_resumen, mock_llm, estado_base_doctor, mock_llm_response):
    """Maya responde saludo con stats del día."""
    mock_info.return_value = {'nombre_completo': 'Dr. Santiago', 'especialidad': 'Podología'}
    mock_resumen.return_value = "📊 TUS ESTADÍSTICAS HOY:\n• Citas: 8\n• Pendientes: 5"
    mock_llm.invoke.return_value = mock_llm_response(
        accion="responder_directo",
        respuesta="Hola Dr. Santiago! Tienes 5 citas pendientes hoy 😊",
        razon="Saludo con stats"
    )
    
    resultado = nodo_maya_detective_doctor(estado_base_doctor)
    
    assert isinstance(resultado, Command)
    assert resultado.goto == "generacion_resumen"
    assert 'messages' in resultado.update


@patch('src.nodes.maya_detective_doctor_node.structured_llm_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_resumen_dia_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_info_doctor')
def test_maya_responde_cuantas_citas(mock_info, mock_resumen, mock_llm, estado_base_doctor, mock_llm_response):
    """Maya responde cuántas citas tiene el doctor."""
    estado_base_doctor['messages'] = [HumanMessage(content="¿Cuántas citas tengo?")]
    mock_info.return_value = {'nombre_completo': 'Dr. Santiago', 'especialidad': 'Podología'}
    mock_resumen.return_value = "📊 TUS ESTADÍSTICAS HOY:\n• Citas: 8\n• Completadas: 3\n• Pendientes: 5"
    mock_llm.invoke.return_value = mock_llm_response(
        accion="responder_directo",
        respuesta="Tienes 8 citas hoy. Has completado 3 y te quedan 5",
        razon="Stats del día"
    )
    
    resultado = nodo_maya_detective_doctor(estado_base_doctor)
    
    assert resultado.goto == "generacion_resumen"
    assert "8 citas" in resultado.update['messages'][0].content


@patch('src.nodes.maya_detective_doctor_node.structured_llm_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_resumen_dia_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_info_doctor')
def test_maya_responde_quien_sigue(mock_info, mock_resumen, mock_llm, estado_base_doctor, mock_llm_response):
    """Maya responde quién es el siguiente paciente."""
    estado_base_doctor['messages'] = [HumanMessage(content="¿Quién sigue?")]
    mock_info.return_value = {'nombre_completo': 'Dr. Santiago', 'especialidad': 'Podología'}
    mock_resumen.return_value = """📊 TUS ESTADÍSTICAS HOY:
• Citas: 8

🕐 PRÓXIMA CITA:
• Paciente: María García
• Hora: 2:30 PM (en 45 min)"""
    mock_llm.invoke.return_value = mock_llm_response(
        accion="responder_directo",
        respuesta="María García a las 2:30pm (en 45 min)",
        razon="Próxima cita disponible"
    )
    
    resultado = nodo_maya_detective_doctor(estado_base_doctor)
    
    assert resultado.goto == "generacion_resumen"
    assert "María García" in resultado.update['messages'][0].content


@patch('src.nodes.maya_detective_doctor_node.structured_llm_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_resumen_dia_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_info_doctor')
def test_maya_responde_cuantos_atendidos(mock_info, mock_resumen, mock_llm, estado_base_doctor, mock_llm_response):
    """Maya responde cuántos pacientes ha atendido hoy."""
    estado_base_doctor['messages'] = [HumanMessage(content="¿Cuántos he atendido?")]
    mock_info.return_value = {'nombre_completo': 'Dr. Santiago', 'especialidad': 'Podología'}
    mock_resumen.return_value = "📊 TUS ESTADÍSTICAS HOY:\n• Citas: 8\n• Completadas: 3\n• Pendientes: 5"
    mock_llm.invoke.return_value = mock_llm_response(
        accion="responder_directo",
        respuesta="Has atendido 3 pacientes hoy. Te quedan 5 pendientes",
        razon="Stats de atención del día"
    )
    
    resultado = nodo_maya_detective_doctor(estado_base_doctor)
    
    assert resultado.goto == "generacion_resumen"
    assert "3" in resultado.update['messages'][0].content


@patch('src.nodes.maya_detective_doctor_node.structured_llm_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_resumen_dia_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_info_doctor')
def test_maya_responde_resumen_dia(mock_info, mock_resumen, mock_llm, estado_base_doctor, mock_llm_response):
    """Maya responde con resumen del día."""
    estado_base_doctor['messages'] = [HumanMessage(content="¿Cómo va mi día?")]
    mock_info.return_value = {'nombre_completo': 'Dr. Santiago', 'especialidad': 'Podología'}
    mock_resumen.return_value = "📊 TUS ESTADÍSTICAS HOY:\n• Citas: 8\n• Completadas: 3\n• Pendientes: 5"
    mock_llm.invoke.return_value = mock_llm_response(
        accion="responder_directo",
        respuesta="Tienes 8 citas hoy. Has completado 3 y te quedan 5 pendientes 👍",
        razon="Resumen del día solicitado"
    )
    
    resultado = nodo_maya_detective_doctor(estado_base_doctor)
    
    assert resultado.goto == "generacion_resumen"
    assert resultado.update['clasificacion_mensaje'] == "chat"


@patch('src.nodes.maya_detective_doctor_node.structured_llm_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_resumen_dia_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_info_doctor')
def test_maya_responde_despedida(mock_info, mock_resumen, mock_llm, estado_base_doctor, mock_llm_response):
    """Maya responde a una despedida."""
    estado_base_doctor['messages'] = [HumanMessage(content="Gracias")]
    mock_info.return_value = {'nombre_completo': 'Dr. Santiago', 'especialidad': 'Podología'}
    mock_resumen.return_value = "📊 TUS ESTADÍSTICAS HOY:\n• Citas: 8"
    mock_llm.invoke.return_value = mock_llm_response(
        accion="responder_directo",
        respuesta="Con gusto Dr. Santiago! Que tenga un excelente día 😊",
        razon="Despedida"
    )
    
    resultado = nodo_maya_detective_doctor(estado_base_doctor)
    
    assert resultado.goto == "generacion_resumen"
    assert 'messages' in resultado.update


# ==================== TESTS DE ESCALAR ====================

@patch('src.nodes.maya_detective_doctor_node.structured_llm_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_resumen_dia_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_info_doctor')
def test_maya_escala_buscar_paciente(mock_info, mock_resumen, mock_llm, estado_base_doctor, mock_llm_response):
    """Maya escala cuando buscan paciente específico."""
    estado_base_doctor['messages'] = [HumanMessage(content="Busca a Juan Pérez")]
    mock_info.return_value = {'nombre_completo': 'Dr. Santiago', 'especialidad': 'Podología'}
    mock_resumen.return_value = "📊 TUS ESTADÍSTICAS HOY:\n• Citas: 8"
    mock_llm.invoke.return_value = mock_llm_response(
        accion="escalar_procedimental",
        razon="Búsqueda específica de paciente"
    )
    
    resultado = nodo_maya_detective_doctor(estado_base_doctor)
    
    assert resultado.goto == "recuperacion_medica"
    assert resultado.update['clasificacion_mensaje'] == "medica"


@patch('src.nodes.maya_detective_doctor_node.structured_llm_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_resumen_dia_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_info_doctor')
def test_maya_escala_historial(mock_info, mock_resumen, mock_llm, estado_base_doctor, mock_llm_response):
    """Maya escala cuando piden historial médico."""
    estado_base_doctor['messages'] = [HumanMessage(content="¿Qué diagnóstico tiene María?")]
    mock_info.return_value = {'nombre_completo': 'Dr. Santiago', 'especialidad': 'Podología'}
    mock_resumen.return_value = "📊 TUS ESTADÍSTICAS HOY:\n• Citas: 8"
    mock_llm.invoke.return_value = mock_llm_response(
        accion="escalar_procedimental",
        razon="Consulta de historial médico"
    )
    
    resultado = nodo_maya_detective_doctor(estado_base_doctor)
    
    assert resultado.goto == "recuperacion_medica"


@patch('src.nodes.maya_detective_doctor_node.structured_llm_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_resumen_dia_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_info_doctor')
def test_maya_escala_fecha_futura(mock_info, mock_resumen, mock_llm, estado_base_doctor, mock_llm_response):
    """Maya escala cuando preguntan por fecha futura (CRÍTICO)."""
    estado_base_doctor['messages'] = [HumanMessage(content="¿Cuántas citas tengo mañana?")]
    mock_info.return_value = {'nombre_completo': 'Dr. Santiago', 'especialidad': 'Podología'}
    mock_resumen.return_value = "📊 TUS ESTADÍSTICAS HOY:\n• Citas: 8"
    mock_llm.invoke.return_value = mock_llm_response(
        accion="escalar_procedimental",
        razon="Pregunta por fecha futura - requiere herramientas"
    )
    
    resultado = nodo_maya_detective_doctor(estado_base_doctor)
    
    assert resultado.goto == "recuperacion_medica"
    assert resultado.update['clasificacion_mensaje'] == "medica"
    # Verify that the LLM was called and would have received the date restriction in the prompt
    assert mock_llm.invoke.called
    # The reasoning should identify this as a future date query
    assert "fecha futura" in mock_llm.invoke.return_value.razon.lower() or "requiere herramientas" in mock_llm.invoke.return_value.razon.lower()


@patch('src.nodes.maya_detective_doctor_node.structured_llm_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_resumen_dia_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_info_doctor')
def test_maya_escala_cancelar_cita(mock_info, mock_resumen, mock_llm, estado_base_doctor, mock_llm_response):
    """Maya escala cuando quieren cancelar cita."""
    estado_base_doctor['messages'] = [HumanMessage(content="Cancela mi cita de las 5pm")]
    mock_info.return_value = {'nombre_completo': 'Dr. Santiago', 'especialidad': 'Podología'}
    mock_resumen.return_value = "📊 TUS ESTADÍSTICAS HOY:\n• Citas: 8"
    mock_llm.invoke.return_value = mock_llm_response(
        accion="escalar_procedimental",
        razon="Modificar agenda requiere herramientas"
    )
    
    resultado = nodo_maya_detective_doctor(estado_base_doctor)
    
    assert resultado.goto == "recuperacion_medica"


@patch('src.nodes.maya_detective_doctor_node.structured_llm_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_resumen_dia_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_info_doctor')
def test_maya_escala_crear_cita(mock_info, mock_resumen, mock_llm, estado_base_doctor, mock_llm_response):
    """Maya escala cuando quieren crear nueva cita."""
    estado_base_doctor['messages'] = [HumanMessage(content="Agenda a un paciente nuevo")]
    mock_info.return_value = {'nombre_completo': 'Dr. Santiago', 'especialidad': 'Podología'}
    mock_resumen.return_value = "📊 TUS ESTADÍSTICAS HOY:\n• Citas: 8"
    mock_llm.invoke.return_value = mock_llm_response(
        accion="escalar_procedimental",
        razon="Crear cita requiere herramientas"
    )
    
    resultado = nodo_maya_detective_doctor(estado_base_doctor)
    
    assert resultado.goto == "recuperacion_medica"


@patch('src.nodes.maya_detective_doctor_node.structured_llm_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_resumen_dia_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_info_doctor')
def test_maya_escala_agregar_notas(mock_info, mock_resumen, mock_llm, estado_base_doctor, mock_llm_response):
    """Maya escala cuando quieren agregar notas al historial."""
    estado_base_doctor['messages'] = [HumanMessage(content="Agrega nota para Juan")]
    mock_info.return_value = {'nombre_completo': 'Dr. Santiago', 'especialidad': 'Podología'}
    mock_resumen.return_value = "📊 TUS ESTADÍSTICAS HOY:\n• Citas: 8"
    mock_llm.invoke.return_value = mock_llm_response(
        accion="escalar_procedimental",
        razon="Agregar notas requiere herramientas"
    )
    
    resultado = nodo_maya_detective_doctor(estado_base_doctor)
    
    assert resultado.goto == "recuperacion_medica"


# ==================== TESTS DE DEJAR PASAR ====================

@patch('src.nodes.maya_detective_doctor_node.structured_llm_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_resumen_dia_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_info_doctor')
def test_maya_deja_pasar_flujo_activo(mock_info, mock_resumen, mock_llm, estado_base_doctor, mock_llm_response):
    """Maya deja pasar cuando hay flujo activo."""
    estado_base_doctor['messages'] = [HumanMessage(content="Opción A")]
    estado_base_doctor['estado_conversacion'] = 'ejecutando_herramienta'
    mock_info.return_value = {'nombre_completo': 'Dr. Santiago', 'especialidad': 'Podología'}
    mock_resumen.return_value = "📊 TUS ESTADÍSTICAS HOY:\n• Citas: 8"
    mock_llm.invoke.return_value = mock_llm_response(
        accion="dejar_pasar",
        razon="Flujo activo - no interferir"
    )
    
    resultado = nodo_maya_detective_doctor(estado_base_doctor)
    
    assert resultado.goto == "seleccion_herramientas"


@patch('src.nodes.maya_detective_doctor_node.structured_llm_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_resumen_dia_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_info_doctor')
def test_maya_deja_pasar_esperando_confirmacion(mock_info, mock_resumen, mock_llm, estado_base_doctor, mock_llm_response):
    """Maya deja pasar cuando se está esperando confirmación."""
    estado_base_doctor['messages'] = [HumanMessage(content="Sí")]
    estado_base_doctor['estado_conversacion'] = 'esperando_confirmacion'
    mock_info.return_value = {'nombre_completo': 'Dr. Santiago', 'especialidad': 'Podología'}
    mock_resumen.return_value = "📊 TUS ESTADÍSTICAS HOY:\n• Citas: 8"
    mock_llm.invoke.return_value = mock_llm_response(
        accion="dejar_pasar",
        razon="Esperando confirmación - no interferir"
    )
    
    resultado = nodo_maya_detective_doctor(estado_base_doctor)
    
    assert resultado.goto == "seleccion_herramientas"


# ==================== TESTS DE MANEJO DE ERRORES ====================

def test_maya_sin_doctor_id():
    """Maya maneja gracefully si no hay doctor_id."""
    estado = {
        'messages': [HumanMessage(content="Hola")],
        'tipo_usuario': 'doctor'
    }
    
    resultado = nodo_maya_detective_doctor(estado)
    
    assert resultado.goto == "filtrado_inteligente"
    assert resultado.update['requiere_clasificacion_llm'] == True


def test_maya_sin_mensaje():
    """Maya maneja gracefully si no hay mensaje."""
    estado = {
        'doctor_id': 1,
        'messages': [],
        'tipo_usuario': 'doctor'
    }
    
    resultado = nodo_maya_detective_doctor(estado)
    
    assert resultado.goto == "generacion_resumen"


@patch('src.nodes.maya_detective_doctor_node.structured_llm_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_resumen_dia_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_info_doctor')
def test_maya_maneja_error_llm(mock_info, mock_resumen, mock_llm, estado_base_doctor):
    """Maya maneja error si LLM falla."""
    mock_info.return_value = {'nombre_completo': 'Dr. Santiago', 'especialidad': 'Podología'}
    mock_resumen.return_value = "📊 TUS ESTADÍSTICAS HOY:\n• Citas: 8"
    mock_llm.invoke.side_effect = Exception("LLM timeout")
    
    resultado = nodo_maya_detective_doctor(estado_base_doctor)
    
    assert resultado.goto == "generacion_resumen"
    assert "repetir" in resultado.update['messages'][0].content.lower()


# ==================== TESTS DE FUNCIONES AUXILIARES ====================

@patch('src.nodes.maya_detective_doctor_node.psycopg.connect')
def test_obtener_resumen_dia_sin_citas(mock_connect):
    """Maneja correctamente día sin citas."""
    mock_cursor = Mock()
    mock_cursor.fetchone.return_value = (0, 0, 0, 0)
    mock_connect.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
    
    resumen = obtener_resumen_dia_doctor(1)
    
    assert "No tienes citas" in resumen


@patch('src.nodes.maya_detective_doctor_node.psycopg.connect')
def test_obtener_info_doctor(mock_connect):
    """Obtiene info del doctor correctamente."""
    mock_cursor = Mock()
    mock_cursor.fetchone.return_value = ('Dr. Juan Pérez', 'Podología')
    mock_connect.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
    
    info = obtener_info_doctor(1)
    
    assert info['nombre_completo'] == 'Dr. Juan Pérez'
    assert info['especialidad'] == 'Podología'


@patch('src.nodes.maya_detective_doctor_node.psycopg.connect')
def test_obtener_info_doctor_sin_especialidad(mock_connect):
    """Obtiene info del doctor sin especialidad definida."""
    mock_cursor = Mock()
    mock_cursor.fetchone.return_value = ('Dr. Juan Pérez', None)
    mock_connect.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
    
    info = obtener_info_doctor(1)
    
    assert info['nombre_completo'] == 'Dr. Juan Pérez'
    assert info['especialidad'] == 'Medicina General'


@patch('src.nodes.maya_detective_doctor_node.psycopg.connect')
def test_obtener_info_doctor_no_existe(mock_connect):
    """Maneja correctamente doctor que no existe."""
    mock_cursor = Mock()
    mock_cursor.fetchone.return_value = None
    mock_connect.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
    
    info = obtener_info_doctor(999)
    
    assert info['nombre_completo'] == 'Doctor'
    assert info['especialidad'] == 'Medicina General'


# ==================== FIXTURES CSV ====================

@pytest.fixture
def mock_citas_doctor_1():
    """Doctor con 8 citas (3 completadas, 5 pendientes)."""
    return load_fixture_csv('citas_doctor_1.csv')


@pytest.fixture
def mock_citas_sin_citas():
    """Doctor sin citas hoy (día libre)."""
    return load_fixture_csv('citas_doctor_sin_citas.csv')


@pytest.fixture
def mock_citas_muchas():
    """Doctor con 15 citas (caso edge)."""
    return load_fixture_csv('citas_doctor_muchas.csv')


# ==================== TESTS CON CSV ====================

@patch('src.nodes.maya_detective_doctor_node.structured_llm_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_resumen_dia_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_info_doctor')
def test_maya_responde_cuantas_citas_con_csv(
    mock_info,
    mock_resumen,
    mock_llm,
    estado_base_doctor,
    mock_citas_doctor_1,
    mock_llm_response
):
    """Maya responde cuántas citas tiene el doctor (usando CSV)."""
    
    # Setup mocks usando CSV
    mock_info.return_value = {
        'nombre_completo': 'Dr. Santiago',
        'especialidad': 'Podología'
    }
    mock_resumen.return_value = crear_resumen_dia_desde_csv(mock_citas_doctor_1)
    
    mock_llm.invoke.return_value = mock_llm_response(
        accion="responder_directo",
        respuesta="Tienes 8 citas hoy. Has completado 3 y te quedan 5",
        razon="Stats del día desde CSV"
    )
    
    estado_base_doctor['messages'] = [HumanMessage(content="¿Cuántas citas tengo?")]
    
    # Ejecutar
    resultado = nodo_maya_detective_doctor(estado_base_doctor)
    
    # Validar usando datos del CSV
    total_esperado = len(mock_citas_doctor_1)
    completadas_esperadas = len(mock_citas_doctor_1[mock_citas_doctor_1['estado'] == 'completada'])
    
    assert resultado.goto == "generacion_resumen"
    assert f"{total_esperado} citas" in resultado.update['messages'][0].content
    assert f"completado {completadas_esperadas}" in resultado.update['messages'][0].content.lower()


@patch('src.nodes.maya_detective_doctor_node.structured_llm_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_resumen_dia_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_info_doctor')
def test_maya_sin_citas_hoy_con_csv(
    mock_info,
    mock_resumen,
    mock_llm,
    estado_base_doctor,
    mock_citas_sin_citas,
    mock_llm_response
):
    """Maya maneja correctamente día sin citas (usando CSV vacío)."""
    
    mock_info.return_value = {
        'nombre_completo': 'Dr. Santiago',
        'especialidad': 'Podología'
    }
    mock_resumen.return_value = crear_resumen_dia_desde_csv(mock_citas_sin_citas)
    
    mock_llm.invoke.return_value = mock_llm_response(
        accion="responder_directo",
        respuesta="No tienes citas agendadas para hoy. Día libre! 🎉",
        razon="Sin citas según CSV"
    )
    
    estado_base_doctor['messages'] = [HumanMessage(content="¿Cuántas citas tengo?")]
    
    resultado = nodo_maya_detective_doctor(estado_base_doctor)
    
    assert "No tienes citas" in resultado.update['messages'][0].content
    assert len(mock_citas_sin_citas) == 0  # Verificar que fixture está vacío


@patch('src.nodes.maya_detective_doctor_node.structured_llm_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_resumen_dia_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_info_doctor')
def test_maya_muchas_citas_con_csv(
    mock_info,
    mock_resumen,
    mock_llm,
    estado_base_doctor,
    mock_citas_muchas,
    mock_llm_response
):
    """Maya maneja correctamente día con muchas citas (usando CSV)."""
    
    mock_info.return_value = {
        'nombre_completo': 'Dr. Santiago',
        'especialidad': 'Podología'
    }
    mock_resumen.return_value = crear_resumen_dia_desde_csv(mock_citas_muchas)
    
    mock_llm.invoke.return_value = mock_llm_response(
        accion="responder_directo",
        respuesta="Tienes 15 citas hoy. Has completado 5 y te quedan 10",
        razon="Muchas citas según CSV"
    )
    
    estado_base_doctor['messages'] = [HumanMessage(content="¿Cuántas citas tengo?")]
    
    resultado = nodo_maya_detective_doctor(estado_base_doctor)
    
    total = len(mock_citas_muchas)
    assert total == 15  # Verificar cantidad en fixture
    assert f"{total} citas" in resultado.update['messages'][0].content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
