"""
Tests de Decisiones de Clasificación - ETAPA 8

Valida que la función decidir_flujo_clasificacion funcione correctamente.
"""

import pytest
import sys
import os
from pathlib import Path

# Añadir path del proyecto
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.graph_whatsapp import decidir_flujo_clasificacion
from src.state.agent_state import WhatsAppAgentState


class TestDecisionesClasificacion:
    """Tests de la función decidir_flujo_clasificacion"""
    
    def test_decision_solicitud_cita_paciente(self):
        """Test solicitud_cita + paciente → recepcionista"""
        state = {
            'clasificacion': 'solicitud_cita',
            'tipo_usuario': 'paciente'
        }
        
        resultado = decidir_flujo_clasificacion(state)
        assert resultado == 'recepcionista'
    
    def test_decision_solicitud_cita_admin(self):
        """Test solicitud_cita + admin → recepcionista"""
        state = {
            'clasificacion': 'solicitud_cita', 
            'tipo_usuario': 'admin'
        }
        
        resultado = decidir_flujo_clasificacion(state)
        assert resultado == 'recepcionista'
    
    def test_decision_medica_doctor(self):
        """Test medica + doctor → recuperacion_medica"""
        state = {
            'clasificacion': 'medica',
            'tipo_usuario': 'doctor'
        }
        
        resultado = decidir_flujo_clasificacion(state)
        assert resultado == 'recuperacion_medica'
    
    def test_decision_medica_no_doctor_falla(self):
        """Test medica + no doctor → NO va a recuperacion_medica"""
        state = {
            'clasificacion': 'medica',
            'tipo_usuario': 'paciente'
        }
        
        resultado = decidir_flujo_clasificacion(state)
        assert resultado != 'recuperacion_medica'
        # Debería ir a generacion_resumen por defecto
        assert resultado == 'generacion_resumen'
    
    def test_decision_personal_doctor(self):
        """Test personal + doctor → recuperacion_episodica"""
        state = {
            'clasificacion': 'personal',
            'tipo_usuario': 'doctor'
        }
        
        resultado = decidir_flujo_clasificacion(state)
        assert resultado == 'recuperacion_episodica'
    
    def test_decision_personal_paciente(self):
        """Test personal + paciente → recuperacion_episodica"""
        state = {
            'clasificacion': 'personal',
            'tipo_usuario': 'paciente'
        }
        
        resultado = decidir_flujo_clasificacion(state)
        assert resultado == 'recuperacion_episodica'
    
    def test_decision_chat_casual(self):
        """Test chat_casual → generacion_resumen"""
        state = {
            'clasificacion': 'chat_casual',
            'tipo_usuario': 'paciente'
        }
        
        resultado = decidir_flujo_clasificacion(state)
        assert resultado == 'generacion_resumen'
    
    def test_decision_clasificacion_invalida(self):
        """Test clasificación inválida → generacion_resumen"""
        state = {
            'clasificacion': 'clasificacion_inexistente',
            'tipo_usuario': 'doctor'
        }
        
        resultado = decidir_flujo_clasificacion(state)
        assert resultado == 'generacion_resumen'
    
    def test_decision_sin_tipo_usuario(self):
        """Test sin tipo_usuario → maneja gracefully"""
        state = {
            'clasificacion': 'medica'
            # Sin 'tipo_usuario'
        }
        
        # No debería crashear
        resultado = decidir_flujo_clasificacion(state)
        assert resultado in ['recuperacion_medica', 'recuperacion_episodica', 'generacion_resumen', 'recepcionista']
    
    def test_decision_paciente_externo_medica(self):
        """Test paciente + medica → generacion_resumen (no acceso médico)"""
        state = {
            'clasificacion': 'medica',
            'tipo_usuario': 'paciente_externo'
        }
        
        resultado = decidir_flujo_clasificacion(state)
        assert resultado == 'generacion_resumen'
    
    def test_decision_admin_personal(self):
        """Test admin + personal → recuperacion_episodica"""
        state = {
            'clasificacion': 'personal',
            'tipo_usuario': 'admin'
        }
        
        resultado = decidir_flujo_clasificacion(state)
        assert resultado == 'recuperacion_episodica'
    
    def test_decision_estado_vacio(self):
        """Test estado vacío → generacion_resumen"""
        state = {}
        
        resultado = decidir_flujo_clasificacion(state)
        assert resultado == 'generacion_resumen'


class TestPrioridadDecisiones:
    """Tests de prioridades en las decisiones"""
    
    def test_solicitud_cita_tiene_maxima_prioridad(self):
        """Test que solicitud_cita tiene prioridad sobre otros clasificaciones"""
        # Caso: solicitud_cita + personal → debe ir a recepcionista (no a recuperacion_episodica)
        state = {
            'clasificacion': 'solicitud_cita',
            'tipo_usuario': 'doctor'
        }
        
        resultado = decidir_flujo_clasificacion(state)
        assert resultado == 'recepcionista'
    
    def test_medica_doctor_tiene_prioridad_sobre_personal(self):
        """Test que medica + doctor tiene prioridad"""
        state = {
            'clasificacion': 'medica',
            'tipo_usuario': 'doctor'
        }
        
        resultado = decidir_flujo_clasificacion(state)
        assert resultado == 'recuperacion_medica'
        assert resultado != 'recuperacion_episodica'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])