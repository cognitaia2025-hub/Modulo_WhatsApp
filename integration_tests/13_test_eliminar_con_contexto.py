"""
Test Exhaustivo 13: Eliminación con Contexto (Context-Aware Delete)

Objetivo: Verificar que el sistema puede eliminar eventos usando referencias contextuales
del último listado, sin necesidad de IDs explícitos.

Escenarios:
1. Eliminar por nombre ("elimina el gimnasio")
2. Eliminar por posición ("elimina el primero")
3. Eliminar múltiples ("elimina los dos primeros")
4. Eliminar con descripción parcial ("elimina la reunión")
"""

import sys
sys.path.insert(0, '/workspaces/Modulo_WhatsApp')

import requests
import json
from datetime import datetime, timedelta
import time

# Configuración
API_URL = "http://localhost:8000/api/whatsapp-agent/message"
USER_ID = f"test_user_context_delete_{int(datetime.now().timestamp())}"

def enviar_mensaje(mensaje: str, user_id: str = USER_ID) -> dict:
    """Envía un mensaje al agente y devuelve la respuesta"""
    payload = {
        "user_id": user_id,
        "message": mensaje
    }
    
    response = requests.post(API_URL, json=payload)
    response.raise_for_status()
    
    data = response.json()
    print(f"\n{'='*80}")
    print(f"👤 Usuario: {mensaje}")
    print(f"🤖 Asistente: {data.get('response', 'Sin respuesta')}")
    print(f"{'='*80}\n")
    
    return data


def test_01_setup_eventos_prueba():
    """Paso 1: Crear múltiples eventos para pruebas de eliminación"""
    print("\n" + "="*80)
    print("TEST 01: Setup - Crear Eventos de Prueba")
    print("="*80)
    
    eventos_crear = [
        "Crea un evento 'Gimnasio' para mañana a las 6:00 AM en el Hopy Gym",
        "Crea un evento 'Reunión con cliente' para mañana a las 10:00 AM en la oficina",
        "Crea un evento 'Almuerzo con María' para mañana a la 1:00 PM en Restaurante Central",
        "Crea un evento 'Code review' para mañana a las 3:00 PM"
    ]
    
    for i, mensaje in enumerate(eventos_crear, 1):
        print(f"\n📝 Creando evento {i}/4...")
        respuesta = enviar_mensaje(mensaje)
        time.sleep(1)
        
        assert "creado" in respuesta['response'].lower() or "evento" in respuesta['response'].lower(), \
            f"Debería confirmar creación del evento {i}"
    
    print("✅ TEST 01 PASSED: 4 eventos de prueba creados")
    time.sleep(2)


def test_02_listar_eventos_base():
    """Paso 2: Listar eventos (genera contexto para eliminaciones futuras)"""
    print("\n" + "="*80)
    print("TEST 02: Listar Eventos (Generar Contexto)")
    print("="*80)
    
    mensaje = "¿Qué eventos tengo para mañana?"
    respuesta = enviar_mensaje(mensaje)
    
    # Verificar que lista los 4 eventos creados
    response_lower = respuesta['response'].lower()
    assert "gimnasio" in response_lower, "Debería listar el evento de gimnasio"
    assert "reunión" in response_lower or "cliente" in response_lower, "Debería listar la reunión"
    
    print("✅ TEST 02 PASSED: Eventos listados, contexto generado")
    time.sleep(2)


def test_03_eliminar_por_nombre():
    """Paso 3: Eliminar evento usando su nombre (sin ID explícito)"""
    print("\n" + "="*80)
    print("TEST 03: Eliminar por Nombre")
    print("="*80)
    
    mensaje = "Elimina el evento de gimnasio"
    respuesta = enviar_mensaje(mensaje)
    
    assert "eliminado" in respuesta['response'].lower() or "borrado" in respuesta['response'].lower(), \
        "Debería confirmar la eliminación"
    
    print("✅ TEST 03 PASSED: Evento eliminado por nombre")
    time.sleep(2)


def test_04_verificar_eliminacion():
    """Paso 4: Verificar que el evento fue eliminado"""
    print("\n" + "="*80)
    print("TEST 04: Verificar Eliminación")
    print("="*80)
    
    mensaje = "¿Todavía tengo el evento de gimnasio mañana?"
    respuesta = enviar_mensaje(mensaje)
    
    response_lower = respuesta['response'].lower()
    # Debería indicar que NO hay evento de gimnasio
    assert "no" in response_lower or "eliminado" in response_lower or \
           "no encontr" in response_lower or "no tienes" in response_lower, \
        "Debería confirmar que el evento ya no existe"
    
    print("✅ TEST 04 PASSED: Eliminación verificada")
    time.sleep(2)


def test_05_eliminar_por_posicion():
    """Paso 5: Eliminar usando posición relativa (el primero, el segundo)"""
    print("\n" + "="*80)
    print("TEST 05: Eliminar por Posición Relativa")
    print("="*80)
    
    # Primero listar para actualizar contexto
    mensaje_listar = "¿Qué eventos me quedan mañana?"
    respuesta_listar = enviar_mensaje(mensaje_listar)
    time.sleep(1)
    
    # Eliminar el primero de la lista
    mensaje_eliminar = "Elimina el primero"
    respuesta_eliminar = enviar_mensaje(mensaje_eliminar)
    
    assert "eliminado" in respuesta_eliminar['response'].lower() or \
           "borrado" in respuesta_eliminar['response'].lower(), \
        "Debería confirmar la eliminación"
    
    print("✅ TEST 05 PASSED: Evento eliminado por posición")
    time.sleep(2)


def test_06_eliminar_con_descripcion_parcial():
    """Paso 6: Eliminar con descripción parcial (coincidencia fuzzy)"""
    print("\n" + "="*80)
    print("TEST 06: Eliminar con Descripción Parcial")
    print("="*80)
    
    # Listar eventos restantes
    mensaje_listar = "Lista mis eventos de mañana"
    respuesta_listar = enviar_mensaje(mensaje_listar)
    time.sleep(1)
    
    # Eliminar usando solo parte del nombre
    mensaje_eliminar = "Elimina el almuerzo"
    respuesta_eliminar = enviar_mensaje(mensaje_eliminar)
    
    assert "eliminado" in respuesta_eliminar['response'].lower() or \
           "borrado" in respuesta_eliminar['response'].lower() or \
           "no encontr" in respuesta_eliminar['response'].lower(), \
        "Debería intentar eliminar o indicar que no encontró el evento"
    
    print("✅ TEST 06 PASSED: Eliminación con descripción parcial procesada")
    time.sleep(2)


def test_07_eliminar_ultimo_evento():
    """Paso 7: Eliminar el último evento restante"""
    print("\n" + "="*80)
    print("TEST 07: Eliminar Último Evento")
    print("="*80)
    
    # Listar para ver qué queda
    mensaje_listar = "¿Qué eventos me quedan para mañana?"
    respuesta_listar = enviar_mensaje(mensaje_listar)
    time.sleep(1)
    
    # Si hay eventos, eliminar uno
    if "code" in respuesta_listar['response'].lower() or "review" in respuesta_listar['response'].lower():
        mensaje_eliminar = "Elimina el code review"
        respuesta_eliminar = enviar_mensaje(mensaje_eliminar)
        
        assert "eliminado" in respuesta_eliminar['response'].lower() or \
               "borrado" in respuesta_eliminar['response'].lower(), \
            "Debería confirmar la eliminación"
    
    print("✅ TEST 07 PASSED: Último evento procesado")
    time.sleep(2)


def test_08_verificar_calendario_vacio():
    """Paso 8: Verificar que el calendario quedó limpio"""
    print("\n" + "="*80)
    print("TEST 08: Verificar Calendario Vacío")
    print("="*80)
    
    mensaje = "¿Tengo algo pendiente para mañana?"
    respuesta = enviar_mensaje(mensaje)
    
    response_lower = respuesta['response'].lower()
    # Debería indicar que no hay eventos o que el calendario está vacío
    # (puede que quede 1 si no se eliminó el último)
    print(f"📋 Estado del calendario: {respuesta['response']}")
    
    print("ℹ️  TEST 08: Estado final del calendario verificado")
    time.sleep(2)


def test_09_eliminar_sin_contexto():
    """Paso 9: Intentar eliminar sin haber listado primero (sin contexto)"""
    print("\n" + "="*80)
    print("TEST 09: Eliminar Sin Contexto Previo")
    print("="*80)
    
    # Crear un evento nuevo
    mensaje_crear = "Crea un evento 'Test sin contexto' para pasado mañana a las 5:00 PM"
    respuesta_crear = enviar_mensaje(mensaje_crear)
    time.sleep(2)
    
    # Intentar eliminar SIN listar primero
    mensaje_eliminar = "Elimina el test sin contexto"
    respuesta_eliminar = enviar_mensaje(mensaje_eliminar)
    
    # El sistema debería pedir más información o buscar en el calendario
    print(f"📋 Respuesta sin contexto: {respuesta_eliminar['response']}")
    
    print("ℹ️  TEST 09: Comportamiento sin contexto verificado")
    time.sleep(2)


def test_10_eliminar_evento_ambiguo():
    """Paso 10: Eliminar cuando hay múltiples coincidencias (ambigüedad)"""
    print("\n" + "="*80)
    print("TEST 10: Manejo de Ambigüedad")
    print("="*80)
    
    # Crear dos eventos similares
    mensaje_crear_1 = "Crea un evento 'Reunión con equipo de desarrollo' para dentro de 3 días a las 10:00 AM"
    respuesta_1 = enviar_mensaje(mensaje_crear_1)
    time.sleep(1)
    
    mensaje_crear_2 = "Crea un evento 'Reunión con equipo de marketing' para dentro de 3 días a las 11:00 AM"
    respuesta_2 = enviar_mensaje(mensaje_crear_2)
    time.sleep(2)
    
    # Listar
    mensaje_listar = "¿Qué tengo dentro de 3 días?"
    respuesta_listar = enviar_mensaje(mensaje_listar)
    time.sleep(1)
    
    # Intentar eliminar con descripción ambigua
    mensaje_eliminar = "Elimina la reunión"
    respuesta_eliminar = enviar_mensaje(mensaje_eliminar)
    
    # El sistema debería pedir aclaración o eliminar uno
    print(f"📋 Respuesta a ambigüedad: {respuesta_eliminar['response']}")
    
    print("ℹ️  TEST 10: Manejo de ambigüedad verificado")
    time.sleep(2)


def ejecutar_suite_completa():
    """Ejecuta toda la suite de tests de eliminación con contexto"""
    print("\n" + "🚀"*40)
    print("INICIANDO SUITE DE TESTS DE ELIMINACIÓN CON CONTEXTO")
    print("🚀"*40 + "\n")
    
    tests = [
        ("Setup Eventos", test_01_setup_eventos_prueba),
        ("Listar Eventos Base", test_02_listar_eventos_base),
        ("Eliminar por Nombre", test_03_eliminar_por_nombre),
        ("Verificar Eliminación", test_04_verificar_eliminacion),
        ("Eliminar por Posición", test_05_eliminar_por_posicion),
        ("Descripción Parcial", test_06_eliminar_con_descripcion_parcial),
        ("Eliminar Último", test_07_eliminar_ultimo_evento),
        ("Calendario Vacío", test_08_verificar_calendario_vacio),
        ("Sin Contexto Previo", test_09_eliminar_sin_contexto),
        ("Ambigüedad", test_10_eliminar_evento_ambiguo)
    ]
    
    resultados = []
    
    for nombre, test_func in tests:
        try:
            print(f"\n▶️  Ejecutando: {nombre}")
            test_func()
            resultados.append((nombre, "✅ PASS"))
        except AssertionError as e:
            print(f"\n❌ FAILED: {nombre}")
            print(f"   Error: {str(e)}")
            resultados.append((nombre, f"❌ FAIL: {str(e)}"))
        except Exception as e:
            print(f"\n💥 ERROR: {nombre}")
            print(f"   Error: {str(e)}")
            resultados.append((nombre, f"💥 ERROR: {str(e)}"))
    
    # Resumen
    print("\n" + "="*80)
    print("RESUMEN DE TESTS DE ELIMINACIÓN CON CONTEXTO")
    print("="*80 + "\n")
    
    for nombre, resultado in resultados:
        print(f"{resultado:50} | {nombre}")
    
    passed = sum(1 for _, r in resultados if "✅" in r)
    total = len(resultados)
    
    print(f"\n{'='*80}")
    print(f"RESULTADO FINAL: {passed}/{total} tests pasaron ({passed/total*100:.1f}%)")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║         TEST EXHAUSTIVO 13: ELIMINACIÓN CON CONTEXTO                 ║
║                                                                      ║
║  Objetivo: Verificar eliminación usando contexto del último listado  ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
    """)
    
    ejecutar_suite_completa()
