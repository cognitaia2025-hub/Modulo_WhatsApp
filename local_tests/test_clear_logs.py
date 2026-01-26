"""
Script para probar el endpoint /clear-logs del backend.

Uso:
1. Asegúrate de que el backend esté corriendo (uvicorn app:app)
2. Ejecuta este script: python test_clear_logs.py
"""

import requests
import sys
from datetime import datetime

def test_clear_logs():
    """Prueba el endpoint /clear-logs"""
    
    BASE_URL = "http://localhost:8000"
    
    print("\n" + "="*70)
    print("  TEST: Endpoint /clear-logs")
    print("="*70 + "\n")
    
    try:
        print("📡 Enviando POST request a /clear-logs...")
        response = requests.post(f"{BASE_URL}/clear-logs", timeout=5)
        
        print(f"✅ Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("\n📦 Respuesta del servidor:")
            print(f"   Status: {data.get('status')}")
            print(f"   Message: {data.get('message')}")
            print(f"   Timestamp: {data.get('timestamp')}")
            print("\n✅ Logs limpiados exitosamente!")
        else:
            print(f"\n⚠️  Error: Status code {response.status_code}")
            print(f"   Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: No se pudo conectar al backend")
        print("   Asegúrate de que el servidor esté corriendo:")
        print("   uvicorn app:app --reload --port 8000")
        sys.exit(1)
        
    except requests.exceptions.Timeout:
        print("\n❌ Error: Timeout al conectar con el backend")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        sys.exit(1)


def test_invoke():
    """Prueba el endpoint /invoke para generar logs"""
    
    BASE_URL = "http://localhost:8000"
    
    print("\n" + "="*70)
    print("  TEST: Endpoint /invoke (generar logs)")
    print("="*70 + "\n")
    
    try:
        payload = {
            "user_input": "¿Qué eventos tengo hoy?"
        }
        
        print("📡 Enviando mensaje de prueba...")
        response = requests.post(f"{BASE_URL}/invoke", json=payload, timeout=30)
        
        print(f"✅ Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("\n📦 Respuesta del agente:")
            print(f"   {data}")
            print("\n✅ El agente procesó el mensaje correctamente!")
        else:
            print(f"\n⚠️  Error: Status code {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: No se pudo conectar al backend")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Prueba los endpoints del backend")
    parser.add_argument(
        "--clear", 
        action="store_true", 
        help="Limpia los logs"
    )
    parser.add_argument(
        "--invoke", 
        action="store_true", 
        help="Envía un mensaje de prueba (genera logs)"
    )
    parser.add_argument(
        "--all", 
        action="store_true", 
        help="Ejecuta ambas pruebas"
    )
    
    args = parser.parse_args()
    
    if args.all:
        test_invoke()
        print("\n" + "-"*70 + "\n")
        input("Presiona Enter para limpiar los logs...")
        test_clear_logs()
    elif args.invoke:
        test_invoke()
    elif args.clear:
        test_clear_logs()
    else:
        # Por defecto, solo limpiar logs
        test_clear_logs()
    
    print("\n" + "="*70)
    print("  Tests completados")
    print("="*70 + "\n")
