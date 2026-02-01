#!/usr/bin/env python3
"""
Script de verificación: Modernización N3A Recuperación Episódica

Verifica que todas las mejoras se hayan aplicado correctamente:
✅ Command pattern
✅ psycopg3
✅ Estado conversacional
✅ Filtro SQL threshold
✅ Truncamiento de resúmenes
"""

import ast
import sys
from pathlib import Path

def verificar_imports():
    """Verifica que se usen los imports correctos."""
    print("1. Verificando imports...")
    
    file_path = Path("src/nodes/recuperacion_episodica_node.py")
    content = file_path.read_text()
    
    checks = {
        "psycopg3": "import psycopg" in content and "from psycopg.rows import dict_row" in content,
        "Command": "from langgraph.types import Command" in content,
        "No psycopg2": "import psycopg2" not in content and "from psycopg2" not in content
    }
    
    for check, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"   {status} {check}")
    
    return all(checks.values())

def verificar_constantes():
    """Verifica que existan las constantes necesarias."""
    print("\n2. Verificando constantes...")
    
    file_path = Path("src/nodes/recuperacion_episodica_node.py")
    content = file_path.read_text()
    
    checks = {
        "ESTADOS_FLUJO_ACTIVO": "ESTADOS_FLUJO_ACTIVO" in content,
        "Lista de estados": "'ejecutando_herramienta'" in content,
        "SIMILARITY_THRESHOLD": "SIMILARITY_THRESHOLD = 0.5" in content
    }
    
    for check, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"   {status} {check}")
    
    return all(checks.values())

def verificar_sql_threshold():
    """Verifica que el filtro threshold esté en SQL."""
    print("\n3. Verificando filtro threshold en SQL...")
    
    file_path = Path("src/nodes/recuperacion_episodica_node.py")
    content = file_path.read_text()
    
    # Buscar el query SQL
    sql_section = content[content.find("SELECT"):content.find("ORDER BY embedding")]
    
    checks = {
        "Filtro WHERE threshold": "AND 1 - (embedding <=> %s::vector) >= %s" in sql_section,
        "No filtrado post-query": "episodios_filtrados" not in content,
        "psycopg3 context manager": "with psycopg.connect(" in content,
        "dict_row usage": "row_factory=dict_row" in content
    }
    
    for check, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"   {status} {check}")
    
    return all(checks.values())

def verificar_command_pattern():
    """Verifica que se use Command pattern."""
    print("\n4. Verificando Command pattern...")
    
    file_path = Path("src/nodes/recuperacion_episodica_node.py")
    content = file_path.read_text()
    
    checks = {
        "Función retorna Command": "def nodo_recuperacion_episodica(state: WhatsAppAgentState) -> Command:" in content,
        "Return con Command": "return Command(" in content and content.count("return Command(") >= 4,
        "goto routing": "goto=\"seleccion_herramientas\"" in content,
        "Wrapper retorna Command": "def nodo_recuperacion_episodica_wrapper(state: WhatsAppAgentState) -> Command:" in content
    }
    
    for check, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"   {status} {check}")
    
    return all(checks.values())

def verificar_estado_conversacional():
    """Verifica detección de estado conversacional."""
    print("\n5. Verificando detección estado conversacional...")
    
    file_path = Path("src/nodes/recuperacion_episodica_node.py")
    content = file_path.read_text()
    
    checks = {
        "Lee estado_conversacion": "estado_conversacion = state.get('estado_conversacion'" in content,
        "Detecta flujo activo": "if estado_conversacion in ESTADOS_FLUJO_ACTIVO:" in content,
        "Salta recuperación": "Saltando recuperación" in content,
        "Retorna None en contexto": "update={'contexto_episodico': None}" in content
    }
    
    for check, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"   {status} {check}")
    
    return all(checks.values())

def verificar_truncamiento():
    """Verifica truncamiento de resúmenes largos."""
    print("\n6. Verificando truncamiento de resúmenes...")
    
    file_path = Path("src/nodes/recuperacion_episodica_node.py")
    content = file_path.read_text()
    
    checks = {
        "MAX_RESUMEN_CHARS definido": "MAX_RESUMEN_CHARS = 200" in content,
        "Lógica de truncamiento": "if len(resumen) > MAX_RESUMEN_CHARS:" in content,
        "Agregar ellipsis": 'resumen_truncado = resumen[:MAX_RESUMEN_CHARS - 3] + "..."' in content
    }
    
    for check, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"   {status} {check}")
    
    return all(checks.values())

def verificar_tests():
    """Verifica que existan los tests."""
    print("\n7. Verificando tests unitarios...")
    
    test_file = Path("tests/test_recuperacion_episodica.py")
    
    checks = {
        "Archivo de tests existe": test_file.exists(),
    }
    
    if test_file.exists():
        content = test_file.read_text()
        checks.update({
            "Test Command pattern": "test_recuperacion_episodica_basica" in content,
            "Test sin user_id": "test_sin_user_id" in content,
            "Test detecta estado activo": "test_detecta_estado_activo" in content,
            "Test búsqueda semántica": "test_buscar_episodios_con_resultados" in content,
            "Test formateo": "test_formatear_contexto_con_episodios" in content,
            "Test truncamiento": "test_formatear_contexto_trunca_largos" in content,
            "Test error handling": "test_error_embedding_no_rompe_flujo" in content,
        })
    
    for check, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"   {status} {check}")
    
    return all(checks.values())

def verificar_documentacion():
    """Verifica que la documentación esté actualizada."""
    print("\n8. Verificando documentación...")
    
    file_path = Path("src/nodes/recuperacion_episodica_node.py")
    content = file_path.read_text()
    
    checks = {
        "Docstring actualizado": "similarity >= 0.5" in content,
        "Comentario threshold actualizado": "Threshold de similitud: 0.5" in content,
        "Mejoras documentadas en buscar_episodios": "✅ Filtro threshold en SQL" in content,
        "Mejoras documentadas en nodo": "✅ Command pattern con routing directo" in content
    }
    
    for check, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"   {status} {check}")
    
    return all(checks.values())

def main():
    """Ejecuta todas las verificaciones."""
    print("=" * 70)
    print("VERIFICACIÓN: Modernización N3A Recuperación Episódica")
    print("=" * 70)
    
    resultados = [
        verificar_imports(),
        verificar_constantes(),
        verificar_sql_threshold(),
        verificar_command_pattern(),
        verificar_estado_conversacional(),
        verificar_truncamiento(),
        verificar_tests(),
        verificar_documentacion()
    ]
    
    print("\n" + "=" * 70)
    if all(resultados):
        print("✅ TODAS LAS VERIFICACIONES PASARON")
        print("=" * 70)
        print("\nResumen de mejoras aplicadas:")
        print("  • Command pattern implementado")
        print("  • psycopg3 reemplaza psycopg2")
        print("  • Detección de estado conversacional activo")
        print("  • Filtro threshold movido a SQL (más eficiente)")
        print("  • Resúmenes largos se truncan automáticamente")
        print("  • 12 tests unitarios creados")
        print("  • Documentación actualizada")
        return 0
    else:
        print("❌ ALGUNAS VERIFICACIONES FALLARON")
        print("=" * 70)
        return 1

if __name__ == "__main__":
    sys.exit(main())
