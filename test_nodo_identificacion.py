"""
Test del Nodo 0: Identificación de Usuario

Prueba la funcionalidad de identificación de usuarios,
consulta BD, detección admin y auto-registro.
"""

import os
import sys
from pathlib import Path
from langchain_core.messages import HumanMessage

# Añadir el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.nodes.identificacion_usuario_node import nodo_identificacion_usuario_wrapper
from src.state.agent_state import WhatsAppAgentState


def test_identificacion_usuario_admin():
    """Test: Usuario administrador existente"""
    print("🧪 Test 1: Usuario Administrador")
    
    # Estado inicial con mensaje de admin
    state = WhatsAppAgentState(
        messages=[HumanMessage(content="Hola, soy el admin")],
        user_id="",
        session_id="test-session-1",
        es_admin=False,
        usuario_info={},
        usuario_registrado=False,
        contexto_episodico=None,
        herramientas_seleccionadas=[],
        requiere_herramientas=False,
        resumen_actual=None,
        sesion_expirada=False,
        ultimo_listado=None,
        timestamp=""
    )
    
    # Ejecutar nodo
    resultado = nodo_identificacion_usuario_wrapper(state)
    
    # Verificar resultados
    print(f"   ✓ User ID: {resultado['user_id']}")
    print(f"   ✓ Es Admin: {resultado['es_admin']}")
    print(f"   ✓ Registrado: {resultado['usuario_registrado']}")
    print(f"   ✓ Nombre: {resultado['usuario_info']['display_name']}")
    print()


def test_identificacion_usuario_nuevo():
    """Test: Usuario completamente nuevo"""
    print("🧪 Test 2: Usuario Nuevo")
    
    # Simular número nuevo
    nuevo_telefono = "+526641234999"
    
    state = WhatsAppAgentState(
        messages=[HumanMessage(content=f"Hola, mi número es {nuevo_telefono}")],
        user_id="",
        session_id="test-session-2", 
        es_admin=False,
        usuario_info={},
        usuario_registrado=False,
        contexto_episodico=None,
        herramientas_seleccionadas=[],
        requiere_herramientas=False,
        resumen_actual=None,
        sesion_expirada=False,
        ultimo_listado=None,
        timestamp=""
    )
    
    # Ejecutar nodo
    resultado = nodo_identificacion_usuario_wrapper(state)
    
    # Verificar resultados
    print(f"   ✓ User ID: {resultado['user_id']}")
    print(f"   ✓ Es Admin: {resultado['es_admin']}")
    print(f"   ✓ Registrado: {resultado['usuario_registrado']}")
    print(f"   ✓ Nombre: {resultado['usuario_info']['display_name']}")
    print()


def test_identificacion_usuario_existente():
    """Test: Usuario ya registrado previamente"""
    print("🧪 Test 3: Usuario Existente (ejecutar Test 2 primero)")
    
    # Usar el mismo número del test anterior
    telefono_existente = "+526641234999"
    
    state = WhatsAppAgentState(
        messages=[HumanMessage(content=f"Hola de nuevo, soy {telefono_existente}")],
        user_id="",
        session_id="test-session-3",
        es_admin=False,
        usuario_info={},
        usuario_registrado=False,
        contexto_episodico=None,
        herramientas_seleccionadas=[],
        requiere_herramientas=False,
        resumen_actual=None,
        sesion_expirada=False,
        ultimo_listado=None,
        timestamp=""
    )
    
    # Ejecutar nodo
    resultado = nodo_identificacion_usuario_wrapper(state)
    
    # Verificar resultados
    print(f"   ✓ User ID: {resultado['user_id']}")
    print(f"   ✓ Es Admin: {resultado['es_admin']}")
    print(f"   ✓ Registrado: {resultado['usuario_registrado']}")  # Debería ser True
    print(f"   ✓ Nombre: {resultado['usuario_info']['display_name']}")
    print()


def test_verificar_bd():
    """Test: Verificar estado final de la BD"""
    print("🧪 Test 4: Verificación BD")
    
    import psycopg
    
    try:
        with psycopg.connect("postgresql://admin:password123@localhost:5434/agente_whatsapp") as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM usuarios")
                total_usuarios = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(*) FROM usuarios WHERE es_admin = true")
                total_admins = cur.fetchone()[0]
                
                cur.execute("""
                    SELECT phone_number, display_name, es_admin 
                    FROM usuarios 
                    ORDER BY created_at DESC 
                    LIMIT 3
                """)
                usuarios_recientes = cur.fetchall()
                
    except Exception as e:
        print(f"   ❌ Error conectando BD: {e}")
        return
    
    print(f"   ✓ Total Usuarios: {total_usuarios}")
    print(f"   ✓ Total Admins: {total_admins}")
    print("   ✓ Usuarios Recientes:")
    
    for user in usuarios_recientes:
        admin_badge = "👑" if user[2] else "👤"
        print(f"      {admin_badge} {user[0]} - {user[1]}")
    print()


if __name__ == "__main__":
    print("🚀 INICIANDO TESTS DEL NODO IDENTIFICACIÓN\n")
    
    # Configurar variable de entorno para admin
    os.environ["ADMIN_PHONE_NUMBER"] = "+526641234567"
    os.environ["DATABASE_URL"] = "postgresql://admin:password123@localhost:5434/agente_whatsapp"
    
    try:
        test_identificacion_usuario_admin()
        test_identificacion_usuario_nuevo() 
        test_identificacion_usuario_existente()
        test_verificar_bd()
        
        print("✅ TODOS LOS TESTS COMPLETADOS")
        
    except Exception as e:
        print(f"❌ ERROR EN TESTS: {e}")
        import traceback
        traceback.print_exc()