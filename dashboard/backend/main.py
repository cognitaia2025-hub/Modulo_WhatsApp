"""
Dashboard Backend - FastAPI + Socket.IO

Expone API REST y WebSocket para visualización de logs en tiempo real.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import socketio
from typing import Dict, List, Any
from datetime import datetime
import json

from database_api import router as database_router

# ==================== SOCKET.IO SETUP ====================

sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*'  # Permitir Codespaces y localhost
)

# ==================== LIFESPAN ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manejador de ciclo de vida del servidor."""
    # Startup
    print("🚀 Dashboard Backend iniciado")
    print("   API: http://localhost:8000")
    print("   Docs: http://localhost:8000/docs")
    print("   WebSocket: ws://localhost:8000/ws")
    
    yield  # Servidor corriendo
    
    # Shutdown
    print("👋 Dashboard Backend detenido")

app = FastAPI(title="WhatsApp Agent Dashboard API", lifespan=lifespan)

# CORS para React (localhost y Codespaces)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173", 
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Montar Socket.IO en una ruta específica
socket_app = socketio.ASGIApp(sio, other_asgi_app=app)

# Incluir router de base de datos
app.include_router(database_router)

# ==================== STORAGE ====================

# En producción usar Redis
executions: Dict[str, Dict] = {}

# Grafo completo del sistema con bases de datos, herramientas y servicios
# Layout organizado en filas para mejor visualización
graph_structure = {
    "nodes": [
        # ==================== FILA 0: ENTRADA (x=0) ====================
        {"id": "whatsapp", "label": "📱 WhatsApp", "position": {"x": 0, "y": 300}, "type": "service", "category": "external"},
        
        # ==================== FILA 1: IDENTIFICACIÓN (x=200) ====================
        {"id": "n0", "label": "🔍 N0 Identificación", "position": {"x": 200, "y": 300}, "type": "node", "category": "processing"},
        
        # ==================== FILA 2: CACHE (x=400) ====================
        {"id": "n1", "label": "💾 N1 Cache Sesión", "position": {"x": 400, "y": 300}, "type": "node", "category": "processing"},
        {"id": "db_cache", "label": "⚡ Redis Cache", "position": {"x": 400, "y": 150}, "type": "database", "category": "cache"},
        
        # ==================== FILA 3: FILTRADO/DECISIÓN (x=600) ====================
        {"id": "n2", "label": "🎯 N2 Filtrado", "position": {"x": 600, "y": 300}, "type": "node", "category": "decision"},
        
        # ==================== FILA 3.5: LLMs (x=600, arriba) ====================
        {"id": "llm_deepseek", "label": "🧠 DeepSeek", "position": {"x": 550, "y": 50}, "type": "llm", "category": "ai"},
        {"id": "llm_claude", "label": "🤖 Claude Sonnet", "position": {"x": 700, "y": 50}, "type": "llm", "category": "ai"},
        
        # ==================== FILA 4: ASISTENTES MAYA (x=850) ====================
        # Rama Conversacional (arriba)
        {"id": "conv", "label": "💬 Respuesta Conv.", "position": {"x": 850, "y": 100}, "type": "node", "category": "ai"},
        # Rama Paciente (centro-arriba)
        {"id": "n2a", "label": "🤖 N2A Maya Paciente", "position": {"x": 850, "y": 250}, "type": "node", "category": "ai"},
        # Rama Doctor (centro-abajo)
        {"id": "n2b", "label": "👨‍⚕️ N2B Maya Doctor", "position": {"x": 850, "y": 400}, "type": "node", "category": "ai"},
        # Rama Recepcionista (abajo)
        {"id": "n6r", "label": "📞 N6R Recepcionista", "position": {"x": 850, "y": 550}, "type": "node", "category": "ai"},
        
        # ==================== FILA 5: RECUPERACIÓN MEMORIA (x=1100) ====================
        {"id": "n3a", "label": "🧠 N3A Rec. Episódica", "position": {"x": 1100, "y": 250}, "type": "node", "category": "memory"},
        {"id": "n3b", "label": "📋 N3B Rec. Médica", "position": {"x": 1100, "y": 400}, "type": "node", "category": "memory"},
        {"id": "n8", "label": "🔄 N8 Sincronizador", "position": {"x": 1100, "y": 550}, "type": "node", "category": "sync"},
        
        # ==================== FILA 6: SELECCIÓN HERRAMIENTAS (x=1350) ====================
        {"id": "n4a", "label": "⚡ N4 Selección Tools", "position": {"x": 1350, "y": 250}, "type": "node", "category": "decision"},
        {"id": "n4b", "label": "⚡ N4 Selección Tools", "position": {"x": 1350, "y": 400}, "type": "node", "category": "decision"},
        {"id": "n9", "label": "⏰ N9 Recordatorios", "position": {"x": 1350, "y": 550}, "type": "node", "category": "scheduler"},
        
        # ==================== FILA 7: EJECUCIÓN (x=1600) ====================
        {"id": "n5a", "label": "🔧 N5A Ejec. Personal", "position": {"x": 1600, "y": 250}, "type": "node", "category": "execution"},
        {"id": "n5b", "label": "🏥 N5B Ejec. Médica", "position": {"x": 1600, "y": 400}, "type": "node", "category": "execution"},
        
        # ==================== FILA 7.5: HERRAMIENTAS (x=1600, lateral) ====================
        {"id": "tool_search", "label": "🔍 Buscador", "position": {"x": 1600, "y": 100}, "type": "tool", "category": "tool"},
        {"id": "tool_calendar", "label": "📅 Google Calendar", "position": {"x": 1750, "y": 175}, "type": "tool", "category": "external"},
        {"id": "tool_citas", "label": "🗓️ Gestor Citas", "position": {"x": 1750, "y": 475}, "type": "tool", "category": "tool"},
        
        # ==================== FILA 8: RESUMEN (x=1850) ====================
        {"id": "n6", "label": "✍️ N6 Resumen", "position": {"x": 1850, "y": 300}, "type": "node", "category": "processing"},
        
        # ==================== FILA 9: PERSISTENCIA (x=2100) ====================
        {"id": "n7", "label": "💾 N7 Persistencia", "position": {"x": 2100, "y": 300}, "type": "node", "category": "storage"},
        
        # ==================== FILA 9.5: BASES DE DATOS (x=2100, lateral) ====================
        {"id": "db_postgres", "label": "🐘 PostgreSQL", "position": {"x": 2100, "y": 150}, "type": "database", "category": "storage"},
        {"id": "db_pgvector", "label": "🔢 pgVector", "position": {"x": 2100, "y": 450}, "type": "database", "category": "storage"},
        
        # ==================== FILA 10: SALIDA (x=2350) ====================
        {"id": "response", "label": "📤 Respuesta", "position": {"x": 2350, "y": 300}, "type": "service", "category": "output"},
    ],
    "edges": [
        # ══════════════════ FLUJO PRINCIPAL (líneas horizontales) ══════════════════
        {"source": "whatsapp", "target": "n0", "type": "flow"},
        {"source": "n0", "target": "n1", "type": "flow"},
        {"source": "n1", "target": "n2", "type": "flow"},
        
        # ══════════════════ BIFURCACIONES DESDE N2 ══════════════════
        {"source": "n2", "target": "conv", "type": "conditional", "label": "chat"},
        {"source": "n2", "target": "n2a", "type": "conditional", "label": "paciente"},
        {"source": "n2", "target": "n2b", "type": "conditional", "label": "doctor"},
        {"source": "n2", "target": "n6r", "type": "conditional", "label": "agendar"},
        
        # ══════════════════ RAMA PACIENTE (horizontal) ══════════════════
        {"source": "n2a", "target": "n3a", "type": "flow"},
        {"source": "n3a", "target": "n4a", "type": "flow"},
        {"source": "n4a", "target": "n5a", "type": "flow"},
        {"source": "n5a", "target": "n6", "type": "flow"},
        
        # ══════════════════ RAMA DOCTOR (horizontal) ══════════════════
        {"source": "n2b", "target": "n3b", "type": "flow"},
        {"source": "n3b", "target": "n4b", "type": "flow"},
        {"source": "n4b", "target": "n5b", "type": "flow"},
        {"source": "n5b", "target": "n6", "type": "flow"},
        
        # ══════════════════ RAMA RECEPCIONISTA (horizontal) ══════════════════
        {"source": "n6r", "target": "n8", "type": "flow"},
        {"source": "n8", "target": "n9", "type": "flow"},
        {"source": "n8", "target": "n6", "type": "flow"},
        
        # ══════════════════ RAMA CONVERSACIONAL ══════════════════
        {"source": "conv", "target": "n6", "type": "flow"},
        
        # ══════════════════ SALIDA (horizontal) ══════════════════
        {"source": "n6", "target": "n7", "type": "flow"},
        {"source": "n7", "target": "response", "type": "flow"},
        
        # ══════════════════ CONEXIONES A CACHE (vertical) ══════════════════
        {"source": "n1", "target": "db_cache", "type": "data", "label": "read/write"},
        
        # ══════════════════ CONEXIONES A LLMs (vertical) ══════════════════
        {"source": "n2", "target": "llm_deepseek", "type": "api", "label": "classify"},
        {"source": "n2a", "target": "llm_deepseek", "type": "api"},
        {"source": "n2b", "target": "llm_deepseek", "type": "api"},
        {"source": "conv", "target": "llm_deepseek", "type": "api"},
        {"source": "llm_deepseek", "target": "llm_claude", "type": "fallback", "label": "fallback"},
        
        # ══════════════════ CONEXIONES A HERRAMIENTAS ══════════════════
        {"source": "n5a", "target": "tool_search", "type": "api"},
        {"source": "n5a", "target": "tool_calendar", "type": "api", "label": "eventos"},
        {"source": "n5b", "target": "tool_citas", "type": "api", "label": "citas"},
        {"source": "n8", "target": "tool_calendar", "type": "api", "label": "sync"},
        
        # ══════════════════ CONEXIONES A BASES DE DATOS ══════════════════
        {"source": "n0", "target": "db_postgres", "type": "data", "label": "usuarios"},
        {"source": "n3a", "target": "db_pgvector", "type": "data", "label": "embeddings"},
        {"source": "n3b", "target": "db_postgres", "type": "data", "label": "historial"},
        {"source": "n7", "target": "db_postgres", "type": "data", "label": "persist"},
        {"source": "n7", "target": "db_pgvector", "type": "data", "label": "embeddings"},
        {"source": "n9", "target": "db_postgres", "type": "data", "label": "recordatorios"},
    ]
}

# ==================== REST API ====================

@app.get("/")
async def root():
    return {"status": "running", "service": "WhatsApp Agent Dashboard"}

@app.get("/api/graph")
async def get_graph():
    """Retorna estructura del grafo para visualización."""
    return graph_structure

@app.get("/api/executions")
async def get_executions():
    """Retorna últimas 50 ejecuciones."""
    return list(executions.values())[-50:]

@app.get("/api/executions/{execution_id}")
async def get_execution(execution_id: str):
    """Retorna detalles de una ejecución específica."""
    return executions.get(execution_id, {"error": "Not found"})

@app.post("/api/log")
async def receive_log(log_data: dict):
    """
    Recibe logs del backend principal y los emite a clientes conectados.
    """
    print(f"📥 Log recibido: {log_data.get('message', '')[:50]}...")
    await emit_log(log_data)
    return {"status": "ok"}

# ==================== SOCKET.IO EVENTS ====================

@sio.event
async def connect(sid, environ):
    print(f"✅ Cliente conectado: {sid}")
    await sio.emit('connected', {'sid': sid})

@sio.event
async def disconnect(sid):
    print(f"❌ Cliente desconectado: {sid}")

# ==================== LOG RECEIVER ====================

async def emit_log(log_data: Dict[str, Any]):
    """
    Recibe logs del sistema y los emite a clientes conectados.
    
    Llamado desde logger_interceptor.py
    """
    execution_id = log_data.get('execution_id', 'unknown')
    
    # Actualizar estado de ejecución
    if execution_id not in executions:
        executions[execution_id] = {
            'id': execution_id,
            'start_time': datetime.now().isoformat(),
            'nodes': {},
            'logs': []
        }
    
    executions[execution_id]['logs'].append(log_data)
    
    # Actualizar estado del nodo
    node_id = log_data.get('node_id')
    if node_id:
        executions[execution_id]['nodes'][node_id] = {
            'status': log_data.get('status', 'running'),
            'duration_ms': log_data.get('duration_ms'),
            'timestamp': log_data.get('timestamp')
        }
    
    # Emitir a todos los clientes
    await sio.emit('log', log_data)
    await sio.emit('execution_update', {
        'execution_id': execution_id,
        'nodes': executions[execution_id]['nodes']
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(socket_app, host="0.0.0.0", port=8000)
