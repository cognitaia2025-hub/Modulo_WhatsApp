#!/usr/bin/env python3
"""
Test de Infraestructura - Verificación de Base de Datos
Verifica que PostgreSQL, pgvector y las tablas estén correctamente configuradas
"""

import sys
import psycopg2
from psycopg2.extras import RealDictCursor
import json
from datetime import datetime

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)

def test_database_connection():
    """Test 1: Verificar conexión a PostgreSQL"""
    print_section("TEST 1: Conexión a Base de Datos")
    
    try:
        conn = psycopg2.connect(
            "postgresql://admin:password123@localhost:5434/agente_whatsapp"
        )
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"✅ Conexión exitosa")
        print(f"📊 PostgreSQL: {version.split(',')[0]}")
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return False

def test_pgvector_extension():
    """Test 2: Verificar extensión pgvector"""
    print_section("TEST 2: Extensión pgvector")
    
    try:
        conn = psycopg2.connect(
            "postgresql://admin:password123@localhost:5434/agente_whatsapp"
        )
        cursor = conn.cursor()
        cursor.execute("""
            SELECT extname, extversion 
            FROM pg_extension 
            WHERE extname = 'vector';
        """)
        result = cursor.fetchone()
        if result:
            print(f"✅ Extensión pgvector instalada")
            print(f"📦 Versión: {result[1]}")
            cursor.close()
            conn.close()
            return True
        else:
            print("❌ Extensión pgvector NO encontrada")
            cursor.close()
            conn.close()
            return False
    except Exception as e:
        print(f"❌ Error verificando pgvector: {e}")
        return False

def test_herramientas_table():
    """Test 3: Verificar tabla herramientas_disponibles"""
    print_section("TEST 3: Tabla de Herramientas")
    
    try:
        conn = psycopg2.connect(
            "postgresql://admin:password123@localhost:5434/agente_whatsapp",
            cursor_factory=RealDictCursor
        )
        cursor = conn.cursor()
        
        # Verificar estructura
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'herramientas_disponibles'
            ORDER BY ordinal_position;
        """)
        columns = cursor.fetchall()
        
        if not columns:
            print("❌ Tabla herramientas_disponibles NO existe")
            return False
        
        print(f"✅ Tabla herramientas_disponibles existe")
        print(f"📋 Columnas ({len(columns)}):")
        for col in columns:
            print(f"   - {col['column_name']} ({col['data_type']})")
        
        # Verificar datos
        cursor.execute("SELECT COUNT(*) as total FROM herramientas_disponibles;")
        count = cursor.fetchone()['total']
        print(f"\n📊 Total de herramientas: {count}")
        
        if count == 0:
            print("⚠️  No hay herramientas insertadas")
            cursor.close()
            conn.close()
            return False
        
        # Listar herramientas
        cursor.execute("""
            SELECT nombre, activa 
            FROM herramientas_disponibles 
            ORDER BY id_tool;
        """)
        herramientas = cursor.fetchall()
        print("\n🔧 Herramientas disponibles:")
        for h in herramientas:
            status = "✅" if h['activa'] else "❌"
            print(f"   {status} {h['nombre']}")
        
        cursor.close()
        conn.close()
        return count == 5  # Deben ser exactamente 5 herramientas
        
    except Exception as e:
        print(f"❌ Error verificando tabla herramientas: {e}")
        return False

def test_memoria_episodica_table():
    """Test 4: Verificar tabla memoria_episodica con pgvector"""
    print_section("TEST 4: Tabla de Memoria Episódica")
    
    try:
        conn = psycopg2.connect(
            "postgresql://admin:password123@localhost:5434/agente_whatsapp",
            cursor_factory=RealDictCursor
        )
        cursor = conn.cursor()
        
        # Verificar estructura
        cursor.execute("""
            SELECT column_name, data_type, udt_name
            FROM information_schema.columns 
            WHERE table_name = 'memoria_episodica'
            ORDER BY ordinal_position;
        """)
        columns = cursor.fetchall()
        
        if not columns:
            print("❌ Tabla memoria_episodica NO existe")
            return False
        
        print(f"✅ Tabla memoria_episodica existe")
        print(f"📋 Columnas ({len(columns)}):")
        
        has_vector = False
        for col in columns:
            dtype = col['udt_name'] if col['data_type'] == 'USER-DEFINED' else col['data_type']
            if dtype == 'vector':
                has_vector = True
                print(f"   - {col['column_name']} ({dtype}) ⭐ PGVECTOR")
            else:
                print(f"   - {col['column_name']} ({dtype})")
        
        if not has_vector:
            print("❌ No se encontró columna tipo 'vector'")
            return False
        
        # Verificar índices
        cursor.execute("""
            SELECT indexname, indexdef 
            FROM pg_indexes 
            WHERE tablename = 'memoria_episodica';
        """)
        indices = cursor.fetchall()
        print(f"\n📑 Índices ({len(indices)}):")
        for idx in indices:
            print(f"   - {idx['indexname']}")
        
        # Verificar datos
        cursor.execute("SELECT COUNT(*) as total FROM memoria_episodica;")
        count = cursor.fetchone()['total']
        print(f"\n📊 Total de memorias: {count}")
        
        if count == 0:
            print("ℹ️  Tabla vacía (esperado en primera ejecución)")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error verificando tabla memoria_episodica: {e}")
        return False

def test_insert_and_search_vector():
    """Test 5: Insertar y buscar vectores (Test de pgvector)"""
    print_section("TEST 5: Inserción y Búsqueda de Vectores")
    
    try:
        conn = psycopg2.connect(
            "postgresql://admin:password123@localhost:5434/agente_whatsapp"
        )
        cursor = conn.cursor()
        
        # Crear un vector de prueba (384 dimensiones)
        import random
        test_vector = [random.random() for _ in range(384)]
        test_vector_str = "[" + ",".join(map(str, test_vector)) + "]"
        
        # Insertar memoria de prueba
        cursor.execute("""
            INSERT INTO memoria_episodica (user_id, resumen, embedding, metadata)
            VALUES (%s, %s, %s::vector, %s::jsonb)
            RETURNING id;
        """, (
            "test_user",
            "Test de infraestructura - verificación de pgvector",
            test_vector_str,
            json.dumps({"tipo": "test", "timestamp": datetime.now().isoformat()})
        ))
        
        test_id = cursor.fetchone()[0]
        print(f"✅ Vector insertado (ID: {test_id})")
        
        # Buscar por similitud (debería devolver el mismo vector)
        cursor.execute("""
            SELECT id, user_id, resumen, 
                   embedding <=> %s::vector as distance
            FROM memoria_episodica
            WHERE user_id = 'test_user'
            ORDER BY distance ASC
            LIMIT 1;
        """, (test_vector_str,))
        
        result = cursor.fetchone()
        if result:
            print(f"✅ Búsqueda de similitud exitosa")
            print(f"   - ID: {result[0]}")
            print(f"   - Resumen: {result[2]}")
            print(f"   - Distancia: {result[3]:.6f}")
        
        # Limpiar datos de prueba
        cursor.execute("DELETE FROM memoria_episodica WHERE user_id = 'test_user';")
        print(f"✅ Datos de prueba eliminados")
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error en test de vectores: {e}")
        return False

def main():
    """Ejecutar todos los tests de infraestructura"""
    print("\n" + "="*60)
    print("  TEST DE INFRAESTRUCTURA - PostgreSQL + pgvector")
    print("="*60)
    print(f"⏰ Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {
        "Conexión BD": test_database_connection(),
        "Extensión pgvector": test_pgvector_extension(),
        "Tabla Herramientas": test_herramientas_table(),
        "Tabla Memoria": test_memoria_episodica_table(),
        "Insert & Search Vectores": test_insert_and_search_vector()
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
        print("\n🎉 ¡Todos los tests de infraestructura pasaron!")
        print("✅ La base de datos está lista para uso")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) fallaron")
        print("❌ Revisar configuración de la base de datos")
        return 1

if __name__ == "__main__":
    sys.exit(main())
