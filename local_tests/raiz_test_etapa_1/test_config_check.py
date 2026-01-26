"""
Test Rápido de Configuración
============================

Verifica que todos los componentes estén listos antes del test E2E.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def check_imports():
    """Verifica que todos los módulos se importen correctamente"""
    print("🔍 Verificando imports...")
    
    try:
        from src.graph_whatsapp import crear_grafo
        print("   ✅ graph_whatsapp importado")
    except Exception as e:
        print(f"   ❌ graph_whatsapp: {e}")
        return False
    
    try:
        # Los nodos principales están en src/nodes
        from src.nodes import (
            nodo_seleccion_herramientas_wrapper,
            nodo_ejecucion_herramientas_wrapper,
            nodo_generacion_resumen_wrapper,
            nodo_persistencia_episodica_wrapper
        )
        print("   ✅ Nodos principales importados (4/4)")
        print("   ℹ️  Otros nodos (cache, filtrado, recuperación) están en graph_whatsapp.py")
    except Exception as e:
        print(f"   ❌ Nodos: {e}")
        return False
    
    return True


def check_env():
    """Verifica variables de entorno"""
    print("\n🔍 Verificando .env...")
    
    required = {
        'OPENAI_API_KEY': 'DeepSeek API',
        'ANTHROPIC_API_KEY': 'Claude Fallback',
        'POSTGRES_HOST': 'PostgreSQL (opcional)',
        'GOOGLE_CALENDAR_CREDENTIALS': 'Google OAuth (opcional)'
    }
    
    found = 0
    for key, desc in required.items():
        value = os.getenv(key)
        if value:
            masked = value[:8] + "***" if len(value) > 8 else "***"
            print(f"   ✅ {key}: {masked} ({desc})")
            found += 1
        else:
            optional = "(opcional)" in desc
            symbol = "⚠️ " if optional else "❌"
            print(f"   {symbol} {key}: No configurado ({desc})")
    
    return found >= 2  # Al menos DeepSeek y Claude


def check_graph():
    """Verifica que el grafo compile"""
    print("\n🔍 Verificando compilación del grafo...")
    
    try:
        from src.graph_whatsapp import crear_grafo
        grafo = crear_grafo()
        print("   ✅ Grafo compilado exitosamente")
        
        # Verificar nodos
        nodes = list(grafo.nodes.keys()) if hasattr(grafo, 'nodes') else []
        expected = [
            'filtrado',
            'recuperacion_episodica',
            'seleccion_herramientas',
            'ejecucion_herramientas',
            'generacion_resumen',
            'persistencia_episodica'
        ]
        
        print(f"\n   📊 Nodos en el grafo: {len(nodes)}")
        for node in expected:
            if node in nodes:
                print(f"      ✅ {node}")
            else:
                print(f"      ❌ {node} (faltante)")
        
        # Verificar que tenga al menos los nodos principales
        return len([n for n in expected if n in nodes]) >= 4
        
    except Exception as e:
        print(f"   ❌ Error compilando grafo: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("="*80)
    print("  TEST RÁPIDO DE CONFIGURACIÓN")
    print("="*80)
    print("\nVerificando que el sistema esté listo para test E2E...\n")
    
    # Checks
    imports_ok = check_imports()
    env_ok = check_env()
    graph_ok = check_graph()
    
    # Resultado
    print("\n" + "="*80)
    print("  RESULTADO")
    print("="*80 + "\n")
    
    checks = [
        ("Imports", imports_ok),
        ("Variables de entorno", env_ok),
        ("Compilación del grafo", graph_ok)
    ]
    
    for name, result in checks:
        status = "✅ OK" if result else "❌ FALLO"
        print(f"{status} - {name}")
    
    all_ok = all(result for _, result in checks)
    
    if all_ok:
        print("\n🎉 ¡Sistema listo para test E2E!")
        print("\nEjecuta: python test_end_to_end.py")
        return 0
    else:
        print("\n⚠️  Hay problemas de configuración. Revisa los errores arriba.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
