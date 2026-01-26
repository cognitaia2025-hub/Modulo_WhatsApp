"""
🔍 Validador de Entorno - AI Calendar Agent
==========================================

Verifica que todas las dependencias y configuraciones estén correctas
antes de ejecutar los tests.

Autor: Test Automation
Fecha: 24/01/2026
"""

import os
import sys
import importlib
from typing import List, Tuple


def print_header():
    """Imprime encabezado"""
    print("=" * 80)
    print("🔍 VALIDADOR DE ENTORNO - AI CALENDAR AGENT".center(80))
    print("=" * 80)
    print()


def check_python_version() -> bool:
    """Verifica versión de Python"""
    print("🐍 Versión de Python:")
    version = sys.version_info
    print(f"   {version.major}.{version.minor}.{version.micro}")
    
    if version.major >= 3 and version.minor >= 10:
        print("   ✅ Versión compatible (>= 3.10)")
        return True
    else:
        print("   ❌ Se requiere Python 3.10 o superior")
        return False


def check_dependencies() -> Tuple[int, int]:
    """Verifica dependencias instaladas"""
    print("\n📦 Dependencias:")
    
    required_packages = [
        'langchain',
        'langchain_openai',
        'langchain_anthropic',
        'langgraph',
        'fastapi',
        'streamlit',
        'psycopg',
        'psycopg2',
        'google.oauth2',
        'googleapiclient',
        'sentence_transformers',
        'numpy',
        'pendulum',
        'dotenv',
        'dateparser',
    ]
    
    installed = 0
    missing = 0
    
    for package in required_packages:
        try:
            importlib.import_module(package.replace('-', '_'))
            print(f"   ✅ {package}")
            installed += 1
        except ImportError:
            print(f"   ❌ {package} - NO INSTALADO")
            missing += 1
    
    print(f"\n   Total: {installed}/{len(required_packages)} instalados")
    return installed, missing


def check_env_file() -> bool:
    """Verifica archivo .env"""
    print("\n⚙️  Archivo .env:")
    
    if not os.path.exists('.env'):
        print("   ❌ Archivo .env no encontrado")
        return False
    
    print("   ✅ Archivo .env existe")
    
    # Cargar variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        # Variables críticas
        critical_vars = [
            'DEEPSEEK_API_KEY',
            'ANTHROPIC_API_KEY',
            'TOGETHER_API_KEY',
        ]
        
        optional_vars = [
            'POSTGRES_HOST',
            'POSTGRES_PORT',
            'POSTGRES_DB',
            'POSTGRES_USER',
            'POSTGRES_PASSWORD',
        ]
        
        print("\n   Variables críticas:")
        for var in critical_vars:
            value = os.getenv(var)
            if value:
                masked = value[:8] + "..." if len(value) > 8 else "***"
                print(f"      ✅ {var}: {masked}")
            else:
                print(f"      ⚠️  {var}: No configurada")
        
        print("\n   Variables opcionales (PostgreSQL):")
        for var in optional_vars:
            value = os.getenv(var)
            if value:
                print(f"      ✅ {var}: {value}")
            else:
                print(f"      ℹ️  {var}: No configurada (usará fallback)")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error cargando .env: {e}")
        return False


def check_google_credentials() -> bool:
    """Verifica credenciales de Google"""
    print("\n🔑 Credenciales de Google Calendar:")
    
    files = ['credentials.json', 'token.json']
    found = 0
    
    for file in files:
        if os.path.exists(file):
            print(f"   ✅ {file} existe")
            found += 1
        else:
            print(f"   ⚠️  {file} no encontrado")
    
    if found == 0:
        print("   ℹ️  Ejecuta el flujo OAuth para generar credenciales")
        return False
    
    return True


def check_project_structure() -> bool:
    """Verifica estructura del proyecto"""
    print("\n📁 Estructura del proyecto:")
    
    required_dirs = [
        'src',
        'src/auth',
        'src/database',
        'src/embeddings',
        'src/memory',
        'src/nodes',
        'src/state',
        'src/utils',
    ]
    
    required_files = [
        'src/graph.py',
        'src/graph_whatsapp.py',
        'src/tool.py',
        'requirements.txt',
        'README.md',
    ]
    
    all_ok = True
    
    print("   Directorios:")
    for dir_path in required_dirs:
        if os.path.isdir(dir_path):
            print(f"      ✅ {dir_path}/")
        else:
            print(f"      ❌ {dir_path}/ - NO EXISTE")
            all_ok = False
    
    print("\n   Archivos clave:")
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"      ✅ {file_path}")
        else:
            print(f"      ❌ {file_path} - NO EXISTE")
            all_ok = False
    
    return all_ok


def check_database_connection() -> bool:
    """Verifica conexión a PostgreSQL (opcional)"""
    print("\n🐘 PostgreSQL:")
    
    host = os.getenv('POSTGRES_HOST')
    if not host:
        print("   ℹ️  No configurado (usará fallback a logging)")
        return True
    
    try:
        import psycopg2
        
        conn_params = {
            'host': os.getenv('POSTGRES_HOST'),
            'port': os.getenv('POSTGRES_PORT', '5432'),
            'dbname': os.getenv('POSTGRES_DB'),
            'user': os.getenv('POSTGRES_USER'),
            'password': os.getenv('POSTGRES_PASSWORD'),
        }
        
        print(f"   Intentando conexión a {conn_params['host']}:{conn_params['port']}")
        
        conn = psycopg2.connect(**conn_params, connect_timeout=5)
        conn.close()
        
        print("   ✅ Conexión exitosa")
        return True
        
    except Exception as e:
        print(f"   ⚠️  No se pudo conectar: {e}")
        print("   ℹ️  El sistema usará fallback a logging")
        return False


def main():
    """Función principal"""
    print_header()
    
    results = {
        'python_version': check_python_version(),
        'env_file': check_env_file(),
        'google_creds': check_google_credentials(),
        'project_structure': check_project_structure(),
        'database': check_database_connection(),
    }
    
    # Verificar dependencias (crítico)
    installed, missing = check_dependencies()
    results['dependencies'] = missing == 0
    
    # Resumen final
    print("\n" + "=" * 80)
    print("📊 RESUMEN DE VALIDACIÓN".center(80))
    print("=" * 80)
    print()
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    for key, value in results.items():
        status = "✅" if value else "❌"
        name = key.replace('_', ' ').title()
        print(f"   {status} {name}")
    
    print(f"\n   Total: {passed}/{total} checks pasados")
    
    print("\n" + "=" * 80)
    
    if passed == total:
        print("🎉 ¡ENTORNO COMPLETAMENTE CONFIGURADO!".center(80))
        print("Puedes ejecutar los tests sin problemas.".center(80))
        return 0
    elif results['python_version'] and results['dependencies']:
        print("⚠️  ENTORNO PARCIALMENTE CONFIGURADO".center(80))
        print("Los tests se pueden ejecutar pero algunas funcionalidades".center(80))
        print("pueden usar fallbacks (ej: PostgreSQL → logging).".center(80))
        return 0
    else:
        print("❌ ENTORNO INCOMPLETO".center(80))
        print("Instala las dependencias faltantes antes de ejecutar tests.".center(80))
        return 1
    
    print("=" * 80)
    print()


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
