"""
Nodo 0: Identificación de Usuario

Extrae número de teléfono del mensaje WhatsApp, consulta BD de usuarios,
determina si es admin, y carga perfil. Si es usuario nuevo, auto-registro.
"""

import os
import re
import logging
from datetime import datetime
from typing import Optional, Dict, Any

import psycopg
from dotenv import load_dotenv

from src.state.agent_state import WhatsAppAgentState
from src.utils.logging_config import setup_colored_logging

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logger = setup_colored_logging()

# Variables de configuración
ADMIN_PHONE_NUMBER = os.getenv("ADMIN_PHONE_NUMBER", "+526641234567")  # Número del administrador
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5434/agente_whatsapp")


def extraer_numero_telefono(mensaje_contenido: str, metadata: Dict[str, Any] = None) -> Optional[str]:
    """
    Extrae número de teléfono del mensaje WhatsApp.
    
    Args:
        mensaje_contenido: Contenido del mensaje
        metadata: Metadata del mensaje WhatsApp (contiene phone_number)
    
    Returns:
        Número de teléfono en formato internacional (+52664...)
    """
    # Si viene en metadata (caso WhatsApp real)
    if metadata and "phone_number" in metadata:
        phone = metadata["phone_number"]
        if phone.startswith("+"):
            return phone
        else:
            # Agregar código de país México si no tiene
            return f"+52{phone}"
    
    # Fallback: extraer del contenido del mensaje (para testing)
    phone_patterns = [
        r'\+\d{1,4}\d{10}',  # +52664123456
        r'\d{10}',           # 6641234567
        r'\(\d{3}\)\s?\d{3}-?\d{4}'  # (664) 123-4567
    ]
    
    for pattern in phone_patterns:
        match = re.search(pattern, mensaje_contenido)
        if match:
            phone = match.group()
            # Normalizar a formato internacional
            if not phone.startswith("+"):
                phone = f"+52{phone}"
            return phone
    
    # Si no se encuentra, usar un número por defecto para testing
    logger.warning("⚠️  No se pudo extraer número de teléfono, usando default")
    return "+526641234567"


def consultar_usuario_bd(phone_number: str) -> Optional[Dict[str, Any]]:
    """
    Consulta usuario en BD por número de teléfono.
    
    Args:
        phone_number: Número en formato internacional
        
    Returns:
        Diccionario con datos del usuario o None si no existe
    """
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, phone_number, display_name, es_admin, 
                           timezone, preferencias, created_at, last_seen
                    FROM usuarios 
                    WHERE phone_number = %s
                """, (phone_number,))
                
                result = cur.fetchone()
                if result:
                    return {
                        "id": result[0],
                        "phone_number": result[1],
                        "display_name": result[2],
                        "es_admin": result[3],
                        "timezone": result[4] or "America/Tijuana",
                        "preferencias": result[5] or {},
                        "created_at": result[6],
                        "last_seen": result[7]
                    }
                return None
                
    except Exception as e:
        logger.error(f"❌ Error consultando usuario en BD: {e}")
        return None


def crear_usuario_nuevo(phone_number: str) -> Dict[str, Any]:
    """
    Crea un nuevo registro de usuario en BD.
    
    Args:
        phone_number: Número en formato internacional
        
    Returns:
        Diccionario con datos del usuario creado
    """
    try:
        # Determinar si es admin por número configurado
        es_admin = (phone_number == ADMIN_PHONE_NUMBER)
        
        display_name = "Usuario Nuevo"
        if es_admin:
            display_name = "Administrador"
        
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO usuarios (phone_number, display_name, es_admin, timezone, preferencias)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id, phone_number, display_name, es_admin, timezone, preferencias, created_at
                """, (
                    phone_number,
                    display_name, 
                    es_admin,
                    "America/Tijuana",
                    {"primer_uso": True}
                ))
                
                result = cur.fetchone()
                if result:
                    logger.info(f"✅ Usuario nuevo creado: {phone_number} (Admin: {es_admin})")
                    return {
                        "id": result[0],
                        "phone_number": result[1],
                        "display_name": result[2],
                        "es_admin": result[3],
                        "timezone": result[4],
                        "preferencias": result[5],
                        "created_at": result[6],
                        "last_seen": datetime.now()
                    }
                    
    except Exception as e:
        logger.error(f"❌ Error creando usuario nuevo: {e}")
        # Devolver usuario por defecto en caso de error
        return {
            "id": None,
            "phone_number": phone_number,
            "display_name": "Usuario Temporal",
            "es_admin": (phone_number == ADMIN_PHONE_NUMBER),
            "timezone": "America/Tijuana",
            "preferencias": {},
            "created_at": datetime.now(),
            "last_seen": datetime.now()
        }


def actualizar_ultima_actividad(phone_number: str) -> bool:
    """
    Actualiza el timestamp de última actividad del usuario.
    
    Args:
        phone_number: Número del usuario
        
    Returns:
        True si se actualizó correctamente
    """
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE usuarios 
                    SET last_seen = NOW() 
                    WHERE phone_number = %s
                """, (phone_number,))
                
                return cur.rowcount > 0
                
    except Exception as e:
        logger.error(f"❌ Error actualizando última actividad: {e}")
        return False


def nodo_identificacion_usuario(state: WhatsAppAgentState) -> WhatsAppAgentState:
    """
    [0] Nodo de Identificación de Usuario
    
    Extrae número de teléfono del mensaje WhatsApp, consulta BD de usuarios,
    determina permisos de administrador, y carga perfil completo.
    
    Args:
        state: Estado actual del grafo
        
    Returns:
        Estado actualizado con información del usuario
    """
    logger.info("👤 [0] NODO_IDENTIFICACION - Identificando usuario")
    
    # 1. Extraer número de teléfono del último mensaje
    ultimo_mensaje = state.get("messages", [])[-1] if state.get("messages") else None
    
    if not ultimo_mensaje:
        logger.error("❌ No hay mensajes para procesar")
        return state
    
    # Extraer número (en producción vendría de WhatsApp metadata)
    phone_number = extraer_numero_telefono(
        ultimo_mensaje.content if hasattr(ultimo_mensaje, 'content') else str(ultimo_mensaje),
        getattr(ultimo_mensaje, 'metadata', None)
    )
    
    logger.info(f"    📱 Número detectado: {phone_number}")
    
    # 2. Consultar si usuario existe en BD
    usuario_existente = consultar_usuario_bd(phone_number)
    
    if usuario_existente:
        # Usuario registrado
        logger.info(f"    ✅ Usuario REGISTRADO: {usuario_existente['display_name']}")
        
        # Cargar datos en estado
        state["user_id"] = phone_number
        state["es_admin"] = usuario_existente["es_admin"] 
        state["usuario_info"] = usuario_existente
        state["usuario_registrado"] = True
        
        # Actualizar última actividad
        actualizar_ultima_actividad(phone_number)
        
    else:
        # Usuario nuevo - auto-registro
        logger.info(f"    🆕 Usuario NUEVO - Creando registro automático")
        
        nuevo_usuario = crear_usuario_nuevo(phone_number)
        
        # Cargar datos en estado
        state["user_id"] = phone_number
        state["es_admin"] = nuevo_usuario["es_admin"]
        state["usuario_info"] = nuevo_usuario  
        state["usuario_registrado"] = False
    
    # 3. Log final del estado de identificación
    admin_status = "👑 ADMINISTRADOR" if state["es_admin"] else "👤 Usuario"
    registro_status = "Existente" if state["usuario_registrado"] else "Nuevo"
    
    logger.info(f"    🎯 Identificación completa:")
    logger.info(f"       • Tipo: {admin_status}")
    logger.info(f"       • Estado: {registro_status}")
    logger.info(f"       • Nombre: {state['usuario_info']['display_name']}")
    
    return state


def nodo_identificacion_usuario_wrapper(state: WhatsAppAgentState) -> WhatsAppAgentState:
    """
    Wrapper para manejar errores del nodo de identificación.
    """
    try:
        return nodo_identificacion_usuario(state)
    except Exception as e:
        logger.error(f"❌ Error en nodo de identificación: {e}")
        
        # Estado de emergencia - continuar con datos básicos
        state["user_id"] = "+526641234567"  # Número por defecto
        state["es_admin"] = True  # Asumir admin en caso de error
        state["usuario_info"] = {
            "phone_number": "+526641234567",
            "display_name": "Usuario Temporal", 
            "es_admin": True,
            "timezone": "America/Tijuana",
            "preferencias": {}
        }
        state["usuario_registrado"] = False
        
        return state