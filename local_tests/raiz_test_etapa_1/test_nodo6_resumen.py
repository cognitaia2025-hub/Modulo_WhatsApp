"""
Test del Nodo 6: Generación de Resúmenes (Auditoría)

Prueba:
1. Conversación normal con agendamiento
2. Sesión expirada con tarea pendiente
3. Sin contenido relevante (conversación trivial)
4. Conversación compleja con múltiples temas
5. Verificación de timestamp de Mexicali
"""

from src.nodes.generacion_resumen_node import (
    nodo_generacion_resumen,
    extraer_mensajes_relevantes,
    construir_prompt_auditoria
)
from datetime import datetime


def test_extraccion_mensajes():
    """Test 1: Extracción de mensajes relevantes"""
    print("\n" + "="*80)
    print("🧪 TEST 1: Extracción de Mensajes Relevantes")
    print("="*80 + "\n")
    
    messages = [
        {'role': 'user', 'content': 'Hola'},
        {'role': 'ai', 'content': '¡Hola! ¿En qué puedo ayudarte?'},
        {'role': 'user', 'content': 'Necesito agendar una reunión'},
        {'role': 'ai', 'content': '¿Para cuándo?'},
        {'role': 'user', 'content': 'Mañana a las 3 pm'},
        {'role': 'ai', 'content': 'Perfecto, agendé tu reunión'}
    ]
    
    conversacion = extraer_mensajes_relevantes(messages)
    
    print("   📝 Conversación extraída:")
    print("   " + "-"*70)
    print(conversacion)
    print("   " + "-"*70)
    
    assert len(conversacion) > 0, "❌ No se extrajo conversación"
    assert "USER:" in conversacion, "❌ Falta rol USER"
    assert "AI:" in conversacion, "❌ Falta rol AI"
    assert "reunión" in conversacion, "❌ Falta contenido clave"
    
    print("\n✅ Extracción de mensajes funcionando")


def test_prompt_auditoria_normal():
    """Test 2: Construcción de prompt (modo normal)"""
    print("\n" + "="*80)
    print("🧪 TEST 2: Prompt de Auditoría (Modo Normal)")
    print("="*80 + "\n")
    
    conversacion = """USER: Necesito agendar una reunión
AI: ¿Para cuándo?
USER: Mañana a las 3 pm
AI: Perfecto, agendé tu reunión"""
    
    prompt = construir_prompt_auditoria(
        conversacion=conversacion,
        contexto_episodico=None,
        sesion_expirada=False
    )
    
    print("   📝 Prompt generado (primeros 400 caracteres):")
    print("   " + "-"*70)
    print(prompt[:400] + "...")
    print("   " + "-"*70)
    
    assert "Mexicali" in prompt, "❌ Falta timestamp de Mexicali"
    assert conversacion in prompt, "❌ Falta conversación"
    assert "HECHOS" in prompt, "❌ Falta instrucción HECHOS"
    assert "PENDIENTES" in prompt, "❌ Falta instrucción PENDIENTES"
    assert "PERFIL" in prompt, "❌ Falta instrucción PERFIL"
    assert "ESTADO" in prompt, "❌ Falta instrucción ESTADO"
    assert "⚠️ IMPORTANTE" not in prompt, "❌ No debería tener instrucción de sesión expirada"
    
    print("\n✅ Prompt de auditoría normal construido correctamente")


def test_prompt_auditoria_expirada():
    """Test 3: Construcción de prompt (sesión expirada)"""
    print("\n" + "="*80)
    print("🧪 TEST 3: Prompt de Auditoría (Sesión Expirada)")
    print("="*80 + "\n")
    
    conversacion = """USER: Ponme una cita el miércoles
AI: ¿A qué hora?
USER: A las 10 am pero déjame confirmar el lugar"""
    
    contexto_previo = {
        'resumen': 'Usuario prefiere reuniones por la mañana'
    }
    
    prompt = construir_prompt_auditoria(
        conversacion=conversacion,
        contexto_episodico=contexto_previo,
        sesion_expirada=True
    )
    
    print("   📝 Prompt con sesión expirada (primeros 500 caracteres):")
    print("   " + "-"*70)
    print(prompt[:500] + "...")
    print("   " + "-"*70)
    
    assert "⚠️ IMPORTANTE" in prompt, "❌ Falta instrucción especial para sesión expirada"
    assert "24 horas" in prompt or "timeout" in prompt, "❌ Falta contexto de expiración"
    assert "CONTEXTO PREVIO" in prompt, "❌ Falta contexto episódico"
    assert "Usuario prefiere reuniones por la mañana" in prompt, "❌ Falta contenido del contexto"
    
    print("\n✅ Prompt para sesión expirada construido correctamente")


def test_resumen_agendamiento():
    """Test 4: Resumen de conversación con agendamiento"""
    print("\n" + "="*80)
    print("🧪 TEST 4: Resumen de Agendamiento")
    print("="*80 + "\n")
    
    state = {
        'messages': [
            {'role': 'user', 'content': 'Necesito agendar una reunión para mañana'},
            {'role': 'ai', 'content': '¿A qué hora te gustaría agendar?'},
            {'role': 'user', 'content': 'A las 3 de la tarde'},
            {'role': 'ai', 'content': 'Perfecto, agendé tu reunión para mañana a las 15:00'},
            {'role': 'user', 'content': 'Gracias'}
        ],
        'user_id': 'test_user',
        'session_id': 'session_test4',
        'contexto_episodico': None,
        'sesion_expirada': False
    }
    
    print("💬 Conversación: Agendamiento de reunión para mañana 15:00")
    print("🤖 Generando resumen con LLM auditor...")
    
    resultado = nodo_generacion_resumen(state)
    resumen = resultado['resumen_actual']
    
    print(f"\n   ✅ Resumen generado:")
    print(f"   {resumen}")
    print(f"\n   📊 Longitud: {len(resumen)} caracteres")
    
    # Verificaciones
    assert resumen, "❌ No se generó resumen"
    assert len(resumen) > 0, "❌ Resumen vacío"
    assert "[" in resumen and "]" in resumen, "❌ Falta timestamp en formato [DD/MM/YYYY HH:mm]"
    
    print("\n✅ Resumen de agendamiento generado correctamente")


def test_resumen_sesion_expirada():
    """Test 5: Resumen con sesión expirada (recuperación)"""
    print("\n" + "="*80)
    print("🧪 TEST 5: Resumen con Sesión Expirada")
    print("="*80 + "\n")
    
    state = {
        'messages': [
            {'role': 'user', 'content': 'Ponme una cita para el miércoles a las 10am'},
            {'role': 'ai', 'content': '¿En qué lugar será la cita?'},
            {'role': 'user', 'content': 'Déjame confirmar y te digo'}
        ],
        'user_id': 'test_user',
        'session_id': 'session_test5',
        'contexto_episodico': {
            'resumen': 'Usuario prefiere reuniones por la mañana. Trabaja en oficina central.'
        },
        'sesion_expirada': True  # ⚠️ Sesión interrumpida
    }
    
    print("💬 Conversación: Tarea PENDIENTE (usuario debe confirmar lugar)")
    print("⏰ Sesión expirada: TRUE (hace 24h)")
    print("🤖 Generando resumen de recuperación...")
    
    resultado = nodo_generacion_resumen(state)
    resumen = resultado['resumen_actual']
    
    print(f"\n   ✅ Resumen de recuperación:")
    print(f"   {resumen}")
    print(f"\n   📊 Longitud: {len(resumen)} caracteres")
    
    # Verificaciones específicas para sesión expirada
    assert resumen, "❌ No se generó resumen"
    assert "miércoles" in resumen.lower() or "10" in resumen, "❌ Falta información de fecha/hora"
    
    print("\n✅ Resumen de sesión expirada permite retomar conversación")


def test_resumen_sin_contenido():
    """Test 6: Conversación sin contenido relevante"""
    print("\n" + "="*80)
    print("🧪 TEST 6: Conversación Sin Contenido Relevante")
    print("="*80 + "\n")
    
    state = {
        'messages': [
            {'role': 'user', 'content': 'Hola'},
            {'role': 'ai', 'content': '¡Hola! ¿En qué puedo ayudarte?'},
            {'role': 'user', 'content': 'ok'}
        ],
        'user_id': 'test_user',
        'session_id': 'session_test6',
        'contexto_episodico': None,
        'sesion_expirada': False
    }
    
    print("💬 Conversación: Solo saludos sin contenido relevante")
    print("🤖 Generando resumen...")
    
    resultado = nodo_generacion_resumen(state)
    resumen = resultado['resumen_actual']
    
    print(f"\n   ✅ Resumen: {resumen}")
    print(f"   📊 Longitud: {len(resumen)} caracteres")
    
    # Verificar que se generó resumen aunque sea conversación trivial
    assert resumen, "❌ No se generó resumen"
    assert "HECHOS" in resumen or "saludo" in resumen.lower(), "❌ Falta análisis de hechos"
    
    print("\n✅ Manejo correcto de conversaciones sin contenido relevante")


def test_timestamp_mexicali():
    """Test 7: Verificar timestamp de Mexicali"""
    print("\n" + "="*80)
    print("🧪 TEST 7: Timestamp de Mexicali en Resumen")
    print("="*80 + "\n")
    
    state = {
        'messages': [
            {'role': 'user', 'content': 'Necesito ayuda con algo importante'},
            {'role': 'ai', 'content': 'Claro, ¿en qué puedo ayudarte?'},
            {'role': 'user', 'content': 'Agendar cita para revisar documentos'}
        ],
        'user_id': 'test_user',
        'session_id': 'session_test7',
        'contexto_episodico': None,
        'sesion_expirada': False
    }
    
    resultado = nodo_generacion_resumen(state)
    resumen = resultado['resumen_actual']
    
    print(f"   ✅ Resumen: {resumen[:100]}...")
    
    # Verificar formato de timestamp: [DD/MM/YYYY HH:mm]
    assert resumen.startswith("["), "❌ Falta apertura de timestamp"
    assert "]" in resumen, "❌ Falta cierre de timestamp"
    
    # Extraer timestamp
    timestamp_end = resumen.index("]")
    timestamp = resumen[1:timestamp_end]
    
    print(f"\n   📅 Timestamp extraído: {timestamp}")
    print(f"   🌐 Formato: DD/MM/YYYY HH:mm (Mexicali, BC)")
    
    assert "/" in timestamp, "❌ Formato de fecha incorrecto"
    assert ":" in timestamp, "❌ Formato de hora incorrecto"
    assert "2026" in timestamp, "❌ Año incorrecto"
    
    print("\n✅ Timestamp de Mexicali correcto en resumen")


if __name__ == "__main__":
    print("\n" + "🤖 "+"="*76 + "🤖")
    print("🤖 PRUEBAS DEL NODO 6 - Generación de Resúmenes (Auditoría)")
    print("🤖 "+"="*76 + "🤖")
    
    print("\n⚠️  NOTA: Tests invocan DeepSeek API para generación de resúmenes")
    print("   Los tests pueden tomar ~5-10 segundos por llamada LLM.\n")
    
    try:
        # Tests de utilidades
        test_extraccion_mensajes()
        test_prompt_auditoria_normal()
        test_prompt_auditoria_expirada()
        
        # Tests de generación con LLM
        test_resumen_agendamiento()
        test_resumen_sesion_expirada()
        test_resumen_sin_contenido()
        test_timestamp_mexicali()
        
        print("\n" + "="*80)
        print("🎉 TODAS LAS PRUEBAS COMPLETADAS")
        print("="*80)
        print("\n📋 RESUMEN DEL NODO 6:")
        print("   1. ✅ Extracción de mensajes relevantes")
        print("   2. ✅ Prompt de auditoría (modo normal)")
        print("   3. ✅ Prompt de auditoría (sesión expirada)")
        print("   4. ✅ Resumen de agendamiento con LLM")
        print("   5. ✅ Resumen de recuperación (sesión expirada)")
        print("   6. ✅ Manejo de conversaciones sin contenido")
        print("   7. ✅ Timestamp de Mexicali correcto")
        
        print("\n💡 CAPACIDADES DEL AUDITOR:")
        print("   • Extrae HECHOS (qué se hizo)")
        print("   • Identifica PENDIENTES (qué falta)")
        print("   • Aprende PERFIL (preferencias del usuario)")
        print("   • Define ESTADO (tarea completada/interrumpida)")
        print("   • Modo especial para RECUPERACIÓN tras 24h")
        print("   • Timestamp de Mexicali para contexto temporal")
        print("   • Resumen <100 palabras (optimizado para pgvector)")
        
        print("\n✅ El agente ahora AUDITA y DESTILA conocimiento\n")
        
    except Exception as e:
        print(f"\n❌ ERROR EN PRUEBAS: {e}")
        import traceback
        traceback.print_exc()
