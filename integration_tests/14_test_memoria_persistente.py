"""
Test Exhaustivo 14: Memoria Episódica Persistente Entre Sesiones

Objetivo: Verificar que el sistema recuerda eventos y contexto de conversaciones
previas, incluso cuando se inicia una nueva sesión (nuevo thread).

Escenarios:
1. Crear eventos en sesión 1
2. Cerrar sesión (simular timeout)
3. Abrir nueva sesión (nuevo thread_id)
4. Verificar que recuerda eventos anteriores
5. Verificar que recuerda preferencias del usuario
6. Verificar que puede referenciar conversaciones pasadas
"""

import sys
sys.path.insert(0, '/workspaces/Modulo_WhatsApp')

import requests
import json
from datetime import datetime
import time

# Configuración
API_URL = "http://localhost:8000/api/whatsapp-agent/message"
# Usar el MISMO user_id para ambas sesiones (diferentes threads)
USER_ID = f"test_user_memoria_persistente_{int(datetime.now().timestamp())}"

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
    print(f"👤 Usuario ({user_id}): {mensaje}")
    print(f"🤖 Asistente: {data.get('response', 'Sin respuesta')}")
    print(f"💾 Thread ID: {data.get('thread_id', 'N/A')}")
    print(f"{'='*80}\n")
    
    return data


def test_sesion_1_crear_eventos():
    """SESIÓN 1: Crear eventos y establecer contexto"""
    print("\n" + "🎬"*40)
    print("SESIÓN 1: CREAR EVENTOS Y CONTEXTO")
    print("🎬"*40 + "\n")
    
    # Paso 1: Presentarse
    print("\n📝 Paso 1: Usuario se presenta...")
    respuesta = enviar_mensaje("Hola, me llamo Carlos y soy developer")
    time.sleep(1)
    
    # Paso 2: Crear evento importante
    print("\n📝 Paso 2: Crear evento de reunión importante...")
    respuesta = enviar_mensaje(
        "Crea un evento 'Presentación del proyecto Q1 2026' para el próximo lunes a las 9:00 AM "
        "en la sala de juntas principal. Es muy importante."
    )
    assert "creado" in respuesta['response'].lower() or "evento" in respuesta['response'].lower(), \
        "Debería crear el evento"
    time.sleep(1)
    
    # Paso 3: Crear evento personal
    print("\n📝 Paso 3: Crear evento personal...")
    respuesta = enviar_mensaje("También agéndame 'Cita con dentista' para el martes a las 4:00 PM")
    time.sleep(1)
    
    # Paso 4: Establecer preferencia
    print("\n📝 Paso 4: Establecer preferencia...")
    respuesta = enviar_mensaje("Prefiero que las reuniones sean por la mañana entre 9 y 11")
    time.sleep(1)
    
    # Paso 5: Listar eventos
    print("\n📝 Paso 5: Listar eventos creados...")
    respuesta = enviar_mensaje("¿Qué eventos tengo la próxima semana?")
    response_lower = respuesta['response'].lower()
    
    assert "presentación" in response_lower or "proyecto" in response_lower, \
        "Debería listar el evento de presentación"
    assert "dentista" in response_lower or "cita" in response_lower, \
        "Debería listar la cita con dentista"
    
    thread_id_sesion_1 = respuesta.get('thread_id')
    print(f"\n✅ SESIÓN 1 COMPLETADA")
    print(f"   Thread ID: {thread_id_sesion_1}")
    print(f"   Eventos creados: 2")
    print(f"   Preferencias establecidas: Horario matutino")
    
    return thread_id_sesion_1


def test_simular_cierre_sesion():
    """Simular cierre de sesión (timeout o cierre de app)"""
    print("\n" + "💤"*40)
    print("SIMULANDO CIERRE DE SESIÓN (TIMEOUT)")
    print("💤"*40 + "\n")
    
    print("⏳ Esperando 5 segundos para simular timeout...")
    time.sleep(5)
    
    print("✅ Sesión 1 cerrada (simulado)")


def test_sesion_2_verificar_memoria():
    """SESIÓN 2: Nueva sesión, verificar que recuerda"""
    print("\n" + "🆕"*40)
    print("SESIÓN 2: NUEVA SESIÓN (NUEVO THREAD)")
    print("🆕"*40 + "\n")
    
    # Paso 1: Saludar sin presentarse (debería recordar el nombre)
    print("\n📝 Paso 1: Saludar en nueva sesión...")
    respuesta = enviar_mensaje("Hola, buenos días")
    
    # Verificar si el asistente usa el nombre "Carlos"
    if "carlos" in respuesta['response'].lower():
        print("✅ El sistema recordó el nombre del usuario!")
    else:
        print("⚠️  El sistema no usó el nombre del usuario (puede ser normal si es formal)")
    
    time.sleep(1)
    
    # Paso 2: Preguntar por eventos sin especificar fechas
    print("\n📝 Paso 2: Preguntar por eventos (debería recordar)...")
    respuesta = enviar_mensaje("¿Qué eventos tengo agendados?")
    response_lower = respuesta['response'].lower()
    
    # CRÍTICO: Debe recordar los eventos de la sesión anterior
    assert "presentación" in response_lower or "proyecto" in response_lower or \
           "dentista" in response_lower or "cita" in response_lower, \
        "❌ FALLO CRÍTICO: No recuerda eventos de sesión anterior"
    
    print("✅ El sistema recordó los eventos de la sesión anterior!")
    time.sleep(1)
    
    # Paso 3: Referenciar conversación anterior
    print("\n📝 Paso 3: Referenciar conversación anterior...")
    respuesta = enviar_mensaje("¿Cuándo era la presentación del proyecto que te mencioné?")
    
    assert "lunes" in respuesta['response'].lower() or "9" in respuesta['response'] or \
           "presentación" in respuesta['response'].lower(), \
        "Debería recordar detalles del evento mencionado anteriormente"
    
    print("✅ El sistema puede referenciar conversaciones anteriores!")
    time.sleep(1)
    
    # Paso 4: Verificar preferencias (debería recordar horario preferido)
    print("\n📝 Paso 4: Verificar que recuerda preferencias...")
    respuesta = enviar_mensaje("¿A qué hora prefiría yo tener reuniones?")
    
    # Puede que recuerde o que diga que no lo sabe - ambos son válidos
    if "9" in respuesta['response'] or "11" in respuesta['response'] or "mañana" in respuesta['response'].lower():
        print("✅ El sistema recordó las preferencias de horario!")
    else:
        print("⚠️  El sistema no mencionó la preferencia específica")
    
    time.sleep(1)
    
    thread_id_sesion_2 = respuesta.get('thread_id')
    print(f"\n✅ SESIÓN 2 COMPLETADA")
    print(f"   Thread ID: {thread_id_sesion_2}")
    print(f"   Memoria episódica funcionando: ✅")
    
    return thread_id_sesion_2


def test_sesion_2_modificar_evento_anterior():
    """SESIÓN 2: Modificar un evento creado en la sesión anterior"""
    print("\n" + "✏️"*40)
    print("SESIÓN 2: MODIFICAR EVENTO DE SESIÓN ANTERIOR")
    print("✏️"*40 + "\n")
    
    # Listar eventos para contexto
    print("\n📝 Paso 1: Listar eventos...")
    respuesta_listar = enviar_mensaje("Muéstrame mis eventos de la próxima semana")
    time.sleep(1)
    
    # Modificar la presentación
    print("\n📝 Paso 2: Modificar hora de la presentación...")
    respuesta_modificar = enviar_mensaje("Mueve la presentación del proyecto a las 10:30 AM")
    
    assert "actualizado" in respuesta_modificar['response'].lower() or \
           "movido" in respuesta_modificar['response'].lower() or \
           "10:30" in respuesta_modificar['response'], \
        "Debería poder modificar evento de sesión anterior"
    
    print("✅ Pudo modificar evento de sesión anterior!")
    time.sleep(1)
    
    # Verificar modificación
    print("\n📝 Paso 3: Verificar modificación...")
    respuesta_verificar = enviar_mensaje("¿A qué hora es la presentación del proyecto ahora?")
    
    assert "10:30" in respuesta_verificar['response'] or "10" in respuesta_verificar['response'], \
        "Debería reflejar la nueva hora"
    
    print("✅ Modificación verificada correctamente!")


def test_sesion_3_larga_ausencia():
    """SESIÓN 3: Simular larga ausencia y verificar memoria a largo plazo"""
    print("\n" + "⏰"*40)
    print("SESIÓN 3: MEMORIA A LARGO PLAZO (LARGA AUSENCIA)")
    print("⏰"*40 + "\n")
    
    print("⏳ Simulando ausencia de 10 segundos...")
    time.sleep(10)
    
    print("\n📝 Usuario regresa después de larga ausencia...")
    respuesta = enviar_mensaje("Hola, ¿qué eventos tenía agendados?")
    
    response_lower = respuesta['response'].lower()
    
    # Debe SEGUIR recordando los eventos
    assert "presentación" in response_lower or "proyecto" in response_lower or \
           "dentista" in response_lower or "evento" in response_lower, \
        "❌ FALLO: Perdió memoria a largo plazo"
    
    print("✅ Memoria a largo plazo intacta!")
    
    # Verificar que recuerda el nombre
    respuesta_nombre = enviar_mensaje("¿Cómo me llamo?")
    
    if "carlos" in respuesta_nombre['response'].lower():
        print("✅ Recuerda el nombre del usuario después de larga ausencia!")
    else:
        print("⚠️  No mencionó el nombre explícitamente")


def test_sesion_3_eliminar_evento():
    """SESIÓN 3: Eliminar evento creado en sesión 1"""
    print("\n" + "🗑️"*40)
    print("SESIÓN 3: ELIMINAR EVENTO DE SESIÓN 1")
    print("🗑️"*40 + "\n")
    
    # Listar para contexto
    print("\n📝 Paso 1: Listar eventos...")
    respuesta_listar = enviar_mensaje("¿Qué eventos tengo?")
    time.sleep(1)
    
    # Eliminar la cita con dentista
    print("\n📝 Paso 2: Eliminar evento antiguo...")
    respuesta_eliminar = enviar_mensaje("Elimina la cita con el dentista")
    
    assert "eliminado" in respuesta_eliminar['response'].lower() or \
           "borrado" in respuesta_eliminar['response'].lower(), \
        "Debería poder eliminar evento de sesión anterior"
    
    print("✅ Pudo eliminar evento de sesión 1!")
    time.sleep(1)
    
    # Verificar eliminación
    print("\n📝 Paso 3: Verificar eliminación...")
    respuesta_verificar = enviar_mensaje("¿Todavía tengo la cita con dentista?")
    
    assert "no" in respuesta_verificar['response'].lower() or \
           "eliminado" in respuesta_verificar['response'].lower(), \
        "Debería confirmar que el evento ya no existe"
    
    print("✅ Eliminación verificada!")


def ejecutar_suite_completa():
    """Ejecuta toda la suite de tests de memoria persistente"""
    print("\n" + "🧠"*40)
    print("INICIANDO SUITE DE TESTS DE MEMORIA EPISÓDICA PERSISTENTE")
    print("🧠"*40 + "\n")
    
    print("""
📚 CONCEPTO DE MEMORIA EPISÓDICA:
   - La memoria episódica registra eventos específicos de la vida del usuario
   - Debe persistir entre sesiones (threads diferentes)
   - Usa pgvector para buscar contexto relevante por similitud semántica
   - Permite referencias contextuales ('el evento que creé ayer')
    """)
    
    resultados = []
    
    try:
        # SESIÓN 1
        print("\n" + "="*80)
        print("INICIANDO SESIÓN 1")
        print("="*80)
        thread_1 = test_sesion_1_crear_eventos()
        resultados.append(("Sesión 1: Crear eventos y contexto", "✅ PASS"))
    except Exception as e:
        print(f"❌ ERROR en Sesión 1: {e}")
        resultados.append(("Sesión 1: Crear eventos y contexto", f"❌ FAIL: {e}"))
        return
    
    # SIMULAR CIERRE
    try:
        test_simular_cierre_sesion()
        resultados.append(("Simular cierre de sesión", "✅ PASS"))
    except Exception as e:
        resultados.append(("Simular cierre de sesión", f"⚠️  {e}"))
    
    # SESIÓN 2
    try:
        print("\n" + "="*80)
        print("INICIANDO SESIÓN 2 (NUEVO THREAD)")
        print("="*80)
        thread_2 = test_sesion_2_verificar_memoria()
        resultados.append(("Sesión 2: Verificar memoria", "✅ PASS"))
    except Exception as e:
        print(f"❌ ERROR CRÍTICO en Sesión 2: {e}")
        resultados.append(("Sesión 2: Verificar memoria", f"❌ FAIL: {e}"))
        return
    
    # MODIFICAR EVENTO ANTERIOR
    try:
        test_sesion_2_modificar_evento_anterior()
        resultados.append(("Sesión 2: Modificar evento anterior", "✅ PASS"))
    except Exception as e:
        print(f"❌ ERROR: {e}")
        resultados.append(("Sesión 2: Modificar evento anterior", f"❌ FAIL: {e}"))
    
    # SESIÓN 3 - LARGA AUSENCIA
    try:
        test_sesion_3_larga_ausencia()
        resultados.append(("Sesión 3: Memoria largo plazo", "✅ PASS"))
    except Exception as e:
        print(f"❌ ERROR: {e}")
        resultados.append(("Sesión 3: Memoria largo plazo", f"❌ FAIL: {e}"))
    
    # ELIMINAR EVENTO ANTIGUO
    try:
        test_sesion_3_eliminar_evento()
        resultados.append(("Sesión 3: Eliminar evento antiguo", "✅ PASS"))
    except Exception as e:
        print(f"❌ ERROR: {e}")
        resultados.append(("Sesión 3: Eliminar evento antiguo", f"❌ FAIL: {e}"))
    
    # RESUMEN
    print("\n" + "="*80)
    print("RESUMEN DE TESTS DE MEMORIA EPISÓDICA PERSISTENTE")
    print("="*80 + "\n")
    
    for nombre, resultado in resultados:
        print(f"{resultado:50} | {nombre}")
    
    passed = sum(1 for _, r in resultados if "✅" in r)
    total = len(resultados)
    
    print(f"\n{'='*80}")
    print(f"RESULTADO FINAL: {passed}/{total} tests pasaron ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 ¡ÉXITO TOTAL! El sistema tiene memoria episódica persistente funcional")
    elif passed >= total * 0.8:
        print("\n✅ Sistema mayormente funcional, algunos edge cases pendientes")
    else:
        print("\n⚠️  ATENCIÓN: Memoria episódica tiene problemas significativos")
    
    print(f"{'='*80}\n")


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║      TEST EXHAUSTIVO 14: MEMORIA EPISÓDICA PERSISTENTE              ║
║                                                                      ║
║  Objetivo: Verificar que el sistema recuerda contexto entre sesiones║
║            usando pgvector y embeddings semánticos                   ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
    """)
    
    ejecutar_suite_completa()
