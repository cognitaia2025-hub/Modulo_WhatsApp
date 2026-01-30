"""
Tests para Router por Identidad
"""

import pytest
from src.nodes.router_identidad_node import (
    nodo_router_identidad,
    _es_saludo_inicial,
    _clasificar_doctor_rapido,
    _es_comando_admin
)
from langchain_core.messages import HumanMessage


# ==================== TESTS DE SALUDOS ====================

def test_es_saludo_simple():
    """Detecta saludos simples correctamente"""
    assert _es_saludo_inicial("Hola") == True
    assert _es_saludo_inicial("Buenos días") == True
    assert _es_saludo_inicial("Hola buenos días") == True
    assert _es_saludo_inicial("Hey") == True


def test_no_es_saludo_con_accion():
    """No detecta como saludo si lleva acción"""
    assert _es_saludo_inicial("Hola, necesito una cita") == False
    assert _es_saludo_inicial("Buenos días doctor, tengo una pregunta") == False
    assert _es_saludo_inicial("Quiero agendar") == False


# ==================== TESTS DE CLASIFICACIÓN DOCTOR ====================

def test_clasificar_doctor_medica():
    """Detecta contexto médico correctamente"""
    state = {}
    
    assert _clasificar_doctor_rapido("revisar paciente Juan", state) == 'medica'
    assert _clasificar_doctor_rapido("cuántas consultas tengo hoy", state) == 'medica'
    assert _clasificar_doctor_rapido("ver historial de María", state) == 'medica'


def test_clasificar_doctor_personal():
    """Detecta contexto personal correctamente"""
    state = {}
    
    assert _clasificar_doctor_rapido("mi cumpleaños es mañana", state) == 'personal'
    assert _clasificar_doctor_rapido("recordarme ir al banco", state) == 'personal'
    assert _clasificar_doctor_rapido("evento personal el viernes", state) == 'personal'


def test_clasificar_doctor_ambiguo():
    """Detecta mensajes ambiguos que requieren LLM"""
    state = {}
    
    # "cita" sin contexto puede ser médico o personal
    assert _clasificar_doctor_rapido("agendar cita para mañana", state) == 'requiere_llm'


# ==================== TESTS DE COMANDOS ADMIN ====================

def test_comando_admin():
    """Detecta comandos administrativos"""
    assert _es_comando_admin("reporte de cancelaciones") == True
    assert _es_comando_admin("estadísticas de la semana") == True
    assert _es_comando_admin("dashboard") == True


def test_no_comando_admin():
    """No detecta mensajes normales como comandos admin"""
    assert _es_comando_admin("hola buenos días") == False
    assert _es_comando_admin("necesito una cita") == False


# ==================== TESTS DE ROUTING COMPLETO ====================

def test_routing_paciente_a_recepcionista():
    """Pacientes externos van directo a recepcionista"""
    state = {
        'tipo_usuario': 'paciente_externo',
        'messages': [HumanMessage(content="Necesito una cita")]
    }
    
    resultado = nodo_router_identidad(state)
    
    assert resultado['ruta_siguiente'] == 'recepcionista'
    assert resultado['clasificacion_mensaje'] == 'solicitud_cita_paciente'
    assert resultado['requiere_clasificacion_llm'] == False


def test_routing_paciente_saludo():
    """Pacientes con saludo van a respuesta conversacional"""
    state = {
        'tipo_usuario': 'paciente_externo',
        'messages': [HumanMessage(content="Hola")]
    }
    
    resultado = nodo_router_identidad(state)
    
    assert resultado['ruta_siguiente'] == 'respuesta_conversacional'
    assert resultado['clasificacion_mensaje'] == 'chat'


def test_routing_doctor_medico():
    """Doctor con mensaje médico va directo a recuperacion_medica"""
    state = {
        'tipo_usuario': 'doctor',
        'messages': [HumanMessage(content="revisar pacientes de hoy")]
    }
    
    resultado = nodo_router_identidad(state)
    
    assert resultado['ruta_siguiente'] == 'medica'
    assert resultado['clasificacion_mensaje'] == 'medica'
    assert resultado['requiere_clasificacion_llm'] == False


def test_routing_doctor_personal():
    """Doctor con mensaje personal va directo a recuperacion_episodica"""
    state = {
        'tipo_usuario': 'doctor',
        'messages': [HumanMessage(content="recordarme mi cumpleaños")]
    }
    
    resultado = nodo_router_identidad(state)
    
    assert resultado['ruta_siguiente'] == 'personal'
    assert resultado['clasificacion_mensaje'] == 'personal'
    assert resultado['requiere_clasificacion_llm'] == False


def test_routing_doctor_ambiguo():
    """Doctor con mensaje ambiguo requiere LLM"""
    state = {
        'tipo_usuario': 'doctor',
        'messages': [HumanMessage(content="agendar para mañana")]
    }
    
    resultado = nodo_router_identidad(state)
    
    assert resultado['ruta_siguiente'] == 'clasificador_llm'
    assert resultado['requiere_clasificacion_llm'] == True


def test_routing_admin():
    """Admin con comando admin va a procesador_admin"""
    state = {
        'tipo_usuario': 'admin',
        'es_admin': True,
        'messages': [HumanMessage(content="reporte de la semana")]
    }
    
    resultado = nodo_router_identidad(state)
    
    assert resultado['ruta_siguiente'] == 'procesador_admin'
    assert resultado['clasificacion_mensaje'] == 'administrativo'


def test_routing_tipo_usuario_desconocido():
    """Tipo de usuario desconocido va a respuesta conversacional"""
    state = {
        'tipo_usuario': 'desconocido',
        'messages': [HumanMessage(content="Hola, ¿cómo estás?")]
    }
    
    resultado = nodo_router_identidad(state)
    
    assert resultado['ruta_siguiente'] == 'respuesta_conversacional'
    assert resultado['clasificacion_mensaje'] == 'chat'


def test_detecta_saludo_variaciones():
    """Detecta diferentes variaciones de saludos"""
    assert _es_saludo_inicial("Buenos días") == True
    assert _es_saludo_inicial("Buenas tardes") == True
    assert _es_saludo_inicial("Buenas noches") == True
    assert _es_saludo_inicial("Qué tal") == True
    assert _es_saludo_inicial("Holi") == True
    assert _es_saludo_inicial("Saludos") == True


def test_no_detecta_saludo_largo():
    """No detecta mensajes largos como saludos simples"""
    assert _es_saludo_inicial("Hola buenos días doctor cómo está") == False
    assert _es_saludo_inicial("Hola necesito hablar con alguien urgente") == False


def test_clasificar_doctor_con_contexto():
    """Usa contexto episódico para desambiguar cuando es posible"""
    state_con_contexto = {
        'contexto_episodico': {
            'resumen': 'Conversación previa sobre paciente Juan'
        }
    }
    
    resultado = _clasificar_doctor_rapido("agendar cita", state_con_contexto)
    assert resultado == 'medica'  # Usa contexto para clasificar como médico


def test_clasificar_doctor_palabras_inequivocas():
    """Detecta palabras inequívocas de contexto médico"""
    state = {}
    
    # Médico inequívoco
    assert _clasificar_doctor_rapido("ver expediente del paciente", state) == 'medica'
    assert _clasificar_doctor_rapido("mi consultorio está libre?", state) == 'medica'
    assert _clasificar_doctor_rapido("receta para el tratamiento", state) == 'medica'
    
    # Personal inequívoco
    assert _clasificar_doctor_rapido("ir al banco mañana", state) == 'personal'
    assert _clasificar_doctor_rapido("comprar regalo para mi esposa", state) == 'personal'
    assert _clasificar_doctor_rapido("vacaciones en diciembre", state) == 'personal'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
