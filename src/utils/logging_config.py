"""
Configuración centralizada de logging con colores para el agente de calendario.

Este módulo proporciona:
- Colores ANSI para diferentes tipos de mensajes
- Formatter personalizado con colores
- Funciones para separadores visuales
- Función para limpiar logs sin reiniciar el backend
"""

import logging
import sys
from typing import Optional
from datetime import datetime
from colorama import init, Fore, Back, Style

# Inicializar colorama para Windows
init(autoreset=True)

# Definir colores para diferentes tipos de mensajes
class LogColors:
    """Colores para diferentes elementos del log"""
    # Separadores
    SEPARATOR = Fore.RED + Style.BRIGHT
    
    # Mensajes de nodos (entrada/salida)
    NODE_IO = Fore.YELLOW + Style.BRIGHT
    
    # Mensajes del usuario
    USER = Fore.CYAN + Style.BRIGHT
    
    # Niveles de logging
    DEBUG = Fore.BLUE
    INFO = Fore.GREEN
    WARNING = Fore.YELLOW
    ERROR = Fore.RED + Style.BRIGHT
    CRITICAL = Fore.RED + Back.WHITE + Style.BRIGHT
    
    # LLM inputs/outputs
    LLM_INPUT = Fore.MAGENTA + Style.BRIGHT
    LLM_OUTPUT = Fore.MAGENTA + Style.DIM
    
    # Reset
    RESET = Style.RESET_ALL


class ColoredFormatter(logging.Formatter):
    """Formatter personalizado que agrega colores a los logs"""
    
    LEVEL_COLORS = {
        logging.DEBUG: LogColors.DEBUG,
        logging.INFO: LogColors.INFO,
        logging.WARNING: LogColors.WARNING,
        logging.ERROR: LogColors.ERROR,
        logging.CRITICAL: LogColors.CRITICAL
    }
    
    def format(self, record):
        # Guardar el levelname original
        original_levelname = record.levelname
        
        # Aplicar color al nivel
        level_color = self.LEVEL_COLORS.get(record.levelno, '')
        record.levelname = f"{level_color}{record.levelname}{LogColors.RESET}"
        
        # Formatear el mensaje base
        formatted = super().format(record)
        
        # Restaurar el levelname original
        record.levelname = original_levelname
        
        return formatted


def log_separator(logger: logging.Logger, node_name: str, stage: str = "INICIO"):
    """
    Imprime un separador visual entre nodos.
    
    Args:
        logger: Logger a usar
        node_name: Nombre del nodo (ej: "NODO_1_CACHE")
        stage: "INICIO" o "FIN"
    """
    separator = "=" * 100
    colored_separator = f"{LogColors.SEPARATOR}{separator}{LogColors.RESET}"
    message = f"{LogColors.SEPARATOR}{'▶' if stage == 'INICIO' else '◀'} [{node_name}] - {stage} {LogColors.RESET}"
    
    logger.info(colored_separator)
    logger.info(message)
    if stage == "INICIO":
        logger.info(colored_separator)


def log_node_io(logger: logging.Logger, direction: str, node_name: str, content: str, truncate: int = 500):
    """
    Log de entrada/salida de un nodo.
    
    Args:
        logger: Logger a usar
        direction: "INPUT" o "OUTPUT"
        node_name: Nombre del nodo
        content: Contenido del mensaje
        truncate: Máximo de caracteres a mostrar (0 = sin límite)
    """
    arrow = "📥" if direction == "INPUT" else "📤"
    
    # Truncar si es necesario
    if truncate > 0 and len(content) > truncate:
        content = content[:truncate] + f"... ({len(content)} caracteres totales)"
    
    message = f"{LogColors.NODE_IO}{arrow} [{node_name}] {direction}:{LogColors.RESET}\n{content}"
    logger.info(message)


def log_user_message(logger: logging.Logger, message: str):
    """Log de mensaje del usuario."""
    formatted = f"{LogColors.USER}👤 USUARIO:{LogColors.RESET} {message}"
    logger.info(formatted)


def log_llm_interaction(logger: logging.Logger, 
                        llm_name: str, 
                        prompt: str, 
                        response: str,
                        truncate_prompt: int = 1000,
                        truncate_response: int = 1000):
    """
    Log detallado de interacción con LLM.
    
    Args:
        logger: Logger a usar
        llm_name: Nombre del LLM (ej: "DeepSeek", "Claude")
        prompt: Prompt enviado al LLM
        response: Respuesta del LLM
        truncate_prompt: Máximo de caracteres para el prompt (0 = sin límite)
        truncate_response: Máximo de caracteres para la respuesta (0 = sin límite)
    """
    # Truncar prompt
    prompt_display = prompt
    if truncate_prompt > 0 and len(prompt) > truncate_prompt:
        prompt_display = prompt[:truncate_prompt] + f"... ({len(prompt)} caracteres totales)"
    
    # Truncar response
    response_display = response
    if truncate_response > 0 and len(response) > truncate_response:
        response_display = response[:truncate_response] + f"... ({len(response)} caracteres totales)"
    
    logger.info(f"{LogColors.LLM_INPUT}🤖 [{llm_name}] PROMPT ENVIADO:{LogColors.RESET}")
    logger.info(f"{prompt_display}")
    logger.info(f"{LogColors.LLM_OUTPUT}🤖 [{llm_name}] RESPUESTA RECIBIDA:{LogColors.RESET}")
    logger.info(f"{response_display}")


def setup_colored_logging(log_level: int = logging.INFO):
    """
    Configura el sistema de logging con colores.
    
    Args:
        log_level: Nivel de logging (default: INFO)
    
    Returns:
        Logger raíz configurado
    """
    # Crear formatter personalizado
    formatter = ColoredFormatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Configurar handler para stdout
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.stream.reconfigure(encoding='utf-8')
    
    # Configurar logger raíz
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Limpiar handlers existentes y agregar el nuevo
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    
    return root_logger


def clear_logs():
    """
    Limpia la consola sin terminar el backend.
    Funciona en Windows, Linux y macOS.
    """
    import os
    import platform
    
    system = platform.system()
    
    if system == "Windows":
        os.system('cls')
    else:
        os.system('clear')
    
    # Log de confirmación
    logger = logging.getLogger(__name__)
    logger.info(f"{LogColors.INFO}🧹 Logs limpiados - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{LogColors.RESET}")


# Configurar logging al importar el módulo
logger = setup_colored_logging()

# Exportar funciones principales
__all__ = [
    'LogColors',
    'ColoredFormatter',
    'log_separator',
    'log_node_io',
    'log_user_message',
    'log_llm_interaction',
    'setup_colored_logging',
    'clear_logs'
]
