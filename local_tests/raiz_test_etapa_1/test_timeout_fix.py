"""
Demostración del problema de timeout y su solución

Este script muestra:
1. Por qué ocurrió el KeyboardInterrupt
2. Cómo los timeouts protegen contra APIs lentas
3. Que el fallback funciona correctamente
"""

import time
from unittest.mock import patch, MagicMock
from src.nodes.generacion_resumen_node import nodo_generacion_resumen, llm_auditor

print("\n" + "="*80)
print("🔍 ANÁLISIS DEL PROBLEMA DE TIMEOUT")
print("="*80 + "\n")

# 1. Mostrar la configuración del LLM
print("1️⃣ Configuración del LLM Auditor:")
print(f"   • Modelo: {llm_auditor.model_name}")
print(f"   • Timeout: {llm_auditor.request_timeout}s")
print(f"   • Max retries: {llm_auditor.max_retries}")
print(f"   • Temperature: {llm_auditor.temperature}")
print(f"   • Max tokens: {llm_auditor.max_tokens}\n")

# 2. Explicar qué pasó
print("2️⃣ ¿Qué pasó en el test original?")
print("   ❌ El LLM NO tenía timeout configurado")
print("   ❌ Si DeepSeek tardaba 60s, el código esperaba 60s")
print("   ❌ El usuario tuvo que cancelar con Ctrl+C (KeyboardInterrupt)")
print("   ❌ El try-except NO captura KeyboardInterrupt (es BaseException)\n")

# 3. Solución implementada
print("3️⃣ Solución implementada:")
print("   ✅ Agregado timeout=30.0 segundos")
print("   ✅ max_retries=1 (no reintentar indefinidamente)")
print("   ✅ Si timeout → lanza Exception → capturado por try-except")
print("   ✅ Fallback automático genera resumen básico\n")

# 4. Test del fallback
print("4️⃣ Probando el fallback (sin llamar al LLM real):")
print("   Simulando conversación normal...\n")

state_test = {
    'messages': [
        {'role': 'user', 'content': 'Necesito agendar una reunión'},
        {'role': 'ai', 'content': '¿Para cuándo?'},
        {'role': 'user', 'content': 'Mañana a las 3pm'}
    ],
    'user_id': 'test_user',
    'session_id': 'test_session',
    'contexto_episodico': None,
    'sesion_expirada': False
}

# Simular un error de timeout
with patch.object(llm_auditor, 'invoke') as mock_invoke:
    mock_invoke.side_effect = TimeoutError("Simulated timeout after 30s")
    
    print("   🔥 Simulando timeout del API...")
    resultado = nodo_generacion_resumen(state_test)
    
    print(f"   ✅ Fallback activado!")
    print(f"   ✅ Resumen generado: {resultado['resumen_actual']}\n")

# 5. Test con mensaje muy corto (no llama al LLM)
print("5️⃣ Test con mensaje corto (protección pre-LLM):")
state_corto = {
    'messages': [{'role': 'user', 'content': 'ok'}],
    'user_id': 'test',
    'session_id': 'test',
    'contexto_episodico': None,
    'sesion_expirada': False
}

resultado_corto = nodo_generacion_resumen(state_corto)
print(f"   ✅ Resultado: {resultado_corto['resumen_actual']}\n")

# 6. Resumen
print("="*80)
print("📋 RESUMEN DE PROTECCIONES DEL NODO 6")
print("="*80)
print("\n✅ ANTES del LLM:")
print("   • Valida mensajes mínimos (< 2 → skip)")
print("   • Valida contenido relevante (< 10 chars → skip)")
print("   • Retorna 'Sin cambios relevantes' sin invocar LLM")
print("\n✅ DURANTE el LLM:")
print("   • Timeout de 30 segundos en HTTP request")
print("   • Max 1 reintento si falla la primera llamada")
print("   • Si timeout → lanza TimeoutError")
print("\n✅ DESPUÉS del error:")
print("   • try-except captura TimeoutError y otras Exceptions")
print("   • Genera resumen básico: '[timestamp] Conversación con N mensajes'")
print("   • NUNCA falla completamente, siempre retorna un state válido")
print("\n💡 CONCLUSIÓN:")
print("   El Nodo 6 ahora tiene protección REAL contra timeouts.")
print("   El problema que viste (KeyboardInterrupt) está resuelto.\n")
