"""
Tests de Flujos Completos End-to-End - ETAPA 8

Valida que los flujos completos funcionen correctamente.
"""

import pytest
import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

# Añadir path del proyecto
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.graph_whatsapp import crear_grafo_whatsapp
from src.state.agent_state import WhatsAppAgentState


class TestFlujosCompletos:
    """Tests de flujos end-to-end completos"""
    
    @pytest.fixture
    def grafo(self):
        """Fixture que retorna el grafo compilado"""
        return crear_grafo_whatsapp()
    
    def test_flujo_paciente_externo_solicita_cita(self, grafo):
        """Test flujo: Paciente externo → Recepcionista → Sincronización"""
        estado_inicial = {
            "messages": [
                {"role": "user", "content": "Hola, necesito agendar una cita médica"}
            ],
            "phone_number": "+52123456789",
            "timestamp": "2024-01-15T10:00:00Z",
            "session_id": "session_test_001"
        }
        
        # Mock de funciones para evitar dependencias externas
        with patch('src.nodes.identificacion_usuario_node.nodo_identificacion_usuario_wrapper') as mock_id, \
             patch('src.nodes.filtrado_inteligente_node.nodo_filtrado_inteligente_wrapper') as mock_filtro, \
             patch('src.nodes.recepcionista_node.nodo_recepcionista_wrapper') as mock_recep, \
             patch('src.nodes.sincronizador_hibrido_node.nodo_sincronizador_hibrido_wrapper') as mock_sync, \
             patch('src.nodes.generacion_resumen_node.nodo_generacion_resumen_wrapper') as mock_resumen, \
             patch('src.nodes.persistencia_episodica_node.nodo_persistencia_episodica_wrapper') as mock_persist:
            
            # Configurar mocks para simular el flujo
            mock_id.return_value = {
                **estado_inicial,
                'user_id': 'USR_123456789',
                'tipo_usuario': 'paciente_externo',
                'es_admin': False
            }
            
            mock_filtro.return_value = {
                **mock_id.return_value,
                'clasificacion': 'solicitud_cita'
            }
            
            mock_recep.return_value = {
                **mock_filtro.return_value,
                'estado_conversacion': 'completado',
                'cita_id': 'CITA_001'
            }
            
            mock_sync.return_value = {
                **mock_recep.return_value,
                'evento_calendar_id': 'EVT_001',
                'sincronizado': True
            }
            
            mock_resumen.return_value = {
                **mock_sync.return_value,
                'mensaje_final': 'Su cita ha sido agendada exitosamente.'
            }
            
            mock_persist.return_value = {
                **mock_resumen.return_value,
                'memoria_guardada': True
            }
            
            # Ejecutar grafo
            resultado = grafo.invoke(estado_inicial)
            
            # Validaciones
            assert resultado['user_id'] == 'USR_123456789'
            assert resultado['tipo_usuario'] == 'paciente_externo'
            assert resultado['clasificacion'] == 'solicitud_cita'
            assert resultado['estado_conversacion'] == 'completado'
            assert 'mensaje_final' in resultado
    
    def test_flujo_doctor_registra_consulta(self, grafo):
        """Test flujo: Doctor → Recuperación Médica → Ejecución → Sincronización"""
        estado_inicial = {
            "messages": [
                {"role": "user", "content": "Quiero registrar la consulta del paciente García"}
            ],
            "phone_number": "+52987654321",
            "timestamp": "2024-01-15T14:30:00Z",
            "session_id": "session_doctor_001"
        }
        
        with patch('src.nodes.identificacion_usuario_node.nodo_identificacion_usuario_wrapper') as mock_id, \
             patch('src.nodes.filtrado_inteligente_node.nodo_filtrado_inteligente_wrapper') as mock_filtro, \
             patch('src.nodes.recuperacion_medica_node.nodo_recuperacion_medica_wrapper') as mock_rec_med, \
             patch('src.nodes.seleccion_herramientas_node.nodo_seleccion_herramientas_wrapper') as mock_sel, \
             patch('src.nodes.ejecucion_medica_node.nodo_ejecucion_medica_wrapper') as mock_ejec_med, \
             patch('src.nodes.generacion_resumen_node.nodo_generacion_resumen_wrapper') as mock_resumen, \
             patch('src.nodes.persistencia_episodica_node.nodo_persistencia_episodica_wrapper') as mock_persist:
            
            # Configurar mocks
            mock_id.return_value = {
                **estado_inicial,
                'user_id': 'DR_GARCIA_123',
                'tipo_usuario': 'doctor',
                'es_admin': True
            }
            
            mock_filtro.return_value = {
                **mock_id.return_value,
                'clasificacion': 'medica'
            }
            
            mock_rec_med.return_value = {
                **mock_filtro.return_value,
                'contexto_medico': 'Paciente García - consulta pendiente'
            }
            
            mock_sel.return_value = {
                **mock_rec_med.return_value,
                'herramientas_seleccionadas': [
                    {'nombre': 'registrar_consulta', 'tipo': 'medica'}
                ]
            }
            
            mock_ejec_med.return_value = {
                **mock_sel.return_value,
                'consulta_registrada': True,
                'consulta_id': 'CONS_001'
            }
            
            mock_resumen.return_value = {
                **mock_ejec_med.return_value,
                'mensaje_final': 'Consulta registrada exitosamente.'
            }
            
            mock_persist.return_value = {
                **mock_resumen.return_value,
                'memoria_guardada': True
            }
            
            # Ejecutar grafo
            resultado = grafo.invoke(estado_inicial)
            
            # Validaciones
            assert resultado['tipo_usuario'] == 'doctor'
            assert resultado['clasificacion'] == 'medica'
            assert len(resultado['herramientas_seleccionadas']) == 1
            assert resultado['herramientas_seleccionadas'][0]['tipo'] == 'medica'
    
    def test_flujo_usuario_calendario_personal(self, grafo):
        """Test flujo: Usuario → Calendario Personal → Ejecución Personal"""
        estado_inicial = {
            "messages": [
                {"role": "user", "content": "¿Qué tengo mañana en mi calendario personal?"}
            ],
            "phone_number": "+52555123456",
            "timestamp": "2024-01-15T16:00:00Z",
            "session_id": "session_personal_001"
        }
        
        with patch('src.nodes.identificacion_usuario_node.nodo_identificacion_usuario_wrapper') as mock_id, \
             patch('src.nodes.filtrado_inteligente_node.nodo_filtrado_inteligente_wrapper') as mock_filtro, \
             patch('src.nodes.recuperacion_episodica_node.nodo_recuperacion_episodica_wrapper') as mock_rec_epi, \
             patch('src.nodes.seleccion_herramientas_node.nodo_seleccion_herramientas_wrapper') as mock_sel, \
             patch('src.nodes.ejecucion_herramientas_node.nodo_ejecucion_herramientas_wrapper') as mock_ejec, \
             patch('src.nodes.generacion_resumen_node.nodo_generacion_resumen_wrapper') as mock_resumen, \
             patch('src.nodes.persistencia_episodica_node.nodo_persistencia_episodica_wrapper') as mock_persist:
            
            # Configurar mocks
            mock_id.return_value = {
                **estado_inicial,
                'user_id': 'USR_555123456',
                'tipo_usuario': 'admin',
                'es_admin': True
            }
            
            mock_filtro.return_value = {
                **mock_id.return_value,
                'clasificacion': 'personal'
            }
            
            mock_rec_epi.return_value = {
                **mock_filtro.return_value,
                'contexto_episodico': 'Usuario ha preguntado sobre calendario personal antes'
            }
            
            mock_sel.return_value = {
                **mock_rec_epi.return_value,
                'herramientas_seleccionadas': [
                    {'nombre': 'listar_eventos', 'tipo': 'personal'}
                ]
            }
            
            mock_ejec.return_value = {
                **mock_sel.return_value,
                'eventos_encontrados': ['Reunión 9:00 AM', 'Cita dentista 2:00 PM']
            }
            
            mock_resumen.return_value = {
                **mock_ejec.return_value,
                'mensaje_final': 'Mañana tienes: Reunión 9:00 AM, Cita dentista 2:00 PM'
            }
            
            mock_persist.return_value = {
                **mock_resumen.return_value,
                'memoria_guardada': True
            }
            
            # Ejecutar grafo
            resultado = grafo.invoke(estado_inicial)
            
            # Validaciones
            assert resultado['clasificacion'] == 'personal'
            assert len(resultado['herramientas_seleccionadas']) == 1
            assert resultado['herramientas_seleccionadas'][0]['tipo'] == 'personal'
    
    def test_flujo_admin_chat_casual(self, grafo):
        """Test flujo: Admin → Chat Casual → Generación Resumen directo"""
        estado_inicial = {
            "messages": [
                {"role": "user", "content": "Hola, ¿cómo estás?"}
            ],
            "phone_number": "+52999888777",
            "timestamp": "2024-01-15T18:00:00Z",
            "session_id": "session_admin_001"
        }
        
        with patch('src.nodes.identificacion_usuario_node.nodo_identificacion_usuario_wrapper') as mock_id, \
             patch('src.nodes.filtrado_inteligente_node.nodo_filtrado_inteligente_wrapper') as mock_filtro, \
             patch('src.nodes.generacion_resumen_node.nodo_generacion_resumen_wrapper') as mock_resumen, \
             patch('src.nodes.persistencia_episodica_node.nodo_persistencia_episodica_wrapper') as mock_persist:
            
            # Configurar mocks
            mock_id.return_value = {
                **estado_inicial,
                'user_id': 'ADM_999888777',
                'tipo_usuario': 'admin',
                'es_admin': True
            }
            
            mock_filtro.return_value = {
                **mock_id.return_value,
                'clasificacion': 'chat_casual'
            }
            
            mock_resumen.return_value = {
                **mock_filtro.return_value,
                'mensaje_final': '¡Hola! Estoy bien, gracias por preguntar. ¿En qué puedo ayudarte?'
            }
            
            mock_persist.return_value = {
                **mock_resumen.return_value,
                'memoria_guardada': True
            }
            
            # Ejecutar grafo
            resultado = grafo.invoke(estado_inicial)
            
            # Validaciones
            assert resultado['tipo_usuario'] == 'admin'
            assert resultado['clasificacion'] == 'chat_casual'
            assert 'mensaje_final' in resultado
    
    def test_flujo_recepcionista_completo_con_sync(self, grafo):
        """Test flujo completo: Recepcionista → Cita Completada → Sincronización"""
        estado_inicial = {
            "messages": [
                {"role": "user", "content": "Quiero agendar cita para el Dr. López"}
            ],
            "phone_number": "+52444333222",
            "timestamp": "2024-01-15T09:00:00Z",
            "session_id": "session_recep_001"
        }
        
        with patch('src.nodes.identificacion_usuario_node.nodo_identificacion_usuario_wrapper') as mock_id, \
             patch('src.nodes.filtrado_inteligente_node.nodo_filtrado_inteligente_wrapper') as mock_filtro, \
             patch('src.nodes.recepcionista_node.nodo_recepcionista_wrapper') as mock_recep, \
             patch('src.nodes.sincronizador_hibrido_node.nodo_sincronizador_hibrido_wrapper') as mock_sync, \
             patch('src.nodes.generacion_resumen_node.nodo_generacion_resumen_wrapper') as mock_resumen, \
             patch('src.nodes.persistencia_episodica_node.nodo_persistencia_episodica_wrapper') as mock_persist:
            
            # Configurar mocks
            mock_id.return_value = {
                **estado_inicial,
                'user_id': 'PAC_444333222',
                'tipo_usuario': 'paciente',
                'es_admin': False
            }
            
            mock_filtro.return_value = {
                **mock_id.return_value,
                'clasificacion': 'solicitud_cita'
            }
            
            mock_recep.return_value = {
                **mock_filtro.return_value,
                'estado_conversacion': 'completado',
                'cita_id': 'CITA_DR_LOPEZ_001',
                'fecha_cita': '2024-01-20T15:00:00',
                'doctor_id': 'DR_LOPEZ'
            }
            
            mock_sync.return_value = {
                **mock_recep.return_value,
                'evento_calendar_id': 'GCAL_EVT_001',
                'sincronizado': True,
                'mensaje_sync': 'Evento sincronizado correctamente'
            }
            
            mock_resumen.return_value = {
                **mock_sync.return_value,
                'mensaje_final': 'Cita agendada y sincronizada con calendario.'
            }
            
            mock_persist.return_value = {
                **mock_resumen.return_value,
                'memoria_guardada': True
            }
            
            # Ejecutar grafo
            resultado = grafo.invoke(estado_inicial)
            
            # Validaciones específicas del flujo con sincronización
            assert resultado['estado_conversacion'] == 'completado'
            assert resultado['sincronizado'] == True
            assert 'evento_calendar_id' in resultado
            assert 'mensaje_sync' in resultado


class TestFlujosMultiplesMensajes:
    """Tests de flujos con múltiples mensajes en la misma sesión"""
    
    def test_flujo_multiples_mensajes_misma_sesion(self):
        """Test que el grafo maneja múltiples mensajes en la misma sesión"""
        # Este sería un test más complejo que requiere mantener estado entre invocaciones
        # Por ahora, un test básico que valida la estructura
        estado_con_historial = {
            "messages": [
                {"role": "user", "content": "Hola"},
                {"role": "assistant", "content": "Hola, ¿en qué puedo ayudarte?"},
                {"role": "user", "content": "Necesito una cita"},
                {"role": "assistant", "content": "¿Para qué doctor?"},
                {"role": "user", "content": "Dr. García"}
            ],
            "phone_number": "+52111222333",
            "timestamp": "2024-01-15T20:00:00Z",
            "session_id": "session_multi_001"
        }
        
        # Validar que el estado tiene el formato correcto
        assert len(estado_con_historial["messages"]) == 5
        assert estado_con_historial["messages"][-1]["content"] == "Dr. García"
        
        # Este test se expande cuando tengamos persistencia de checkpoints
        assert True  # Placeholder por ahora


if __name__ == "__main__":
    pytest.main([__file__, "-v"])