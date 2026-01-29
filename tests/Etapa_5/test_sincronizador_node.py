"""
TEST ETAPA 5.1: test_sincronizador_node.py
Tests del nodo sincronizador híbrido BD ↔ Google Calendar

6 tests que validan:
- test_sincronizacion_exitosa()
- test_bd_mantiene_cita_si_falla_google()
- test_actualiza_google_event_id()
- test_registra_error_sincronizacion()
- test_color_rojo_para_citas_medicas()
- test_extended_properties_correctas()

REGLA CRÍTICA: BD es source of truth siempre
"""

import pytest
import os
import sys
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# Ajustar path para importaciones
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_root)

from src.nodes.sincronizador_hibrido_node import sincronizador_hibrido_node
from src.medical.models import CitasMedicas, Doctores, Pacientes, SincronizacionCalendar, EstadoSincronizacion
from src.state.agent_state import WhatsAppAgentState

# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_db_session():
    """Mock de sesión de base de datos"""
    session_mock = Mock()
    
    # Configurar mocks de query
    session_mock.query.return_value.filter.return_value.first.return_value = None
    session_mock.query.return_value.get.return_value = None
    
    return session_mock

@pytest.fixture
def mock_cita_completa():
    """Mock de cita médica completa con doctor y paciente"""
    # Mock cita
    cita = Mock(spec=CitasMedicas)
    cita.id = 123
    cita.doctor_id = 1
    cita.paciente_id = 1
    cita.fecha_hora_inicio = datetime(2024, 3, 15, 10, 0, 0)
    cita.fecha_hora_fin = datetime(2024, 3, 15, 10, 30, 0)
    cita.tipo_consulta = Mock()
    cita.tipo_consulta.value = 'primera_vez'
    cita.google_event_id = None
    cita.sincronizada_google = False
    
    # Mock doctor
    doctor = Mock(spec=Doctores)
    doctor.id = 1
    doctor.nombre_completo = "Dr. Juan Pérez"
    doctor.especialidad = "Medicina General"
    
    # Mock paciente
    paciente = Mock(spec=Pacientes)
    paciente.id = 1
    paciente.nombre_completo = "María García"
    paciente.telefono = "+52 664 123 4567"
    
    return cita, doctor, paciente

@pytest.fixture
def mock_google_calendar_service():
    """Mock del servicio Google Calendar"""
    service = Mock()
    
    # Configurar respuesta exitosa por defecto
    insert_result = {
        'id': 'google_event_test_123',
        'summary': 'Consulta - María García',
        'status': 'confirmed'
    }
    
    service.events.return_value.insert.return_value.execute.return_value = insert_result
    
    return service

@pytest.fixture
def estado_test():
    """Estado de prueba para el nodo"""
    return {
        'cita_id_creada': 123,
        'messages': [],
        'user_info': {}
    }

# ============================================================================
# TESTS
# ============================================================================

class TestSincronizadorNode:
    """Suite de tests para el nodo sincronizador híbrido"""
    
    def test_sincronizacion_exitosa(self, mock_db_session, mock_cita_completa, mock_google_calendar_service, estado_test):
        """Test 1: Sincronización exitosa BD → Google Calendar"""
        cita, doctor, paciente = mock_cita_completa
        
        with patch('src.nodes.sincronizador_hibrido_node.SessionLocal', return_value=mock_db_session):
            with patch('src.nodes.sincronizador_hibrido_node.get_calendar_service', return_value=mock_google_calendar_service):
                # Configurar mocks para retornar datos válidos
                mock_db_session.query.return_value.filter.return_value.first.return_value = cita
                mock_db_session.query.return_value.filter.side_effect = [
                    Mock(first=Mock(return_value=cita)),
                    Mock(first=Mock(return_value=doctor)),
                    Mock(first=Mock(return_value=paciente))
                ]
                
                # Ejecutar nodo
                resultado = sincronizador_hibrido_node(estado_test)
                
                # Verificaciones
                assert resultado['sincronizado'] == True
                assert 'google_event_id' in resultado
                assert resultado['google_event_id'] == 'google_event_test_123'
                assert 'mensaje_sync' in resultado
                
                # Verificar que se actualizó la cita en BD
                assert cita.google_event_id == 'google_event_test_123'
                assert cita.sincronizada_google == True
                mock_db_session.commit.assert_called()
    
    def test_bd_mantiene_cita_si_falla_google(self, mock_db_session, mock_cita_completa, estado_test):
        """Test 2: BD mantiene cita válida si falla Google Calendar"""
        cita, doctor, paciente = mock_cita_completa
        
        with patch('src.nodes.sincronizador_hibrido_node.SessionLocal', return_value=mock_db_session):
            with patch('src.nodes.sincronizador_hibrido_node.get_calendar_service', side_effect=Exception("Google Calendar API Error")):
                # Configurar mocks
                mock_db_session.query.return_value.filter.side_effect = [
                    Mock(first=Mock(return_value=cita)),
                    Mock(first=Mock(return_value=doctor)),
                    Mock(first=Mock(return_value=paciente))
                ]
                
                # Ejecutar nodo
                resultado = sincronizador_hibrido_node(estado_test)
                
                # Verificaciones CRÍTICAS
                assert resultado['sincronizado'] == False
                assert 'error_sync' in resultado
                assert 'mensaje_sync' in resultado
                
                # BD NO debe verse afectada - cita sigue válida
                assert cita.google_event_id is None  # No se modificó
                assert cita.sincronizada_google == False  # No se modificó
                
                # Debe registrar el error en tabla sincronizacion_calendar
                mock_db_session.add.assert_called()  # Se agregó registro de error
    
    def test_actualiza_google_event_id(self, mock_db_session, mock_cita_completa, mock_google_calendar_service, estado_test):
        """Test 3: Actualiza google_event_id en BD cuando sincronización es exitosa"""
        cita, doctor, paciente = mock_cita_completa
        google_event_id = 'test_google_event_456'
        
        # Configurar respuesta específica de Google
        mock_google_calendar_service.events.return_value.insert.return_value.execute.return_value = {
            'id': google_event_id,
            'summary': 'Consulta - María García'
        }
        
        with patch('src.nodes.sincronizador_hibrido_node.SessionLocal', return_value=mock_db_session):
            with patch('src.nodes.sincronizador_hibrido_node.get_calendar_service', return_value=mock_google_calendar_service):
                # Configurar mocks
                mock_db_session.query.return_value.filter.side_effect = [
                    Mock(first=Mock(return_value=cita)),
                    Mock(first=Mock(return_value=doctor)),
                    Mock(first=Mock(return_value=paciente))
                ]
                
                # Ejecutar nodo
                resultado = sincronizador_hibrido_node(estado_test)
                
                # Verificaciones
                assert resultado['sincronizado'] == True
                assert resultado['google_event_id'] == google_event_id
                
                # Verificar actualización en BD
                assert cita.google_event_id == google_event_id
                assert cita.sincronizada_google == True
    
    def test_registra_error_sincronizacion(self, mock_db_session, mock_cita_completa, estado_test):
        """Test 4: Registra error de sincronización en tabla SincronizacionCalendar"""
        cita, doctor, paciente = mock_cita_completa
        error_message = "Error de conexión Google Calendar"
        
        with patch('src.nodes.sincronizador_hibrido_node.SessionLocal', return_value=mock_db_session):
            with patch('src.nodes.sincronizador_hibrido_node.get_calendar_service', side_effect=Exception(error_message)):
                # Configurar mocks
                mock_db_session.query.return_value.filter.side_effect = [
                    Mock(first=Mock(return_value=cita)),
                    Mock(first=Mock(return_value=doctor)),
                    Mock(first=Mock(return_value=paciente))
                ]
                
                # Ejecutar nodo
                resultado = sincronizador_hibrido_node(estado_test)
                
                # Verificaciones
                assert resultado['sincronizado'] == False
                assert error_message in resultado.get('error_sync', '')
                
                # Verificar que se registró el error
                mock_db_session.add.assert_called()
                
                # Verificar que se llamó con instancia de SincronizacionCalendar
                call_args = mock_db_session.add.call_args[0][0]
                assert hasattr(call_args, 'cita_id')
                assert hasattr(call_args, 'estado') 
                assert hasattr(call_args, 'error_message')
    
    def test_color_rojo_para_citas_medicas(self, mock_db_session, mock_cita_completa, mock_google_calendar_service, estado_test):
        """Test 5: Eventos de Google Calendar usan color rojo (colorId: '11')"""
        cita, doctor, paciente = mock_cita_completa
        
        with patch('src.nodes.sincronizador_hibrido_node.SessionLocal', return_value=mock_db_session):
            with patch('src.nodes.sincronizador_hibrido_node.get_calendar_service', return_value=mock_google_calendar_service):
                # Configurar mocks
                mock_db_session.query.return_value.filter.side_effect = [
                    Mock(first=Mock(return_value=cita)),
                    Mock(first=Mock(return_value=doctor)),
                    Mock(first=Mock(return_value=paciente))
                ]
                
                # Ejecutar nodo
                sincronizador_hibrido_node(estado_test)
                
                # Verificar que se llamó insert con el color correcto
                mock_google_calendar_service.events.return_value.insert.assert_called_once()
                
                call_args = mock_google_calendar_service.events.return_value.insert.call_args
                evento = call_args[1]['body']  # Segundo argumento (body)
                
                # Verificaciones del evento
                assert 'colorId' in evento
                assert evento['colorId'] == '11'  # Rojo para citas médicas
    
    def test_extended_properties_correctas(self, mock_db_session, mock_cita_completa, mock_google_calendar_service, estado_test):
        """Test 6: Extended properties contienen cita_id y sistema correctos"""
        cita, doctor, paciente = mock_cita_completa
        
        with patch('src.nodes.sincronizador_hibrido_node.SessionLocal', return_value=mock_db_session):
            with patch('src.nodes.sincronizador_hibrido_node.get_calendar_service', return_value=mock_google_calendar_service):
                # Configurar mocks
                mock_db_session.query.return_value.filter.side_effect = [
                    Mock(first=Mock(return_value=cita)),
                    Mock(first=Mock(return_value=doctor)),
                    Mock(first=Mock(return_value=paciente))
                ]
                
                # Ejecutar nodo
                sincronizador_hibrido_node(estado_test)
                
                # Verificar extended properties
                call_args = mock_google_calendar_service.events.return_value.insert.call_args
                evento = call_args[1]['body']
                
                # Verificaciones
                assert 'extendedProperties' in evento
                assert 'private' in evento['extendedProperties']
                
                private_props = evento['extendedProperties']['private']
                assert 'cita_id' in private_props
                assert 'sistema' in private_props
                assert private_props['cita_id'] == str(cita.id)
                assert private_props['sistema'] == 'whatsapp_agent'

# ============================================================================
# TESTS DE EDGE CASES
# ============================================================================

class TestSincronizadorEdgeCases:
    """Tests de casos extremos y edge cases"""
    
    def test_sin_cita_id_en_estado(self):
        """Test: Sin cita_id_creada en estado"""
        estado_sin_cita = {'messages': []}
        
        resultado = sincronizador_hibrido_node(estado_sin_cita)
        
        assert resultado['sincronizado'] == False
        assert 'mensaje_sync' in resultado
    
    def test_cita_inexistente(self, mock_db_session):
        """Test: Cita no existe en BD"""
        estado = {'cita_id_creada': 999}
        
        with patch('src.nodes.sincronizador_hibrido_node.SessionLocal', return_value=mock_db_session):
            # Configurar mock para retornar None (cita no encontrada)
            mock_db_session.query.return_value.filter.return_value.first.return_value = None
            
            resultado = sincronizador_hibrido_node(estado)
            
            assert resultado['sincronizado'] == False
            assert 'error_sync' in resultado

if __name__ == "__main__":
    pytest.main([__file__, "-v"])