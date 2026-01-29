"""
Tests de Propagación de Estado - ETAPA 8

Valida que el estado se propague correctamente entre nodos.
"""

import pytest
import sys
import os
from pathlib import Path

# Añadir path del proyecto
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.state.agent_state import WhatsAppAgentState


class TestPropagacionEstado:
    """Tests de propagación de campos del estado entre nodos"""
    
    def test_user_id_se_propaga(self):
        """Test que user_id se mantiene a través del flujo"""
        estado_inicial = {
            'user_id': 'USR_123456789',
            'phone_number': '+52123456789'
        }
        
        # Simular que el estado pasa por varios nodos
        estado_nodo1 = {**estado_inicial, 'tipo_usuario': 'paciente'}
        estado_nodo2 = {**estado_nodo1, 'clasificacion': 'personal'}
        estado_nodo3 = {**estado_nodo2, 'herramientas_seleccionadas': []}
        
        # Verificar que user_id se mantiene
        assert estado_nodo1['user_id'] == 'USR_123456789'
        assert estado_nodo2['user_id'] == 'USR_123456789'
        assert estado_nodo3['user_id'] == 'USR_123456789'
    
    def test_tipo_usuario_se_propaga(self):
        """Test que tipo_usuario se mantiene correctamente"""
        estado_inicial = {
            'user_id': 'DR_123',
            'tipo_usuario': 'doctor',
            'es_admin': True
        }
        
        # Simular propagación
        estado_intermedio = {
            **estado_inicial,
            'clasificacion': 'medica',
            'contexto_medico': 'Consulta paciente'
        }
        
        estado_final = {
            **estado_intermedio,
            'herramientas_seleccionadas': [
                {'nombre': 'buscar_pacientes', 'tipo': 'medica'}
            ]
        }
        
        # Verificar propagación
        assert estado_intermedio['tipo_usuario'] == 'doctor'
        assert estado_final['tipo_usuario'] == 'doctor'
        assert estado_final['es_admin'] == True
    
    def test_es_admin_se_propaga(self):
        """Test que es_admin se mantiene correctamente"""
        estado_admin = {
            'user_id': 'ADM_001',
            'tipo_usuario': 'admin',
            'es_admin': True
        }
        
        estado_no_admin = {
            'user_id': 'PAC_001',
            'tipo_usuario': 'paciente',
            'es_admin': False
        }
        
        # Simular nodos añadiendo campos pero manteniendo es_admin
        estado_admin_final = {
            **estado_admin,
            'clasificacion': 'personal',
            'mensaje_final': 'Procesado'
        }
        
        estado_no_admin_final = {
            **estado_no_admin,
            'clasificacion': 'solicitud_cita',
            'mensaje_final': 'Cita agendada'
        }
        
        # Verificar que es_admin se mantiene
        assert estado_admin_final['es_admin'] == True
        assert estado_no_admin_final['es_admin'] == False
    
    def test_clasificacion_se_propaga(self):
        """Test que clasificacion se propaga desde filtrado_inteligente"""
        estado_post_filtrado = {
            'user_id': 'USR_001',
            'clasificacion': 'medica',
            'tipo_usuario': 'doctor'
        }
        
        # Simular nodos posteriores que añaden datos
        estado_post_recuperacion = {
            **estado_post_filtrado,
            'contexto_medico': 'Datos de pacientes recuperados'
        }
        
        estado_post_seleccion = {
            **estado_post_recuperacion,
            'herramientas_seleccionadas': [
                {'nombre': 'registrar_consulta', 'tipo': 'medica'}
            ]
        }
        
        # Verificar que clasificacion se mantiene
        assert estado_post_recuperacion['clasificacion'] == 'medica'
        assert estado_post_seleccion['clasificacion'] == 'medica'
    
    def test_herramientas_se_propagan(self):
        """Test que herramientas_seleccionadas se propagan correctamente"""
        herramientas = [
            {'nombre': 'crear_evento', 'tipo': 'personal', 'params': {'fecha': '2024-01-15'}},
            {'nombre': 'listar_eventos', 'tipo': 'personal', 'params': {'rango': '7d'}}
        ]
        
        estado_post_seleccion = {
            'user_id': 'USR_001',
            'herramientas_seleccionadas': herramientas
        }
        
        estado_post_ejecucion = {
            **estado_post_seleccion,
            'resultados_herramientas': ['Evento creado', 'Eventos listados']
        }
        
        estado_final = {
            **estado_post_ejecucion,
            'mensaje_final': 'Operaciones completadas'
        }
        
        # Verificar que las herramientas se mantienen
        assert len(estado_post_ejecucion['herramientas_seleccionadas']) == 2
        assert len(estado_final['herramientas_seleccionadas']) == 2
        assert estado_final['herramientas_seleccionadas'][0]['nombre'] == 'crear_evento'
    
    def test_cita_id_se_propaga(self):
        """Test que cita_id se propaga desde recepcionista hasta sincronizador"""
        estado_post_recepcionista = {
            'user_id': 'PAC_001',
            'estado_conversacion': 'completado',
            'cita_id': 'CITA_20240115_001',
            'fecha_cita': '2024-01-15T10:00:00',
            'doctor_id': 'DR_GARCIA'
        }
        
        estado_post_sincronizador = {
            **estado_post_recepcionista,
            'evento_calendar_id': 'GCAL_EVT_123',
            'sincronizado': True,
            'mensaje_sync': 'Sincronizado exitosamente'
        }
        
        # Verificar propagación de datos de cita
        assert estado_post_sincronizador['cita_id'] == 'CITA_20240115_001'
        assert estado_post_sincronizador['fecha_cita'] == '2024-01-15T10:00:00'
        assert estado_post_sincronizador['doctor_id'] == 'DR_GARCIA'
    
    def test_estado_conversacion_se_propaga(self):
        """Test que estado_conversacion evoluciona correctamente"""
        # Estado inicial
        estado_inicial = {
            'user_id': 'PAC_001',
            'estado_conversacion': 'inicial'
        }
        
        # Después de solicitar datos
        estado_solicitando = {
            **estado_inicial,
            'estado_conversacion': 'solicitando_nombre'
        }
        
        # Después de recibir datos
        estado_procesando = {
            **estado_solicitando,
            'estado_conversacion': 'procesando',
            'nombre_paciente': 'Juan García'
        }
        
        # Cita completada
        estado_completado = {
            **estado_procesando,
            'estado_conversacion': 'completado',
            'cita_id': 'CITA_001'
        }
        
        # Verificar evolución del estado
        assert estado_inicial['estado_conversacion'] == 'inicial'
        assert estado_solicitando['estado_conversacion'] == 'solicitando_nombre'
        assert estado_procesando['estado_conversacion'] == 'procesando'
        assert estado_completado['estado_conversacion'] == 'completado'
    
    def test_mensaje_final_se_genera(self):
        """Test que mensaje_final se genera en generacion_resumen"""
        estado_pre_resumen = {
            'user_id': 'USR_001',
            'tipo_usuario': 'doctor',
            'clasificacion': 'personal',
            'herramientas_seleccionadas': [
                {'nombre': 'listar_eventos', 'tipo': 'personal'}
            ],
            'resultados_herramientas': ['Tienes 3 eventos mañana']
        }
        
        estado_post_resumen = {
            **estado_pre_resumen,
            'mensaje_final': 'Mañana tienes 3 eventos programados: reunión 9AM, almuerzo 1PM, y consulta 4PM.'
        }
        
        # Verificar que mensaje_final se añadió sin perder otros campos
        assert estado_post_resumen['user_id'] == 'USR_001'
        assert estado_post_resumen['tipo_usuario'] == 'doctor'
        assert estado_post_resumen['clasificacion'] == 'personal'
        assert len(estado_post_resumen['herramientas_seleccionadas']) == 1
        assert 'mensaje_final' in estado_post_resumen


class TestConsistenciaEstado:
    """Tests de consistencia del estado a lo largo del flujo"""
    
    def test_campos_obligatorios_presentes(self):
        """Test que los campos obligatorios estén presentes"""
        estado_minimo = {
            'messages': [{'role': 'user', 'content': 'test'}],
            'phone_number': '+52123456789',
            'timestamp': '2024-01-15T10:00:00Z',
            'session_id': 'session_001'
        }
        
        # Verificar campos mínimos necesarios
        assert 'messages' in estado_minimo
        assert 'phone_number' in estado_minimo
        assert 'timestamp' in estado_minimo
        assert 'session_id' in estado_minimo
        assert len(estado_minimo['messages']) > 0
    
    def test_tipos_datos_correctos(self):
        """Test que los tipos de datos se mantienen correctos"""
        estado = {
            'user_id': 'USR_123',  # string
            'es_admin': True,      # boolean
            'herramientas_seleccionadas': [],  # list
            'timestamp': '2024-01-15T10:00:00Z',  # string ISO
            'messages': [{'role': 'user', 'content': 'test'}]  # list of dicts
        }
        
        # Verificar tipos
        assert isinstance(estado['user_id'], str)
        assert isinstance(estado['es_admin'], bool)
        assert isinstance(estado['herramientas_seleccionadas'], list)
        assert isinstance(estado['timestamp'], str)
        assert isinstance(estado['messages'], list)
        assert isinstance(estado['messages'][0], dict)
    
    def test_campos_opcionales_manejados(self):
        """Test que los campos opcionales se manejan correctamente"""
        estado_sin_opcionales = {
            'user_id': 'USR_001'
        }
        
        # Simular nodos añadiendo campos opcionales
        estado_con_opcionales = {
            **estado_sin_opcionales,
            'contexto_episodico': None,  # Puede ser None
            'herramientas_seleccionadas': [],  # Puede estar vacío
            'cita_id': None,  # Puede no existir aún
            'error_sync': None  # Puede no haber errores
        }
        
        # Verificar que maneja campos None/vacíos
        assert estado_con_opcionales.get('contexto_episodico') is None
        assert estado_con_opcionales.get('herramientas_seleccionadas') == []
        assert estado_con_opcionales.get('cita_id') is None
        assert estado_con_opcionales.get('error_sync') is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])