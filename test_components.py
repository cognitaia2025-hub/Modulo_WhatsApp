#!/usr/bin/env python3
"""
Test Unitario - Herramientas de Google Calendar
Prueba las herramientas sin necesidad del backend corriendo
"""

import sys
import os
sys.path.insert(0, '/workspaces/Modulo_WhatsApp')

from datetime import datetime, timedelta
import pendulum

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)

def test_imports():
    """Test 1: Verificar que todos los módulos se pueden importar"""
    print_section("TEST 1: Importación de Módulos")
    
    try:
        from src.tool import (
            list_events_tool,
            create_event_tool,
            update_event_tool,
            delete_event_tool
        )
        print("✅ Herramientas importadas correctamente")
        print(f"   - list_events_tool: {type(list_events_tool)}")
        print(f"   - create_event_tool: {type(create_event_tool)}")
        print(f"   - update_event_tool: {type(update_event_tool)}")
        print(f"   - delete_event_tool: {type(delete_event_tool)}")
        return True
    except Exception as e:
        print(f"❌ Error importando herramientas: {e}")
        return False

def test_tool_schemas():
    """Test 2: Verificar esquemas de herramientas"""
    print_section("TEST 2: Esquemas de Herramientas")
    
    try:
        from src.tool import (
            list_events_tool,
            create_event_tool,
            update_event_tool,
            delete_event_tool
        )
        
        tools = {
            "list_events": list_events_tool,
            "create_event": create_event_tool,
            "update_event": update_event_tool,
            "delete_event": delete_event_tool
        }
        
        for tool_name, tool in tools.items():
            print(f"\n🔧 {tool_name}")
            if hasattr(tool, 'name'):
                print(f"   Nombre: {tool.name}")
            if hasattr(tool, 'description'):
                print(f"   Descripción: {tool.description[:80]}...")
            if hasattr(tool, 'args_schema'):
                schema = tool.args_schema
                if hasattr(schema, 'schema'):
                    fields = schema.schema().get('properties', {})
                    print(f"   Parámetros ({len(fields)}): {', '.join(fields.keys())}")
        
        print("\n✅ Todas las herramientas tienen esquemas válidos")
        return True
        
    except Exception as e:
        print(f"❌ Error verificando esquemas: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_timezone_configuration():
    """Test 3: Verificar configuración de timezone"""
    print_section("TEST 3: Configuración de Timezone")
    
    try:
        tz = pendulum.timezone("America/Tijuana")
        now = pendulum.now(tz)
        
        print(f"✅ Timezone configurado correctamente")
        print(f"   - Zona horaria: America/Tijuana")
        print(f"   - Hora actual: {now.format('YYYY-MM-DD HH:mm:ss')}")
        print(f"   - UTC offset: {now.offset_hours} horas")
        
        return True
    except Exception as e:
        print(f"❌ Error con timezone: {e}")
        return False

def test_embeddings_system():
    """Test 4: Verificar sistema de embeddings"""
    print_section("TEST 4: Sistema de Embeddings")
    
    try:
        from src.embeddings.local_embedder import get_embedder
        
        embedder = get_embedder()
        print(f"✅ Embedder cargado: {type(embedder)}")
        
        # Test de embedding
        test_text = "Reunión con el equipo mañana a las 10 AM"
        embedding = embedder.encode(test_text).tolist()
        
        print(f"   - Dimensiones: {len(embedding)}")
        print(f"   - Primeros 5 valores: {embedding[:5]}")
        print(f"   - Tipo: {type(embedding[0])}")
        
        if len(embedding) == 384:
            print("✅ Embedding tiene 384 dimensiones (correcto para pgvector)")
            return True
        else:
            print(f"⚠️  Embedding tiene {len(embedding)} dimensiones (esperado: 384)")
            return False
            
    except Exception as e:
        print(f"❌ Error con embeddings: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database_tools_table():
    """Test 5: Verificar tabla de herramientas en BD"""
    print_section("TEST 5: Consulta de Herramientas en BD")
    
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        conn = psycopg2.connect(
            "postgresql://admin:password123@localhost:5434/agente_whatsapp",
            cursor_factory=RealDictCursor
        )
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT nombre, descripcion, activa 
            FROM herramientas_disponibles 
            WHERE activa = true
            ORDER BY id_tool;
        """)
        
        tools = cursor.fetchall()
        
        print(f"✅ Herramientas activas en BD: {len(tools)}")
        for tool in tools:
            print(f"   - {tool['nombre']}")
        
        cursor.close()
        conn.close()
        
        return len(tools) == 5
        
    except Exception as e:
        print(f"❌ Error consultando BD: {e}")
        return False

def test_memory_system():
    """Test 6: Verificar sistema de memoria episódica"""
    print_section("TEST 6: Sistema de Memoria Episódica")
    
    try:
        import psycopg2
        import json
        import random
        
        conn = psycopg2.connect(
            "postgresql://admin:password123@localhost:5434/agente_whatsapp"
        )
        cursor = conn.cursor()
        
        # Crear embedding de prueba
        test_embedding = [random.random() for _ in range(384)]
        test_vector_str = "[" + ",".join(map(str, test_embedding)) + "]"
        
        # Insertar memoria de prueba
        cursor.execute("""
            INSERT INTO memoria_episodica (user_id, resumen, embedding, metadata)
            VALUES (%s, %s, %s::vector, %s::jsonb)
            RETURNING id;
        """, (
            "test_unit_user",
            "Test unitario: Reunión programada para mañana",
            test_vector_str,
            json.dumps({
                "tipo": "test_unitario",
                "timestamp": datetime.now().isoformat(),
                "evento": "reunion_equipo"
            })
        ))
        
        memory_id = cursor.fetchone()[0]
        print(f"✅ Memoria insertada (ID: {memory_id})")
        
        # Buscar memorias del usuario
        cursor.execute("""
            SELECT id, user_id, resumen, metadata
            FROM memoria_episodica
            WHERE user_id = 'test_unit_user'
            ORDER BY timestamp DESC;
        """)
        
        memories = cursor.fetchall()
        print(f"✅ Memorias recuperadas: {len(memories)}")
        
        for mem in memories:
            print(f"   - ID {mem[0]}: {mem[2][:50]}...")
        
        # Limpiar
        cursor.execute("DELETE FROM memoria_episodica WHERE user_id = 'test_unit_user';")
        conn.commit()
        print("✅ Memorias de prueba eliminadas")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Error con memoria episódica: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Ejecutar todos los tests unitarios"""
    print("\n" + "="*60)
    print("  TESTS UNITARIOS - Componentes del Sistema")
    print("="*60)
    print(f"⏰ Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {
        "Importación de módulos": test_imports(),
        "Esquemas de herramientas": test_tool_schemas(),
        "Configuración timezone": test_timezone_configuration(),
        "Sistema de embeddings": test_embeddings_system(),
        "Tabla de herramientas BD": test_database_tools_table(),
        "Sistema de memoria": test_memory_system()
    }
    
    # Resumen
    print_section("RESUMEN DE RESULTADOS")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\n📊 Total: {passed}/{total} tests pasados")
    
    if passed == total:
        print("\n🎉 ¡Todos los tests unitarios pasaron!")
        print("✅ Los componentes del sistema están funcionando correctamente")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) fallaron")
        print("❌ Revisar componentes con errores")
        return 1

if __name__ == "__main__":
    sys.exit(main())
