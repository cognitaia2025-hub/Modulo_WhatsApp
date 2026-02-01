"""
Dashboard Backend - FastAPI + Socket.IO

Expone API REST y WebSocket para visualización de logs en tiempo real.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import socketio
from typing import Dict, List, Any
from datetime import datetime
import json

# ==================== SOCKET.IO SETUP ====================

sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins=['http://localhost:3000']
)

app = FastAPI(title="WhatsApp Agent Dashboard API")
socket_app = socketio.ASGIApp(sio, app)

# CORS para React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== STORAGE ====================

# En producción usar Redis
executions: Dict[str, Dict] = {}
graph_structure = {
    "nodes": [
        {"id": "n0", "label": "N0 Identificación", "position": {"x": 0, "y": 0}},
        {"id": "n1", "label": "N1 Cache", "position": {"x": 200, "y": 0}},
        {"id": "n2", "label": "N2 Filtrado", "position": {"x": 400, "y": 0}},
        {"id": "n2a", "label": "N2A Maya Paciente", "position": {"x": 600, "y": -100}},
        {"id": "n2b", "label": "N2B Maya Doctor", "position": {"x": 600, "y": 100}},
        {"id": "n3a", "label": "N3A Rec. Episódica", "position": {"x": 800, "y": -100}},
        {"id": "n3b", "label": "N3B Rec. Médica", "position": {"x": 800, "y": 100}},
        {"id": "n4", "label": "N4 Selección", "position": {"x": 1000, "y": 0}},
        {"id": "n5a", "label": "N5A Ejec. Personal", "position": {"x": 1200, "y": -100}},
        {"id": "n5b", "label": "N5B Ejec. Médica", "position": {"x": 1200, "y": 100}},
        {"id": "n6", "label": "N6 Resumen", "position": {"x": 1400, "y": 0}},
        {"id": "n7", "label": "N7 Persistencia", "position": {"x": 1600, "y": 0}},
        {"id": "n6r", "label": "N6R Recepcionista", "position": {"x": 600, "y": 200}},
        {"id": "n8", "label": "N8 Sincronizador", "position": {"x": 800, "y": 200}},
        {"id": "n9", "label": "N9 Recordatorios", "position": {"x": 1000, "y": 200}},
    ],
    "edges": [
        {"source": "n0", "target": "n1"},
        {"source": "n1", "target": "n2"},
        {"source": "n2", "target": "n2a"},
        {"source": "n2", "target": "n2b"},
        {"source": "n2a", "target": "n3a"},
        {"source": "n2b", "target": "n3b"},
        {"source": "n3a", "target": "n4"},
        {"source": "n3b", "target": "n4"},
        {"source": "n4", "target": "n5a"},
        {"source": "n4", "target": "n5b"},
        {"source": "n5a", "target": "n6"},
        {"source": "n5b", "target": "n6"},
        {"source": "n6", "target": "n7"},
        {"source": "n2", "target": "n6r"},
        {"source": "n6r", "target": "n8"},
        {"source": "n8", "target": "n9"},
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

# ==================== STARTUP ====================

@app.on_event("startup")
async def startup():
    print("🚀 Dashboard Backend iniciado")
    print("   API: http://localhost:8000")
    print("   Docs: http://localhost:8000/docs")
    print("   WebSocket: ws://localhost:8000/ws")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(socket_app, host="0.0.0.0", port=8000)
