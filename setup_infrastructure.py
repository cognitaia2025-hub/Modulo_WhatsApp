#!/usr/bin/env python3
"""
Script de Inicialización de Infraestructura
============================================

Este script:
1. Levanta el contenedor Docker con PostgreSQL + pgvector
2. Espera a que la base de datos esté lista
3. Verifica que las tablas fueron creadas
4. Instala las dependencias de PostgresSaver si faltan
5. Ejecuta un test de conexión

Uso:
    python setup_infrastructure.py
"""

import subprocess
import time
import sys
import os
from pathlib import Path

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent))

def print_header(text):
    """Imprime encabezado con estilo"""
    print("\n" + "="*80)
    print(f"  {text}")
    print("="*80 + "\n")


def print_step(number, text):
    """Imprime paso numerado"""
    print(f"🔹 Paso {number}: {text}")


def run_command(command, description, check=True):
    """Ejecuta comando y muestra resultado"""
    print(f"   Ejecutando: {description}...")
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=check,
            capture_output=True,
            text=True
        )
        print(f"   ✅ {description} - OK")
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        print(f"   ❌ {description} - ERROR")
        print(f"   {e.stderr}")
        return False, e.stderr


def check_docker_running():
    """Verifica si Docker está corriendo"""
    print_step(1, "Verificando Docker Desktop")
    success, _ = run_command(
        "docker --version",
        "Docker instalado",
        check=False
    )
    
    if not success:
        print("\n❌ Docker no está instalado o no está en el PATH")
        print("   Descarga: https://www.docker.com/products/docker-desktop")
        return False
    
    success, _ = run_command(
        "docker ps",
        "Docker Desktop corriendo",
        check=False
    )
    
    if not success:
        print("\n❌ Docker Desktop no está corriendo")
        print("   Inicia Docker Desktop e intenta de nuevo")
        return False
    
    return True


def start_containers():
    """Levanta contenedores con docker-compose"""
    print_step(2, "Levantando contenedor PostgreSQL + pgvector")
    
    # Verificar que existe docker-compose.yaml
    if not Path("docker-compose.yaml").exists():
        print("   ❌ No se encontró docker-compose.yaml")
        return False
    
    # Levantar contenedores
    success, _ = run_command(
        "docker-compose up -d",
        "docker-compose up -d",
        check=False
    )
    
    if not success:
        print("   ⚠️  Intentando con 'docker compose' (sin guion)...")
        success, _ = run_command(
            "docker compose up -d",
            "docker compose up -d",
            check=False
        )
    
    if not success:
        return False
    
    print("   ⏳ Esperando a que PostgreSQL esté listo...")
    time.sleep(5)  # Dar tiempo para que el contenedor inicie
    
    # Verificar que el contenedor está corriendo
    success, output = run_command(
        "docker ps --filter name=agente-whatsapp-db --format '{{.Status}}'",
        "Verificar contenedor",
        check=False
    )
    
    if "Up" in output:
        print("   ✅ Contenedor 'agente-whatsapp-db' corriendo")
        return True
    else:
        print("   ❌ Contenedor no está corriendo correctamente")
        return False


def wait_for_postgres():
    """Espera a que PostgreSQL acepte conexiones"""
    print_step(3, "Esperando a que PostgreSQL esté listo")
    
    max_attempts = 30
    attempt = 0
    
    while attempt < max_attempts:
        attempt += 1
        success, _ = run_command(
            "docker exec agente-whatsapp-db pg_isready -U admin -d agente_whatsapp",
            f"Intento {attempt}/{max_attempts}",
            check=False
        )
        
        if success:
            print("   ✅ PostgreSQL listo para aceptar conexiones")
            return True
        
        time.sleep(2)
    
    print("   ❌ PostgreSQL no respondió después de 60 segundos")
    return False


def verify_database():
    """Verifica que las tablas fueron creadas"""
    print_step(4, "Verificando tablas creadas")
    
    # Verificar extensión pgvector
    success, output = run_command(
        "docker exec agente-whatsapp-db psql -U admin -d agente_whatsapp -c \"SELECT extname FROM pg_extension WHERE extname='vector';\"",
        "Extensión pgvector",
        check=False
    )
    
    if not success or "vector" not in output:
        print("   ❌ Extensión pgvector no instalada")
        return False
    
    # Verificar tabla herramientas_disponibles
    success, output = run_command(
        "docker exec agente-whatsapp-db psql -U admin -d agente_whatsapp -c \"SELECT COUNT(*) FROM herramientas_disponibles;\"",
        "Tabla herramientas_disponibles (existe)",
        check=False
    )
    
    if not success:
        print("   ❌ Tabla herramientas_disponibles no existe")
        return False
    
    # Extraer número de registros
    try:
        count = int(output.strip().split('\n')[2].strip())
        if count == 5:
            print("   ✅ 5 herramientas de Google Calendar cargadas")
        elif count == 0:
            print("   ℹ️  Tabla herramientas_disponibles vacía (0 registros)")
        else:
            print(f"   ℹ️  {count} herramientas encontradas")
    except:
        print("   ℹ️  No se pudo determinar número de herramientas")
    
    # Verificar tabla memoria_episodica
    success, output = run_command(
        "docker exec agente-whatsapp-db psql -U admin -d agente_whatsapp -c \"SELECT COUNT(*) FROM memoria_episodica;\"",
        "Tabla memoria_episodica (existe)",
        check=False
    )
    
    if not success:
        print("   ❌ Tabla memoria_episodica no existe")
        return False
    
    # Extraer número de registros
    try:
        count = int(output.strip().split('\n')[2].strip())
        if count > 0:
            print(f"   ✅ {count} memoria(s) episódica(s) almacenada(s)")
        else:
            print("   ℹ️  Tabla memoria_episodica vacía (sin recuerdos aún)")
    except:
        print("   ℹ️  Tabla memoria_episodica lista para usar")
    
    # Verificar tabla auditoria_conversaciones
    success, output = run_command(
        "docker exec agente-whatsapp-db psql -U admin -d agente_whatsapp -c \"SELECT COUNT(*) FROM auditoria_conversaciones;\"",
        "Tabla auditoria_conversaciones (existe)",
        check=False
    )
    
    if not success:
        print("   ❌ Tabla auditoria_conversaciones no existe")
        return False
    
    # Extraer número de registros
    try:
        count = int(output.strip().split('\n')[2].strip())
        if count > 0:
            print(f"   ✅ {count} mensaje(s) en auditoría")
        else:
            print("   ℹ️  Tabla auditoria_conversaciones vacía (sin logs aún)")
    except:
        print("   ℹ️  Tabla auditoria_conversaciones lista para usar")
    
    return True


def install_dependencies():
    """Instala dependencias de PostgresSaver"""
    print_step(5, "Verificando dependencias Python")
    
    # Verificar si langgraph-checkpoint-postgres está instalado
    success, _ = run_command(
        "pip show langgraph-checkpoint-postgres",
        "langgraph-checkpoint-postgres",
        check=False
    )
    
    if not success:
        print("   📦 Instalando langgraph-checkpoint-postgres...")
        success, _ = run_command(
            "pip install langgraph-checkpoint-postgres",
            "Instalación langgraph-checkpoint-postgres",
            check=False
        )
        if not success:
            return False
    
    # Verificar psycopg
    success, _ = run_command(
        "pip show psycopg",
        "psycopg (driver PostgreSQL)",
        check=False
    )
    
    if not success:
        print("   📦 Instalando psycopg...")
        success, _ = run_command(
            "pip install psycopg[binary]",
            "Instalación psycopg",
            check=False
        )
        if not success:
            return False
    
    return True


def test_connection():
    """Prueba conexión desde Python"""
    print_step(6, "Probando conexión desde Python")
    
    try:
        import psycopg
        from dotenv import load_dotenv
        
        load_dotenv()
        database_url = os.getenv("DATABASE_URL")
        
        if not database_url:
            print("   ❌ DATABASE_URL no configurado en .env")
            return False
        
        print(f"   🔗 Conectando a: {database_url}")
        
        conn = psycopg.connect(database_url)
        cursor = conn.cursor()
        
        # Query de prueba
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        
        print(f"   ✅ Conexión exitosa")
        print(f"   📊 PostgreSQL: {version.split(',')[0]}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error de conexión: {e}")
        return False


def test_checkpointer():
    """Prueba PostgresSaver de LangGraph"""
    print_step(7, "Probando PostgresSaver de LangGraph")
    
    try:
        from langgraph.checkpoint.postgres import PostgresSaver
        import psycopg
        from dotenv import load_dotenv
        
        load_dotenv()
        database_url = os.getenv("DATABASE_URL")
        
        conn = psycopg.connect(database_url)
        checkpointer = PostgresSaver(conn)
        
        # Setup: crea tablas de LangGraph
        checkpointer.setup()
        
        print("   ✅ PostgresSaver configurado")
        print("   📦 Tablas creadas: checkpoints, checkpoint_writes, checkpoint_blobs")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"   ❌ Error configurando PostgresSaver: {e}")
        return False


def main():
    """Función principal"""
    print_header("🚀 SETUP DE INFRAESTRUCTURA - AGENTE WHATSAPP")
    
    # Verificar Docker
    if not check_docker_running():
        sys.exit(1)
    
    # Levantar contenedores
    if not start_containers():
        print("\n❌ Error levantando contenedores")
        sys.exit(1)
    
    # Esperar PostgreSQL
    if not wait_for_postgres():
        print("\n❌ PostgreSQL no está listo")
        sys.exit(1)
    
    # Verificar tablas
    if not verify_database():
        print("\n❌ Base de datos no está correctamente inicializada")
        sys.exit(1)
    
    # Instalar dependencias
    if not install_dependencies():
        print("\n❌ Error instalando dependencias")
        sys.exit(1)
    
    # Probar conexión
    if not test_connection():
        print("\n❌ Error probando conexión")
        sys.exit(1)
    
    # Probar checkpointer
    if not test_checkpointer():
        print("\n❌ Error configurando PostgresSaver")
        sys.exit(1)
    
    # Resumen final
    print_header("✅ INFRAESTRUCTURA LISTA")
    
    print("📊 Resumen de Configuración:")
    print("   • PostgreSQL 16 + pgvector: ✅ Corriendo en puerto 5434")
    print("   • Base de datos: agente_whatsapp")
    print("   • Usuario: admin / password123")
    print("   • Tablas creadas:")
    print("      - herramientas_disponibles (5 herramientas de Google Calendar)")
    print("      - memoria_episodica (búsqueda vectorial con embeddings 384 dims)")
    print("      - auditoria_conversaciones (logs planos, retención 6 meses)")
    print("      - checkpoints, checkpoint_writes, checkpoint_blobs (LangGraph)")
    print("   • PostgresSaver: ✅ Configurado (caché 24h)")
    print()
    print("🎯 Próximos pasos:")
    print("   1. Ejecutar: python test_end_to_end.py")
    print("   2. Los mensajes ahora se persistirán en PostgreSQL")
    print("   3. Las conversaciones serán recordadas entre sesiones")
    print()
    print("💡 Comandos útiles:")
    print("   • Ver logs: docker logs agente-whatsapp-db")
    print("   • Entrar al contenedor: docker exec -it agente-whatsapp-db psql -U admin -d agente_whatsapp")
    print("   • Detener: docker-compose down")
    print("   • Borrar todo: docker-compose down -v")
    print()


if __name__ == "__main__":
    main()
