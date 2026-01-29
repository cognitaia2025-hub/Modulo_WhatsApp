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
from psycopg.types.json import Json
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
    Incluye información de doctor si aplica (ETAPA 1).
    
    Args:
        phone_number: Número en formato internacional
        
    Returns:
        Diccionario con datos del usuario o None si no existe
    """
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                # Consulta completa con LEFT JOIN a doctores
                cur.execute("""
                    SELECT 
                        u.id, u.phone_number, u.display_name, u.es_admin,
                        u.timezone, u.preferencias, u.created_at, u.last_seen,
                        u.tipo_usuario, u.email, u.is_active,
                        d.id as doctor_id, d.nombre_completo, d.especialidad
                    FROM usuarios u
                    LEFT JOIN doctores d ON d.phone_number = u.phone_number
                    WHERE u.phone_number = %s
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
                        "last_seen": result[7],
                        "tipo_usuario": result[8] or "paciente_externo",
                        "email": result[9],
                        "is_active": result[10] if result[10] is not None else True,
                        "doctor_id": result[11],
                        "doctor_nombre": result[12],
                        "especialidad": result[13]
                    }
                return None
                
    except Exception as e:
        logger.error(f"❌ Error consultando usuario en BD: {e}")
        return None


def crear_usuario_nuevo(phone_number: str) -> Dict[str, Any]:
    """
    Crea un nuevo registro de usuario en BD (ETAPA 1: auto-registro).
    Por defecto se registra como 'paciente_externo'.
    
    Args:
        phone_number: Número en formato internacional
        
    Returns:
        Diccionario con datos del usuario creado
    """
    try:
        # Determinar si es admin por número configurado
        es_admin = (phone_number == ADMIN_PHONE_NUMBER)
        
        # Determinar tipo de usuario
        tipo_usuario = "admin" if es_admin else "paciente_externo"
        
        display_name = "Administrador" if es_admin else "Usuario Nuevo"
        
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO usuarios (
                        phone_number, display_name, es_admin, tipo_usuario,
                        is_active, timezone, preferencias
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, phone_number, display_name, es_admin, 
                              tipo_usuario, is_active, timezone, preferencias, created_at
                """, (
                    phone_number,
                    display_name,
                    es_admin,
                    tipo_usuario,
                    True,
                    "America/Tijuana",
                    Json({"primer_uso": True, "auto_registrado": True})
                ))
                
                result = cur.fetchone()
                if result:
                    logger.info(f"✅ Usuario nuevo creado: {phone_number} (Tipo: {tipo_usuario})")
                    return {
                        "id": result[0],
                        "phone_number": result[1],
                        "display_name": result[2],
                        "es_admin": result[3],
                        "tipo_usuario": result[4],
                        "is_active": result[5],
                        "timezone": result[6],
                        "preferencias": result[7],
                        "created_at": result[8],
                        "last_seen": datetime.now(),
                        "doctor_id": None,
                        "doctor_nombre": None,
                        "especialidad": None
                    }
                    
    except Exception as e:
        logger.error(f"❌ Error creando usuario nuevo: {e}")
        # Devolver usuario por defecto en caso de error
        return {
            "id": None,
            "phone_number": phone_number,
            "display_name": "Usuario Temporal",
            "es_admin": (phone_number == ADMIN_PHONE_NUMBER),
            "tipo_usuario": "admin" if (phone_number == ADMIN_PHONE_NUMBER) else "paciente_externo",
            "is_active": True,
            "timezone": "America/Tijuana",
            "preferencias": {},
            "created_at": datetime.now(),
            "last_seen": datetime.now(),
            "doctor_id": None,
            "doctor_nombre": None,
            "especialidad": None
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
        
        # Cargar datos en estado (ETAPA 1)
        state["user_id"] = phone_number
        state["es_admin"] = usuario_existente["es_admin"] 
        state["usuario_info"] = usuario_existente
        state["usuario_registrado"] = True
        state["tipo_usuario"] = usuario_existente.get("tipo_usuario", "paciente_externo")
        state["doctor_id"] = usuario_existente.get("doctor_id")
        state["paciente_id"] = None  # Se carga en otro nodo si es necesario
        
        # Actualizar última actividad
        actualizar_ultima_actividad(phone_number)
        
    else:
        # Usuario nuevo - auto-registro (ETAPA 1)
        logger.info(f"    🆕 Usuario NUEVO - Creando registro automático")
        
        nuevo_usuario = crear_usuario_nuevo(phone_number)
        
        # Cargar datos en estado (ETAPA 1)
        state["user_id"] = phone_number
        state["es_admin"] = nuevo_usuario["es_admin"]
        state["usuario_info"] = nuevo_usuario  
        state["usuario_registrado"] = False
        state["tipo_usuario"] = nuevo_usuario.get("tipo_usuario", "paciente_externo")
        state["doctor_id"] = nuevo_usuario.get("doctor_id")
        state["paciente_id"] = None
    
    # 3. Log final del estado de identificación (ETAPA 1)
    tipo_emoji = {
        "admin": "👑",
        "doctor": "👨‍⚕️",
        "personal": "👤",
        "paciente_externo": "🧑"
    }
    emoji = tipo_emoji.get(state["tipo_usuario"], "👤")
    
    registro_status = "Existente" if state["usuario_registrado"] else "Nuevo"
    
    logger.info(f"    🎯 Identificación completa:")
    logger.info(f"       • Tipo: {emoji} {state['tipo_usuario']}")
    logger.info(f"       • Estado: {registro_status}")
    logger.info(f"       • Nombre: {state['usuario_info']['display_name']}")
    if state["doctor_id"]:
        logger.info(f"       • Doctor ID: {state['doctor_id']}")
        logger.info(f"       • Especialidad: {state['usuario_info'].get('especialidad', 'N/A')}")
    
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
            "tipo_usuario": "admin",
            "timezone": "America/Tijuana",
            "preferencias": {},
            "doctor_id": None
        }
        state["usuario_registrado"] = False
        state["tipo_usuario"] = "admin"
        state["doctor_id"] = None
        state["paciente_id"] = None
        
        return state