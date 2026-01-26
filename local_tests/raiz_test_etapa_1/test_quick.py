"""Prueba rápida de sesión expirada"""
from src.graph_whatsapp import crear_grafo
from datetime import datetime, timedelta

print("\n🧪 Prueba de Sesión Expirada (30h inactividad)\n")

g = crear_grafo()

# Estado con timestamp de hace 30 horas
estado = {
    'messages': [{'role': 'user', 'content': 'Agendar reunión lunes'}],
    'user_id': 'user_test',
    'session_id': 'session_test',
    'contexto_episodico': None,
    'herramientas_seleccionadas': [],
    'cambio_de_tema': False,
    'resumen_actual': None,
    'timestamp': (datetime.now() - timedelta(hours=30)).isoformat(),
    'sesion_expirada': False
}

r = g.invoke(estado)

print("\n✅ RESULTADO:")
print(f"   - Sesión expirada: {r.get('sesion_expirada')}")
print(f"   - Mensajes restantes: {len(r.get('messages', []))}")
print(f"   - Contenido mensajes: {r.get('messages', [])}")
print(f"   - Resumen generado: {r.get('resumen_actual', '')[:80]}...")
print("\n")
