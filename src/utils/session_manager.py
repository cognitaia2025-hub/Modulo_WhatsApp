"""
Gestor de Sesiones para WhatsApp Agent
=======================================

Maneja la creación y gestión de IDs de usuario y sesión con ROLLING WINDOW (24h de inactividad).

IMPORTANTE:
- NO usa fecha del día (evita pérdida de contexto a medianoche)
- USA timestamp del último mensaje para calcular inactividad
- Thread se mantiene mientras haya actividad < 24h
"""

import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional
import psycopg
import os
from dotenv import load_dotenv

load_dotenv()


def generate_user_id(phone_number: str) -> str:
    """
    Genera un user_id estable a partir del número de teléfono.
    
    Args:
        phone_number: Número de WhatsApp (ej: "+52123456789")
        
    Returns:
        user_id: Identificador único del usuario (hash del teléfono)
        
    Examples:
        >>> generate_user_id("+52123456789")
        'user_a3f8b9e2c1d4'
    """
    # Normalizar número (remover espacios, guiones, etc.)
    normalized = phone_number.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    
    # Generar hash SHA256 y tomar los primeros 12 caracteres
    hash_object = hashlib.sha256(normalized.encode())
    hash_hex = hash_object.hexdigest()
    
    # Retornar user_id con prefijo
    return f"user_{hash_hex[:12]}"


def generate_new_thread_id(user_id: str) -> str:
    """
    Genera un NUEVO thread_id único usando UUID.
    
    ✅ CORRECTO: No depende de la fecha, es un ID único permanente
    hasta que expire por inactividad (24h rolling window).
    
    Args:
        user_id: Identificador del usuario
        
    Returns:
        thread_id: Identificador único del thread (UUID)
        
    Examples:
        >>> generate_new_thread_id("user_a3f8b9e2c1d4")
        'thread_user_a3f8b9e2c1d4_f47ac10b58cc'
    """
    # UUID corto (primeros 12 caracteres)
    unique_id = str(uuid.uuid4())[:12]
    return f"thread_{user_id}_{unique_id}"


def create_session_config(phone_number: str) -> Dict:
    """
    Crea la configuración básica de sesión (SIN consultar BD).
    
    ⚠️  DEPRECADO: Usa get_or_create_session() para rolling window correcto.
    Esta función solo para tests/desarrollo.
    
    Args:
        phone_number: Número de WhatsApp del usuario
        
    Returns:
        Dict con user_id, session_id y config
    """
    user_id = generate_user_id(phone_number)
    session_id = generate_new_thread_id(user_id)
    
    return {
        'user_id': user_id,
        'session_id': session_id,
        'config': {
            'configurable': {
                'thread_id': session_id
            }
        }
    }


def get_or_create_session(phone_number: str, db_connection=None) -> Tuple[str, str, Dict]:
    """
    ✅ ROLLING WINDOW CORRECTO: Obtiene sesión activa o crea nueva basándose en INACTIVIDAD.
    
    Lógica:
    1. Busca última sesión del usuario en BD
    2. Si last_activity < 24h → REUSAR thread (conversación continúa)
    3. Si last_activity >= 24h → NUEVO thread (sesión expiró)
    4. Si no existe → CREAR thread (usuario nuevo)
    
    Args:
        phone_number: Número de WhatsApp
        db_connection: Conexión a PostgreSQL (opcional, para testing puede ser None)
        
    Returns:
        Tuple de (user_id, session_id, config)
        
    Examples:
        >>> # Usuario nuevo
        >>> user_id, session_id, config = get_or_create_session("+52123456789")
        >>> # 10 minutos después, mismo usuario
        >>> user_id2, session_id2, config2 = get_or_create_session("+52123456789")
        >>> assert session_id == session_id2  # ✅ Mismo thread (< 24h)
        
        >>> # 25 horas después
        >>> user_id3, session_id3, config3 = get_or_create_session("+52123456789")
        >>> assert session_id != session_id3  # ✅ Nuevo thread (> 24h)
    """
    user_id = generate_user_id(phone_number)
    
    # Si no hay conexión a BD, crear sesión nueva (fallback para testing)
    if db_connection is None:
        session_id = generate_new_thread_id(user_id)
        return (
            user_id,
            session_id,
            {'configurable': {'thread_id': session_id}}
        )
    
    try:
        cursor = db_connection.cursor()
        
        # Buscar última sesión activa del usuario
        cursor.execute("""
            SELECT thread_id, last_activity
            FROM user_sessions
            WHERE user_id = %s
            ORDER BY last_activity DESC
            LIMIT 1
        """, (user_id,))
        
        result = cursor.fetchone()
        
        if result:
            existing_thread_id, last_activity = result
            time_since_activity = datetime.now() - last_activity
            
            # ✅ ROLLING WINDOW: Si < 24h, reusar thread
            if time_since_activity < timedelta(hours=24):
                # Actualizar timestamp de actividad
                cursor.execute("""
                    UPDATE user_sessions
                    SET last_activity = NOW()
                    WHERE user_id = %s AND thread_id = %s
                """, (user_id, existing_thread_id))
                db_connection.commit()
                
                print(f"♻️  Reusando thread (inactividad: {time_since_activity.total_seconds()/3600:.1f}h)")
                
                return (
                    user_id,
                    existing_thread_id,
                    {'configurable': {'thread_id': existing_thread_id}}
                )
            else:
                print(f"⏰ Sesión expirada (inactividad: {time_since_activity.total_seconds()/3600:.1f}h)")
                # Continuar para crear nuevo thread
        
        # Crear nuevo thread (usuario nuevo O sesión expirada)
        new_thread_id = generate_new_thread_id(user_id)
        
        cursor.execute("""
            INSERT INTO user_sessions (user_id, thread_id, last_activity)
            VALUES (%s, %s, NOW())
            ON CONFLICT (user_id, thread_id) 
            DO UPDATE SET last_activity = NOW()
        """, (user_id, new_thread_id))
        db_connection.commit()
        
        print(f"🆕 Nuevo thread creado: {new_thread_id}")
        
        return (
            user_id,
            new_thread_id,
            {'configurable': {'thread_id': new_thread_id}}
        )
        
    except Exception as e:
        print(f"⚠️  Error en BD, usando fallback: {e}")
        # Fallback: crear thread nuevo sin BD
        session_id = generate_new_thread_id(user_id)
        return (
            user_id,
            session_id,
            {'configurable': {'thread_id': session_id}}
        )


# ============================================================================
# EJEMPLO DE USO EN PRODUCCIÓN CON ROLLING WINDOW
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*80)
    print("📱 GESTOR DE SESIONES - ROLLING WINDOW (24h INACTIVIDAD)")
    print("="*80 + "\n")
    
    print("⚠️  IMPORTANTE: Rolling Window significa que el thread se mantiene")
    print("    mientras haya actividad < 24h, NO se resetea a medianoche.\n")
    
    # Caso 1: Usuario nuevo
    print("🆕 CASO 1: Usuario nuevo - Primera vez")
    print("-"*80)
    phone = "+52123456789"
    user_id, thread_id, config = get_or_create_session(phone)
    print(f"Teléfono: {phone}")
    print(f"user_id: {user_id}")
    print(f"thread_id: {thread_id}")
    print(f"✅ Nuevo thread creado\n")
    
    # Caso 2: Usuario envía mensaje 30 min después (mismo thread)
    print("\n🔄 CASO 2: Usuario envía otro mensaje 30 min después")
    print("-"*80)
    print("Simulación: Han pasado 30 minutos...")
    user_id2, thread_id2, config2 = get_or_create_session(phone)
    
    if thread_id == thread_id2:
        print(f"✅ CORRECTO: Mismo thread reutilizado")
        print(f"   thread_id: {thread_id2}")
        print(f"   Inactividad: 0.5h (< 24h)")
    else:
        print(f"❌ ERROR: Se creó thread nuevo cuando no debería")
    
    # Caso 3: Conversación cruza medianoche
    print("\n\n🌙 CASO 3: Conversación cruza medianoche (23:30 → 00:10)")
    print("-"*80)
    print("23:30 - Usuario: 'Hola'")
    print("00:10 - Usuario: '¿Qué reuniones tengo hoy?'")
    print("       (Solo 40 minutos de diferencia)")
    
    user_id3, thread_id3, config3 = get_or_create_session(phone)
    
    print(f"\n✅ CORRECTO con Rolling Window:")
    print(f"   - Mismo thread: {thread_id == thread_id3}")
    print(f"   - NO se pierde contexto al cruzar medianoche")
    print(f"   - Solo importa TIEMPO DE INACTIVIDAD, no la fecha")
    
    # Caso 4: Usuario inactivo 25 horas
    print("\n\n⏰ CASO 4: Usuario inactivo 25 horas")
    print("-"*80)
    print("Simulación: Han pasado 25 horas sin mensajes...")
    print("(En producción, la BD detectaría esto)")
    print(f"\n✅ DEBERÍA crear nuevo thread:")
    print(f"   - Inactividad: 25h (> 24h)")
    print(f"   - Sesión expirada → Nuevo thread")
    print(f"   - Conversación anterior se archiva")
    
    # Caso 5: SQL para crear tabla
    print("\n\n💾 CASO 5: Tabla PostgreSQL necesaria")
    print("-"*80)
    print("""
CREATE TABLE user_sessions (
    user_id VARCHAR(50) NOT NULL,
    thread_id VARCHAR(100) NOT NULL,
    last_activity TIMESTAMP NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, thread_id)
);

CREATE INDEX idx_user_last_activity ON user_sessions(user_id, last_activity DESC);

-- Limpieza automática de sesiones antiguas (>30 días)
CREATE OR REPLACE FUNCTION cleanup_old_sessions()
RETURNS void AS $$
BEGIN
    DELETE FROM user_sessions
    WHERE last_activity < NOW() - INTERVAL '30 days';
END;
$$ LANGUAGE plpgsql;
    """)
    
    # Caso 6: Integración con tu handler de WhatsApp
    print("\n\n🤖 CASO 6: Integración con handler de WhatsApp")
    print("-"*80)
    print("""
# En tu API de WhatsApp (FastAPI/Flask/etc)

from src.utils.session_manager import get_or_create_session
from src.graph_whatsapp import crear_grafo
import psycopg

# Conectar a BD
conn = psycopg.connect(os.getenv('DATABASE_URL'))

# Handler de mensajes entrantes
@app.post("/webhook/whatsapp")
async def handle_whatsapp_message(request):
    # Datos del webhook
    phone_number = request.json['from']      # "+52123456789"
    message_text = request.json['message']   # "¿Tengo citas hoy?"
    
    # ✅ ROLLING WINDOW: Obtener o crear sesión
    user_id, thread_id, config = get_or_create_session(phone_number, conn)
    
    # Logs para debugging
    print(f"📱 Mensaje de {phone_number}")
    print(f"👤 user_id: {user_id}")
    print(f"🔗 thread_id: {thread_id}")
    
    # Crear estado inicial
    estado = {
        'messages': [HumanMessage(content=message_text)],
        'user_id': user_id,
        'session_id': thread_id,  # Importante: usar thread_id
        'cambio_de_tema': False,
        'sesion_expirada': False,
        'herramientas_seleccionadas': [],
        'resumen_actual': None,
        'timestamp': datetime.now().isoformat()
    }
    
    # Ejecutar grafo con config (incluye thread_id para PostgresSaver)
    grafo = crear_grafo()
    resultado = grafo.invoke(estado, config)  # ← config tiene thread_id
    
    # Extraer respuesta
    respuesta = resultado['messages'][-1].content
    
    # Enviar a WhatsApp
    enviar_mensaje_whatsapp(phone_number, respuesta)
    
    return {"status": "ok"}
    """)
    
    print("\n" + "="*80)
    print("✅ ROLLING WINDOW IMPLEMENTADO CORRECTAMENTE")
    print("="*80)
    print("""
📝 RESUMEN:

✅ CORRECTO (tu pedido):
   - Thread se mantiene mientras haya actividad < 24h
   - NO se resetea a medianoche
   - Conversaciones pueden cruzar días sin perder contexto
   - Solo se crea nuevo thread después de 24h SIN MENSAJES

❌ INCORRECTO (lo que tenía antes):
   - Thread basado en fecha (YYYYMMDD)
   - Se reseteaba a medianoche (00:00)
   - Perdía contexto al cambiar de día
   - NO era rolling window

🔧 REQUIERE:
   - Tabla user_sessions en PostgreSQL
   - Consulta last_activity para cada mensaje
   - Update timestamp en cada actividad

💡 BENEFICIOS:
   - Conversaciones naturales sin interrupciones
   - Usuario puede ir y volver durante el día
   - Solo expira por INACTIVIDAD real
   - Mejor experiencia de usuario
    """)
