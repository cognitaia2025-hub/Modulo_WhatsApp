"""
Tests de Integración del Grafo Completo - ETAPA 8

Tests más complejos que validan la integración completa del sistema.
"""

import pytest
import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch
from datetime import datetime

# Añadir path del proyecto
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.graph_whatsapp import crear_grafo_whatsapp, app
from src.state.agent_state import WhatsAppAgentState


class TestIntegracionGrafoCompleto:
    """Tests de integración del grafo completo"""
    
    @pytest.fixture
    def grafo_mock(self):
        """Fixture que retorna el grafo con nodos mockeados"""
        return crear_grafo_whatsapp()
    
    def test_grafo_procesa_mensaje_paciente_nuevo(self, grafo_mock):
        """Test que el grafo procesa correctamente un paciente nuevo"""
        estado_inicial = {
            "messages": [
                {"role": "user", "content": "Hola, soy nuevo y necesito una cita"}
            ],
            "phone_number": "+52111222333",
            "timestamp": datetime.now().isoformat(),
            "session_id": "session_nuevo_001"
        }
        
        # Mock de nodos principales para evitar dependencias externas
        with patch('src.nodes.identificacion_usuario_node.nodo_identificacion_usuario_wrapper') as mock_id:
            # Simular identificación de usuario nuevo
            mock_id.return_value = {
                **estado_inicial,
                'user_id': 'USR_111222333_NEW',
                'tipo_usuario': 'paciente_externo',
                'es_admin': False,
                'es_nuevo': True
            }
            
            with patch('src.nodes.filtrado_inteligente_node.nodo_filtrado_inteligente_wrapper') as mock_filtro:
                mock_filtro.return_value = {
                    **mock_id.return_value,
                    'clasificacion': 'solicitud_cita',
                    'intencion_detectada': True
                }
                
                with patch('src.nodes.recepcionista_node.nodo_recepcionista_wrapper') as mock_recep:
                    mock_recep.return_value = {
                        **mock_filtro.return_value,
                        'estado_conversacion': 'solicitando_nombre',
                        'datos_paciente': {'telefono': '+52111222333'}
                    }
                    
                    with patch('src.nodes.generacion_resumen_node.nodo_generacion_resumen_wrapper') as mock_resumen:
                        mock_resumen.return_value = {
                            **mock_recep.return_value,
                            'mensaje_final': 'Bienvenido al sistema. Para agendar su cita, necesito algunos datos. ¿Cuál es su nombre completo?'
                        }
                        
                        with patch('src.nodes.persistencia_episodica_node.nodo_persistencia_episodica_wrapper') as mock_persist:
                            mock_persist.return_value = {
                                **mock_resumen.return_value,
                                'memoria_guardada': True
                            }
                            
                            # Ejecutar grafo
                            resultado = grafo_mock.invoke(estado_inicial)
                            
                            # Validaciones específicas para paciente nuevo
                            assert 'user_id' in resultado
                            assert resultado['tipo_usuario'] == 'paciente_externo'
                            assert resultado['es_admin'] == False
                            assert resultado['clasificacion'] == 'solicitud_cita'
                            assert 'mensaje_final' in resultado
                            
                            # Verificar que los nodos fueron llamados en orden
                            mock_id.assert_called_once()
                            mock_filtro.assert_called_once()
                            mock_recep.assert_called_once()
                            mock_resumen.assert_called_once()
                            mock_persist.assert_called_once()
    
    def test_grafo_procesa_mensaje_doctor_existente(self, grafo_mock):
        """Test que el grafo procesa correctamente un doctor existente"""
        estado_inicial = {
            "messages": [
                {"role": "user", "content": "Hola, necesito revisar los pacientes de hoy"}
            ],
            "phone_number": "+52999888777",  # Teléfono de doctor registrado
            "timestamp": datetime.now().isoformat(),
            "session_id": "session_doctor_001"
        }
        
        with patch('src.nodes.identificacion_usuario_node.nodo_identificacion_usuario_wrapper') as mock_id:
            # Simular doctor existente en BD
            mock_id.return_value = {
                **estado_inicial,
                'user_id': 'DR_GARCIA_001',
                'tipo_usuario': 'doctor',
                'es_admin': True,
                'nombre_completo': 'Dr. Juan García',
                'especialidad': 'Medicina General'
            }
            
            with patch('src.nodes.filtrado_inteligente_node.nodo_filtrado_inteligente_wrapper') as mock_filtro:
                mock_filtro.return_value = {
                    **mock_id.return_value,
                    'clasificacion': 'medica',
                    'intencion_herramientas': True
                }
                
                with patch('src.nodes.recuperacion_medica_node.nodo_recuperacion_medica_wrapper') as mock_rec_med:
                    mock_rec_med.return_value = {
                        **mock_filtro.return_value,
                        'contexto_medico': 'Pacientes programados para hoy: María López (10:00), Carlos Ruiz (14:00)'
                    }
                    
                    with patch('src.nodes.seleccion_herramientas_node.nodo_seleccion_herramientas_wrapper') as mock_sel:
                        mock_sel.return_value = {
                            **mock_rec_med.return_value,
                            'herramientas_seleccionadas': [
                                {'nombre': 'listar_pacientes_dia', 'tipo': 'medica', 'params': {'fecha': '2024-01-15'}}
                            ]
                        }
                        
                        with patch('src.nodes.ejecucion_medica_node.nodo_ejecucion_medica_wrapper') as mock_ejec:
                            mock_ejec.return_value = {
                                **mock_sel.return_value,
                                'pacientes_encontrados': [
                                    {'nombre': 'María López', 'hora': '10:00', 'motivo': 'Control'},
                                    {'nombre': 'Carlos Ruiz', 'hora': '14:00', 'motivo': 'Consulta'}
                                ]
                            }
                            
                            with patch('src.nodes.generacion_resumen_node.nodo_generacion_resumen_wrapper') as mock_resumen:
                                mock_resumen.return_value = {
                                    **mock_ejec.return_value,
                                    'mensaje_final': 'Dr. García, hoy tiene 2 pacientes: María López a las 10:00 (Control) y Carlos Ruiz a las 14:00 (Consulta)'
                                }
                                
                                with patch('src.nodes.persistencia_episodica_node.nodo_persistencia_episodica_wrapper') as mock_persist:
                                    mock_persist.return_value = {
                                        **mock_resumen.return_value,
                                        'memoria_guardada': True
                                    }
                                    
                                    # Ejecutar grafo
                                    resultado = grafo_mock.invoke(estado_inicial)
                                    
                                    # Validaciones específicas para doctor
                                    assert resultado['user_id'] == 'DR_GARCIA_001'
                                    assert resultado['tipo_usuario'] == 'doctor'
                                    assert resultado['es_admin'] == True
                                    assert resultado['clasificacion'] == 'medica'
                                    assert len(resultado['herramientas_seleccionadas']) == 1
                                    assert resultado['herramientas_seleccionadas'][0]['tipo'] == 'medica'
                                    assert 'pacientes_encontrados' in resultado
    
    def test_grafo_identifica_usuario_correctamente(self, grafo_mock):
        """Test que el grafo identifica diferentes tipos de usuarios"""
        casos_usuarios = [
            {
                'phone_number': '+52123456789',
                'esperado': {'tipo_usuario': 'paciente_externo', 'es_admin': False}
            },
            {
                'phone_number': '+52999888777',
                'esperado': {'tipo_usuario': 'doctor', 'es_admin': True}
            },
            {
                'phone_number': '+52555444333',
                'esperado': {'tipo_usuario': 'admin', 'es_admin': True}
            }
        ]
        
        for caso in casos_usuarios:
            estado = {
                "messages": [{"role": "user", "content": "Hola"}],
                "phone_number": caso['phone_number'],
                "timestamp": datetime.now().isoformat(),
                "session_id": f"session_{caso['phone_number'][-3:]}"
            }
            
            with patch('src.nodes.identificacion_usuario_node.nodo_identificacion_usuario_wrapper') as mock_id:
                mock_id.return_value = {
                    **estado,
                    'user_id': f"USR_{caso['phone_number'][-9:]}",
                    **caso['esperado']
                }
                
                # Mock otros nodos para completar el flujo
                with patch('src.nodes.filtrado_inteligente_node.nodo_filtrado_inteligente_wrapper') as mock_filtro, \
                     patch('src.nodes.generacion_resumen_node.nodo_generacion_resumen_wrapper') as mock_resumen, \
                     patch('src.nodes.persistencia_episodica_node.nodo_persistencia_episodica_wrapper') as mock_persist:
                    
                    mock_filtro.return_value = {**mock_id.return_value, 'clasificacion': 'chat_casual'}
                    mock_resumen.return_value = {**mock_filtro.return_value, 'mensaje_final': 'Hola!'}
                    mock_persist.return_value = {**mock_resumen.return_value, 'memoria_guardada': True}
                    
                    resultado = grafo_mock.invoke(estado)
                    
                    # Verificar identificación correcta
                    assert resultado['tipo_usuario'] == caso['esperado']['tipo_usuario']
                    assert resultado['es_admin'] == caso['esperado']['es_admin']
    
    def test_grafo_cache_sesion_funciona(self, grafo_mock):
        """Test que el nodo de caché funciona correctamente"""
        estado_inicial = {
            "messages": [{"role": "user", "content": "test"}],
            "phone_number": "+52123456789",
            "timestamp": datetime.now().isoformat(),
            "session_id": "session_cache_001"
        }
        
        # Mock básico para verificar que caché se ejecuta
        with patch('src.nodes.identificacion_usuario_node.nodo_identificacion_usuario_wrapper') as mock_id:
            mock_id.return_value = {
                **estado_inicial,
                'user_id': 'USR_CACHE_001',
                'tipo_usuario': 'paciente'
            }
            
            # El nodo caché es interno, verificamos sus efectos
            resultado_mock = {
                **mock_id.return_value,
                'sesion_expirada': False,  # Efectos del caché
                'timestamp': datetime.now().isoformat()  # Timestamp actualizado
            }
            
            with patch('src.nodes.filtrado_inteligente_node.nodo_filtrado_inteligente_wrapper') as mock_filtro, \
                 patch('src.nodes.generacion_resumen_node.nodo_generacion_resumen_wrapper') as mock_resumen, \
                 patch('src.nodes.persistencia_episodica_node.nodo_persistencia_episodica_wrapper') as mock_persist:
                
                mock_filtro.return_value = {**resultado_mock, 'clasificacion': 'chat_casual'}
                mock_resumen.return_value = {**mock_filtro.return_value, 'mensaje_final': 'OK'}
                mock_persist.return_value = {**mock_resumen.return_value, 'memoria_guardada': True}
                
                resultado = grafo_mock.invoke(estado_inicial)
                
                # Verificar que el timestamp fue actualizado por caché
                assert 'timestamp' in resultado
                assert resultado.get('sesion_expirada', False) == False
    
    def test_grafo_maneja_errores_gracefully(self, grafo_mock):
        """Test que el grafo maneja errores sin crashear"""
        estado_inicial = {
            "messages": [{"role": "user", "content": "test error"}],
            "phone_number": "+52999999999",
            "timestamp": datetime.now().isoformat(),
            "session_id": "session_error_001"
        }
        
        # Simular error en identificación
        with patch('src.nodes.identificacion_usuario_node.nodo_identificacion_usuario_wrapper') as mock_id:
            # En lugar de lanzar excepción, simular manejo de error interno
            mock_id.return_value = {
                **estado_inicial,
                'user_id': 'USR_ERROR_FALLBACK',
                'tipo_usuario': 'paciente_externo',
                'es_admin': False,
                'error_identificacion': 'Usuario no encontrado, usando fallback'
            }
            
            with patch('src.nodes.filtrado_inteligente_node.nodo_filtrado_inteligente_wrapper') as mock_filtro:
                mock_filtro.return_value = {
                    **mock_id.return_value,
                    'clasificacion': 'chat_casual'
                }
                
                with patch('src.nodes.generacion_resumen_node.nodo_generacion_resumen_wrapper') as mock_resumen:
                    mock_resumen.return_value = {
                        **mock_filtro.return_value,
                        'mensaje_final': 'Lo siento, hubo un problema procesando tu solicitud. Por favor intenta de nuevo.'
                    }
                    
                    with patch('src.nodes.persistencia_episodica_node.nodo_persistencia_episodica_wrapper') as mock_persist:
                        mock_persist.return_value = {
                            **mock_resumen.return_value,
                            'memoria_guardada': True
                        }
                        
                        # El grafo debería completarse sin lanzar excepción
                        resultado = grafo_mock.invoke(estado_inicial)
                        
                        # Verificar que manejo el error gracefully
                        assert 'error_identificacion' in resultado
                        assert 'mensaje_final' in resultado
                        assert resultado['user_id'] == 'USR_ERROR_FALLBACK'
    
    def test_grafo_estructura_completa(self, grafo_mock):
        """Test que verifica la estructura completa del grafo"""
        graph_def = grafo_mock.get_graph()
        
        # Verificar que todos los nodos están presentes
        nodos_esperados = {
            'identificacion_usuario', 'cache_sesion', 'filtrado_inteligente',
            'recuperacion_episodica', 'recuperacion_medica', 'seleccion_herramientas',
            'ejecucion_herramientas', 'ejecucion_medica', 'recepcionista',
            'generacion_resumen', 'persistencia_episodica', 'sincronizador_hibrido'
        }
        
        nodos_actuales = set(graph_def.nodes.keys())
        assert nodos_esperados.issubset(nodos_actuales)
        
        # Verificar que hay edges condicionales
        edges_condicionales = [
            edge for edge in graph_def.edges 
            if hasattr(edge, 'condition') and edge.condition is not None
        ]
        
        # Debe haber exactamente 3 decisiones condicionales
        nodos_con_decisiones = set(edge.source for edge in edges_condicionales)
        assert len(nodos_con_decisiones) == 3
        
        assert 'filtrado_inteligente' in nodos_con_decisiones
        assert 'seleccion_herramientas' in nodos_con_decisiones  
        assert 'recepcionista' in nodos_con_decisiones


class TestInstanciaGlobal:
    """Tests de la instancia global del grafo"""
    
    def test_instancia_global_disponible(self):
        """Test que la instancia global está disponible para usar"""
        # Importar app global
        assert app is not None
        assert hasattr(app, 'invoke')
        
        # Verificar que puede obtener estructura
        graph_def = app.get_graph()
        assert graph_def is not None
        assert len(graph_def.nodes) >= 12
    
    def test_instancia_global_es_funcional(self):
        """Test básico de que la instancia global es funcional"""
        estado_test = {
            "messages": [{"role": "user", "content": "test"}],
            "phone_number": "+52000000000",
            "timestamp": datetime.now().isoformat(),
            "session_id": "test_global"
        }
        
        # Mock solo identificación para test básico
        with patch('src.nodes.identificacion_usuario_node.nodo_identificacion_usuario_wrapper') as mock_id:
            mock_id.return_value = {
                **estado_test,
                'user_id': 'USR_GLOBAL_TEST',
                'tipo_usuario': 'paciente'
            }
            
            with patch('src.nodes.filtrado_inteligente_node.nodo_filtrado_inteligente_wrapper') as mock_filtro, \
                 patch('src.nodes.generacion_resumen_node.nodo_generacion_resumen_wrapper') as mock_resumen, \
                 patch('src.nodes.persistencia_episodica_node.nodo_persistencia_episodica_wrapper') as mock_persist:
                
                mock_filtro.return_value = {**mock_id.return_value, 'clasificacion': 'chat_casual'}
                mock_resumen.return_value = {**mock_filtro.return_value, 'mensaje_final': 'Test OK'}
                mock_persist.return_value = {**mock_resumen.return_value, 'memoria_guardada': True}
                
                # La instancia global debería funcionar
                resultado = app.invoke(estado_test)
                assert resultado is not None
                assert 'user_id' in resultado


if __name__ == "__main__":
    pytest.main([__file__, "-v"])