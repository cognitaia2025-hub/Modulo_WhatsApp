"""
Tests de Decisiones del Recepcionista - ETAPA 8

Valida que la función decidir_despues_recepcionista funcione correctamente.
"""

import pytest
import sys
import os
from pathlib import Path

# Añadir path del proyecto
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.graph_whatsapp import decidir_despues_recepcionista
from src.state.agent_state import WhatsAppAgentState


class TestDecisionesRecepcionista:
    """Tests de la función decidir_despues_recepcionista"""
    
    def test_decision_recepcionista_completado(self):
        """Test estado_conversacion = 'completado' → sincronizador_hibrido"""
        state = {
            'estado_conversacion': 'completado'
        }
        
        resultado = decidir_despues_recepcionista(state)
        assert resultado == 'sincronizador_hibrido'
    
    def test_decision_recepcionista_inicial(self):
        """Test estado_conversacion = 'inicial' → generacion_resumen"""
        state = {
            'estado_conversacion': 'inicial'
        }
        
        resultado = decidir_despues_recepcionista(state)
        assert resultado == 'generacion_resumen'
    
    def test_decision_recepcionista_solicitando_nombre(self):
        """Test estado_conversacion = 'solicitando_nombre' → generacion_resumen"""
        state = {
            'estado_conversacion': 'solicitando_nombre'
        }
        
        resultado = decidir_despues_recepcionista(state)
        assert resultado == 'generacion_resumen'
    
    def test_decision_recepcionista_esperando_seleccion(self):
        """Test estado_conversacion = 'esperando_seleccion' → generacion_resumen"""
        state = {
            'estado_conversacion': 'esperando_seleccion'
        }
        
        resultado = decidir_despues_recepcionista(state)
        assert resultado == 'generacion_resumen'
    
    def test_decision_recepcionista_sin_estado(self):
        """Test sin estado_conversacion → generacion_resumen"""
        state = {}  # Sin key estado_conversacion
        
        resultado = decidir_despues_recepcionista(state)
        assert resultado == 'generacion_resumen'
    
    def test_decision_recepcionista_estado_invalido(self):
        """Test estado_conversacion inválido → generacion_resumen"""
        state = {
            'estado_conversacion': 'estado_inexistente'
        }
        
        resultado = decidir_despues_recepcionista(state)
        assert resultado == 'generacion_resumen'


class TestEstadosConversacionValidos:
    """Tests de diferentes estados válidos de conversación"""
    
    def test_confirmando_datos(self):
        """Test estado_conversacion = 'confirmando_datos' → generacion_resumen"""
        state = {
            'estado_conversacion': 'confirmando_datos'
        }
        
        resultado = decidir_despues_recepcionista(state)
        assert resultado == 'generacion_resumen'
    
    def test_solicitando_fecha(self):
        """Test estado_conversacion = 'solicitando_fecha' → generacion_resumen"""
        state = {
            'estado_conversacion': 'solicitando_fecha'
        }
        
        resultado = decidir_despues_recepcionista(state)
        assert resultado == 'generacion_resumen'
    
    def test_solicitando_motivo(self):
        """Test estado_conversacion = 'solicitando_motivo' → generacion_resumen"""
        state = {
            'estado_conversacion': 'solicitando_motivo'
        }
        
        resultado = decidir_despues_recepcionista(state)
        assert resultado == 'generacion_resumen'
    
    def test_procesando(self):
        """Test estado_conversacion = 'procesando' → generacion_resumen"""
        state = {
            'estado_conversacion': 'procesando'
        }
        
        resultado = decidir_despues_recepcionista(state)
        assert resultado == 'generacion_resumen'


class TestLogicaCompletado:
    """Tests específicos para el estado 'completado'"""
    
    def test_completado_case_sensitive(self):
        """Test que 'completado' es case-sensitive"""
        estados_invalidos = [
            'COMPLETADO',
            'Completado', 
            'completAdo',
            'completado '  # Con espacio
        ]
        
        for estado in estados_invalidos:
            state = {
                'estado_conversacion': estado
            }
            
            resultado = decidir_despues_recepcionista(state)
            assert resultado == 'generacion_resumen', f"Estado '{estado}' debería ir a generacion_resumen"
    
    def test_completado_exacto(self):
        """Test que solo 'completado' exacto activa sincronización"""
        state = {
            'estado_conversacion': 'completado'
        }
        
        resultado = decidir_despues_recepcionista(state)
        assert resultado == 'sincronizador_hibrido'
    
    def test_completado_con_contexto_adicional(self):
        """Test completado con datos adicionales en el state"""
        state = {
            'estado_conversacion': 'completado',
            'cita_id': 'CITA_12345',
            'fecha_cita': '2024-01-15 10:00',
            'motivo_cita': 'Consulta general',
            'doctor_id': 'DR_001'
        }
        
        resultado = decidir_despues_recepcionista(state)
        assert resultado == 'sincronizador_hibrido'


class TestCasosEdge:
    """Tests de casos edge y situaciones extremas"""
    
    def test_estado_conversacion_none(self):
        """Test estado_conversacion = None"""
        state = {
            'estado_conversacion': None
        }
        
        resultado = decidir_despues_recepcionista(state)
        assert resultado == 'generacion_resumen'
    
    def test_estado_conversacion_vacio(self):
        """Test estado_conversacion = ''"""
        state = {
            'estado_conversacion': ''
        }
        
        resultado = decidir_despues_recepcionista(state)
        assert resultado == 'generacion_resumen'
    
    def test_estado_conversacion_numerico(self):
        """Test estado_conversacion con valor numérico"""
        state = {
            'estado_conversacion': 123
        }
        
        resultado = decidir_despues_recepcionista(state)
        assert resultado == 'generacion_resumen'
    
    def test_state_completamente_vacio(self):
        """Test state completamente vacío"""
        state = {}
        
        resultado = decidir_despues_recepcionista(state)
        assert resultado == 'generacion_resumen'


class TestIntegracionConRecepcionista:
    """Tests que simulan la integración con el nodo recepcionista"""
    
    def test_flujo_cita_agendada_exitosamente(self):
        """Test simulando cita agendada exitosamente"""
        # Simular state después de que recepcionista agendó cita
        state = {
            'estado_conversacion': 'completado',
            'cita_id': 'CITA_20240115_001',
            'fecha_cita': '2024-01-15T10:00:00',
            'doctor_id': 'DR_GARCIA',
            'motivo_cita': 'Consulta general',
            'paciente_id': 'PAC_12345'
        }
        
        resultado = decidir_despues_recepcionista(state)
        assert resultado == 'sincronizador_hibrido'
    
    def test_flujo_cita_en_proceso(self):
        """Test simulando cita aún en proceso de agendamiento"""
        state = {
            'estado_conversacion': 'esperando_seleccion',
            'doctores_disponibles': [
                {'id': 'DR_GARCIA', 'nombre': 'Dr. García'},
                {'id': 'DR_LOPEZ', 'nombre': 'Dr. López'}
            ],
            'fecha_propuesta': '2024-01-15'
        }
        
        resultado = decidir_despues_recepcionista(state)
        assert resultado == 'generacion_resumen'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])