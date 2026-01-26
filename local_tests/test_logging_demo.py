"""
Script de prueba para demostrar el nuevo sistema de logging con colores.

Este script simula el flujo de un nodo para mostrar:
- Separadores visuales (===)
- Colores en logs (usuario=azul, nodos=amarillo, separadores=rojo)
- Logs detallados de LLM
- Input/Output estructurado
"""

import sys
import os
from pathlib import Path

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.logging_config import (
    setup_colored_logging,
    log_separator,
    log_node_io,
    log_user_message,
    log_llm_interaction,
    clear_logs
)
import logging
import time

# Configurar logging
logger = setup_colored_logging()

def simular_nodo_seleccion():
    """Simula el flujo del Nodo 4: Selección de Herramientas"""
    
    # Separador de inicio
    log_separator(logger, "NODO_4_SELECCION_HERRAMIENTAS", "INICIO")
    
    # Log de input
    input_data = """messages: 3 mensajes
contexto_episodico: True
user_id: user_demo_123"""
    log_node_io(logger, "INPUT", "NODO_4_SELECCION", input_data)
    
    # Simular procesamiento
    logger.info("    📦 Herramientas disponibles: 5")
    time.sleep(0.5)
    
    # Log mensaje del usuario
    mensaje_usuario = "¿Qué eventos tengo hoy en mi calendario?"
    log_user_message(logger, mensaje_usuario)
    time.sleep(0.5)
    
    logger.info("    📖 Contexto episódico disponible: True")
    logger.info("    🤖 Consultando LLM para selección...")
    time.sleep(0.5)
    
    # Simular interacción con LLM
    prompt = """Eres un selector de herramientas de calendario. Tu trabajo es ÚNICAMENTE responder con el ID exacto de la herramienta.

HERRAMIENTAS DISPONIBLES:
• list_calendar_events — Lista eventos del calendario en un rango de fechas
• create_calendar_event — Crea un nuevo evento en el calendario
• update_calendar_event — Actualiza un evento existente
• delete_calendar_event — Elimina un evento del calendario

MENSAJE DEL USUARIO:
"¿Qué eventos tengo hoy en mi calendario?"

CONTEXTO HISTÓRICO:
El usuario suele preguntar por eventos de la semana...

REGLAS ESTRICTAS:
1. NO utilices números, índices ni explicaciones
2. Responde ÚNICAMENTE con el ID exacto de la herramienta
3. Si NO estás seguro, responde: NONE

RESPUESTA (solo ID o NONE):"""
    
    respuesta_llm = "list_calendar_events"
    
    log_llm_interaction(
        logger, 
        "DeepSeek/Claude", 
        prompt, 
        respuesta_llm,
        truncate_prompt=600,
        truncate_response=200
    )
    time.sleep(0.5)
    
    logger.info(f"    ✅ Herramientas seleccionadas: ['list_calendar_events']")
    
    # Log de output
    output_data = "herramientas_seleccionadas: ['list_calendar_events']"
    log_node_io(logger, "OUTPUT", "NODO_4_SELECCION", output_data)
    
    # Separador de fin
    log_separator(logger, "NODO_4_SELECCION_HERRAMIENTAS", "FIN")


def simular_nodo_ejecucion():
    """Simula el flujo del Nodo 5: Ejecución de Herramientas"""
    
    log_separator(logger, "NODO_5_EJECUCION_HERRAMIENTAS", "INICIO")
    
    input_data = """herramientas_seleccionadas: ['list_calendar_events']
contexto_episodico: True
mensajes: 4"""
    log_node_io(logger, "INPUT", "NODO_5_EJECUCION", input_data)
    
    logger.info("    ⏰ Contexto de tiempo: Sábado 25 de enero de 2025, 10:30 AM (America/Tijuana)")
    logger.info("    📋 Herramientas a ejecutar: ['list_calendar_events']")
    time.sleep(0.5)
    
    logger.info("    🔧 Ejecutando: list_calendar_events")
    logger.info("    ✅ list_calendar_events exitoso")
    time.sleep(0.5)
    
    logger.info("    🎭 Orquestador generando respuesta...")
    
    mensaje_usuario = "¿Qué eventos tengo hoy en mi calendario?"
    log_user_message(logger, mensaje_usuario)
    
    prompt_orquestador = """Eres un asistente de WhatsApp profesional y amigable.

CONTEXTO DE TIEMPO:
Hora actual: Sábado 25 de enero de 2025, 10:30 AM
Zona horaria: America/Tijuana (UTC-8)

RESULTADOS DE GOOGLE CALENDAR:
📅 Eventos encontrados (3):
1. Junta de equipo - Hoy 14:00 - 15:00
2. Llamada con cliente - Hoy 16:00 - 17:00  
3. Cena familiar - Hoy 20:00 - 22:00

MENSAJE DEL USUARIO:
"¿Qué eventos tengo hoy en mi calendario?"

Genera una respuesta natural y amigable en español.

RESPUESTA:"""
    
    respuesta_orquestador = """¡Hola! Tienes 3 eventos programados para hoy:

📅 **Junta de equipo** - 14:00 a 15:00
📅 **Llamada con cliente** - 16:00 a 17:00
📅 **Cena familiar** - 20:00 a 22:00

¿Necesitas hacer algún cambio en tu agenda? 😊"""
    
    log_llm_interaction(
        logger,
        "Orquestador (DeepSeek/Claude)",
        prompt_orquestador,
        respuesta_orquestador,
        truncate_prompt=1000
    )
    
    output_data = f"""respuesta: {respuesta_orquestador[:80]}...
herramientas_ejecutadas: 1"""
    log_node_io(logger, "OUTPUT", "NODO_5_EJECUCION", output_data)
    
    log_separator(logger, "NODO_5_EJECUCION_HERRAMIENTAS", "FIN")


def simular_nodo_recuperacion():
    """Simula el flujo del Nodo 3: Recuperación Episódica"""
    
    log_separator(logger, "NODO_3_RECUPERACION_EPISODICA", "INICIO")
    
    input_data = """user_id: user_demo_123
mensajes: 2"""
    log_node_io(logger, "INPUT", "NODO_3_RECUPERACION", input_data)
    
    logger.info("    👤 User ID: user_demo_123")
    
    mensaje = "¿Qué eventos tengo esta semana?"
    log_user_message(logger, mensaje)
    
    logger.info("    🔢 Generando embedding del mensaje...")
    time.sleep(0.3)
    logger.info("    ✅ Embedding generado (384 dims)")
    
    logger.info("    🔍 Buscando TOP 5 episodios similares...")
    time.sleep(0.3)
    logger.info("    ✅ 2 episodios recuperados")
    
    output_data = """episodios_recuperados: 2
similarity_threshold: 0.7"""
    log_node_io(logger, "OUTPUT", "NODO_3_RECUPERACION", output_data)
    
    log_separator(logger, "NODO_3_RECUPERACION_EPISODICA", "FIN")


def main():
    """Función principal"""
    
    print("\n" + "="*80)
    print("  DEMOSTRACIÓN DEL SISTEMA DE LOGGING CON COLORES")
    print("="*80 + "\n")
    
    logger.info("🚀 Iniciando simulación del flujo del agente...")
    logger.info("")
    
    time.sleep(1)
    
    # Simular 3 nodos
    simular_nodo_recuperacion()
    print()
    time.sleep(0.5)
    
    simular_nodo_seleccion()
    print()
    time.sleep(0.5)
    
    simular_nodo_ejecucion()
    print()
    
    logger.info("")
    logger.info("✅ Simulación completada")
    logger.info("")
    logger.info("💡 Tip: Puedes limpiar los logs con: POST http://localhost:8000/clear-logs")
    logger.info("")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n\n⚠️  Simulación interrumpida por el usuario")
    except Exception as e:
        logger.error(f"\n\n❌ Error en simulación: {e}")
