from src.database import get_herramientas_disponibles
import json

print("\n🔍 Probando get_herramientas_disponibles()...\n")

herramientas = get_herramientas_disponibles(force_refresh=True)

print(f"Total herramientas: {len(herramientas)}\n")

for i, h in enumerate(herramientas, 1):
    print(f"{i}. {h}")
    print(f"   Tipo: {type(h)}")
    print(f"   Keys: {h.keys() if isinstance(h, dict) else 'N/A'}")
    print()

print("\n📋 Lista de id_tool:")
ids = [h['id_tool'] for h in herramientas]
print(ids)
print(f"\nTipos de IDs: {[type(id) for id in ids]}")