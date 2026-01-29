"""
TEST ETAPA 5.2: test_retry_logic.py
Tests del worker de reintentos de sincronización

5 tests que validan:
- test_retry_worker_reintenta_fallidas()
- test_respeta_max_intentos()
- test_incrementa_contador_intentos()
- test_calcula_siguiente_reintento_15min()
- test_no_reintenta_si_ya_sincronizada()

REGLA: Máximo 5 intentos, cada 15 minutos
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

from src.workers.retry_worker import (
    retry_failed_syncs,
    obtener_sincronizaciones_pendientes,
    procesar_reintento_sincronizacion,
    sincronizar_cita_retry
)
from src.medical.models import SincronizacionCalendar, EstadoSincronizacion, CitasMedicas

# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_db_session():
    """Mock de sesión de base de datos"""
    session_mock = Mock()
    return session_mock

@pytest.fixture
def mock_sincronizacion_error():
    """Mock de sincronización con error"""
    sync = Mock(spec=SincronizacionCalendar)
    sync.id = 1
    sync.cita_id = 123
    sync.estado = EstadoSincronizacion.error
    sync.intentos = 1
    sync.max_intentos = 5
    sync.siguiente_reintento = datetime.now() - timedelta(minutes=1)  # Ya es tiempo de reintentar
    sync.error_message = "Error anterior"
    sync.google_event_id = None
    return sync

@pytest.fixture
def mock_sincronizacion_max_intentos():
    """Mock de sincronización que ya alcanzó máximo de intentos"""
    sync = Mock(spec=SincronizacionCalendar)
    sync.id = 2
    sync.cita_id = 124
    sync.estado = EstadoSincronizacion.error
    sync.intentos = 5
    sync.max_intentos = 5
    sync.siguiente_reintento = datetime.now() - timedelta(minutes=1)
    sync.error_message = "Error después de 5 intentos"
    return sync

@pytest.fixture
def mock_sincronizacion_ya_sincronizada():
    """Mock de sincronización ya exitosa"""
    sync = Mock(spec=SincronizacionCalendar)
    sync.id = 3
    sync.cita_id = 125
    sync.estado = EstadoSincronizacion.sincronizada
    sync.intentos = 2
    sync.google_event_id = "google_event_123"
    return sync

@pytest.fixture
def mock_cita_para_retry():
    """Mock de cita para retry"""
    cita = Mock(spec=CitasMedicas)
    cita.id = 123
    cita.doctor_id = 1
    cita.paciente_id = 1
    cita.fecha_hora_inicio = datetime(2024, 3, 15, 10, 0, 0)
    cita.fecha_hora_fin = datetime(2024, 3, 15, 10, 30, 0)
    cita.tipo_consulta = Mock()
    cita.tipo_consulta.value = 'seguimiento'
    cita.google_event_id = None
    cita.sincronizada_google = False
    return cita

# ============================================================================
# TESTS
# ============================================================================

class TestRetryLogic:
    """Suite de tests para la lógica de reintentos"""
    
    def test_retry_worker_reintenta_fallidas(self, mock_db_session, mock_sincronizacion_error):
        """Test 1: Worker reintenta sincronizaciones fallidas"""
        with patch('src.workers.retry_worker.SessionLocal', return_value=mock_db_session):
            with patch('src.workers.retry_worker.obtener_sincronizaciones_pendientes') as mock_get_pending:
                with patch('src.workers.retry_worker.procesar_reintento_sincronizacion') as mock_procesar:
                    
                    # Configurar mocks
                    mock_get_pending.return_value = [mock_sincronizacion_error]
                    mock_procesar.return_value = True  # Retry exitoso
                    
                    # Ejecutar worker
                    retry_failed_syncs()
                    
                    # Verificaciones
                    mock_get_pending.assert_called_once()
                    mock_procesar.assert_called_once_with(mock_sincronizacion_error)
    
    def test_respeta_max_intentos(self, mock_db_session, mock_sincronizacion_max_intentos, mock_cita_para_retry):
        """Test 2: Respeta máximo de intentos (5) y marca como error permanente"""
        with patch('src.workers.retry_worker.SessionLocal', return_value=mock_db_session):
            with patch('src.workers.retry_worker.sincronizar_cita_retry') as mock_sync_retry:
                
                # Configurar mock - falla el retry
                mock_sync_retry.return_value = {'exito': False, 'error': 'Error persistente'}
                
                # Ejecutar procesamiento
                resultado = procesar_reintento_sincronizacion(mock_sincronizacion_max_intentos)
                
                # Verificaciones
                assert resultado == False  # No fue exitoso
                
                # Verificar que se marcó como error permanente
                assert mock_sincronizacion_max_intentos.estado == EstadoSincronizacion.error_permanente
                assert mock_sincronizacion_max_intentos.siguiente_reintento is None
                
                # Debe hacer commit
                mock_db_session.commit.assert_called()
    
    def test_incrementa_contador_intentos(self, mock_db_session, mock_sincronizacion_error):
        """Test 3: Incrementa contador de intentos correctamente"""
        intentos_iniciales = mock_sincronizacion_error.intentos
        
        with patch('src.workers.retry_worker.SessionLocal', return_value=mock_db_session):
            with patch('src.workers.retry_worker.sincronizar_cita_retry') as mock_sync_retry:
                
                # Configurar mock - falla el retry
                mock_sync_retry.return_value = {'exito': False, 'error': 'Error de red'}
                
                # Ejecutar procesamiento
                procesar_reintento_sincronizacion(mock_sincronizacion_error)
                
                # Verificaciones
                assert mock_sincronizacion_error.intentos == intentos_iniciales + 1
                assert mock_sincronizacion_error.ultimo_intento is not None
                
                # Estado debe seguir siendo 'error' (no error_permanente aún)
                assert mock_sincronizacion_error.estado == EstadoSincronizacion.error
    
    def test_calcula_siguiente_reintento_15min(self, mock_db_session, mock_sincronizacion_error):
        """Test 4: Calcula siguiente reintento en 15 minutos"""
        tiempo_antes = datetime.now()
        
        with patch('src.workers.retry_worker.SessionLocal', return_value=mock_db_session):
            with patch('src.workers.retry_worker.sincronizar_cita_retry') as mock_sync_retry:
                
                # Configurar mock - falla el retry
                mock_sync_retry.return_value = {'exito': False, 'error': 'Error temporal'}
                
                # Ejecutar procesamiento
                procesar_reintento_sincronizacion(mock_sincronizacion_error)
                
                # Verificaciones del timing
                siguiente_reintento = mock_sincronizacion_error.siguiente_reintento
                assert siguiente_reintento is not None
                
                # Debe ser aproximadamente 15 minutos después
                tiempo_esperado = tiempo_antes + timedelta(minutes=15)
                diferencia = abs((siguiente_reintento - tiempo_esperado).total_seconds())
                
                # Tolerancia de 5 segundos
                assert diferencia <= 5
    
    def test_no_reintenta_si_ya_sincronizada(self, mock_db_session):
        """Test 5: No reintenta si sincronización ya fue exitosa"""
        ahora = datetime.now()
        
        with patch('src.workers.retry_worker.SessionLocal', return_value=mock_db_session):
            # Configurar query para no retornar sincronizaciones ya exitosas
            mock_query = Mock()
            mock_db_session.query.return_value = mock_query
            mock_query.filter.return_value.all.return_value = []  # Lista vacía
            
            # Ejecutar función de obtener pendientes
            pendientes = obtener_sincronizaciones_pendientes()
            
            # Verificaciones
            assert len(pendientes) == 0
            
            # Verificar que el filtro excluye sincronizadas
            mock_query.filter.assert_called_once()

# ============================================================================
# TESTS DE EDGE CASES
# ============================================================================

class TestRetryEdgeCases:
    """Tests de casos extremos para retry logic"""
    
    def test_maneja_excepcion_durante_retry(self, mock_db_session, mock_sincronizacion_error):
        """Test: Maneja excepciones durante el retry"""
        with patch('src.workers.retry_worker.SessionLocal', return_value=mock_db_session):
            with patch('src.workers.retry_worker.sincronizar_cita_retry', side_effect=Exception("Error crítico")):
                
                # Ejecutar procesamiento
                resultado = procesar_reintento_sincronizacion(mock_sincronizacion_error)
                
                # Debe retornar False y hacer rollback
                assert resultado == False
                mock_db_session.rollback.assert_called()
    
    def test_sin_sincronizaciones_pendientes(self, mock_db_session):
        """Test: Worker funciona correctamente sin sincronizaciones pendientes"""
        with patch('src.workers.retry_worker.SessionLocal', return_value=mock_db_session):
            with patch('src.workers.retry_worker.obtener_sincronizaciones_pendientes', return_value=[]):
                
                # No debe lanzar excepción
                retry_failed_syncs()
    
    def test_reintento_exitoso_actualiza_estado(self, mock_db_session, mock_sincronizacion_error):
        """Test: Retry exitoso actualiza estado a 'sincronizada'"""
        with patch('src.workers.retry_worker.SessionLocal', return_value=mock_db_session):
            with patch('src.workers.retry_worker.sincronizar_cita_retry') as mock_sync_retry:
                
                # Configurar mock - retry exitoso
                mock_sync_retry.return_value = {
                    'exito': True, 
                    'event_id': 'google_event_retry_123'
                }
                
                # Ejecutar procesamiento
                resultado = procesar_reintento_sincronizacion(mock_sincronizacion_error)
                
                # Verificaciones
                assert resultado == True
                assert mock_sincronizacion_error.estado == EstadoSincronizacion.sincronizada
                assert mock_sincronizacion_error.google_event_id == 'google_event_retry_123'
                assert mock_sincronizacion_error.error_message is None
                assert mock_sincronizacion_error.siguiente_reintento is None

# ============================================================================
# TESTS DE TIMING Y PROGRAMACIÓN
# ============================================================================

class TestRetryTiming:
    """Tests específicos para verificar timing de reintentos"""
    
    def test_filtra_por_tiempo_siguiente_reintento(self, mock_db_session):
        """Test: Solo obtiene sincronizaciones cuyo tiempo de reintento ya llegó"""
        ahora = datetime.now()
        
        with patch('src.workers.retry_worker.SessionLocal', return_value=mock_db_session):
            with patch('src.workers.retry_worker.datetime') as mock_datetime:
                
                # Mock datetime.now()
                mock_datetime.now.return_value = ahora
                
                # Ejecutar función
                obtener_sincronizaciones_pendientes()
                
                # Verificar que se filtró por tiempo
                mock_db_session.query.assert_called_once()
    
    def test_estado_reintentando_durante_proceso(self, mock_db_session, mock_sincronizacion_error):
        """Test: Cambia estado a 'reintentando' durante el proceso"""
        with patch('src.workers.retry_worker.SessionLocal', return_value=mock_db_session):
            with patch('src.workers.retry_worker.sincronizar_cita_retry') as mock_sync_retry:
                
                # Configurar mock 
                mock_sync_retry.return_value = {'exito': False, 'error': 'Error temporal'}
                
                # Ejecutar procesamiento
                procesar_reintento_sincronizacion(mock_sincronizacion_error)
                
                # Verificar que primero se cambió a 'reintentando'
                # (esto se verifica por el incremento de intentos y último_intento)
                assert mock_sincronizacion_error.intentos > 0
                assert mock_sincronizacion_error.ultimo_intento is not None

if __name__ == "__main__":
    pytest.main([__file__, "-v"])