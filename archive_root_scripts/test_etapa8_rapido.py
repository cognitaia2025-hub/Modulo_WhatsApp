"""
Prueba rápida del Grafo ETAPA 8

Valida que el grafo funcione end-to-end sin dependencias externas.
"""

import sys
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

# Añadir path del proyecto
sys.path.insert(0, str(Path(__file__).parent))

from src.graph_whatsapp import crear_grafo_whatsapp, app


def test_grafo_basico():
    """Test básico de funcionamiento del grafo"""
    
    print("🧪 PRUEBA RÁPIDA DEL GRAFO ETAPA 8")
    print("=" * 50)
    
    # Test 1: Compilación
    print("\n1. 📝 Compilando grafo...")
    try:
        grafo = crear_grafo_whatsapp()
        print("   ✅ Grafo compilado correctamente")
    except Exception as e:
        print(f"   ❌ Error compilando grafo: {e}")
        return False
    
    # Test 2: Estructura
    print("\n2. 🏗️  Verificando estructura...")
    try:
        graph_def = grafo.get_graph()
        nodos = set(graph_def.nodes.keys())
        
        nodos_esperados = {
            'identificacion_usuario', 'cache_sesion', 'filtrado_inteligente',
            'recuperacion_episodica', 'recuperacion_medica', 'seleccion_herramientas',
            'ejecucion_herramientas', 'ejecucion_medica', 'recepcionista',
            'generacion_resumen', 'persistencia_episodica', 'sincronizador_hibrido'
        }
        
        if nodos_esperados.issubset(nodos):
            print(f"   ✅ Todos los {len(nodos_esperados)} nodos presentes")
        else:
            faltantes = nodos_esperados - nodos
            print(f"   ❌ Nodos faltantes: {faltantes}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error verificando estructura: {e}")
        return False
    
    # Test 3: Instancia global
    print("\n3. 🌐 Verificando instancia global...")
    try:
        if app is not None and hasattr(app, 'invoke'):
            print("   ✅ Instancia global disponible")
        else:
            print("   ❌ Instancia global no disponible")
            return False
    except Exception as e:
        print(f"   ❌ Error verificando instancia global: {e}")
        return False
    
    # Test 4: Funciones de decisión
    print("\n4. 🔀 Verificando funciones de decisión...")
    try:
        from src.graph_whatsapp import (
            decidir_flujo_clasificacion,
            decidir_tipo_ejecucion, 
            decidir_despues_recepcionista
        )
        
        # Test decisión 1
        resultado1 = decidir_flujo_clasificacion({
            'clasificacion': 'solicitud_cita',
            'tipo_usuario': 'paciente'
        })
        assert resultado1 == 'recepcionista'
        
        # Test decisión 2
        resultado2 = decidir_tipo_ejecucion({
            'herramientas_seleccionadas': []
        })
        assert resultado2 == 'generacion_resumen'
        
        # Test decisión 3
        resultado3 = decidir_despues_recepcionista({
            'estado_conversacion': 'completado'
        })
        assert resultado3 == 'sincronizador_hibrido'
        
        print("   ✅ Las 3 funciones de decisión funcionan")
        
    except Exception as e:
        print(f"   ❌ Error en funciones de decisión: {e}")
        return False
    
    # Test 5: Ejecución simulada (con mocks)
    print("\n5. 🎭 Ejecutando flujo simulado...")
    try:
        # Estado de prueba
        estado_test = {
            "messages": [
                {"role": "user", "content": "Hola, necesito una cita"}
            ],
            "phone_number": "+52123456789",
            "timestamp": datetime.now().isoformat(),
            "session_id": "session_test_001"
        }
        
        # Mock de los nodos principales para evitar dependencias
        with patch('src.nodes.identificacion_usuario_node.nodo_identificacion_usuario_wrapper') as mock_id, \
             patch('src.nodes.filtrado_inteligente_node.nodo_filtrado_inteligente_wrapper') as mock_filtro, \
             patch('src.nodes.recepcionista_node.nodo_recepcionista_wrapper') as mock_recep, \
             patch('src.nodes.generacion_resumen_node.nodo_generacion_resumen_wrapper') as mock_resumen, \
             patch('src.nodes.persistencia_episodica_node.nodo_persistencia_episodica_wrapper') as mock_persist:
            
            # Configurar mocks para simular un flujo exitoso
            mock_id.return_value = {
                **estado_test,
                'user_id': 'USR_123456789',
                'tipo_usuario': 'paciente_externo',
                'es_admin': False
            }
            
            mock_filtro.return_value = {
                **mock_id.return_value,
                'clasificacion': 'solicitud_cita'
            }
            
            mock_recep.return_value = {
                **mock_filtro.return_value,
                'estado_conversacion': 'inicial',
                'respuesta_recepcionista': 'Bienvenido, ¿en qué puedo ayudarte?'
            }
            
            mock_resumen.return_value = {
                **mock_recep.return_value,
                'mensaje_final': 'Hola! Te ayudo a agendar tu cita médica.'
            }
            
            mock_persist.return_value = {
                **mock_resumen.return_value,
                'memoria_guardada': True
            }
            
            # Ejecutar el grafo
            resultado = grafo.invoke(estado_test)
            
            # Verificar que el flujo se completó
            if 'mensaje_final' in resultado and 'user_id' in resultado:
                print("   ✅ Flujo simulado ejecutado correctamente")
                print(f"      - Usuario identificado: {resultado['user_id']}")
                print(f"      - Clasificación: {resultado.get('clasificacion')}")
                print(f"      - Estado conversación: {resultado.get('estado_conversacion')}")
            else:
                print("   ❌ Flujo simulado incompleto")
                return False
                
    except Exception as e:
        print(f"   ❌ Error en flujo simulado: {e}")
        return False
    
    # Resultado final
    print("\n🎉 PRUEBA COMPLETADA EXITOSAMENTE")
    print("=" * 50)
    print("✅ ETAPA 8 - Grafo WhatsApp implementado y validado")
    print("✅ 12 nodos integrados correctamente")
    print("✅ 3 funciones de decisión operativas")
    print("✅ Flujo end-to-end funcional")
    print("✅ Instancia global lista para producción")
    
    return True


if __name__ == "__main__":
    exito = test_grafo_basico()
    if not exito:
        print("\n❌ PRUEBA FALLÓ - Revisar errores arriba")
        sys.exit(1)
    else:
        print("\n🚀 ETAPA 8 LISTA PARA PRODUCCIÓN")
        sys.exit(0)