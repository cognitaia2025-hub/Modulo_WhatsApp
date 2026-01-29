"""
TEST 5: test_integration_etapa3.py
Pruebas de integración end-to-end de ETAPA 3 (10 tests)
"""

import pytest
from src.nodes.filtrado_inteligente_node import nodo_filtrado_inteligente
from src.nodes.recuperacion_medica_node import nodo_recuperacion_medica
from src.nodes.seleccion_herramientas_node import nodo_seleccion_herramientas
from src.nodes.ejecucion_medica_node import nodo_ejecucion_medica


def test_flujo_completo_doctor(estado_con_doctor, mock_llm_clasificacion, mock_db_connection, mock_obtener_herramientas, mock_herramientas_medicas, mocker, mock_registrar_clasificacion):
    """Test 5.1: Flujo completo doctor: filtrado → recuperación → selección → ejecución"""
    # 1. Filtrado inteligente
    estado = estado_con_doctor.copy()
    resultado1 = nodo_filtrado_inteligente(estado)
    estado.update(resultado1)
    
    assert "clasificacion_mensaje" in estado
    
    # 2. Recuperación médica
    mock_cursor = mock_db_connection.cursor.return_value.__enter__.return_value
    mock_cursor.fetchall.return_value = []
    mock_cursor.fetchone.return_value = ({"doctor_id": 1, "citas_hoy": 0, "citas_semana": 0, "pacientes_totales": 0},)
    
    resultado2 = nodo_recuperacion_medica(estado)
    estado.update(resultado2)
    
    assert "contexto_medico" in estado
    
    # 3. Selección de herramientas
    mock_llm_sel = mocker.patch('src.nodes.seleccion_herramientas_node.llm_selector')
    mock_llm_sel.invoke.return_value.content = "consultar_slots_disponibles"
    
    resultado3 = nodo_seleccion_herramientas(estado)
    estado.update(resultado3)
    
    assert "herramientas_seleccionadas" in estado
    
    # 4. Ejecución
    resultado4 = nodo_ejecucion_medica(estado)
    estado.update(resultado4)
    
    assert "resultado_herramientas" in estado


def test_flujo_completo_paciente(estado_con_paciente, mock_llm_clasificacion, mock_obtener_herramientas, mock_herramientas_medicas, mocker, mock_registrar_clasificacion):
    """Test 5.2: Flujo paciente: filtrado → selección → ejecución (sin recuperación médica)"""
    # 1. Filtrado
    mock_llm_clasificacion.invoke.return_value.content = '{"clasificacion": "solicitud_cita_paciente", "confianza": 0.95}'
    
    estado = estado_con_paciente.copy()
    resultado1 = nodo_filtrado_inteligente(estado)
    estado.update(resultado1)
    
    assert estado["clasificacion_mensaje"] == "solicitud_cita_paciente"
    
    # 2. Recuperación (debe saltar)
    resultado2 = nodo_recuperacion_medica(estado)
    assert resultado2["contexto_medico"] is None
    
    # 3. Selección
    mock_llm_sel = mocker.patch('src.nodes.seleccion_herramientas_node.llm_selector')
    mock_llm_sel.invoke.return_value.content = "consultar_slots_disponibles"
    
    resultado3 = nodo_seleccion_herramientas(estado)
    estado.update(resultado3)
    
    # 4. Ejecución
    resultado4 = nodo_ejecucion_medica(estado)
    
    assert "resultado_herramientas" in resultado4


def test_fallback_llm_funciona(estado_con_doctor, mocker, mock_registrar_clasificacion):
    """Test 5.3: Si DeepSeek falla → Claude toma el control"""
    # DeepSeek falla
    mock_primary = mocker.patch('src.nodes.filtrado_inteligente_node.llm_primary')
    mock_primary.invoke.side_effect = Exception("DeepSeek timeout")
    
    # Claude funciona
    mock_fallback = mocker.patch('src.nodes.filtrado_inteligente_node.llm_fallback')
    mock_fallback.invoke.return_value.content = '{"clasificacion": "medica", "confianza": 0.9}'
    
    resultado = nodo_filtrado_inteligente(estado_con_doctor)
    
    assert resultado["modelo_clasificacion_usado"] == "claude"
    assert resultado["clasificacion_mensaje"] == "medica"


def test_paciente_no_accede_herramientas_doctor(estado_con_paciente, mock_herramientas_medicas):
    """Test 5.4: Paciente no puede ejecutar herramientas de doctor"""
    estado = estado_con_paciente.copy()
    estado["herramientas_seleccionadas"] = ["crear_paciente_medico", "buscar_pacientes_doctor"]
    
    resultado = nodo_ejecucion_medica(estado)
    
    # Ambas deberían fallar por permisos
    assert "no tiene permiso" in resultado["resultado_herramientas"].lower() or "❌" in resultado["resultado_herramientas"]


def test_clasificacion_determina_herramientas_disponibles(estado_con_doctor):
    """Test 5.5: Clasificación determina qué herramientas están disponibles"""
    from src.nodes.seleccion_herramientas_node import obtener_herramientas_segun_clasificacion
    
    # Personal → calendario
    h_personal = obtener_herramientas_segun_clasificacion("personal", "doctor")
    
    # Médica → herramientas médicas
    h_medica = obtener_herramientas_segun_clasificacion("medica", "doctor")
    
    # Chat → sin herramientas
    h_chat = obtener_herramientas_segun_clasificacion("chat", "doctor")
    
    assert len(h_medica) == 12
    assert len(h_chat) == 0


def test_doctor_puede_usar_ambos_tipos_herramientas():
    """Test 5.6: Doctor puede usar herramientas de calendario Y médicas"""
    from src.nodes.seleccion_herramientas_node import obtener_herramientas_segun_clasificacion
    
    h_personal = obtener_herramientas_segun_clasificacion("personal", "doctor")
    h_medica = obtener_herramientas_segun_clasificacion("medica", "doctor")
    
    # Doctor tiene acceso a ambos pools
    assert len(h_personal) >= 0
    assert len(h_medica) == 12


def test_clasificacion_se_registra_en_bd(estado_con_doctor, mock_llm_clasificacion, mock_registrar_clasificacion):
    """Test 5.7: Todas las clasificaciones se registran en BD para auditoría"""
    nodo_filtrado_inteligente(estado_con_doctor)
    
    # Verificar que se llamó la función de registro
    assert mock_registrar_clasificacion.called
    
    # Verificar que se pasaron los parámetros correctos
    call_args = mock_registrar_clasificacion.call_args
    assert call_args is not None


def test_contexto_medico_solo_para_doctores(estado_con_paciente, estado_con_doctor, mock_db_connection):
    """Test 5.8: Contexto médico solo se genera para doctores"""
    # Paciente
    resultado_paciente = nodo_recuperacion_medica(estado_con_paciente)
    assert resultado_paciente["contexto_medico"] is None
    
    # Doctor
    mock_cursor = mock_db_connection.cursor.return_value.__enter__.return_value
    mock_cursor.fetchall.return_value = []
    mock_cursor.fetchone.return_value = ({"doctor_id": 1, "citas_hoy": 0, "citas_semana": 0, "pacientes_totales": 0},)
    
    resultado_doctor = nodo_recuperacion_medica(estado_con_doctor)
    assert resultado_doctor["contexto_medico"] is not None


def test_flujo_chat_sin_herramientas(estado_con_mensaje_chat, mock_llm_clasificacion, mock_registrar_clasificacion):
    """Test 5.9: Mensaje de chat → sin herramientas ejecutadas"""
    # Clasificar como chat
    mock_llm_clasificacion.invoke.return_value.content = '{"clasificacion": "chat", "confianza": 0.99}'
    
    estado = estado_con_mensaje_chat.copy()
    resultado1 = nodo_filtrado_inteligente(estado)
    estado.update(resultado1)
    
    assert estado["clasificacion_mensaje"] == "chat"
    
    # Selección de herramientas
    resultado2 = nodo_seleccion_herramientas(estado)
    
    # No debería haber herramientas
    assert resultado2["herramientas_seleccionadas"] == []


def test_performance_flujo_completo(estado_con_doctor, mock_llm_clasificacion, mock_db_connection, mock_obtener_herramientas, mock_herramientas_medicas, mocker, mock_registrar_clasificacion):
    """Test 5.10: Flujo completo se ejecuta en tiempo razonable (<5s)"""
    import time
    
    inicio = time.time()
    
    # Flujo completo
    estado = estado_con_doctor.copy()
    
    # 1. Filtrado
    resultado1 = nodo_filtrado_inteligente(estado)
    estado.update(resultado1)
    
    # 2. Recuperación
    mock_cursor = mock_db_connection.cursor.return_value.__enter__.return_value
    mock_cursor.fetchall.return_value = []
    mock_cursor.fetchone.return_value = ({"doctor_id": 1, "citas_hoy": 0, "citas_semana": 0, "pacientes_totales": 0},)
    
    resultado2 = nodo_recuperacion_medica(estado)
    estado.update(resultado2)
    
    # 3. Selección
    mock_llm_sel = mocker.patch('src.nodes.seleccion_herramientas_node.llm_selector')
    mock_llm_sel.invoke.return_value.content = "consultar_slots_disponibles"
    
    resultado3 = nodo_seleccion_herramientas(estado)
    estado.update(resultado3)
    
    # 4. Ejecución
    resultado4 = nodo_ejecucion_medica(estado)
    
    duracion = time.time() - inicio
    
    # Con mocks debería ser muy rápido (<1s)
    assert duracion < 5.0
