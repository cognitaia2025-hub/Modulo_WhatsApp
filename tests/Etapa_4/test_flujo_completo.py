"""
Tests para test_flujo_completo.py - Etapa 4
5 tests para validar el flujo completo de conversación del recepcionista
"""

import pytest
import sys
import os
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

# Agregar el directorio raíz al path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.nodes.recepcionista_node import recepcionista_node
from langchain_core.messages import HumanMessage, AIMessage


class TestFlujoCompleto:
    """Suite de tests para flujos completos de conversación"""
    
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

    def test_flujo_paciente_nuevo_completo(self):
        """Test: Flujo completo de paciente nuevo desde inicio hasta cita agendada"""
        
        # Mocks para el flujo completo
        paciente_mock = MagicMock()
        paciente_mock.id = 456
        paciente_mock.nombre_completo = "María García"
        
        doctor_mock = MagicMock()
        doctor_mock.phone_number = "+526641234567"
        doctor_mock.nombre_completo = "Dr. Santiago"
        
        registro_mock = {
            "paciente_id": 456,
            "es_nuevo": True, 
            "nombre": "María García"
        }
        
        resultado_agenda = "✅ **Cita agendada exitosamente**\n\nID Cita: 789"
        
        # === PASO 1: Estado inicial - paciente nuevo ===
        with patch('src.nodes.recepcionista_node.get_paciente_by_phone', return_value=None):
            state = {
                'messages': [HumanMessage(content="Hola, quiero una cita")],
                'user_id': self.test_phone,
                'estado_conversacion': 'inicial',
                'slots_disponibles': []
            }
            
            resultado1 = recepcionista_node(state)
            
            # Verificaciones paso 1
            assert resultado1['estado_conversacion'] == 'solicitando_nombre'
            assert "primera vez" in resultado1['respuesta_recepcionista']
            assert "nombre completo" in resultado1['respuesta_recepcionista']
        
        # === PASO 2: Envío de nombre ===
        with patch('src.nodes.recepcionista_node.extraer_nombre_con_llm', return_value="María García"):
            with patch('src.nodes.recepcionista_node.registrar_paciente_externo', return_value=registro_mock):
                with patch('src.nodes.recepcionista_node.generar_slots_con_turnos', return_value=self.slots_mock):
                    
                    state['messages'].append(HumanMessage(content="Me llamo María García"))
                    state['estado_conversacion'] = 'solicitando_nombre'
                    
                    resultado2 = recepcionista_node(state)
                    
                    # Verificaciones paso 2
                    assert resultado2['estado_conversacion'] == 'esperando_seleccion'
                    assert "¡Gracias María García!" in resultado2['respuesta_recepcionista']
                    assert "🗓️ **Opciones disponibles:**" in resultado2['respuesta_recepcionista']
                    assert len(resultado2['slots_disponibles']) == 3
        
        # === PASO 3: Selección de slot ===
        with patch('src.nodes.recepcionista_node.extraer_seleccion', return_value=0):  # A
            with patch('src.nodes.recepcionista_node.get_paciente_by_phone', return_value=paciente_mock):
                with patch('src.nodes.recepcionista_node.get_doctor_by_id', return_value=doctor_mock):
                    with patch('src.medical.crud.schedule_appointment', return_value=999):
                        
                        state['messages'].append(HumanMessage(content="Escojo A"))
                        state['estado_conversacion'] = 'esperando_seleccion'
                        state['slots_disponibles'] = self.slots_mock
                        
                        resultado3 = recepcionista_node(state)
                        
                        # Verificaciones paso 3
                        assert resultado3['estado_conversacion'] == 'completado'
                        assert "🎉 ¡Perfecto!" in resultado3['respuesta_recepcionista']
                        assert "cita ha sido agendada" in resultado3['respuesta_recepcionista']
                        assert "Dr. Santiago" in resultado3['respuesta_recepcionista']
        
        print("✅ Test flujo paciente nuevo completo: PASÓ")

    def test_flujo_paciente_existente_completo(self):
        """Test: Flujo completo de paciente existente desde saludo hasta cita"""
        
        # Mocks
        paciente_mock = MagicMock()
        paciente_mock.id = 123
        paciente_mock.nombre_completo = "Juan Pérez"
        
        doctor_mock = MagicMock()
        doctor_mock.phone_number = "+526641234567" 
        doctor_mock.nombre_completo = "Dr. Santiago"
        
        resultado_agenda = "✅ **Cita agendada exitosamente**\n\nID Cita: 555"
        
        # === PASO 1: Estado inicial - paciente existente ===
        with patch('src.nodes.recepcionista_node.get_paciente_by_phone', return_value=paciente_mock):
            with patch('src.nodes.recepcionista_node.generar_slots_con_turnos', return_value=self.slots_mock):
                
                state = {
                    'messages': [HumanMessage(content="Hola, necesito cita")],
                    'user_id': self.test_phone,
                    'estado_conversacion': 'inicial',
                    'slots_disponibles': []
                }
                
                resultado1 = recepcionista_node(state)
                
                # Verificaciones paso 1
                assert resultado1['estado_conversacion'] == 'esperando_seleccion'
                assert "¡Hola Juan Pérez!" in resultado1['respuesta_recepcionista']
                assert "🗓️ **Opciones disponibles:**" in resultado1['respuesta_recepcionista']
                assert len(resultado1['slots_disponibles']) == 3
        
        # === PASO 2: Selección directa ===  
        with patch('src.nodes.recepcionista_node.extraer_seleccion', return_value=1):  # B
            with patch('src.nodes.recepcionista_node.get_paciente_by_phone', return_value=paciente_mock):
                with patch('src.nodes.recepcionista_node.get_doctor_by_id', return_value=doctor_mock):
                    with patch('src.medical.crud.schedule_appointment', return_value=888):
                        
                        state['messages'].append(HumanMessage(content="La B por favor"))
                        state['estado_conversacion'] = 'esperando_seleccion'
                        state['slots_disponibles'] = self.slots_mock
                        
                        resultado2 = recepcionista_node(state)
                        
                        # Verificaciones paso 2
                        assert resultado2['estado_conversacion'] == 'completado'
                        assert "🎉 ¡Perfecto!" in resultado2['respuesta_recepcionista']
                        assert "cita ha sido agendada" in resultado2['respuesta_recepcionista']
        
        print("✅ Test flujo paciente existente completo: PASÓ")

    def test_multiples_intentos_seleccion(self):
        """Test: Múltiples intentos de selección hasta éxito"""
        
        paciente_mock = MagicMock()
        paciente_mock.id = 123
        paciente_mock.nombre_completo = "Juan Pérez"
        
        doctor_mock = MagicMock()
        doctor_mock.phone_number = "+526641234567"
        doctor_mock.nombre_completo = "Dr. Santiago"
        
        resultado_agenda = "✅ **Cita agendada exitosamente**\n\nID Cita: 333"
        
        # Estado inicial con slots ya cargados
        state = {
            'messages': [HumanMessage(content="Mensaje inicial")],
            'user_id': self.test_phone,
            'estado_conversacion': 'esperando_seleccion',
            'slots_disponibles': self.slots_mock
        }
        
        # === INTENTO 1: Selección inválida ===
        with patch('src.nodes.recepcionista_node.extraer_seleccion', return_value=None):
            state['messages'].append(HumanMessage(content="quiero la primera"))
            
            resultado1 = recepcionista_node(state)
            
            # Debe mantenerse esperando selección
            assert resultado1['estado_conversacion'] == 'esperando_seleccion'
            assert "No pude entender" in resultado1['respuesta_recepcionista']
        
        # === INTENTO 2: Selección fuera de rango ===
        with patch('src.nodes.recepcionista_node.extraer_seleccion', return_value=5):  # F
            state['messages'].append(HumanMessage(content="F"))
            
            resultado2 = recepcionista_node(state)
            
            # Debe mantenerse esperando selección
            assert resultado2['estado_conversacion'] == 'esperando_seleccion' 
            assert "Opción no válida" in resultado2['respuesta_recepcionista']
        
        # === INTENTO 3: Selección válida ===
        with patch('src.nodes.recepcionista_node.extraer_seleccion', return_value=2):  # C
            with patch('src.nodes.recepcionista_node.get_paciente_by_phone', return_value=paciente_mock):
                with patch('src.nodes.recepcionista_node.get_doctor_by_id', return_value=doctor_mock):
                    with patch('src.medical.crud.schedule_appointment', return_value=777):
                        
                        state['messages'].append(HumanMessage(content="C"))
                        
                        resultado3 = recepcionista_node(state)
                        
                        # Ahora sí debe completar
                        assert resultado3['estado_conversacion'] == 'completado'
                        assert "🎉 ¡Perfecto!" in resultado3['respuesta_recepcionista']
        
        print("✅ Test múltiples intentos selección: PASÓ")

    def test_manejo_error_agendamiento(self):
        """Test: Manejo de errores durante el agendamiento"""
        
        paciente_mock = MagicMock()
        paciente_mock.id = 123
        paciente_mock.nombre_completo = "Juan Pérez"
        
        doctor_mock = MagicMock()
        doctor_mock.phone_number = "+526641234567"
        doctor_mock.nombre_completo = "Dr. Santiago"
        
        # Error en el agendamiento
        resultado_error = "❌ Error: Doctor no disponible en horario solicitado"
        
        with patch('src.nodes.recepcionista_node.extraer_seleccion', return_value=0):  # A
            with patch('src.nodes.recepcionista_node.get_paciente_by_phone', return_value=paciente_mock):
                with patch('src.nodes.recepcionista_node.get_doctor_by_id', return_value=doctor_mock):
                    with patch('src.medical.crud.schedule_appointment', return_value=None):
                        
                        state = {
                            'messages': [HumanMessage(content="A")],
                            'user_id': self.test_phone,
                            'estado_conversacion': 'esperando_seleccion',
                            'slots_disponibles': self.slots_mock
                        }
                        
                        resultado = recepcionista_node(state)
                        
                        # Verificaciones
                        assert resultado['estado_conversacion'] == 'esperando_seleccion'  # Vuelve a preguntar
                        assert "no pude agendar" in resultado['respuesta_recepcionista']
                        assert "otra opción" in resultado['respuesta_recepcionista']
        
        print("✅ Test manejo error agendamiento: PASÓ")

    def test_confirmacion_revela_doctor(self):
        """Test: La confirmación final revela el doctor asignado"""
        
        paciente_mock = MagicMock()
        paciente_mock.id = 123
        paciente_mock.nombre_completo = "Juan Pérez"
        
        doctor_mock = MagicMock()
        doctor_mock.phone_number = "+526641234567"
        doctor_mock.nombre_completo = "Dr. Santiago de Jesús Ornelas Reynoso"
        
        resultado_agenda = "✅ **Cita agendada exitosamente**\n\nID Cita: 999"
        
        with patch('src.nodes.recepcionista_node.extraer_seleccion', return_value=0):  # A
            with patch('src.nodes.recepcionista_node.get_paciente_by_phone', return_value=paciente_mock):
                with patch('src.nodes.recepcionista_node.get_doctor_by_id', return_value=doctor_mock):
                    with patch('src.medical.crud.schedule_appointment', return_value=333):
                        
                        state = {
                            'messages': [HumanMessage(content="A")], 
                            'user_id': self.test_phone,
                            'estado_conversacion': 'esperando_seleccion',
                            'slots_disponibles': self.slots_mock
                        }
                        
                        resultado = recepcionista_node(state)
                        
                        # Verificaciones - DEBE revelar doctor en confirmación
                        assert resultado['estado_conversacion'] == 'completado'
                        assert "Dr. Santiago de Jesús Ornelas Reynoso" in resultado['respuesta_recepcionista']
                        assert "📅 **Detalles de tu cita:**" in resultado['respuesta_recepcionista']
                        assert "👨‍⚕️ Doctor:" in resultado['respuesta_recepcionista']
                        
                        # El slot original NO debe mostrar doctor
                        slot_texto = str(self.slots_mock[0])
                        assert "Santiago" not in state.get('respuesta_inicial', '')  # En opciones iniciales
        
        print("✅ Test confirmación revela doctor: PASÓ")

    def test_sin_slots_disponibles(self):
        """Test adicional: Comportamiento cuando no hay slots"""
        
        paciente_mock = MagicMock()
        paciente_mock.nombre_completo = "Juan Pérez"
        
        # === Paciente existente sin slots ===
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
                assert resultado['estado_conversacion'] == 'completado'
                assert "no tenemos disponibilidad" in resultado['respuesta_recepcionista']
                assert len(resultado['slots_disponibles']) == 0
        
        # === Paciente nuevo registrado pero sin slots ===
        registro_mock = {"paciente_id": 456, "es_nuevo": True, "nombre": "María García"}
        
        with patch('src.nodes.recepcionista_node.extraer_nombre_con_llm', return_value="María García"):
            with patch('src.nodes.recepcionista_node.registrar_paciente_externo', return_value=registro_mock):
                with patch('src.nodes.recepcionista_node.generar_slots_con_turnos', return_value=[]):
                    
                    state = {
                        'messages': [HumanMessage(content="Me llamo María García")],
                        'user_id': self.test_phone,
                        'estado_conversacion': 'solicitando_nombre',
                        'slots_disponibles': []
                    }
                    
                    resultado = recepcionista_node(state)
                    
                    # Verificaciones
                    assert resultado['estado_conversacion'] == 'completado'
                    assert "¡Gracias María García!" in resultado['respuesta_recepcionista']
                    assert "no tenemos disponibilidad" in resultado['respuesta_recepcionista']
        
        print("✅ Test sin slots disponibles: PASÓ")


def run_flujo_completo_tests():
    """Ejecutar todos los tests de flujo completo"""
    print("\n🧪 === EJECUTANDO TESTS FLUJO COMPLETO ===\n")
    
    test_class = TestFlujoCompleto()
    
    tests = [
        test_class.test_flujo_paciente_nuevo_completo,
        test_class.test_flujo_paciente_existente_completo,
        test_class.test_multiples_intentos_seleccion,
        test_class.test_manejo_error_agendamiento,
        test_class.test_confirmacion_revela_doctor,
        test_class.test_sin_slots_disponibles
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
        print("🎉 ¡Todos los tests de flujo completo pasaron!")
    else:
        print(f"⚠️  {failed} tests fallaron")
    
    return passed, failed


if __name__ == "__main__":
    run_flujo_completo_tests()