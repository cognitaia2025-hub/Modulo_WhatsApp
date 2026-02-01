"""
Nodo: Ejecución de Herramientas Médicas (Sin LLM)

Ejecuta herramientas médicas seleccionadas con:
- Validación de permisos (doctor vs paciente)
- Inyección automática de doctor_phone
- Actualización de control_turnos después de agendar
- Manejo robusto de errores

**Sin LLM:** Ejecución determinística
"""

import logging
from typing import Dict, List
from datetime import datetime
import psycopg
import os
from dotenv import load_dotenv
from langgraph.types import Command

from src.state.agent_state import WhatsAppAgentState
from src.medical.tools import MEDICAL_TOOLS
from src.medical.turnos import actualizar_control_turnos
from src.utils.logging_config import (
    log_separator,
    log_node_io
)

load_dotenv()
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5434/agente_whatsapp")

# Herramientas que solo doctores pueden usar
HERRAMIENTAS_SOLO_DOCTOR = [
    "crear_paciente_medico",
    "buscar_pacientes_doctor",
    "modificar_cita_medica",
    "cancelar_cita_medica",
    "confirmar_cita_medica",
    "reprogramar_cita_medica",
    "consultar_historial_paciente",
    "agregar_nota_historial",
    "obtener_citas_doctor",
    "buscar_paciente_por_nombre"
]

# Herramientas que pacientes externos pueden usar
HERRAMIENTAS_PACIENTE_EXTERNO = [
    "consultar_slots_disponibles",
    "agendar_cita_medica_completa"
]

# ==================== CONSTANTES ====================

# Estados conversacionales que requieren saltar ejecución
ESTADOS_FLUJO_ACTIVO = [
    'esperando_confirmacion_medica',
    'recolectando_datos_paciente',
    'recolectando_fecha_cita',
    'recolectando_sintomas'
]


def validar_permiso_herramienta(nombre_herramienta: str, tipo_usuario: str) -> bool:
    """
    Valida si el usuario tiene permiso para usar la herramienta
    
    Args:
        nombre_herramienta: Nombre de la herramienta
        tipo_usuario: Tipo de usuario ('doctor', 'paciente_externo', etc.)
        
    Returns:
        True si tiene permiso, False si no
    """
    # Doctores tienen acceso completo
    if tipo_usuario == "doctor":
        return True
    
    # Pacientes externos solo algunas herramientas
    if tipo_usuario == "paciente_externo":
        return nombre_herramienta in HERRAMIENTAS_PACIENTE_EXTERNO
    
    # Otros tipos de usuario (por ahora no tienen acceso)
    return False


def obtener_doctor_phone_from_state(state: WhatsAppAgentState) -> str:
    """
    Obtiene el teléfono del doctor desde el state
    
    Args:
        state: WhatsAppAgentState
        
    Returns:
        Teléfono del doctor o None
    """
    tipo_usuario = state.get("tipo_usuario", "")
    
    if tipo_usuario == "doctor":
        # El user_id es el teléfono del doctor
        return state.get("user_id", "")
    
    # Si es paciente, no hay doctor_phone (se debe pasar como parámetro)
    return None


def obtener_herramienta_por_nombre(nombre: str):
    """
    Obtiene la función de herramienta por nombre
    
    Args:
        nombre: Nombre de la herramienta
        
    Returns:
        Función de herramienta o None
    """
    for tool in MEDICAL_TOOLS:
        if tool.name == nombre:
            return tool
    return None


def inyectar_doctor_phone_si_necesario(
    nombre_herramienta: str,
    argumentos: Dict,
    doctor_phone: str
) -> Dict:
    """
    Inyecta doctor_phone automáticamente si la herramienta lo requiere
    
    Args:
        nombre_herramienta: Nombre de la herramienta
        argumentos: Argumentos originales
        doctor_phone: Teléfono del doctor
        
    Returns:
        Argumentos con doctor_phone inyectado
    """
    # Si la herramienta requiere doctor_phone y no está en argumentos
    if nombre_herramienta in HERRAMIENTAS_SOLO_DOCTOR:
        if "doctor_phone" not in argumentos and doctor_phone:
            argumentos["doctor_phone"] = doctor_phone
            logger.info(f"  🔧 Inyectado doctor_phone: {doctor_phone}")
    
    return argumentos


def actualizar_turnos_si_es_agendamiento(
    nombre_herramienta: str,
    resultado: str,
    argumentos: Dict
):
    """
    Actualiza control_turnos si la herramienta fue agendar_cita_medica_completa
    
    Args:
        nombre_herramienta: Nombre de la herramienta
        resultado: Resultado de la ejecución
        argumentos: Argumentos usados
    """
    if nombre_herramienta == "agendar_cita_medica_completa":
        # Solo actualizar si fue exitoso
        if "✅" in resultado and "Cita agendada exitosamente" in resultado:
            try:
                # Obtener doctor_id del resultado o argumentos
                doctor_phone = argumentos.get("doctor_phone")
                
                if doctor_phone:
                    # Obtener doctor_id desde BD
                    with psycopg.connect(DATABASE_URL) as conn:
                        with conn.cursor() as cur:
                            cur.execute("""
                                SELECT d.id 
                                FROM doctores d
                                JOIN usuarios u ON d.usuario_id = u.id
                                WHERE u.telefono = %s
                            """, (doctor_phone,))
                            
                            row = cur.fetchone()
                            if row:
                                doctor_id = row[0]
                                
                                # Actualizar control_turnos
                                actualizado = actualizar_control_turnos(doctor_id)
                                
                                if actualizado:
                                    logger.info(f"  ✅ Control de turnos actualizado para doctor {doctor_id}")
                                else:
                                    logger.warning(f"  ⚠️  No se pudo actualizar control_turnos")
            
            except Exception as e:
                logger.error(f"  ❌ Error actualizando turnos: {e}")


def ejecutar_herramienta_con_validaciones(
    nombre_herramienta: str,
    argumentos: Dict,
    tipo_usuario: str,
    doctor_phone: str = None
) -> str:
    """
    Ejecuta una herramienta médica con todas las validaciones
    
    Args:
        nombre_herramienta: Nombre de la herramienta
        argumentos: Argumentos para la herramienta
        tipo_usuario: Tipo de usuario
        doctor_phone: Teléfono del doctor (si aplica)
        
    Returns:
        Resultado de la ejecución
    """
    logger.info(f"  🔧 Ejecutando: {nombre_herramienta}")
    logger.info(f"  📦 Argumentos: {argumentos}")
    
    # 1. Validar permisos
    if not validar_permiso_herramienta(nombre_herramienta, tipo_usuario):
        return f"❌ Error: Usuario tipo '{tipo_usuario}' no tiene permiso para usar '{nombre_herramienta}'"
    
    # 2. Obtener herramienta
    herramienta = obtener_herramienta_por_nombre(nombre_herramienta)
    if not herramienta:
        return f"❌ Error: Herramienta '{nombre_herramienta}' no encontrada"
    
    # 3. Inyectar doctor_phone si es necesario
    argumentos = inyectar_doctor_phone_si_necesario(
        nombre_herramienta,
        argumentos,
        doctor_phone
    )
    
    # 4. Ejecutar herramienta
    try:
        resultado = herramienta.invoke(argumentos)
        
        logger.info(f"  ✅ Ejecución exitosa")
        logger.info(f"  📄 Resultado: {resultado[:200]}...")
        
        # 5. Actualizar turnos si fue agendamiento
        actualizar_turnos_si_es_agendamiento(
            nombre_herramienta,
            resultado,
            argumentos
        )
        
        return resultado
    
    except Exception as e:
        error_msg = f"❌ Error ejecutando {nombre_herramienta}: {str(e)}"
        logger.error(f"  {error_msg}")
        return error_msg


def nodo_ejecucion_medica(state: WhatsAppAgentState) -> Command:
    """
    Nodo 5B: Ejecución de herramientas médicas
    
    MEJORAS APLICADAS:
    ✅ Command pattern con routing directo
    ✅ Detección de estado conversacional
    ✅ Logging estructurado
    
    Flujo:
    1. Verifica estado conversacional (saltar si activo)
    2. Obtiene herramientas seleccionadas
    3. Obtiene doctor_phone si es doctor
    4. Para cada herramienta:
       - Valida permisos
       - Inyecta doctor_phone si necesario
       - Ejecuta la herramienta
       - Actualiza control_turnos si fue agendamiento
    5. Retorna resultados
    
    Returns:
        Command con update y goto
    """
    log_separator(logger, "NODO_5B_EJECUCION_MEDICA", "INICIO")
    
    # Obtener datos del state
    herramientas_seleccionadas = state.get("herramientas_seleccionadas", [])
    tipo_usuario = state.get("tipo_usuario", "")
    estado_conversacion = state.get("estado_conversacion", "inicial")
    doctor_phone = obtener_doctor_phone_from_state(state)
    
    # Log del input
    input_data = f"herramientas: {len(herramientas_seleccionadas)}\ntipo_usuario: {tipo_usuario}\nestado: {estado_conversacion}\ndoctor_phone: {doctor_phone}"
    log_node_io(logger, "INPUT", "NODO_5B_EJECUCION", input_data)
    
    logger.info(f"    👤 Tipo usuario: {tipo_usuario}")
    logger.info(f"    📞 Doctor phone: {doctor_phone}")
    logger.info(f"    🔄 Estado: {estado_conversacion}")
    
    # ✅ NUEVA VALIDACIÓN: Detectar estado conversacional
    if estado_conversacion in ESTADOS_FLUJO_ACTIVO:
        logger.info(f"   🔄 Flujo activo detectado (estado: {estado_conversacion}) - Saltando ejecución")
        return Command(
            update={
                "resultado_herramientas": "Esperando confirmación del usuario",
                "herramientas_ejecutadas": []
            },
            goto="generacion_resumen"
        )
    
    # Validar herramientas
    if not herramientas_seleccionadas:
        logger.info("    ℹ️  No hay herramientas para ejecutar")
        return Command(
            update={
                "resultado_herramientas": "No se seleccionaron herramientas para ejecutar",
                "herramientas_ejecutadas": []
            },
            goto="generacion_resumen"
        )
    
    logger.info(f"    🔧 Herramientas a ejecutar: {len(herramientas_seleccionadas)}")
    
    resultados = []
    
    # Ejecutar cada herramienta
    for item in herramientas_seleccionadas:
        if isinstance(item, str):
            nombre = item
            argumentos = {}
        elif isinstance(item, dict):
            nombre = item.get("nombre", item.get("tool", ""))
            argumentos = item.get("argumentos", item.get("args", {}))
        else:
            logger.warning(f"    ⚠️  Formato inválido: {item}")
            continue
        
        logger.info(f"\n{'=' * 50}")
        logger.info(f"    Herramienta {len(resultados) + 1}/{len(herramientas_seleccionadas)}")
        
        # Ejecutar con validaciones
        resultado = ejecutar_herramienta_con_validaciones(
            nombre_herramienta=nombre,
            argumentos=argumentos,
            tipo_usuario=tipo_usuario,
            doctor_phone=doctor_phone
        )
        
        resultados.append({
            "herramienta": nombre,
            "resultado": resultado,
            "exitoso": "✅" in resultado
        })
    
    # Formatear resultados
    resultados_formateados = "\n\n".join([
        f"**{r['herramienta']}:**\n{r['resultado']}"
        for r in resultados
    ])
    
    exitosos = sum(1 for r in resultados if r["exitoso"])
    
    # Log de output
    output_data = f"ejecutadas: {exitosos}/{len(resultados)}"
    log_node_io(logger, "OUTPUT", "NODO_5B_EJECUCION", output_data)
    logger.info(f"    ✅ Ejecución completada: {exitosos}/{len(resultados)} exitosas")
    log_separator(logger, "NODO_5B_EJECUCION_MEDICA", "FIN")
    
    # ✅ Retornar Command
    return Command(
        update={
            "resultado_herramientas": resultados_formateados,
            "herramientas_ejecutadas": resultados
        },
        goto="generacion_resumen"
    )


# Wrapper para compatibilidad con grafo
def nodo_ejecucion_medica_wrapper(state: WhatsAppAgentState) -> Command:
    """Wrapper para LangGraph - retorna Command directamente."""
    return nodo_ejecucion_medica(state)
