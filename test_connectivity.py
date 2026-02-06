#!/usr/bin/env python3
"""
Script de prueba para verificar conexiones entre servicios
"""

import requests
import json
import os
from datetime import datetime

def test_database_connection():
    """Probar conexión a la base de datos directamente"""
    try:
        import psycopg
        DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:password123@localhost:5434/agente_whatsapp")
        
        print(f"🔌 Probando conexión a: {DATABASE_URL}")
        
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM memoria_episodica;")
                count = cur.fetchone()[0]
                print(f"✅ Conexión BD exitosa - {count} registros en memoria_episodica")
                return True
                
    except Exception as e:
        print(f"❌ Error conexión BD: {e}")
        return False

def test_dashboard_backend():
    """Probar si el dashboard backend está respondiendo"""
    try:
        response = requests.get("http://localhost:8000/", timeout=5)
        print(f"✅ Dashboard Backend: {response.status_code}")
        
        # Probar endpoint específico de vectores
        response = requests.get("http://localhost:8000/api/database/memory-vectors?limit=10", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Endpoint vectores: {data.get('total', 0)} vectores disponibles")
            return True
        else:
            print(f"❌ Endpoint vectores falló: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Dashboard Backend no responde: {e}")
        return False

def test_main_backend():
    """Probar si el backend principal está respondiendo"""
    try:
        response = requests.get("http://localhost:8002/health", timeout=5)
        print(f"✅ Main Backend: {response.status_code}")
        return True
    except Exception as e:
        print(f"❌ Main Backend no responde: {e}")
        return False

def main():
    print("🧪 === TEST DE CONECTIVIDAD ===")
    print(f"⏰ {datetime.now()}")
    print()
    
    # Tests
    db_ok = test_database_connection()
    main_ok = test_main_backend()  
    dashboard_ok = test_dashboard_backend()
    
    print()
    print("📊 === RESUMEN ===")
    print(f"Base de Datos: {'✅' if db_ok else '❌'}")
    print(f"Main Backend (8002): {'✅' if main_ok else '❌'}")
    print(f"Dashboard Backend (8000): {'✅' if dashboard_ok else '❌'}")
    
    if db_ok and main_ok and dashboard_ok:
        print("\n🎉 Todos los servicios funcionando correctamente!")
    else:
        print("\n⚠️  Hay servicios con problemas")

if __name__ == "__main__":
    main()