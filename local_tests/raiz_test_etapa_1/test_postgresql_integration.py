"""
Test de Integración PostgreSQL + pgvector
=========================================

Prueba la infraestructura completa de base de datos:
1. Conexión a PostgreSQL (puerto 5434)
2. Lectura de herramientas desde herramientas_disponibles
3. Guardado de memorias episódicas con embeddings
4. Búsqueda semántica con pgvector (cosine similarity)
5. Auditoría de conversaciones
6. PostgresSaver checkpoints (LangGraph)

Requiere: Docker con PostgreSQL corriendo
Comando: python test_postgresql_integration.py

Autor: Agente con Memoria Infinita
Fecha: 2026-01-24
"""

import os
import sys
import psycopg
from datetime import datetime

# Agregar src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Cargar variables de entorno
from dotenv import load_dotenv
load_dotenv()


def print_separator(title: str = ""):
    """Imprime separador visual"""
    print("\n" + "="*80)
    if title:
        print(f"  {title}")
        print("="*80)
    print()


def test_connection():
    """Test 1: Verifica conexión a PostgreSQL"""
    print_separator("TEST 1: Conexión a PostgreSQL")
    
    try:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            print("❌ DATABASE_URL no encontrado en .env")
            return False
        
        print(f"📡 Conectando a: {database_url.replace('password123', '***')}")
        
        conn = psycopg.connect(database_url)
        cursor = conn.cursor()
        
        # Verificar versión
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"✅ PostgreSQL conectado: {version.split(',')[0]}")
        
        # Verificar extensión pgvector
        cursor.execute("SELECT extname, extversion FROM pg_extension WHERE extname='vector';")
        result = cursor.fetchone()
        if result:
            print(f"✅ pgvector instalado: versión {result[1]}")
        else:
            print("❌ pgvector no encontrado")
            return False
        
        cursor.close()
        conn.close()
        
        print("\n✅ Test 1 PASÓ: Conexión exitosa")
        return True
        
    except Exception as e:
        print(f"❌ Test 1 FALLÓ: {e}")
        return False


def test_herramientas_disponibles():
    """Test 2: Verifica tabla herramientas_disponibles"""
    print_separator("TEST 2: Herramientas Disponibles")
    
    try:
        conn = psycopg.connect(os.getenv("DATABASE_URL"))
        cursor = conn.cursor()
        
        # Contar herramientas activas
        cursor.execute("""
            SELECT COUNT(*) FROM herramientas_disponibles WHERE activa = true;
        """)
        count = cursor.fetchone()[0]
        print(f"📊 Herramientas activas: {count}")
        
        if count != 5:
            print(f"❌ Se esperaban 5 herramientas, encontradas: {count}")
            return False
        
        # Listar herramientas
        cursor.execute("""
            SELECT nombre, descripcion 
            FROM herramientas_disponibles 
            WHERE activa = true 
            ORDER BY id_tool;
        """)
        
        print("\n🛠️  Herramientas cargadas:")
        for idx, (nombre, desc) in enumerate(cursor.fetchall(), 1):
            print(f"   {idx}. {nombre}")
            print(f"      {desc[:60]}...")
        
        cursor.close()
        conn.close()
        
        print("\n✅ Test 2 PASÓ: 5 herramientas de Google Calendar disponibles")
        return True
        
    except Exception as e:
        print(f"❌ Test 2 FALLÓ: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_memoria_episodica():
    """Test 3: Verifica guardado y búsqueda en memoria episódica"""
    print_separator("TEST 3: Memoria Episódica con pgvector")
    
    try:
        conn = psycopg.connect(os.getenv("DATABASE_URL"))
        cursor = conn.cursor()
        
        # 1. Crear embedding de prueba (384 dimensiones)
        import numpy as np
        test_embedding = np.random.rand(384).tolist()
        
        # 2. Insertar memoria de prueba
        cursor.execute("""
            INSERT INTO memoria_episodica (user_id, resumen, embedding, metadata)
            VALUES (%s, %s, %s, %s)
            RETURNING id;
        """, (
            'test_user_123',
            'El usuario agendó reunión con equipo para mañana a las 10:00 AM',
            test_embedding,
            '{"session_id": "test_session", "tipo": "normal", "fecha": "2026-01-24"}'
        ))
        
        memoria_id = cursor.fetchone()[0]
        conn.commit()
        print(f"✅ Memoria guardada con ID: {memoria_id}")
        
        # 3. Verificar que se guardó correctamente
        cursor.execute("""
            SELECT id, user_id, resumen, 
                   array_length(embedding::float8[], 1) as embedding_dim
            FROM memoria_episodica 
            WHERE id = %s;
        """, (memoria_id,))
        
        result = cursor.fetchone()
        print(f"📝 Resumen: {result[2][:50]}...")
        print(f"🔢 Dimensiones del embedding: {result[3]}")
        
        if result[3] != 384:
            print(f"❌ Embedding debería tener 384 dimensiones, tiene: {result[3]}")
            return False
        
        # 4. Probar búsqueda semántica
        test_query_embedding = np.random.rand(384).tolist()
        cursor.execute("""
            SELECT id, resumen, 
                   1 - (embedding <=> %s::vector) as similarity
            FROM memoria_episodica
            WHERE user_id = %s
            ORDER BY embedding <=> %s::vector
            LIMIT 3;
        """, (test_query_embedding, 'test_user_123', test_query_embedding))
        
        print("\n🔍 Búsqueda semántica (top 3):")
        for idx, (mem_id, resumen, similarity) in enumerate(cursor.fetchall(), 1):
            print(f"   {idx}. Similarity: {similarity:.4f}")
            print(f"      {resumen[:60]}...")
        
        # 5. Limpiar datos de prueba
        cursor.execute("DELETE FROM memoria_episodica WHERE user_id = 'test_user_123';")
        conn.commit()
        print("\n🧹 Datos de prueba eliminados")
        
        cursor.close()
        conn.close()
        
        print("\n✅ Test 3 PASÓ: Memoria episódica funcional con pgvector")
        return True
        
    except Exception as e:
        print(f"❌ Test 3 FALLÓ: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_auditoria_conversaciones():
    """Test 4: Verifica tabla de auditoría"""
    print_separator("TEST 4: Auditoría de Conversaciones")
    
    try:
        conn = psycopg.connect(os.getenv("DATABASE_URL"))
        cursor = conn.cursor()
        
        # 1. Insertar log de prueba
        cursor.execute("""
            INSERT INTO auditoria_conversaciones (user_id, session_id, rol, contenido)
            VALUES 
                (%s, %s, 'user', 'Hola, ¿qué tengo agendado mañana?'),
                (%s, %s, 'assistant', 'Revisando tu calendario...')
            RETURNING id;
        """, (
            'test_user_456',
            'test_session_001',
            'test_user_456',
            'test_session_001'
        ))
        
        log_ids = [row[0] for row in cursor.fetchall()]
        conn.commit()
        print(f"✅ {len(log_ids)} logs guardados: {log_ids}")
        
        # 2. Consultar logs por usuario
        cursor.execute("""
            SELECT rol, contenido, timestamp
            FROM auditoria_conversaciones
            WHERE user_id = %s
            ORDER BY timestamp DESC
            LIMIT 5;
        """, ('test_user_456',))
        
        print("\n📜 Últimos logs del usuario:")
        for rol, contenido, timestamp in cursor.fetchall():
            print(f"   [{timestamp.strftime('%H:%M:%S')}] {rol:10s}: {contenido[:50]}...")
        
        # 3. Limpiar datos de prueba
        cursor.execute("DELETE FROM auditoria_conversaciones WHERE user_id = 'test_user_456';")
        conn.commit()
        print("\n🧹 Datos de prueba eliminados")
        
        cursor.close()
        conn.close()
        
        print("\n✅ Test 4 PASÓ: Auditoría funcional")
        return True
        
    except Exception as e:
        print(f"❌ Test 4 FALLÓ: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_postgres_saver():
    """Test 5: Verifica tablas de PostgresSaver (LangGraph)"""
    print_separator("TEST 5: PostgresSaver Checkpoints")
    
    try:
        from langgraph.checkpoint.postgres import PostgresSaver
        
        conn = psycopg.connect(os.getenv("DATABASE_URL"), autocommit=True)
        checkpointer = PostgresSaver(conn)
        
        # Verificar que setup() no falla
        checkpointer.setup()
        print("✅ PostgresSaver.setup() ejecutado correctamente")
        
        # Verificar que las 3 tablas existen
        cursor = conn.cursor()
        cursor.execute("""
            SELECT tablename 
            FROM pg_tables 
            WHERE tablename IN ('checkpoints', 'checkpoint_writes', 'checkpoint_blobs')
            ORDER BY tablename;
        """)
        
        tables = [row[0] for row in cursor.fetchall()]
        print(f"📊 Tablas de LangGraph encontradas: {len(tables)}/3")
        
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table};")
            count = cursor.fetchone()[0]
            print(f"   - {table}: {count} registros")
        
        if len(tables) != 3:
            print(f"❌ Se esperaban 3 tablas, encontradas: {len(tables)}")
            return False
        
        cursor.close()
        conn.close()
        
        print("\n✅ Test 5 PASÓ: PostgresSaver configurado correctamente")
        return True
        
    except Exception as e:
        print(f"❌ Test 5 FALLÓ: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_full_integration():
    """Test 6: Prueba integración completa con el grafo"""
    print_separator("TEST 6: Integración Completa con LangGraph")
    
    try:
        from src.graph_whatsapp import crear_grafo
        
        print("🔧 Creando grafo con PostgresSaver...")
        graph = crear_grafo()
        
        if graph is None:
            print("❌ Grafo no se pudo crear")
            return False
        
        print("✅ Grafo creado exitosamente")
        
        # Verificar que tiene checkpointer
        if hasattr(graph, 'checkpointer') and graph.checkpointer:
            print("✅ Grafo tiene PostgresSaver configurado")
        else:
            print("⚠️  Grafo no tiene checkpointer (modo memoria)")
        
        print("\n✅ Test 6 PASÓ: Integración completa funcional")
        return True
        
    except Exception as e:
        print(f"❌ Test 6 FALLÓ: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Ejecuta todos los tests"""
    print_separator("🧪 TEST SUITE: PostgreSQL + pgvector Integration")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Python: {sys.version.split()[0]}")
    
    results = {
        "Conexión PostgreSQL": test_connection(),
        "Herramientas Disponibles": test_herramientas_disponibles(),
        "Memoria Episódica (pgvector)": test_memoria_episodica(),
        "Auditoría Conversaciones": test_auditoria_conversaciones(),
        "PostgresSaver (LangGraph)": test_postgres_saver(),
        "Integración Completa": test_full_integration(),
    }
    
    # Resumen final
    print_separator("📊 RESUMEN DE TESTS")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASÓ" if result else "❌ FALLÓ"
        print(f"{status:12s} | {test_name}")
    
    print(f"\n{'='*80}")
    print(f"Total: {passed}/{total} tests pasados ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 ¡TODOS LOS TESTS PASARON!")
        print("   Infraestructura PostgreSQL completamente funcional")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) fallaron")
        print("   Revisa los errores arriba para más detalles")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
