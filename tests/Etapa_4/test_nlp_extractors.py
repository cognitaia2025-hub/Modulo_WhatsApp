"""
Tests para test_nlp_extractors.py - Etapa 4
7 tests para validar las funciones de extracción NLP
"""

import pytest
import sys
import os
from unittest.mock import patch, Mock

# Agregar el directorio raíz al path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.utils.nlp_extractors import extraer_nombre_con_llm, extraer_seleccion, _extraer_nombre_fallback


class TestNLPExtractors:
    """Suite de tests para los extractores NLP"""

    def test_extraer_nombre_simple(self):
        """Test: Extracción de nombres simples"""
        
        # Mock de respuesta de DeepSeek API exitosa
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {"content": "Juan Pérez"}
            }]
        }
        
        with patch('src.utils.nlp_extractors.requests.post', return_value=mock_response):
            
            casos = [
                ("Me llamo Juan Pérez", "Juan Pérez"),
                ("Mi nombre es Ana María", "Ana María"),
                ("Soy Carlos", "Carlos")
            ]
            
            for entrada, esperado in casos:
                # Configurar mock response para cada caso
                mock_response.json.return_value = {
                    "choices": [{"message": {"content": esperado}}]
                }
                
                resultado = extraer_nombre_con_llm(entrada)
                assert resultado == esperado, f"Esperaba '{esperado}', obtuvo '{resultado}'"
        
        print("✅ Test extraer nombre simple: PASÓ")

    def test_extraer_nombre_compuesto(self):
        """Test: Extracción de nombres compuestos"""
        
        mock_response = Mock()
        mock_response.status_code = 200
        
        casos = [
            ("Me llamo María José García López", "María José García López"),
            ("Soy Juan Carlos de la Cruz", "Juan Carlos de la Cruz"),
            ("Mi nombre es Ana Sofía Mendoza", "Ana Sofía Mendoza")
        ]
        
        with patch('src.utils.nlp_extractors.requests.post', return_value=mock_response):
            
            for entrada, esperado in casos:
                mock_response.json.return_value = {
                    "choices": [{"message": {"content": esperado}}]
                }
                
                resultado = extraer_nombre_con_llm(entrada)
                assert resultado == esperado, f"Esperaba '{esperado}', obtuvo '{resultado}'"
        
        print("✅ Test extraer nombre compuesto: PASÓ")

    def test_extraer_nombre_con_ruido(self):
        """Test: Extracción de nombres con ruido y fallback"""
        
        # Test 1: API falla, usa fallback
        with patch('src.utils.nlp_extractors.requests.post', side_effect=Exception("API error")):
            resultado = extraer_nombre_con_llm("Me llamo Pedro Ramírez")
            # Debe usar fallback que remueve prefijos
            assert "Pedro Ramírez" in resultado
            assert "me llamo" not in resultado.lower()
        
        # Test 2: API retorna respuesta vacía, usa fallback
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": ""}}]
        }
        
        with patch('src.utils.nlp_extractors.requests.post', return_value=mock_response):
            resultado = extraer_nombre_con_llm("Hola, soy Luis Fernando")
            assert "Luis Fernando" in resultado
            assert "soy" not in resultado.lower() or len(resultado) > 10
        
        # Test 3: API retorna error HTTP, usa fallback  
        mock_response.status_code = 500
        with patch('src.utils.nlp_extractors.requests.post', return_value=mock_response):
            resultado = extraer_nombre_con_llm("Mi nombre es Roberto")
            assert len(resultado) > 0
            assert "Roberto" in resultado
        
        print("✅ Test extraer nombre con ruido: PASÓ")

    def test_extraer_seleccion_letra_sola(self):
        """Test: Extracción de selecciones con letra sola"""
        
        casos = [
            ("A", 0),
            ("B", 1), 
            ("C", 2),
            ("D", 3),
            ("E", 4),
            ("a", 0),  # Case insensitive
            ("b", 1),
            ("c", 2)
        ]
        
        for entrada, esperado in casos:
            resultado = extraer_seleccion(entrada)
            assert resultado == esperado, f"Entrada '{entrada}': esperaba {esperado}, obtuvo {resultado}"
        
        print("✅ Test extraer selección letra sola: PASÓ")

    def test_extraer_seleccion_con_texto(self):
        """Test: Extracción de selecciones con texto adicional"""
        
        casos = [
            ("la opción A", 0),
            ("escojo B por favor", 1),
            ("quiero la C", 2),
            ("prefiero la opción D", 3),
            ("selecciono E", 4),
            ("elijo la letra A", 0),
            ("La B por favor", 1),  # Case insensitive
            ("OPCIÓN C", 2)
        ]
        
        for entrada, esperado in casos:
            resultado = extraer_seleccion(entrada)
            assert resultado == esperado, f"Entrada '{entrada}': esperaba {esperado}, obtuvo {resultado}"
        
        print("✅ Test extraer selección con texto: PASÓ")

    def test_extraer_seleccion_invalida_retorna_none(self):
        """Test: Selecciones inválidas retornan None"""
        
        casos_invalidos = [
            "quiero la primera",
            "la segunda opción", 
            "F",  # Fuera de rango A-E
            "Z",
            "123",
            "xyz",
            "",
            None,
            "si por favor",
            "ok",
            "está bien"
        ]
        
        for entrada in casos_invalidos:
            resultado = extraer_seleccion(entrada)
            assert resultado is None, f"Entrada '{entrada}': esperaba None, obtuvo {resultado}"
        
        print("✅ Test extraer selección inválida retorna None: PASÓ")

    def test_extraer_seleccion_case_insensitive(self):
        """Test: Extracción case insensitive funciona correctamente"""
        
        casos = [
            ("a", 0),
            ("B", 1),
            ("c", 2), 
            ("D", 3),
            ("e", 4),
            ("opción a", 0),
            ("ESCOJO B", 1),
            ("Quiero la C", 2),
            ("letra d", 3),
            ("SELECCIONO E", 4)
        ]
        
        for entrada, esperado in casos:
            resultado = extraer_seleccion(entrada)
            assert resultado == esperado, f"Entrada '{entrada}': esperaba {esperado}, obtuvo {resultado}"
        
        print("✅ Test extraer selección case insensitive: PASÓ")

    def test_fallback_extractor_nombre(self):
        """Test: Función fallback de extracción de nombre"""
        
        casos = [
            ("Me llamo Juan Pérez", "Juan Pérez"),
            ("Soy María García", "María García"), 
            ("Mi nombre es Carlos", "Carlos"),
            ("Hola, me llamo Ana", "Ana"),
            ("yo soy Pedro", "Pedro"),
            ("Juan", "Juan"),  # Sin prefijos
            ("", ""),  # Mensaje vacío
            ("   me llamo   José   ", "José")  # Con espacios extra
        ]
        
        for entrada, esperado_contiene in casos:
            resultado = _extraer_nombre_fallback(entrada)
            
            if esperado_contiene:
                assert esperado_contiene in resultado, f"Esperaba que '{resultado}' contenga '{esperado_contiene}'"
                # Verificar que no contiene prefijos
                assert "me llamo" not in resultado.lower()
                assert "soy" not in resultado.lower() or len(resultado.split()) > 1
                assert "mi nombre es" not in resultado.lower()
            else:
                assert len(resultado.strip()) == 0
        
        print("✅ Test fallback extractor nombre: PASÓ")

    def test_integracion_extractor_completo(self):
        """Test de integración: Flujo completo de extracción"""
        
        # Test con API funcionando
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Ana María Rodríguez"}}]
        }
        
        with patch('src.utils.nlp_extractors.requests.post', return_value=mock_response):
            resultado = extraer_nombre_con_llm("Hola, me llamo Ana María Rodríguez y quiero una cita")
            assert "Ana María Rodríguez" == resultado
        
        # Test con API fallando (debe usar fallback)
        with patch('src.utils.nlp_extractors.requests.post', side_effect=Exception("Network error")):
            resultado = extraer_nombre_con_llm("Me llamo José Luis")
            assert "José Luis" in resultado
            assert "me llamo" not in resultado.lower()
        
        print("✅ Test integración extractor completo: PASÓ")


def run_nlp_extractor_tests():
    """Ejecutar todos los tests de extractores NLP"""
    print("\n🧪 === EJECUTANDO TESTS NLP EXTRACTORS ===\n")
    
    test_class = TestNLPExtractors()
    
    tests = [
        test_class.test_extraer_nombre_simple,
        test_class.test_extraer_nombre_compuesto,
        test_class.test_extraer_nombre_con_ruido,
        test_class.test_extraer_seleccion_letra_sola,
        test_class.test_extraer_seleccion_con_texto,
        test_class.test_extraer_seleccion_invalida_retorna_none,
        test_class.test_extraer_seleccion_case_insensitive,
        test_class.test_fallback_extractor_nombre,
        test_class.test_integracion_extractor_completo
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"❌ {test_func.__name__}: FALLÓ - {str(e)}")
            failed += 1
    
    print(f"\n📊 RESULTADO: {passed}/{len(tests)} tests pasaron")
    if failed == 0:
        print("🎉 ¡Todos los tests de extractores NLP pasaron!")
    else:
        print(f"⚠️  {failed} tests fallaron")
    
    return passed, failed


if __name__ == "__main__":
    run_nlp_extractor_tests()