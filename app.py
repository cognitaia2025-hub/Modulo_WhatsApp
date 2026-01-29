from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, TypedDict, Annotated
from langchain_core.messages import HumanMessage
from datetime import datetime
import logging
from contextlib import asynccontextmanager
import pendulum

# Importar sistema de logging con colores
from src.utils.logging_config import (
    setup_colored_logging,
    clear_logs,
    log_user_message,
    LogColors
)

# Configurar logging con colores
logger = setup_colored_logging()

# Import graph desde el proyecto actual
from src.graph_whatsapp import crear_grafo_whatsapp
from src.utils.session_manager import get_or_create_session
from src.embeddings.local_embedder import warmup_embedder
import psycopg  # ✅ Para conexión a BD (rolling window)
import os
from dotenv import load_dotenv

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manejador de ciclo de vida del servidor FastAPI.
    
    Pre-carga el modelo de embeddings en memoria al iniciar
    para eliminar latencia de ~4-7 segundos en el primer mensaje.
    """
    # Startup
    logger.info("🚀 Iniciando servidor FastAPI...")
    logger.info("📦 Pre-cargando modelo de embeddings...")
    
    try:
        warmup_embedder()
        logger.info("✅ Servidor listo - Modelo de embeddings en memoria")
    except Exception as e:
        logger.error(f"❌ Error en startup: {e}")
        logger.warning("⚠️  El servidor continuará, pero los embeddings se cargarán bajo demanda")
    
    logger.info("")
    logger.info("🌐 API disponible en http://localhost:8000")
    logger.info("📚 Documentación en http://localhost:8000/docs")
    logger.info("")
    
    yield  # Servidor corriendo
    
    # Shutdown (opcional)
    logger.info("👋 Servidor detenido")


app = FastAPI(lifespan=lifespan)

# ✅ Configurar CORS para permitir peticiones del simulador
# NOTA: En producción, cambiar allow_origins=["*"] por dominios específicos
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permitir todos los orígenes (desarrollo/simulador local)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Crear grafo una vez al inicio
grafo = crear_grafo_whatsapp()

# ✅ Conexión global a PostgreSQL para rolling window de sesiones
try:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        db_conn = psycopg.connect(database_url)
        logger.info("✅ Conexión a PostgreSQL establecida para session manager")
    else:
        db_conn = None
        logger.warning("⚠️  DATABASE_URL no configurado - rolling window deshabilitado")
except Exception as e:
    logger.error(f"❌ Error conectando a PostgreSQL: {e}")
    db_conn = None



class UserInput(BaseModel):
    user_input: str

@app.get("/")
async def root():
    """
    Endpoint raíz para verificar que el servidor está funcionando.
    """
    return {
        "status": "ok", 
        "message": "🏥 Backend Médico FastAPI funcionando",
        "timestamp": pendulum.now('America/Tijuana').to_iso8601_string(),
        "endpoints": ["/health", "/api/whatsapp-agent/message", "/docs"]
    }

@app.post("/clear-logs")
async def clear_logs_endpoint():
    """
    Limpia los logs de la consola sin reiniciar el backend.
    Útil para debugging y mantener la consola limpia.
    """
    try:
        clear_logs()
        return {
            "status": "success",
            "message": "Logs limpiados correctamente",
            "timestamp": pendulum.now('America/Tijuana').to_iso8601_string()
        }
    except Exception as e:
        logger.error(f"Error al limpiar logs: {e}")
        return {
            "status": "error",
            "message": str(e)
        }

@app.post("/invoke")
async def invoke_graph(data: UserInput):
    try:
        # Log del mensaje del usuario con color azul
        log_user_message(logger, data.user_input)
        
        # Simular número de teléfono del usuario (en producción vendría del webhook de WhatsApp)
        phone_number = "+521234567890"  # Usuario demo

        # ✅ Obtener o crear sesión con rolling window (pasando conexión BD)
        user_id, session_id, config = get_or_create_session(phone_number, db_conn)
        
        # Crear estado inicial
        estado = {
            "messages": [HumanMessage(content=data.user_input)],
            "user_id": user_id,
            "session_id": session_id,
            "cambio_de_tema": False,
            "sesion_expirada": False,
            "herramientas_seleccionadas": [],
            "resumen_actual": None,
            "timestamp": pendulum.now('America/Tijuana').to_iso8601_string()
        }
        
        # Invocar grafo con config (incluye thread_id para PostgresSaver)
        result = grafo.invoke(estado, config)

        # Extract the most useful result for client consumption
        # Priority: tool results (for structured data) > assistant message
        if "messages" in result and len(result["messages"]) > 0:
            # Look for tool messages in reverse order (most recent first)
            for msg in reversed(result["messages"]):
                # Check if it's a ToolMessage with structured data
                msg_type = getattr(msg, "type", None) or (msg.get("type") if isinstance(msg, dict) else None)

                if msg_type == "tool":
                    # Extract tool result content
                    tool_content = getattr(msg, "content", None) or (msg.get("content") if isinstance(msg, dict) else None)
                    tool_name = getattr(msg, "name", None) or (msg.get("name") if isinstance(msg, dict) else None)

                    # For list_events_tool, return the list directly
                    if tool_name == "list_events_tool" and tool_content:
                        try:
                            import json
                            # Tool content might be a string representation of a list
                            if isinstance(tool_content, str):
                                parsed = json.loads(tool_content) if tool_content.startswith('[') else tool_content
                                return {"status": "success", "result": parsed}
                            elif isinstance(tool_content, list):
                                return {"status": "success", "result": tool_content}
                        except:
                            pass

            # If no tool message found, get the final assistant message
            last_message = result["messages"][-1]
            if hasattr(last_message, "content"):
                final_content = last_message.content
            elif isinstance(last_message, dict) and "content" in last_message:
                final_content = last_message["content"]
            else:
                final_content = str(last_message)

            return {"status": "success", "result": final_content}

        # Fallback to full result if structure is unexpected
        return {"status": "success", "result": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}

class WhatsAppMessage(BaseModel):
    chat_id: str
    message: str
    sender_name: str = "Usuario"
    timestamp: str = None  # Opcional, el backend genera el suyo
    thread_id: str = None

@app.post("/api/whatsapp-agent/message")
async def whatsapp_message(data: WhatsAppMessage):
    """
    Endpoint específico para el servicio de WhatsApp.
    Adapta el formato de WhatsApp al formato del grafo.
    """
    try:
        # Log del mensaje del usuario
        log_user_message(logger, data.message)

        # Extraer phone_number del chat_id (formato: 521234567890@c.us)
        phone_number = data.chat_id.replace('@c.us', '')
        if not phone_number.startswith('+'):
            phone_number = f"+{phone_number}"

        # ✅ Obtener o crear sesión con rolling window (pasando conexión BD)
        user_id, session_id, config = get_or_create_session(phone_number, db_conn)

        # Generar timestamp actual (siempre en backend para consistencia)
        timestamp_actual = pendulum.now('America/Tijuana').to_iso8601_string()

        # Crear estado inicial
        estado = {
            "messages": [HumanMessage(content=data.message)],
            "user_id": user_id,
            "session_id": session_id,
            "cambio_de_tema": False,
            "sesion_expirada": False,
            "herramientas_seleccionadas": [],
            "resumen_actual": None,
            "timestamp": timestamp_actual
        }

        # Invocar grafo con config
        result = grafo.invoke(estado, config)

        # Extraer respuesta del agente (último mensaje AI)
        if "messages" in result and len(result["messages"]) > 0:
            last_message = result["messages"][-1]
            if hasattr(last_message, "content"):
                response_text = last_message.content
            elif isinstance(last_message, dict) and "content" in last_message:
                response_text = last_message["content"]
            else:
                response_text = str(last_message)

            return {
                "response": response_text,
                "user_id": user_id,
                "session_id": session_id
            }

        return {
            "error": "No se pudo generar respuesta",
            "response": None
        }

    except Exception as e:
        logger.error(f"Error en endpoint WhatsApp: {e}")
        return {
            "error": str(e),
            "response": None
        }

@app.get("/health")
async def health_check():
    return {"status": "API is running"}
