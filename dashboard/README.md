# WhatsApp Agent Dashboard

Dashboard visual en tiempo real para monitoreo del sistema WhatsApp Agent con LangGraph.

## 🎯 Características

- ✅ Visualización de grafo tipo N8n con React Flow
- ✅ Estados de nodos en tiempo real (idle/running/completed/error)
- ✅ Logs streaming con WebSocket (Socket.IO)
- ✅ Tiempos de ejecución por nodo
- ✅ Estadísticas de performance
- ✅ Historial de ejecuciones
- ✅ Panel de logs con filtros por nivel

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────┐
│  FRONTEND (React + React Flow)                  │
│  http://localhost:3000                          │
│                                                 │
│  ┌────┐  ┌────┐  ┌────┐  ┌────┐               │
│  │ N0 │─→│ N1 │─→│ N2 │─→│N2A │               │
│  │ ✅ │  │ ⏳ │  │ ⏸️ │  │ ⏸️ │               │
│  └────┘  └────┘  └────┘  └────┘               │
│                                                 │
│  Logs Panel:                                    │
│  [10:23:45] N0: User +5266... ✅ 150ms         │
│  [10:23:46] N1: Cache MISS ⏳ 320ms            │
└─────────────────────────────────────────────────┘
                     ▲                            
                     │ WebSocket (Socket.IO)      
                     │                            
┌─────────────────────────────────────────────────┐
│  BACKEND (FastAPI + Socket.IO)                  │
│  http://localhost:8000                          │
│                                                 │
│  /api/graph        → Estructura del grafo       │
│  /api/executions   → Historial de ejecuciones  │
│  /ws               → WebSocket logs real-time   │
└─────────────────────────────────────────────────┘
                     ▲
                     │
┌─────────────────────────────────────────────────┐
│  WHATSAPP AGENT (src/)                          │
│                                                 │
│  Logger interceptor → emite eventos a Socket.IO │
└─────────────────────────────────────────────────┘
```

## 🚀 Setup Rápido

### Backend

```bash
cd dashboard/backend
pip install -r requirements.txt
python main.py
```

**Backend corriendo en:** http://localhost:8000
**Documentación:** http://localhost:8000/docs

### Frontend

```bash
cd dashboard/frontend
npm install
npm run dev
```

**Frontend corriendo en:** http://localhost:3000

## 📖 Uso

1. **Inicia el backend del dashboard:**
   ```bash
   cd dashboard/backend
   python main.py
   ```

2. **En otra terminal, inicia el frontend:**
   ```bash
   cd dashboard/frontend
   npm run dev
   ```

3. **Ejecuta el sistema WhatsApp Agent:**
   ```bash
   # En el directorio raíz del proyecto
   python app.py
   ```

4. **Abre el dashboard en tu navegador:**
   - Ve a http://localhost:3000
   - Observa el flujo en tiempo real

## 🔌 Integración con el Sistema Existente

El dashboard se integra automáticamente con el sistema WhatsApp Agent existente:

1. **Modificación en `src/utils/logging_config.py`:**
   - Se agregó la función `setup_dashboard_integration()` que conecta el sistema de logging con el dashboard

2. **Modificación en `app.py`:**
   - Se llama a `setup_dashboard_integration()` al iniciar el servidor
   - Los logs se emiten automáticamente al dashboard si está disponible

## 🛠️ Stack Tecnológico

### Backend
- **FastAPI** - Framework web moderno y rápido
- **Socket.IO** - WebSocket bidireccional en tiempo real
- **Pydantic** - Validación de datos

### Frontend
- **React 18** - Framework de UI
- **TypeScript** - Tipado estático
- **React Flow** - Visualización de grafos
- **TailwindCSS** - Estilos utilitarios
- **Socket.IO Client** - Cliente WebSocket
- **Lucide React** - Iconos
- **date-fns** - Manejo de fechas

## 📁 Estructura de Archivos

```
dashboard/
├── backend/                      # FastAPI server
│   ├── main.py                  # FastAPI app + Socket.IO
│   ├── logger_interceptor.py   # Captura logs del sistema
│   ├── models.py                # Pydantic models
│   ├── requirements.txt         # Dependencias Python
│   └── test_dashboard.py        # Tests
│
├── frontend/                     # React app
│   ├── src/
│   │   ├── App.tsx              # Componente principal
│   │   ├── main.tsx             # Entry point
│   │   ├── index.css            # Estilos globales
│   │   ├── components/
│   │   │   ├── LogPanel.tsx    # Panel de logs
│   │   │   └── StatsPanel.tsx  # Estadísticas
│   │   ├── hooks/
│   │   │   └── useWebSocket.ts # Hook Socket.IO
│   │   └── types/
│   │       └── index.ts         # TypeScript types
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   └── index.html
│
└── README.md                     # Este archivo
```

## 🧪 Tests

```bash
cd dashboard/backend
pytest test_dashboard.py
```

## 🎨 Personalización

### Agregar Nuevos Nodos al Grafo

Edita `dashboard/backend/main.py` en la sección `graph_structure`:

```python
graph_structure = {
    "nodes": [
        {"id": "mi_nodo", "label": "Mi Nodo", "position": {"x": 0, "y": 0}},
        # ... más nodos
    ],
    "edges": [
        {"source": "n0", "target": "mi_nodo"},
        # ... más conexiones
    ]
}
```

### Cambiar Colores de Estados

Edita `dashboard/frontend/src/App.tsx` en la función `getNodeStyle()`:

```typescript
function getNodeStyle(status: string) {
  switch (status) {
    case 'running':
      return { ...baseStyle, background: '#tu_color' };
    // ...
  }
}
```

## 🐛 Troubleshooting

### El backend no se conecta
- Verifica que el puerto 8000 esté disponible
- Revisa los logs del backend para errores

### El frontend no se conecta al backend
- Asegúrate de que el backend esté corriendo
- Verifica que la URL en `useWebSocket()` sea correcta (http://localhost:8000)
- Revisa la consola del navegador para errores de CORS

### Los logs no aparecen
- Confirma que `setup_dashboard_integration()` se llama al iniciar el sistema
- Verifica que los logs del sistema usen el formato correcto con "NODO_X INICIO/FIN"

## 📝 Notas

- El dashboard es opcional y no afecta el funcionamiento del sistema principal
- Si el dashboard no está disponible, el sistema funciona normalmente
- Los logs se almacenan en memoria (usar Redis en producción)
- Por defecto solo se muestran los últimos 100 logs en el panel

## 🚢 Deployment (Opcional)

Para producción, considera:

1. **Docker Compose:**
   ```yaml
   version: '3.8'
   services:
     dashboard-backend:
       build: ./dashboard/backend
       ports:
         - "8000:8000"
     
     dashboard-frontend:
       build: ./dashboard/frontend
       ports:
         - "3000:3000"
       depends_on:
         - dashboard-backend
   ```

2. **Variables de entorno:**
   - `DASHBOARD_PORT` - Puerto del backend (default: 8000)
   - `FRONTEND_URL` - URL del frontend para CORS
   - `REDIS_URL` - URL de Redis para almacenamiento persistente

## 📄 Licencia

Parte del proyecto Modulo_WhatsApp
