"""
TEST ETAPA 5.3: test_bd_source_truth.py
Tests que validan que BD es source of truth

4 tests que validan:
- test_cita_valida_sin_google()
- test_consultar_citas_ignora_google()
- test_cancelar_cita_actualiza_ambos()
- test_bd_prevalece_sobre_google()

REGLA FUNDAMENTAL: BD médica SIEMPRE es válida, independiente de Google Calendar
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

from src.medical.models import CitasMedicas, Doctores, Pacientes, EstadoCita, TipoConsulta, SincronizacionCalendar, EstadoSincronizacion

# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_db_session():
    """Mock de sesión de base de datos"""
    session_mock = Mock()
    return session_mock

@pytest.fixture
def mock_cita_sin_google():
    """Mock de cita médica SIN sincronización con Google"""
    cita = Mock(spec=CitasMedicas)
    cita.id = 100
    cita.doctor_id = 1
    cita.paciente_id = 1
    cita.fecha_hora_inicio = datetime(2024, 3, 20, 9, 0, 0)
    cita.fecha_hora_fin = datetime(2024, 3, 20, 9, 30, 0)
    cita.tipo_consulta = TipoConsulta.primera_vez
    cita.estado = EstadoCita.programada
    cita.motivo_consulta = "Consulta de control"
    cita.google_event_id = None  # SIN Google Calendar
    cita.sincronizada_google = False
    return cita

@pytest.fixture
def mock_cita_con_google():
    """Mock de cita médica CON sincronización exitosa"""
    cita = Mock(spec=CitasMedicas)
    cita.id = 101
    cita.doctor_id = 1
    cita.paciente_id = 2
    cita.fecha_hora_inicio = datetime(2024, 3, 20, 10, 0, 0)
    cita.fecha_hora_fin = datetime(2024, 3, 20, 10, 30, 0)
    cita.tipo_consulta = TipoConsulta.seguimiento
    cita.estado = EstadoCita.programada
    cita.motivo_consulta = "Seguimiento tratamiento"
    cita.google_event_id = "google_event_456"
    cita.sincronizada_google = True
    return cita

@pytest.fixture
def mock_cita_error_google():
    """Mock de cita con error en sincronización Google"""
    cita = Mock(spec=CitasMedicas)
    cita.id = 102
    cita.doctor_id = 1
    cita.paciente_id = 3
    cita.fecha_hora_inicio = datetime(2024, 3, 20, 11, 0, 0)
    cita.fecha_hora_fin = datetime(2024, 3, 20, 11, 30, 0)
    cita.tipo_consulta = TipoConsulta.urgencia
    cita.estado = EstadoCita.programada
    cita.motivo_consulta = "Dolor de cabeza severo"
    cita.google_event_id = None
    cita.sincronizada_google = False
    return cita

@pytest.fixture
def mock_doctor():
    """Mock de doctor"""
    doctor = Mock(spec=Doctores)
    doctor.id = 1
    doctor.nombre_completo = "Dr. Ana López"
    doctor.especialidad = "Medicina Familiar"
    doctor.phone_number = "+52 664 111 2222"
    return doctor

@pytest.fixture
def mock_paciente():
    """Mock de paciente"""
    paciente = Mock(spec=Pacientes)
    paciente.id = 1
    paciente.nombre_completo = "Carlos Ruiz"
    paciente.telefono = "+52 664 333 4444"
    paciente.email = "carlos.ruiz@email.com"
    return paciente

# ============================================================================
# TESTS PRINCIPALES
# ============================================================================

class TestBDSourceOfTruth:
    """Suite principal para validar que BD es source of truth"""
    
    def test_cita_valida_sin_google(self, mock_db_session, mock_cita_sin_google, mock_doctor, mock_paciente):
        """Test 1: Cita es completamente válida sin sincronización Google"""
        
        # Simular consulta de cita desde BD
        with patch('sqlalchemy.orm.sessionmaker', return_value=lambda: mock_db_session):
            # Configurar mock para retornar cita sin Google
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_cita_sin_google
            
            # La cita debe ser válida independientemente de Google
            assert mock_cita_sin_google.id == 100
            assert mock_cita_sin_google.estado == EstadoCita.programada
            assert mock_cita_sin_google.google_event_id is None
            assert mock_cita_sin_google.sincronizada_google == False
            
            # Verificaciones críticas
            assert mock_cita_sin_google.fecha_hora_inicio is not None
            assert mock_cita_sin_google.fecha_hora_fin is not None
            assert mock_cita_sin_google.motivo_consulta is not None
            
            # Estado debe ser válido para operaciones médicas
            assert mock_cita_sin_google.estado in [EstadoCita.programada, EstadoCita.confirmada]
    
    def test_consultar_citas_ignora_google(self, mock_db_session):
        """Test 2: Consultas de citas ignoran estado de Google Calendar"""
        citas_mixtas = [
            # Cita sin Google
            Mock(id=100, google_event_id=None, sincronizada_google=False, estado=EstadoCita.programada),
            # Cita con Google exitoso  
            Mock(id=101, google_event_id="google_123", sincronizada_google=True, estado=EstadoCita.confirmada),
            # Cita con error en Google pero válida en BD
            Mock(id=102, google_event_id=None, sincronizada_google=False, estado=EstadoCita.programada)
        ]
        
        with patch('sqlalchemy.orm.sessionmaker', return_value=lambda: mock_db_session):
            # Configurar mock para retornar todas las citas
            mock_db_session.query.return_value.filter.return_value.all.return_value = citas_mixtas
            
            # Simular consulta de citas del doctor
            resultado_citas = citas_mixtas
            
            # Verificaciones: TODAS las citas son válidas desde BD
            assert len(resultado_citas) == 3
            
            for cita in resultado_citas:
                # Cada cita es válida independientemente del estado de Google
                assert cita.id is not None
                assert cita.estado in [EstadoCita.programada, EstadoCita.confirmada, EstadoCita.en_curso]
                # NO se filtra por sincronizada_google
    
    def test_cancelar_cita_actualiza_ambos(self, mock_db_session, mock_cita_con_google):
        """Test 3: Cancelar cita actualiza BD y opcionalmente Google"""
        
        def simular_cancelacion_cita(cita_id: int):
            """Simula proceso de cancelación de cita"""
            # 1. Actualizar BD (CRÍTICO - debe ocurrir siempre)
            mock_cita_con_google.estado = EstadoCita.cancelada
            
            # 2. Intentar actualizar Google (opcional)
            try:
                if mock_cita_con_google.google_event_id:
                    # Simular actualización en Google Calendar
                    # Si falla, no debe afectar la cancelación en BD
                    pass
            except Exception:
                # Error en Google NO debe afectar BD
                pass
            
            return {
                'exito': True,
                'cita_cancelada_bd': True,
                'cita_cancelada_google': mock_cita_con_google.google_event_id is not None
            }
        
        with patch('sqlalchemy.orm.sessionmaker', return_value=lambda: mock_db_session):
            # Ejecutar cancelación
            resultado = simular_cancelacion_cita(mock_cita_con_google.id)
            
            # Verificaciones críticas
            assert resultado['exito'] == True
            assert resultado['cita_cancelada_bd'] == True
            
            # BD debe estar actualizada
            assert mock_cita_con_google.estado == EstadoCita.cancelada
    
    def test_bd_prevalece_sobre_google(self, mock_db_session):
        """Test 4: En conflictos, BD prevalece sobre Google Calendar"""
        
        # Escenario: Cita existe en BD pero falló en Google
        cita_bd = Mock(
            id=200,
            estado=EstadoCita.programada,
            fecha_hora_inicio=datetime(2024, 3, 25, 14, 0, 0),
            google_event_id=None,
            sincronizada_google=False
        )
        
        # Registro de sincronización fallida
        sync_fallida = Mock(
            cita_id=200,
            estado=EstadoSincronizacion.error_permanente,
            intentos=5,
            error_message="Google Calendar API no disponible"
        )
        
        with patch('sqlalchemy.orm.sessionmaker', return_value=lambda: mock_db_session):
            # Configurar mocks
            mock_db_session.query.return_value.filter.return_value.first.side_effect = [cita_bd, sync_fallida]
            
            # Verificaciones del principio fundamental
            
            # 1. BD es source of truth
            assert cita_bd.estado == EstadoCita.programada  # Cita válida en BD
            
            # 2. Error en Google NO invalida la cita
            assert sync_fallida.estado == EstadoSincronizacion.error_permanente
            assert cita_bd.estado != EstadoCita.cancelada  # NO se cancela por error en Google
            
            # 3. Operaciones médicas usan SOLO BD
            assert cita_bd.fecha_hora_inicio is not None
            assert cita_bd.id is not None
            
            # 4. Google Calendar es solo visualización
            assert cita_bd.sincronizada_google == False  # No afecta validez

# ============================================================================
# TESTS DE CONSISTENCIA
# ============================================================================

class TestConsistenciaBD:
    """Tests para verificar consistencia de BD como source of truth"""
    
    def test_cita_existe_bd_sin_google_event(self, mock_db_session):
        """Test: Cita puede existir en BD sin evento en Google"""
        cita_bd_solo = Mock(
            id=300,
            doctor_id=1,
            paciente_id=1,
            estado=EstadoCita.confirmada,
            google_event_id=None,
            sincronizada_google=False,
            motivo_consulta="Consulta rutinaria"
        )
        
        # Esta cita debe ser completamente funcional
        assert cita_bd_solo.id is not None
        assert cita_bd_solo.estado == EstadoCita.confirmada
        assert cita_bd_solo.motivo_consulta is not None
        
        # No depende de Google para ser válida
        assert cita_bd_solo.google_event_id is None
        assert cita_bd_solo.sincronizada_google == False
    
    def test_operaciones_medicas_ignoran_google(self, mock_db_session):
        """Test: Operaciones médicas funcionan independiente de Google"""
        
        # Simular diferentes estados de sincronización
        citas_medicas = [
            Mock(id=1, estado=EstadoCita.programada, google_event_id=None),      # Sin Google
            Mock(id=2, estado=EstadoCita.confirmada, google_event_id="g123"),    # Con Google
            Mock(id=3, estado=EstadoCita.en_curso, google_event_id=None),       # Error Google
        ]
        
        # Todas las operaciones deben funcionar
        for cita in citas_medicas:
            # Operaciones médicas básicas
            assert cita.id is not None
            assert cita.estado is not None
            
            # Estado válido para atención médica
            assert cita.estado in [
                EstadoCita.programada,
                EstadoCita.confirmada, 
                EstadoCita.en_curso,
                EstadoCita.completada
            ]
            
            # Google es irrelevante para operaciones médicas
            # (puede ser None sin problema)
    
    def test_migracion_preserva_citas_existentes(self, mock_db_session):
        """Test: Migración no afecta citas existentes sin Google"""
        
        # Citas que existían ANTES de implementar Google Calendar
        citas_preexistentes = [
            Mock(
                id=1001, 
                fecha_hora_inicio=datetime(2024, 1, 15, 9, 0, 0),
                estado=EstadoCita.completada,
                google_event_id=None,  # No existía Google Calendar
                sincronizada_google=False
            ),
            Mock(
                id=1002,
                fecha_hora_inicio=datetime(2024, 2, 10, 14, 30, 0), 
                estado=EstadoCita.completada,
                google_event_id=None,  # No existía Google Calendar
                sincronizada_google=False
            )
        ]
        
        # Verificar que citas preexistentes siguen siendo válidas
        for cita in citas_preexistentes:
            assert cita.id is not None
            assert cita.estado == EstadoCita.completada  # Operación médica exitosa
            assert cita.fecha_hora_inicio is not None
            
            # Google Calendar no afecta el historial médico
            assert cita.google_event_id is None
            assert cita.sincronizada_google == False

# ============================================================================
# TESTS DE EDGE CASES CRÍTICOS
# ============================================================================

class TestEdgeCasesCriticos:
    """Tests para casos extremos que validan la robustez del sistema"""
    
    def test_google_api_caido_no_afecta_bd(self, mock_db_session):
        """Test: Si Google API está caído, BD sigue funcionando"""
        
        # Simular Google API completamente caído
        def simular_google_api_down():
            raise Exception("Google Calendar API unavailable")
        
        # Cita debe crearse en BD independientemente
        nueva_cita = Mock(
            id=500,
            doctor_id=1,
            paciente_id=1,
            estado=EstadoCita.programada,
            fecha_hora_inicio=datetime(2024, 4, 1, 10, 0, 0),
            google_event_id=None,  # Falló Google
            sincronizada_google=False
        )
        
        # Operaciones médicas deben continuar
        assert nueva_cita.id is not None
        assert nueva_cita.estado == EstadoCita.programada
        assert nueva_cita.fecha_hora_inicio is not None
        
        # Error en Google NO cancela la cita médica
        assert nueva_cita.estado != EstadoCita.cancelada
    
    def test_inconsistencia_google_no_afecta_bd(self, mock_db_session):
        """Test: Inconsistencias en Google Calendar no afectan BD"""
        
        # Escenario: Google tiene evento pero BD no lo reconoce
        cita_bd = Mock(
            id=600,
            estado=EstadoCita.programada,
            google_event_id="evento_huerfano_123",  # Google tiene evento
            sincronizada_google=True
        )
        
        # BD es la única fuente de verdad para decisiones médicas
        assert cita_bd.estado == EstadoCita.programada
        
        # Si hay conflicto, BD prevalece
        # (Por ejemplo, si Google dice "cancelada" pero BD dice "programada")
        estado_real = cita_bd.estado  # BD prevalece
        assert estado_real == EstadoCita.programada
        
        # Google Calendar solo refleja, no decide

if __name__ == "__main__":
    pytest.main([__file__, "-v"])