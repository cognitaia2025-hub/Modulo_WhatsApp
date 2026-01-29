"""
Tests para test_recepcionista_node.py - Etapa 4
8 tests para validar el comportamiento del nodo de recepcionista conversacional
"""

import pytest
import sys
import os
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

# Agregar el directorio raíz al path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.nodes.recepcionista_node import recepcionista_node
from src.state.agent_state import WhatsAppAgentState
from langchain_core.messages import HumanMessage, AIMessage


class TestRecepcionistaNOde:
    """Suite de tests para el nodo de recepcionista conversacional"""
    
    def setup_method(self):
        """Setup para cada test"""
        self.test_phone = "+521234567890"
        self.slots_mock = [
            {
                "fecha": "2026-01-30",
                "hora_inicio": "08:30",
                "hora_fin": "09:30", 
                "doctor_asignado_id": 1,
                "doctor_nombre": "Santiago"
            },
            {
                "fecha": "2026-01-31",
                "hora_inicio": "10:30", 
                "hora_fin": "11:30",
                "doctor_asignado_id": 2,
                "doctor_nombre": "Joana"
            },
            {
                "fecha": "2026-02-01",
                "hora_inicio": "14:30",
                "hora_fin": "15:30",
                "doctor_asignado_id": 1,
                "doctor_nombre": "Santiago"
            }
        ]

    def test_paciente_existente_muestra_slots(self):
        """Test: Paciente existente ve slots disponibles inmediatamente"""
        
        # Mock del paciente existente
        paciente_mock = MagicMock()
        paciente_mock.nombre_completo = "Juan Pérez"
        paciente_mock.id = 123
        
        with patch('src.nodes.recepcionista_node.get_paciente_by_phone', return_value=paciente_mock):
            with patch('src.nodes.recepcionista_node.generar_slots_con_turnos', return_value=self.slots_mock):
                
                state = {
                    'messages': [HumanMessage(content="Hola, quiero cita")],
                    'user_id': self.test_phone,
                    'estado_conversacion': 'inicial',
                    'slots_disponibles': [],
                    'timestamp': datetime.now().isoformat()
                }
                
                resultado = recepcionista_node(state)
                
                # Verificaciones
                assert "¡Hola Juan Pérez!" in resultado['respuesta_recepcionista']
                assert "🗓️ **Opciones disponibles:**" in resultado['respuesta_recepcionista']
                assert "A)" in resultado['respuesta_recepcionista']
                assert "B)" in resultado['respuesta_recepcionista'] 
                assert "C)" in resultado['respuesta_recepcionista']
                assert resultado['estado_conversacion'] == 'esperando_seleccion'
                assert len(resultado['slots_disponibles']) == 3
                
                print("✅ Test paciente existente muestra slots: PASÓ")

    def test_paciente_nuevo_pide_nombre(self):
        """Test: Paciente nuevo recibe solicitud de nombre"""
        
        with patch('src.nodes.recepcionista_node.get_paciente_by_phone', return_value=None):
            
            state = {
                'messages': [HumanMessage(content="Hola")],
                'user_id': self.test_phone,
                'estado_conversacion': 'inicial',
                'slots_disponibles': [],
                'timestamp': datetime.now().isoformat()
            }
            
            resultado = recepcionista_node(state)
            
            # Verificaciones
            assert "¡Hola!" in resultado['respuesta_recepcionista']
            assert "primera vez" in resultado['respuesta_recepcionista']
            assert "nombre completo" in resultado['respuesta_recepcionista']
            assert resultado['estado_conversacion'] == 'solicitando_nombre'
            assert len(resultado['slots_disponibles']) == 0
            
            print("✅ Test paciente nuevo pide nombre: PASÓ")

    def test_registrar_nombre_y_mostrar_slots(self):
        """Test: Registrar nombre de paciente nuevo y mostrar slots"""
        
        registro_mock = {
            "paciente_id": 456,
            "es_nuevo": True,
            "nombre": "María García"
        }
        
        with patch('src.nodes.recepcionista_node.extraer_nombre_con_llm', return_value="María García"):
            with patch('src.nodes.recepcionista_node.registrar_paciente_externo', return_value=registro_mock):
                with patch('src.nodes.recepcionista_node.generar_slots_con_turnos', return_value=self.slots_mock):
                    
                    state = {
                        'messages': [HumanMessage(content="Me llamo María García")],
                        'user_id': self.test_phone,
                        'estado_conversacion': 'solicitando_nombre',
                        'slots_disponibles': [],
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    resultado = recepcionista_node(state)
                    
                    # Verificaciones
                    assert "¡Gracias María García!" in resultado['respuesta_recepcionista']
                    assert "registré en nuestro sistema" in resultado['respuesta_recepcionista']
                    assert "🗓️ **Opciones disponibles:**" in resultado['respuesta_recepcionista']
                    assert resultado['estado_conversacion'] == 'esperando_seleccion'
                    assert len(resultado['slots_disponibles']) == 3
                    
                    print("✅ Test registrar nombre y mostrar slots: PASÓ")

    def test_seleccion_valida_agenda_cita(self):
        """Test: Selección válida agenda la cita exitosamente"""
        
        # Mock del paciente y doctor
        paciente_mock = MagicMock()
        paciente_mock.id = 123
        paciente_mock.nombre_completo = "Juan Pérez"
        
        doctor_mock = MagicMock()
        doctor_mock.phone_number = "+526641234567"
        doctor_mock.nombre_completo = "Dr. Santiago"
        
        # Mock del resultado exitoso del agendamiento
        resultado_agenda = "✅ **Cita agendada exitosamente**\n\nID Cita: 789"
        
        with patch('src.nodes.recepcionista_node.extraer_seleccion', return_value=1):  # B
            with patch('src.nodes.recepcionista_node.get_paciente_by_phone', return_value=paciente_mock):
                with patch('src.nodes.recepcionista_node.get_doctor_by_id', return_value=doctor_mock):
                    with patch('src.medical.crud.schedule_appointment', return_value=789):
                        
                        state = {
                            'messages': [HumanMessage(content="Escojo B")],
                            'user_id': self.test_phone,
                            'estado_conversacion': 'esperando_seleccion',
                            'slots_disponibles': self.slots_mock,
                            'timestamp': datetime.now().isoformat()
                        }
                        
                        resultado = recepcionista_node(state)
                        
                        # Verificaciones
                        assert "🎉 ¡Perfecto!" in resultado['respuesta_recepcionista']
                        assert "cita ha sido agendada" in resultado['respuesta_recepcionista']
                        assert "📅 **Detalles de tu cita:**" in resultado['respuesta_recepcionista']
                        assert "Dr. Santiago" in resultado['respuesta_recepcionista']
                        assert resultado['estado_conversacion'] == 'completado'
                        
                        print("✅ Test selección válida agenda cita: PASÓ")

    def test_seleccion_invalida_repite_pregunta(self):
        """Test: Selección inválida repite la pregunta"""
        
        with patch('src.nodes.recepcionista_node.extraer_seleccion', return_value=None):
            
            state = {
                'messages': [HumanMessage(content="quiero la primera")],
                'user_id': self.test_phone,
                'estado_conversacion': 'esperando_seleccion',
                'slots_disponibles': self.slots_mock,
                'timestamp': datetime.now().isoformat()
            }
            
            resultado = recepcionista_node(state)
            
            # Verificaciones
            assert "No pude entender tu selección" in resultado['respuesta_recepcionista']
            assert "escribir la letra" in resultado['respuesta_recepcionista']
            assert resultado['estado_conversacion'] == 'esperando_seleccion'
            
            print("✅ Test selección inválida repite pregunta: PASÓ")

    def test_estado_inicial_transiciona_correctamente(self):
        """Test: Estado inicial transiciona correctamente según el caso"""
        
        # Caso 1: Paciente nuevo
        with patch('src.nodes.recepcionista_node.get_paciente_by_phone', return_value=None):
            state = {
                'messages': [HumanMessage(content="Hola")],
                'user_id': self.test_phone,
                'estado_conversacion': 'inicial',
                'slots_disponibles': []
            }
            
            resultado = recepcionista_node(state)
            assert resultado['estado_conversacion'] == 'solicitando_nombre'
        
        # Caso 2: Paciente existente con slots
        paciente_mock = MagicMock()
        paciente_mock.nombre_completo = "Juan Pérez"
        
        with patch('src.nodes.recepcionista_node.get_paciente_by_phone', return_value=paciente_mock):
            with patch('src.nodes.recepcionista_node.generar_slots_con_turnos', return_value=self.slots_mock):
                
                resultado = recepcionista_node(state)
                assert resultado['estado_conversacion'] == 'esperando_seleccion'
        
        print("✅ Test estado inicial transiciona correctamente: PASÓ")

    def test_respuesta_formato_correcto(self):
        """Test: Las respuestas tienen el formato correcto esperado"""
        
        paciente_mock = MagicMock()
        paciente_mock.nombre_completo = "Juan Pérez"
        
        with patch('src.nodes.recepcionista_node.get_paciente_by_phone', return_value=paciente_mock):
            with patch('src.nodes.recepcionista_node.generar_slots_con_turnos', return_value=self.slots_mock):
                
                state = {
                    'messages': [HumanMessage(content="Hola")],
                    'user_id': self.test_phone,
                    'estado_conversacion': 'inicial',
                    'slots_disponibles': []
                }
                
                resultado = recepcionista_node(state)
                respuesta = resultado['respuesta_recepcionista']
                
                # Verificar formato de opciones
                assert "A)" in respuesta
                assert "B)" in respuesta  
                assert "C)" in respuesta
                assert "jueves" in respuesta.lower() or "viernes" in respuesta.lower() or "sábado" in respuesta.lower()
                assert "08:30" in respuesta or "10:30" in respuesta or "14:30" in respuesta
                assert "¿Cuál te conviene más?" in respuesta
                
                print("✅ Test respuesta formato correcto: PASÓ")

    def test_slots_sin_mencionar_doctor(self):
        """Test: Los slots no mencionan al doctor hasta la confirmación"""
        
        paciente_mock = MagicMock()
        paciente_mock.nombre_completo = "Juan Pérez"
        
        with patch('src.nodes.recepcionista_node.get_paciente_by_phone', return_value=paciente_mock):
            with patch('src.nodes.recepcionista_node.generar_slots_con_turnos', return_value=self.slots_mock):
                
                state = {
                    'messages': [HumanMessage(content="Hola")],
                    'user_id': self.test_phone,
                    'estado_conversacion': 'inicial',
                    'slots_disponibles': []
                }
                
                resultado = recepcionista_node(state)
                respuesta = resultado['respuesta_recepcionista']
                
                # Verificar que NO menciona doctores en la lista de opciones
                assert "Santiago" not in respuesta
                assert "Joana" not in respuesta
                assert "Dr." not in respuesta
                assert "Doctor" not in respuesta
                
                # Pero sí muestra las opciones
                assert "A)" in respuesta
                assert "B)" in respuesta
                assert "C)" in respuesta
                
                print("✅ Test slots sin mencionar doctor: PASÓ")

    def test_slots_sin_disponibilidad(self):
        """Test adicional: Manejo cuando no hay slots disponibles"""
        
        paciente_mock = MagicMock()
        paciente_mock.nombre_completo = "Juan Pérez"
        
        with patch('src.nodes.recepcionista_node.get_paciente_by_phone', return_value=paciente_mock):
            with patch('src.nodes.recepcionista_node.generar_slots_con_turnos', return_value=[]):  # Sin slots
                
                state = {
                    'messages': [HumanMessage(content="Hola")],
                    'user_id': self.test_phone,
                    'estado_conversacion': 'inicial',
                    'slots_disponibles': []
                }
                
                resultado = recepcionista_node(state)
                
                # Verificaciones
                assert "no tenemos disponibilidad" in resultado['respuesta_recepcionista']
                assert "más tarde" in resultado['respuesta_recepcionista']
                assert resultado['estado_conversacion'] == 'completado'
                
                print("✅ Test sin disponibilidad: PASÓ")


def run_recepcionista_tests():
    """Ejecutar todos los tests del recepcionista"""
    print("\n🧪 === EJECUTANDO TESTS RECEPCIONISTA NODE ===\n")
    
    test_class = TestRecepcionistaNOde()
    
    tests = [
        test_class.test_paciente_existente_muestra_slots,
        test_class.test_paciente_nuevo_pide_nombre,
        test_class.test_registrar_nombre_y_mostrar_slots,
        test_class.test_seleccion_valida_agenda_cita,
        test_class.test_seleccion_invalida_repite_pregunta,
        test_class.test_estado_inicial_transiciona_correctamente,
        test_class.test_respuesta_formato_correcto,
        test_class.test_slots_sin_mencionar_doctor
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            test_class.setup_method()
            test_func()
            passed += 1
        except Exception as e:
            print(f"❌ {test_func.__name__}: FALLÓ - {str(e)}")
            failed += 1
    
    print(f"\n📊 RESULTADO: {passed}/{len(tests)} tests pasaron")
    if failed == 0:
        print("🎉 ¡Todos los tests del recepcionista pasaron!")
    else:
        print(f"⚠️  {failed} tests fallaron")
    
    return passed, failed


if __name__ == "__main__":
    run_recepcionista_tests()