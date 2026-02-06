"""
Nodo 0: Identificación de Usuario

Extrae número de teléfono del mensaje WhatsApp, consulta BD de usuarios,
determina si es admin, y carga perfil. Si es usuario nuevo, auto-registro.

NUEVO: Sistema de cambio de número temporal para doctores
- Comando: {cambio_datos} para solicitar plantilla
- Plantilla completada para activar número temporal
- Validación determinista sin LLM
"""

import os
import re
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

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
