"""
Tests de Decisiones de Ejecución - ETAPA 8

Valida que la función decidir_tipo_ejecucion funcione correctamente.
"""

import pytest
import sys
import os
from pathlib import Path

# Añadir path del proyecto
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.graph_whatsapp import decidir_tipo_ejecucion
from src.state.agent_state import WhatsAppAgentState


class TestDecisionesEjecucion:
    """Tests de la función decidir_tipo_ejecucion"""
    
    def test_decision_sin_herramientas(self):
        """Test sin herramientas → generacion_resumen"""
        state = {
            'herramientas_seleccionadas': []
        }
        
        resultado = decidir_tipo_ejecucion(state)
        assert resultado == 'generacion_resumen'
    
    def test_decision_solo_herramientas_personales(self):
        """Test solo herramientas personales → ejecucion_herramientas"""
        state = {
            'herramientas_seleccionadas': [
                {'nombre': 'crear_evento', 'tipo': 'personal'},
                {'nombre': 'listar_eventos', 'tipo': 'personal'}
            ]
        }
        
        resultado = decidir_tipo_ejecucion(state)
        assert resultado == 'ejecucion_herramientas'
    
    def test_decision_solo_herramientas_medicas(self):
        """Test solo herramientas médicas → ejecucion_medica"""
        state = {
            'herramientas_seleccionadas': [
                {'nombre': 'buscar_pacientes', 'tipo': 'medica'},
                {'nombre': 'registrar_consulta', 'tipo': 'medica'}
            ]
        }
        
        resultado = decidir_tipo_ejecucion(state)
        assert resultado == 'ejecucion_medica'
    
    def test_decision_herramientas_mixtas(self):
        """Test herramientas mixtas (médicas + personales) → ejecucion_medica"""
        state = {
            'herramientas_seleccionadas': [
                {'nombre': 'buscar_pacientes', 'tipo': 'medica'},
                {'nombre': 'crear_evento', 'tipo': 'personal'}
            ]
        }
        
        resultado = decidir_tipo_ejecucion(state)
        # Si hay médicas, debe ir a ejecución médica
        assert resultado == 'ejecucion_medica'
    
    def test_decision_herramientas_vacio(self):
        """Test herramientas_seleccionadas vacío → generacion_resumen"""
        state = {}  # Sin key herramientas_seleccionadas
        
        resultado = decidir_tipo_ejecucion(state)
        assert resultado == 'generacion_resumen'
    
    def test_decision_herramientas_formato_invalido(self):
        """Test herramientas con formato inválido → maneja gracefully"""
        state = {
            'herramientas_seleccionadas': [
                'herramienta_string',  # Formato inválido, no es dict
                {'nombre': 'crear_evento'}  # Sin 'tipo'
            ]
        }
        
        # No debería crashear
        resultado = decidir_tipo_ejecucion(state)
        assert resultado in ['ejecucion_medica', 'ejecucion_herramientas', 'generacion_resumen']
    
    def test_decision_herramienta_sin_tipo(self):
        """Test herramienta sin campo 'tipo' → no considera como médica"""
        state = {
            'herramientas_seleccionadas': [
                {'nombre': 'crear_evento'}  # Sin 'tipo'
            ]
        }
        
        resultado = decidir_tipo_ejecucion(state)
        # Sin tipo definido, no es médica → ejecucion_herramientas
        assert resultado == 'ejecucion_herramientas'
    
    def test_decision_multiples_medicas(self):
        """Test múltiples herramientas médicas → ejecucion_medica"""
        state = {
            'herramientas_seleccionadas': [
                {'nombre': 'buscar_pacientes', 'tipo': 'medica'},
                {'nombre': 'registrar_consulta', 'tipo': 'medica'},
                {'nombre': 'generar_reporte', 'tipo': 'medica'}
            ]
        }
        
        resultado = decidir_tipo_ejecucion(state)
        assert resultado == 'ejecucion_medica'


class TestLogicaMedicas:
    """Tests específicos de la lógica de herramientas médicas"""
    
    def test_una_medica_entre_varias_personales(self):
        """Test que una sola médica entre varias personales → ejecucion_medica"""
        state = {
            'herramientas_seleccionadas': [
                {'nombre': 'crear_evento', 'tipo': 'personal'},
                {'nombre': 'buscar_pacientes', 'tipo': 'medica'},  # Solo esta es médica
                {'nombre': 'listar_eventos', 'tipo': 'personal'},
                {'nombre': 'actualizar_evento', 'tipo': 'personal'}
            ]
        }
        
        resultado = decidir_tipo_ejecucion(state)
        assert resultado == 'ejecucion_medica'
    
    def test_tipo_medica_case_sensitive(self):
        """Test que 'tipo' es case-sensitive para 'medica'"""
        state = {
            'herramientas_seleccionadas': [
                {'nombre': 'buscar_pacientes', 'tipo': 'MEDICA'},  # Mayúsculas
                {'nombre': 'registrar_consulta', 'tipo': 'Medica'}   # Mixed case
            ]
        }
        
        resultado = decidir_tipo_ejecucion(state)
        # Solo 'medica' en minúsculas debe contar como médica
        assert resultado == 'ejecucion_herramientas'  # No reconoce como médicas
    
    def test_valores_tipo_invalidos(self):
        """Test con valores de 'tipo' inválidos → ejecucion_herramientas"""
        state = {
            'herramientas_seleccionadas': [
                {'nombre': 'herramienta1', 'tipo': 'admin'},
                {'nombre': 'herramienta2', 'tipo': 'sistema'},
                {'nombre': 'herramienta3', 'tipo': None}
            ]
        }
        
        resultado = decidir_tipo_ejecucion(state)
        assert resultado == 'ejecucion_herramientas'


class TestCasosEdge:
    """Tests de casos edge y situaciones extremas"""
    
    def test_herramientas_lista_vacia_explicita(self):
        """Test lista explícitamente vacía"""
        state = {
            'herramientas_seleccionadas': []
        }
        
        resultado = decidir_tipo_ejecucion(state)
        assert resultado == 'generacion_resumen'
    
    def test_herramientas_none(self):
        """Test herramientas_seleccionadas = None"""
        state = {
            'herramientas_seleccionadas': None
        }
        
        # Debería manejar gracefully
        resultado = decidir_tipo_ejecucion(state)
        # None se evalúa como falsy → generacion_resumen
        assert resultado == 'generacion_resumen'
    
    def test_herramienta_dict_vacio(self):
        """Test herramienta como dict vacío"""
        state = {
            'herramientas_seleccionadas': [{}]  # Dict vacío
        }
        
        resultado = decidir_tipo_ejecucion(state)
        # Dict vacío no tiene 'tipo' → ejecucion_herramientas
        assert resultado == 'ejecucion_herramientas'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])