# Test básicos para herramientas médicas
# Estos tests validan que las 6 herramientas médicas básicas funcionan correctamente

import pytest
import sys
import os
from datetime import datetime, date, timedelta

# Agregar el directorio raíz al path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.medical.tools import (
    crear_paciente_medico,
    buscar_pacientes_doctor,
    consultar_slots_disponibles,
    agendar_cita_medica_completa,
    modificar_cita_medica,
    cancelar_cita_medica
)
from src.medical.crud import get_doctor_by_phone, create_doctor

class TestMedicalTools:
    """Suite de tests para herramientas médicas básicas"""
    
    @classmethod
    def setup_class(cls):
        """Setup inicial para todos los tests"""
        # Datos de test
        cls.test_doctor_phone = "+524428887777"
        cls.test_patient_data = {
            "nombre_completo": "Juan Pérez González",
            "telefono": "+524429998888",
            "email": "juan.perez@test.com",
            "fecha_nacimiento": "1985-05-15",
            "genero": "masculino",
            "direccion": "Calle Test 123, Ciudad Test",
            "seguro_medico": "IMSS",
            "alergias": "Polen, polvo"
        }
        
    def test_1_crear_doctor_test(self):
        """Test auxiliar: crear doctor para pruebas"""
        try:
            doctor_data = {
                "phone_number": self.test_doctor_phone,
                "especialidad": "Medicina General",
                "num_licencia": "TEST123456",
                "años_experiencia": 5
            }
            doctor = create_doctor(doctor_data)
            assert doctor is not None
            assert doctor.phone_number == self.test_doctor_phone
            print(f"✅ Doctor de test creado: {doctor.phone_number}")
        except Exception as e:
            # Si ya existe, está bien
            doctor = get_doctor_by_phone(self.test_doctor_phone)
            if doctor:
                print(f"✅ Doctor de test ya existe: {doctor.phone_number}")
            else:
                pytest.fail(f"Error creando doctor de test: {e}")
    
    def test_2_crear_paciente_medico(self):
        """Test: Crear un paciente nuevo"""
        resultado = crear_paciente_medico.invoke({
            "doctor_phone": self.test_doctor_phone,
            **self.test_patient_data
        })
        
        assert "✅" in resultado
        assert "registrado exitosamente" in resultado
        assert self.test_patient_data["nombre_completo"] in resultado
        assert self.test_patient_data["telefono"] in resultado
        print(f"✅ Test crear paciente: {resultado[:100]}...")
    
    def test_3_buscar_pacientes_doctor(self):
        """Test: Buscar pacientes por diferentes criterios"""
        # Buscar por nombre
        resultado_nombre = buscar_pacientes_doctor.invoke({
            "doctor_phone": self.test_doctor_phone,
            "busqueda": "Juan"
        })
        
        assert "Pacientes encontrados" in resultado_nombre
        assert self.test_patient_data["nombre_completo"] in resultado_nombre
        
        # Buscar por teléfono
        resultado_telefono = buscar_pacientes_doctor.invoke({
            "doctor_phone": self.test_doctor_phone,
            "busqueda": self.test_patient_data["telefono"]
        })
        
        assert "Pacientes encontrados" in resultado_telefono
        print(f"✅ Test buscar pacientes: encontrados por nombre y teléfono")
    
    def test_4_consultar_slots_disponibles(self):
        """Test: Consultar horarios disponibles"""
        # Fecha de mañana
        mañana = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        resultado = consultar_slots_disponibles.invoke({
            "doctor_phone": self.test_doctor_phone,
            "fecha": mañana,
            "duracion_minutos": 30
        })
        
        # Puede no tener horarios disponibles, pero no debe tener errores
        assert "❌ Error" not in resultado
        print(f"✅ Test consultar slots: {resultado[:100]}...")
    
    def test_5_agendar_cita_con_validaciones(self):
        """Test: Validaciones al agendar cita"""
        # Intentar agendar con fecha pasada (debe fallar)
        ayer = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M")
        
        resultado_error = agendar_cita_medica_completa.invoke({
            "doctor_phone": self.test_doctor_phone,
            "paciente_id": 1,  # ID de test
            "fecha_hora": ayer,
            "tipo_consulta": "seguimiento"
        })
        
        assert "❌ Error" in resultado_error
        assert "fechas y horas pasadas" in resultado_error
        print(f"✅ Test validación fecha pasada: funciona correctamente")
    
    def test_6_modificar_cita_validaciones(self):
        """Test: Validaciones al modificar cita"""
        resultado = modificar_cita_medica.invoke({
            "doctor_phone": self.test_doctor_phone,
            "cita_id": 99999,  # ID inexistente
            "nuevo_estado": "confirmada"
        })
        
        assert "❌ Error" in resultado
        print(f"✅ Test modificar cita inexistente: validación funciona")
    
    def test_7_cancelar_cita_validaciones(self):
        """Test: Validaciones al cancelar cita"""
        resultado = cancelar_cita_medica.invoke({
            "doctor_phone": self.test_doctor_phone,
            "cita_id": 99999,  # ID inexistente
            "motivo_cancelacion": "Paciente no disponible"
        })
        
        assert "❌ Error" in resultado
        print(f"✅ Test cancelar cita inexistente: validación funciona")
    
    def test_8_doctor_inexistente(self):
        """Test: Validación con doctor inexistente"""
        doctor_falso = "+524411111111"
        
        resultado = crear_paciente_medico.invoke({
            "doctor_phone": doctor_falso,
            **self.test_patient_data
        })
        
        assert "❌ Error" in resultado
        assert "no está registrado" in resultado
        print(f"✅ Test doctor inexistente: validación funciona")
    
    def test_9_datos_invalidos(self):
        """Test: Validaciones de datos inválidos"""
        # Teléfono muy corto
        resultado = crear_paciente_medico.invoke({
            "doctor_phone": self.test_doctor_phone,
            "nombre_completo": "Test Usuario",
            "telefono": "123"  # Muy corto
        })
        
        assert "❌ Error" in resultado
        assert "al menos 10 dígitos" in resultado
        print(f"✅ Test datos inválidos: validación funciona")
    
    def test_10_formato_fecha_invalido(self):
        """Test: Validación de formato de fecha"""
        resultado = consultar_slots_disponibles.invoke({
            "doctor_phone": self.test_doctor_phone,
            "fecha": "2024-13-45",  # Fecha inválida
            "duracion_minutos": 30
        })
        
        assert "❌ Error" in resultado
        assert "formato YYYY-MM-DD" in resultado
        print(f"✅ Test formato fecha inválido: validación funciona")

def run_basic_tests():
    """Función para ejecutar tests básicos manualmente"""
    print("\n🧪 Ejecutando tests básicos de herramientas médicas...\n")
    
    test_class = TestMedicalTools()
    test_class.setup_class()
    
    tests = [
        test_class.test_1_crear_doctor_test,
        test_class.test_2_crear_paciente_medico,
        test_class.test_3_buscar_pacientes_doctor,
        test_class.test_4_consultar_slots_disponibles,
        test_class.test_5_agendar_cita_con_validaciones,
        test_class.test_6_modificar_cita_validaciones,
        test_class.test_7_cancelar_cita_validaciones,
        test_class.test_8_doctor_inexistente,
        test_class.test_9_datos_invalidos,
        test_class.test_10_formato_fecha_invalido
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ {test.__name__}: {e}")
            failed += 1
    
    print(f"\n📊 Resultados: {passed} ✅ | {failed} ❌")
    print(f"Total tests ejecutados: {len(tests)}")
    
    if failed == 0:
        print("🎉 ¡Todos los tests pasaron!")
    else:
        print("⚠️ Algunos tests fallaron, revisar configuración")

if __name__ == "__main__":
    run_basic_tests()