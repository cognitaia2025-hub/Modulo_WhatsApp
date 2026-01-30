"""
Backend simplificado para testing del simulador
"""
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json

app = FastAPI(title="Simple WhatsApp Backend Test")

# Configurar CORS - permitir todas las origenes de GitHub Codespaces
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

class MessageRequest(BaseModel):
    chat_id: str
    message: str
    sender_name: str = ""
    timestamp: str = ""
    thread_id: str = ""

@app.get("/api/status")
async def get_status():
    return {
        "status": "healthy",
        "backend": {"status": "healthy"},
        "message": "Backend simple funcionando correctamente"
    }

@app.post("/api/whatsapp-agent/message")
async def process_message(request: MessageRequest):
    print(f"🔥 === MENSAJE RECIBIDO ===")
    print(f"📱 Chat ID: {request.chat_id}")
    print(f"👤 Sender: {request.sender_name}")
    print(f"💬 Message: '{request.message}'")
    print(f"🧵 Thread ID: {request.thread_id}")
    
    # Simular procesamiento del mensaje problemático
    message = request.message.lower().strip()
    
    if "mañana pero en la tarde" in message:
        print(f"🎯 DETECTADO CASO PROBLEMÁTICO: 'mañana pero en la tarde'")
        print(f"📅 Extrayendo fecha: 'mañana' → 'mañana'")
        print(f"⏰ Extrayendo hora: 'en la tarde' → 'tarde'")
        response_text = "¡Perfecto! Para mañana en la tarde tengo disponibilidad a las 14:00, 15:00 y 16:00. ¿Cuál prefieres?"
    elif "mañana" in message and "tarde" in message:
        print(f"🎯 DETECTADO: fecha 'mañana' + hora 'tarde'")
        response_text = "Excelente, para mañana en la tarde tengo horarios disponibles. ¿Prefieres 2:00 PM, 3:00 PM o 4:00 PM?"
    elif "mañana" in message:
        print(f"📅 DETECTADO: solo fecha 'mañana'")
        response_text = "Perfecto para mañana. ¿A qué hora te gustaría? Tengo disponibilidad en la mañana, tarde y noche."
    elif "tarde" in message:
        print(f"⏰ DETECTADO: solo hora 'tarde'")
        response_text = "Te entiendo, prefieres en la tarde. ¿Para qué día? Puedes decir 'mañana', 'el viernes', etc."
    else:
        response_text = f"Hola Juan Pérez! Recibí tu mensaje: '{request.message}'. ¿En qué puedo ayudarte hoy?"
    
    print(f"📤 RESPUESTA: {response_text}")
    print(f"🔥 === FIN PROCESAMIENTO ===")
    
    return {
        "success": True,
        "response": response_text
    }

if __name__ == "__main__":
    print("🚀 Iniciando backend simplificado en puerto 8002...")
    print("📝 Este backend muestra logs detallados para debugging")
    print("🎯 Especializado en detectar 'mañana pero en la tarde'")
    uvicorn.run(app, host="0.0.0.0", port=8002, log_level="info")