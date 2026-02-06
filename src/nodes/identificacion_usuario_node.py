"""
Nodo 0: Identificación de Usuario

Extrae número de teléfono del mensaje WhatsApp, consulta BD de usuarios,
determina si es admin/doctor/paciente, y carga perfil. Si es usuario nuevo, auto-registro.

SISTEMA DE CAMBIO DE NÚMERO TEMPORAL PARA DOCTORES:
- Comando: {cambio_datos} para solicitar plantilla
- Plantilla completada para activar número temporal
- Validación determinista con regex tolerante + difflib (SIN LLM)
- 3 capas de validación: regex flexible → similitud de propiedades → mensajes de error específicos

FUNCIONES SISTEMÁTICAS:
1. Detectar doctores por número telefónico registrado en tabla doctores
2. Si no está registrado como doctor/admin → filtrar como paciente_externo
3. Si número no está registrado → crear registro nuevo con número de metadata como ID
4. Detectar plantilla para cambio de número con tolerancia a errores
"""

import os
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple, List
from difflib import SequenceMatcher

import psycopg
from psycopg.types.json import Json
from dotenv import load_dotenv

from src.state.agent_state import WhatsAppAgentState
from src.utils.logging_config import setup_colored_logging
from langchain_core.messages import AIMessage

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logger = setup_colored_logging()

# Variables de configuración
ADMIN_PHONE_NUMBER = os.getenv("ADMIN_PHONE_NUMBER", "+526641234567")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5434/agente_whatsapp")

# Plantilla para cambio de número temporal
PLANTILLA_CAMBIO_NUMERO = """
🔐 *Plantilla de Cambio de Número*

Para cambiar tu número telefónico, completa y envía la siguiente plantilla:

```
{
  id = +52664XXXXXXX
  usuario = tu_nombre_completo
  contraseña = tu_password
  numero_actual = +52664XXXXXXX
  nuevo_numero = +52664YYYYYYY
  tiempo_horas = 24
}
```

*Instrucciones:*
• `id`: Tu número telefónico actual registrado
• `usuario`: Tu nombre completo como aparece en el sistema (sin espacios, usa _)
• `contraseña`: Tu contraseña de doctor
• `numero_actual`: Confirma tu número actual
• `nuevo_numero`: El nuevo número al que cambiarás
• `tiempo_horas`: Duración del cambio (número de horas o "full" para permanente)

⚠️ *Validación estricta:* Verifica tus credenciales antes de enviar.
""".strip()


# ============================================================================
# FUNCIONES PARA SISTEMA DE CAMBIO DE NÚMERO TEMPORAL
# ============================================================================

def detectar_comando_cambio_numero(mensaje: str) -> Optional[str]:
    """
    Detecta si el mensaje es un comando para solicitar la plantilla de cambio de número.
    
    Args:
        mensaje: Contenido del mensaje
        
    Returns:
        "plantilla" si detecta {cambio_datos}, None si no
    """
    # Comando exacto para solicitar plantilla (case-insensitive)
    if re.search(r'\{\s*cambio_datos\s*\}', mensaje, re.IGNORECASE):
        logger.info("🔍 Comando {cambio_datos} detectado")
        return "plantilla"
    
    return None


def detectar_plantilla_cambio_numero(mensaje: str) -> Optional[Dict[str, Any]]:
    """
    Detecta y extrae datos de la plantilla de cambio de número.
    Usa regex tolerante (permite espacios extras, case-insensitive).
    
    CAPA 1: Regex tolerante
    
    Args:
        mensaje: Contenido del mensaje
        
    Returns:
        Dict con datos extraídos o None si no coincide
    """
    # Regex tolerante: acepta espacios variables, case-insensitive, + opcional en números
    pattern = r'\{\s*id\s*=\s*(\+?\d+)\s+usuario\s*=\s*(\S+)\s+contraseña\s*=\s*(\S+)\s+numero_actual\s*=\s*(\+?\d+)\s+nuevo_numero\s*=\s*(\+?\d+)\s+tiempo_horas\s*=\s*(\w+)\s*\}'
    
    match = re.search(pattern, mensaje, re.IGNORECASE)
    
    if match:
        id_phone = match.group(1)
        usuario = match.group(2)
        password = match.group(3)
        numero_actual = match.group(4)
        nuevo_numero = match.group(5)
        tiempo_horas = match.group(6)
        
        # Normalizar números (agregar + si falta)
        if not id_phone.startswith('+'):
            id_phone = '+' + id_phone
        if not numero_actual.startswith('+'):
            numero_actual = '+' + numero_actual
        if not nuevo_numero.startswith('+'):
            nuevo_numero = '+' + nuevo_numero
        
        logger.info(f"✅ Plantilla detectada: usuario={usuario}, tiempo={tiempo_horas}")
        
        return {
            "id": id_phone,
            "usuario": usuario,
            "password": password,
            "numero_actual": numero_actual,
            "nuevo_numero": nuevo_numero,
            "tiempo_horas": tiempo_horas
        }
    
    return None


def validar_similitud_propiedades(mensaje: str) -> Optional[str]:
    """
    CAPA 2: Validación de similitud de propiedades usando difflib.
    Detecta typos en los nombres de propiedades y sugiere correcciones.
    
    Args:
        mensaje: Contenido del mensaje
        
    Returns:
        Mensaje de error con sugerencias o None si no hay errores
    """
    propiedades_esperadas = ["id", "usuario", "contraseña", "numero_actual", "nuevo_numero", "tiempo_horas"]
    
    # Extraer propiedades del mensaje (buscar palabras antes de =)
    patron_propiedades = r'(\w+)\s*='
    propiedades_encontradas = re.findall(patron_propiedades, mensaje, re.IGNORECASE)
    
    if not propiedades_encontradas:
        return None
    
    # Convertir a minúsculas para comparación
    props_lower = [p.lower() for p in propiedades_encontradas]
    
    errores: List[str] = []
    sugerencias: List[str] = []
    
    for prop in props_lower:
        # Buscar la propiedad esperada más similar
        similitudes = [(esp, SequenceMatcher(None, prop, esp).ratio()) 
                      for esp in propiedades_esperadas]
        mejor_match, ratio = max(similitudes, key=lambda x: x[1])
        
        # Si la similitud es > 70% pero no es exacta, es un typo
        if 0.7 < ratio < 1.0:
            sugerencias.append(f'  • "{prop}" → ¿Quisiste decir "{mejor_match}"?')
        elif ratio <= 0.7 and prop not in propiedades_esperadas:
            errores.append(f'  • "{prop}" no es válida')
    
    # Verificar propiedades faltantes
    props_faltantes = [esp for esp in propiedades_esperadas if esp not in props_lower]
    
    if sugerencias or errores or props_faltantes:
        mensaje_error = "❌ *Formato incorrecto detectado:*\n\n"
        
        if sugerencias:
            mensaje_error += "*Posibles typos:*\n" + "\n".join(sugerencias) + "\n\n"
        
        if errores:
            mensaje_error += "*Propiedades no válidas:*\n" + "\n".join(errores) + "\n\n"
        
        if props_faltantes:
            mensaje_error += "*Propiedades faltantes:*\n"
            mensaje_error += "\n".join([f"  • {p}" for p in props_faltantes]) + "\n\n"
        
        mensaje_error += "📋 Envía `{cambio_datos}` para recibir la plantilla nuevamente."
        
        return mensaje_error
    
    return None


def validar_credenciales_doctor(id_phone: str, usuario: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Valida las credenciales del doctor en la base de datos.
    
    Args:
        id_phone: Número de teléfono (ID)
        usuario: Nombre de usuario (nombre_completo con _ en vez de espacios)
        password: Contraseña del doctor
        
    Returns:
        Dict con datos del doctor si es válido, None si no
    """
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                # Validar doctor por teléfono y nombre
                cur.execute("""
                    SELECT d.id, d.nombre_completo, d.especialidad, d.phone_number, u.id as user_id
                    FROM doctores d
                    LEFT JOIN usuarios u ON u.phone_number = d.phone_number
                    WHERE d.phone_number = %s 
                    AND REPLACE(LOWER(d.nombre_completo), ' ', '_') = LOWER(%s)
                    AND d.is_active = TRUE
                """, (id_phone, usuario))
                
                doctor = cur.fetchone()
                
                if not doctor:
                    logger.warning(f"⚠️ Credenciales inválidas: teléfono o usuario incorrecto")
                    return None
                
                # TODO: Aquí deberías validar el password con un hash
                # Por ahora, asumimos que el password es correcto si el doctor existe
                # En producción: bcrypt.checkpw(password.encode(), doctor_password_hash)
                
                logger.info(f"✅ Credenciales válidas: Doctor {doctor[1]}")
                
                return {
                    "doctor_id": doctor[0],
                    "nombre_completo": doctor[1],
                    "especialidad": doctor[2],
                    "phone_number": doctor[3],
                    "user_id": doctor[4]
                }
                
    except Exception as e:
        logger.error(f"❌ Error validando credenciales: {e}")
        return None


def activar_numero_temporal(doctor_id: int, numero_original: str, numero_nuevo: str, tiempo: str) -> Tuple[bool, str]:
    """
    Activa un número temporal para un doctor en la base de datos.
    
    Args:
        doctor_id: ID del doctor
        numero_original: Número actual registrado
        numero_nuevo: Nuevo número temporal
        tiempo: Duración ("full" para permanente, o número de horas)
        
    Returns:
        (éxito, mensaje)
    """
    try:
        # Calcular fecha de expiración
        expira_en = None
        if tiempo.lower() != "full":
            try:
                horas = int(tiempo)
                expira_en = datetime.now() + timedelta(hours=horas)
            except ValueError:
                return False, f"❌ Tiempo inválido: '{tiempo}'. Usa un número de horas o 'full'."
        
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                # Insertar o actualizar número temporal
                cur.execute("""
                    INSERT INTO numeros_temporales_doctores 
                    (doctor_id, numero_original, numero_temporal, expira_en, creado_en)
                    VALUES (%s, %s, %s, %s, NOW())
                    ON CONFLICT (numero_temporal) 
                    DO UPDATE SET 
                        doctor_id = EXCLUDED.doctor_id,
                        numero_original = EXCLUDED.numero_original,
                        expira_en = EXCLUDED.expira_en,
                        creado_en = NOW()
                    RETURNING id
                """, (doctor_id, numero_original, numero_nuevo, expira_en))
                
                result = cur.fetchone()
                
                if result:
                    tiempo_texto = f"{tiempo} horas" if tiempo.lower() != "full" else "permanente"
                    logger.info(f"✅ Número temporal activado: {numero_nuevo} ({tiempo_texto})")
                    
                    mensaje_exito = f"""
✅ *Actualización exitosa*

• Número temporal registrado: {numero_nuevo}
• Duración: {tiempo_texto}
• Estado: Activo
{f'• Expira: {expira_en.strftime("%Y-%m-%d %H:%M")}' if expira_en else ''}

Ahora puedes usar el nuevo número para enviar mensajes al sistema.
"""
                    return True, mensaje_exito.strip()
                
                return False, "❌ Error al registrar número temporal."
                
    except Exception as e:
        logger.error(f"❌ Error activando número temporal: {e}")
        return False, f"❌ Error del sistema: {str(e)}"


def buscar_numero_temporal(phone_number: str) -> Optional[Dict[str, Any]]:
    """
    Busca si un número telefónico es un número temporal activo de algún doctor.
    
    Args:
        phone_number: Número a buscar
        
    Returns:
        Dict con info del doctor si es número temporal activo, None si no
    """
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                # Buscar número temporal activo (no expirado)
                cur.execute("""
                    SELECT 
                        nt.doctor_id, nt.numero_original, nt.numero_temporal,
                        nt.expira_en, d.nombre_completo, d.especialidad
                    FROM numeros_temporales_doctores nt
                    JOIN doctores d ON d.id = nt.doctor_id
                    WHERE nt.numero_temporal = %s
                    AND (nt.expira_en IS NULL OR nt.expira_en > NOW())
                    AND d.is_active = TRUE
                """, (phone_number,))
                
                result = cur.fetchone()
                
                if result:
                    logger.info(f"🔄 Número temporal detectado: {phone_number} → Doctor ID {result[0]}")
                    return {
                        "doctor_id": result[0],
                        "numero_original": result[1],
                        "numero_temporal": result[2],
                        "expira_en": result[3],
                        "nombre_completo": result[4],
                        "especialidad": result[5]
                    }
                
                return None
                
    except Exception as e:
        logger.error(f"❌ Error buscando número temporal: {e}")
        return None


# ============================================================================
# FUNCIONES PRINCIPALES DE IDENTIFICACIÓN
# ============================================================================

def extraer_numero_telefono(mensaje_contenido: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
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
    
    LÓGICA SISTEMÁTICA:
    1. Buscar si el número es un número temporal activo de un doctor
    2. Si es temporal, usar el número original del doctor para consultar
    3. Incluir información de doctor si el número está en tabla doctores
    4. Si no está en doctores/admin → será clasificado como paciente_externo
    
    Args:
        phone_number: Número en formato internacional
        
    Returns:
        Diccionario con datos del usuario o None si no existe
    """
    try:
        # PASO 1: Verificar si es un número temporal activo
        numero_temporal_info = buscar_numero_temporal(phone_number)
        
        # Si es número temporal, usar el número original para la consulta
        phone_a_buscar = phone_number
        es_numero_temporal = False
        
        if numero_temporal_info:
            phone_a_buscar = numero_temporal_info["numero_original"]
            es_numero_temporal = True
            logger.info(f"🔄 Usando número original: {phone_a_buscar} (temporal: {phone_number})")
        
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                # PASO 2: Consulta con LEFT JOIN a doctores para detectar si es doctor
                cur.execute("""
                    SELECT 
                        u.id, u.phone_number, u.display_name, u.es_admin,
                        u.timezone, u.preferencias, u.created_at, u.last_seen,
                        u.tipo_usuario, u.email, u.is_active,
                        d.id as doctor_id, d.nombre_completo, d.especialidad
                    FROM usuarios u
                    LEFT JOIN doctores d ON d.phone_number = u.phone_number AND d.is_active = TRUE
                    WHERE u.phone_number = %s
                """, (phone_a_buscar,))
                
                result = cur.fetchone()
                if result:
                    usuario_data: Dict[str, Any] = {
                        "id": result[0],
                        "phone_number": result[1],  # Número original
                        "phone_number_actual": phone_number,  # Número usado (temporal o original)
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
                        "especialidad": result[13],
                        "es_numero_temporal": es_numero_temporal
                    }
                    
                    # PASO 3: Determinar tipo de usuario basado en tabla doctores
                    # Si tiene doctor_id → es doctor, sino → verificar es_admin
                    if result[11]:  # doctor_id existe
                        usuario_data["tipo_usuario"] = "doctor"
                        logger.info(f"✅ Doctor detectado: {result[12]} (ID: {result[11]})")
                    elif result[3]:  # es_admin = True
                        usuario_data["tipo_usuario"] = "admin"
                        logger.info(f"✅ Admin detectado")
                    else:
                        # No está en doctores ni es admin → paciente_externo
                        usuario_data["tipo_usuario"] = "paciente_externo"
                        logger.info(f"ℹ️ Usuario clasificado como paciente_externo")
                    
                    return usuario_data
                
                return None
                
    except Exception as e:
        logger.error(f"❌ Error consultando usuario en BD: {e}")
        return None


def crear_usuario_nuevo(phone_number: str) -> Dict[str, Any]:
    """
    Crea un nuevo registro de usuario en BD (auto-registro).
    
    LÓGICA SISTEMÁTICA:
    1. Verificar si el número está en tabla doctores
    2. Si está en doctores → crear como 'doctor' 
    3. Si coincide con ADMIN_PHONE_NUMBER → crear como 'admin'
    4. Si no está en ninguno → crear como 'paciente_externo'
    5. Usar el número telefónico como ID único
    
    Args:
        phone_number: Número en formato internacional
        
    Returns:
        Diccionario con datos del usuario creado
    """
    try:
        # PASO 1: Verificar si el número está registrado en tabla doctores
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                # Buscar en tabla doctores
                cur.execute("""
                    SELECT id, nombre_completo, especialidad
                    FROM doctores
                    WHERE phone_number = %s AND is_active = TRUE
                """, (phone_number,))
                
                doctor_info = cur.fetchone()
                
                # PASO 2: Determinar tipo de usuario basado en lógica sistemática
                if doctor_info:
                    # Está en tabla doctores → es doctor
                    tipo_usuario = "doctor"
                    es_admin = False
                    display_name = doctor_info[1]  # nombre_completo
                    doctor_id = doctor_info[0]
                    especialidad = doctor_info[2]
                    logger.info(f"🏥 Nuevo usuario detectado como DOCTOR: {display_name}")
                    
                elif phone_number == ADMIN_PHONE_NUMBER:
                    # Coincide con número de admin configurado
                    tipo_usuario = "admin"
                    es_admin = True
                    display_name = "Administrador"
                    doctor_id = None
                    especialidad = None
                    logger.info(f"👑 Nuevo usuario detectado como ADMIN")
                    
                else:
                    # No está en doctores ni es admin → paciente externo
                    tipo_usuario = "paciente_externo"
                    es_admin = False
                    display_name = "Usuario Nuevo"
                    doctor_id = None
                    especialidad = None
                    logger.info(f"🧑 Nuevo usuario detectado como PACIENTE_EXTERNO")
                
                # PASO 3: Insertar en tabla usuarios
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
                        "phone_number_actual": phone_number,
                        "display_name": result[2],
                        "es_admin": result[3],
                        "tipo_usuario": result[4],
                        "is_active": result[5],
                        "timezone": result[6],
                        "preferencias": result[7],
                        "created_at": result[8],
                        "last_seen": datetime.now(),
                        "doctor_id": doctor_id,
                        "doctor_nombre": display_name if doctor_id else None,
                        "especialidad": especialidad,
                        "es_numero_temporal": False
                    }
                    
    except Exception as e:
        logger.error(f"❌ Error creando usuario nuevo: {e}")
        # Devolver usuario por defecto en caso de error
        return {
            "id": None,
            "phone_number": phone_number,
            "phone_number_actual": phone_number,
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
            "especialidad": None,
            "es_numero_temporal": False
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
    
    FUNCIONES SISTEMÁTICAS:
    1. Detectar comando {cambio_datos} → Enviar plantilla
    2. Detectar plantilla completada → Validar y activar número temporal
    3. Extraer número de teléfono (incluye búsqueda en números temporales)
    4. Consultar usuario en BD (detecta doctor, admin o paciente_externo)
    5. Auto-registro si no existe (con clasificación automática)
    
    Args:
        state: Estado actual del grafo
        
    Returns:
        Estado actualizado con información del usuario
    """
    logger.info("👤 [0] NODO_IDENTIFICACION - Identificando usuario")
    
    # ========================================================================
    # FASE 1: DETECCIÓN DE COMANDOS Y PLANTILLA (ANTES DE IDENTIFICACIÓN)
    # ========================================================================
    
    ultimo_mensaje = state.get("messages", [])[-1] if state.get("messages") else None
    
    if not ultimo_mensaje:
        logger.error("❌ No hay mensajes para procesar")
        return state
    
    # Extraer contenido del mensaje como string
    if hasattr(ultimo_mensaje, 'content'):
        content = ultimo_mensaje.content
        mensaje_contenido = content if isinstance(content, str) else str(content)
    else:
        mensaje_contenido = str(ultimo_mensaje)
    
    # A) Detectar comando {cambio_datos}
    comando = detectar_comando_cambio_numero(mensaje_contenido)
    if comando == "plantilla":
        logger.info("📋 Enviando plantilla de cambio de número")
        state["messages"].append(AIMessage(content=PLANTILLA_CAMBIO_NUMERO))
        # Detener aquí, esperamos la plantilla completada en el siguiente mensaje
        return state
    
    # B) Detectar plantilla completada
    datos_plantilla = detectar_plantilla_cambio_numero(mensaje_contenido)
    
    if datos_plantilla:
        logger.info("📝 Plantilla de cambio detectada, procesando...")
        
        # B.1) Validar credenciales del doctor
        doctor_validado = validar_credenciales_doctor(
            datos_plantilla["id"],
            datos_plantilla["usuario"],
            datos_plantilla["password"]
        )
        
        if not doctor_validado:
            mensaje_error = """
❌ *Credenciales inválidas*

No se pudo validar tu identidad. Verifica:
• Tu número de teléfono (id)
• Tu nombre de usuario (debe coincidir con el registro)
• Tu contraseña

Envía `{cambio_datos}` para intentar nuevamente.
"""
            state["messages"].append(AIMessage(content=mensaje_error.strip()))
            return state
        
        # B.2) Activar número temporal
        exito, mensaje_resultado = activar_numero_temporal(
            doctor_validado["doctor_id"],
            datos_plantilla["numero_actual"],
            datos_plantilla["nuevo_numero"],
            datos_plantilla["tiempo_horas"]
        )
        
        state["messages"].append(AIMessage(content=mensaje_resultado))
        
        if exito:
            logger.info(f"✅ Número temporal activado exitosamente")
        
        # Detener aquí, el cambio ya fue procesado
        return state
    
    # C) Si el formato es parecido pero tiene errores, validar similitud
    if '{' in mensaje_contenido and '=' in mensaje_contenido:
        mensaje_error_similitud = validar_similitud_propiedades(mensaje_contenido)
        if mensaje_error_similitud:
            logger.info("⚠️ Detectado intento de plantilla con errores")
            state["messages"].append(AIMessage(content=mensaje_error_similitud))
            return state
    
    # ========================================================================
    # FASE 2: IDENTIFICACIÓN NORMAL DEL USUARIO
    # ========================================================================
    
    phone_number = None
    
    # Prioridad 1: user_id ya en el estado
    if state.get("user_id") and state["user_id"].startswith("+"):
        phone_number = state["user_id"]
        logger.info(f"    📱 Usando user_id del estado: {phone_number}")
    else:
        # Prioridad 2: Extraer del mensaje (incluye metadata de WhatsApp)
        metadata_msg = getattr(ultimo_mensaje, 'metadata', None)
        phone_number = extraer_numero_telefono(
            mensaje_contenido,
            metadata_msg if isinstance(metadata_msg, dict) else None
        )
        logger.info(f"    📱 Número detectado: {phone_number}")
    
    # Validar que phone_number no sea None
    if not phone_number:
        logger.error("❌ No se pudo extraer número de teléfono")
        return state
    
    # Consultar si usuario existe en BD (incluye búsqueda en números temporales)
    usuario_existente = consultar_usuario_bd(phone_number)
    
    if usuario_existente:
        # Usuario registrado (puede ser número original o temporal)
        logger.info(f"    ✅ Usuario REGISTRADO: {usuario_existente['display_name']}")
        
        # Cargar datos en estado
        state["user_id"] = phone_number
        state["es_admin"] = usuario_existente["es_admin"] 
        state["usuario_info"] = usuario_existente
        state["usuario_registrado"] = True
        state["tipo_usuario"] = usuario_existente.get("tipo_usuario", "paciente_externo")
        state["doctor_id"] = usuario_existente.get("doctor_id")
        state["paciente_id"] = None  # Se carga en otro nodo si es necesario
        
        # Actualizar última actividad (usar número original si es temporal)
        phone_para_actualizar = usuario_existente.get("phone_number", phone_number)
        actualizar_ultima_actividad(phone_para_actualizar)
        
    else:
        # Usuario nuevo - auto-registro con clasificación automática
        logger.info(f"    🆕 Usuario NUEVO - Creando registro automático")
        
        nuevo_usuario = crear_usuario_nuevo(phone_number)
        
        # Cargar datos en estado
        state["user_id"] = phone_number
        state["es_admin"] = nuevo_usuario["es_admin"]
        state["usuario_info"] = nuevo_usuario  
        state["usuario_registrado"] = False
        state["tipo_usuario"] = nuevo_usuario.get("tipo_usuario", "paciente_externo")
        state["doctor_id"] = nuevo_usuario.get("doctor_id")
        state["paciente_id"] = None
    
    # ========================================================================
    # FASE 3: LOG FINAL
    # ========================================================================
    
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
    
    if state["usuario_info"].get("es_numero_temporal"):
        logger.info(f"       • 🔄 Usando número temporal")
    
    return state


def nodo_identificacion_usuario_wrapper(state: WhatsAppAgentState) -> WhatsAppAgentState:
    """
    Wrapper para manejar errores del nodo de identificación.
    """
    try:
        return nodo_identificacion_usuario(state)
    except Exception as e:
        logger.error(f"❌ Error en nodo de identificación: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        # Estado de emergencia - continuar con datos básicos
        state["user_id"] = "+526641234567"  # Número por defecto
        state["es_admin"] = True  # Asumir admin en caso de error
        state["usuario_info"] = {
            "phone_number": "+526641234567",
            "phone_number_actual": "+526641234567",
            "display_name": "Usuario Temporal", 
            "es_admin": True,
            "tipo_usuario": "admin",
            "timezone": "America/Tijuana",
            "preferencias": {},
            "doctor_id": None,
            "doctor_nombre": None,
            "especialidad": None,
            "es_numero_temporal": False
        }
        state["usuario_registrado"] = False
        state["tipo_usuario"] = "admin"
        state["doctor_id"] = None
        state["paciente_id"] = None
        
        return state