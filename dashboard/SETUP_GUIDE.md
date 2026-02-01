# 🚀 Quick Start Guide - WhatsApp Agent Dashboard

Este documento proporciona instrucciones paso a paso para configurar y ejecutar el dashboard visual.

## 📋 Prerrequisitos

- **Python 3.8+** instalado
- **Node.js 18+** y npm instalado
- **Git** instalado
- Repositorio clonado localmente

## 🔧 Instalación

### 1. Backend Setup (FastAPI + Socket.IO)

```bash
# Navegar al directorio del backend
cd dashboard/backend

# Instalar dependencias de Python
pip install -r requirements.txt

# Iniciar el servidor backend
python main.py
```

**Resultado esperado:**
```
INFO:     Started server process
INFO:     Waiting for application startup.
🚀 Dashboard Backend iniciado
   API: http://localhost:8000
   Docs: http://localhost:8000/docs
   WebSocket: ws://localhost:8000/ws
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

✅ **Backend corriendo en:** http://localhost:8000  
✅ **Documentación API:** http://localhost:8000/docs

---

### 2. Frontend Setup (React + Vite)

**En una nueva terminal:**

```bash
# Navegar al directorio del frontend
cd dashboard/frontend

# Instalar dependencias de Node.js
npm install

# Iniciar servidor de desarrollo
npm run dev
```

**Resultado esperado:**
```
  VITE v5.0.8  ready in 500 ms

  ➜  Local:   http://localhost:3000/
  ➜  Network: use --host to expose
  ➜  press h + enter to show help
```

✅ **Frontend corriendo en:** http://localhost:3000

---

### 3. Sistema WhatsApp Agent (Opcional)

**En una tercera terminal:**

```bash
# Desde el directorio raíz del proyecto
python app.py
```

El dashboard capturará automáticamente los logs del sistema.

---

## 🎯 Verificación de Instalación

### Backend Health Check

```bash
curl http://localhost:8000/
```

**Respuesta esperada:**
```json
{
  "status": "running",
  "service": "WhatsApp Agent Dashboard"
}
```

### Frontend Health Check

Abre tu navegador en http://localhost:3000 y deberías ver:
- ✅ Header "WhatsApp Agent Dashboard"
- ✅ Estado de conexión (🟢 Conectado / 🔴 Desconectado)
- ✅ Visualización del grafo con nodos
- ✅ Panel de logs en el lateral
- ✅ Panel de estadísticas

---

## 🧪 Tests

### Backend Tests

```bash
cd dashboard/backend
pytest test_dashboard.py -v
```

**Resultado esperado:**
```
test_dashboard.py::test_graph_structure PASSED
test_dashboard.py::test_graph_node_structure PASSED
test_dashboard.py::test_graph_edge_structure PASSED
test_dashboard.py::test_executions_storage PASSED
test_dashboard.py::test_socket_io_setup PASSED
test_dashboard.py::test_fastapi_app PASSED

====== 6 passed in 0.53s ======
```

---

## 🔄 Flujo de Trabajo

1. **Iniciar Backend:** `python dashboard/backend/main.py`
2. **Iniciar Frontend:** `npm run dev` en `dashboard/frontend/`
3. **Iniciar Sistema:** `python app.py` (opcional, para ver logs en tiempo real)
4. **Abrir Dashboard:** Navega a http://localhost:3000

### Procesamiento de Mensajes

Cuando el sistema WhatsApp Agent procesa un mensaje:
1. Los logs se capturan automáticamente
2. Se envían al backend vía Socket.IO
3. El frontend recibe los logs en tiempo real
4. Los nodos del grafo cambian de estado:
   - 🟤 **Idle:** Nodo no ejecutado
   - 🔵 **Running:** Nodo en ejecución
   - 🟢 **Completed:** Nodo completado exitosamente
   - 🔴 **Error:** Error en el nodo

---

## 🛠️ Troubleshooting

### Error: "Port 8000 already in use"

```bash
# Encontrar y terminar el proceso
lsof -ti:8000 | xargs kill -9

# O usar otro puerto
uvicorn main:socket_app --port 8001
```

### Error: "Port 3000 already in use"

```bash
# En package.json, cambiar el puerto
# O usar variable de entorno
PORT=3001 npm run dev
```

### Frontend no se conecta al backend

1. Verifica que el backend esté corriendo en http://localhost:8000
2. Abre la consola del navegador (F12) y busca errores de CORS
3. Confirma que el URL en `src/hooks/useWebSocket.ts` sea correcto

### Los logs no aparecen

1. Verifica que el sistema WhatsApp Agent esté corriendo
2. Confirma que `setup_dashboard_integration()` se llama en `app.py`
3. Revisa los logs de la terminal del backend para ver si llegan eventos

---

## 📦 Build de Producción

### Frontend Build

```bash
cd dashboard/frontend
npm run build
```

Los archivos compilados estarán en `dashboard/frontend/dist/`

### Servir Frontend Estático

```bash
npm run preview
```

O usar cualquier servidor web:
```bash
python -m http.server 3000 --directory dist
```

---

## 🐳 Docker (Opcional)

**Crear `dashboard/docker-compose.yml`:**

```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - PORT=8000

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend
    environment:
      - VITE_API_URL=http://localhost:8000
```

**Ejecutar:**
```bash
docker-compose up
```

---

## 📚 Recursos Adicionales

- **FastAPI Docs:** https://fastapi.tiangolo.com/
- **React Flow:** https://reactflow.dev/
- **Socket.IO:** https://socket.io/docs/v4/
- **Vite:** https://vitejs.dev/
- **TailwindCSS:** https://tailwindcss.com/

---

## 🆘 Soporte

Si encuentras problemas:
1. Revisa los logs del backend y frontend
2. Verifica que todas las dependencias estén instaladas
3. Confirma que los puertos 8000 y 3000 estén disponibles
4. Consulta el archivo `dashboard/README.md` para más detalles

---

## 🎉 ¡Listo!

Tu dashboard debería estar funcionando. Abre http://localhost:3000 y comienza a monitorear tu sistema WhatsApp Agent en tiempo real.
