"""
Test del Nodo 3: Recuperación de Memoria Episódica

Valida que el nodo recupere correctamente episodios de pgvector.
"""

import sys
import os

# Agregar directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.nodes.recuperacion_episodica_node import (
    nodo_recuperacion_episodica,
    nodo_recuperacion_episodica_wrapper
)
from langchain_core.messages import HumanMessage
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

print("=" * 80)
print("TEST: Nodo 3 - Recuperación de Memoria Episódica")
print("=" * 80)

# Test 1: Usuario con historial
print("\n[TEST 1] Usuario con posible historial en DB")
print("-" * 80)

estado_test1 = {
    'user_id': 'user_1e3c1c99351f',  # Usuario real de los logs
    'session_id': 'session_test_001',
    'messages': [
        HumanMessage(content="¿Qué eventos tengo esta semana?")
    ],
    'contexto_episodico': None
}

print(f"\n📝 Mensaje: {estado_test1['messages'][0].content}")
print(f"👤 User ID: {estado_test1['user_id']}")

resultado1 = nodo_recuperacion_episodica_wrapper(estado_test1)

contexto1 = resultado1.get('contexto_episodico', {})
print(f"\n📊 Resultados:")
print(f"   • Episodios recuperados: {contexto1.get('episodios_recuperados', 0)}")
print(f"   • Timestamp: {contexto1.get('timestamp_recuperacion', 'N/A')}")
print(f"   • Threshold: {contexto1.get('similarity_threshold', 'N/A')}")

if contexto1.get('episodios_recuperados', 0) > 0:
    print(f"\n📖 Contexto formateado:")
    print("-" * 80)
    print(contexto1.get('texto_formateado', ''))
    print("-" * 80)
    
    if 'episodios_detalle' in contexto1:
        print(f"\n🔍 Detalles de episodios:")
        for ep in contexto1['episodios_detalle']:
            print(f"   • [{ep['fecha']}] Similarity: {ep['similarity']:.3f}")
            print(f"     {ep['preview']}...")
else:
    print(f"\n   Mensaje: {contexto1.get('texto_formateado', 'Sin contexto')}")

# Test 2: Usuario nuevo (sin historial)
print("\n\n[TEST 2] Usuario nuevo sin historial")
print("-" * 80)

estado_test2 = {
    'user_id': 'usuario_nuevo_' + os.urandom(4).hex(),
    'session_id': 'session_test_002',
    'messages': [
        HumanMessage(content="Hola, primera vez usando el bot")
    ],
    'contexto_episodico': None
}

print(f"\n📝 Mensaje: {estado_test2['messages'][0].content}")
print(f"👤 User ID: {estado_test2['user_id']}")

resultado2 = nodo_recuperacion_episodica_wrapper(estado_test2)

contexto2 = resultado2.get('contexto_episodico', {})
print(f"\n📊 Resultados:")
print(f"   • Episodios recuperados: {contexto2.get('episodios_recuperados', 0)}")
print(f"   • Mensaje: {contexto2.get('texto_formateado', 'N/A')}")

# Test 3: Sin user_id (caso edge)
print("\n\n[TEST 3] Sin user_id (caso edge)")
print("-" * 80)

estado_test3 = {
    'user_id': None,
    'session_id': 'session_test_003',
    'messages': [
        HumanMessage(content="Test sin identificación")
    ],
    'contexto_episodico': None
}

resultado3 = nodo_recuperacion_episodica_wrapper(estado_test3)

contexto3 = resultado3.get('contexto_episodico', {})
print(f"\n📊 Resultados:")
print(f"   • Error: {contexto3.get('error', 'N/A')}")
print(f"   • Mensaje: {contexto3.get('texto_formateado', 'N/A')}")

print("\n" + "=" * 80)
print("✅ Tests completados")
print("=" * 80)
