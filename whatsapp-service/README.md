# 📱 WhatsApp Service - Calendar AI Agent

Servicio de WhatsApp que conecta automáticamente con el agente de calendario usando LangGraph.

## 🚀 Inicio Rápido

### Opción 1: Usando el script principal (Recomendado)

Desde la raíz del proyecto:

```powershell
.\start_project_whatsapp.ps1
```

Esto iniciará automáticamente:
1. ✅ Backend FastAPI (puerto 8000)
2. ✅ Servicio WhatsApp (puerto 3001)

### Opción 2: Iniciar solo WhatsApp

Desde la raíz del proyecto:

```bash
.\start_whatsapp.bat
```

O manualmente:

```bash
cd whatsapp-service
node src/index.js
```

## 📋 Requisitos

- Node.js >= 18.0.0
- Backend Python corriendo en `http://localhost:8000`
- PostgreSQL configurado (para persistencia)

## 🔧 Configuración

El archivo `.env` en esta carpeta controla la configuración:

```env
# URL del backend Python
BACKEND_URL=http://localhost:8000

# Puerto del servidor HTTP de status
HTTP_PORT=3001

# Ruta de sesión de WhatsApp
SESSION_PATH=./session

# Timeout para llamadas al backend (ms)
API_TIMEOUT=60000

# Nivel de logs
LOG_LEVEL=debug

# Lista de números permitidos (vacío = todos)
ALLOWED_NUMBERS=
```

## 📱 Conectar WhatsApp

1. **Inicia el servicio**
   ```bash
   node src/index.js
   ```

2. **Escanea el código QR**
   - Abre WhatsApp en tu teléfono
   - Ve a Configuración > Dispositivos vinculados
   - Escanea el código QR que aparece en la terminal

3. **¡Listo!**
   - Envía un mensaje desde WhatsApp
   - El agente responderá automáticamente

## 🔗 Endpoints Disponibles

### Status del Servicio
```bash
GET http://localhost:3001/status
```

Respuesta:
```json
{
  "service": "podoskin-whatsapp",
  "whatsapp": "connected",
  "backend": "healthy",
  "qrCode": null,
  "lastMessage": {
    "from": "521234567890@c.us",
    "body": "¿Qué eventos tengo hoy?",
    "timestamp": "2026-01-25T18:00:00.000Z"
  },
  "config": {
    "backend_url": "http://localhost:8000",
    "allowed_numbers": "all"
  }
}
```

### Obtener Código QR
```bash
GET http://localhost:3001/qr
```

### Health Check
```bash
GET http://localhost:3001/health
```

### Enviar Mensaje Manual (Testing)
```bash
POST http://localhost:3001/send
Content-Type: application/json

{
  "to": "521234567890",
  "message": "Hola desde el servidor"
}
```

## 🔄 Flujo de Comunicación

```
Usuario WhatsApp
    ↓
[WhatsApp Service] (Puerto 3001)
    ↓ HTTP POST /api/whatsapp-agent/message
[Backend Python] (Puerto 8000)
    ↓
[LangGraph Agent] (7 nodos)
    ↓
[Google Calendar API]
    ↓
[PostgreSQL] (Memoria episódica)
    ↓
[Backend Python] ← Respuesta
    ↓
[WhatsApp Service] ← Respuesta
    ↓
Usuario WhatsApp ← Mensaje
```

## 📊 Logs

El servicio genera logs detallados:

```
✅ WhatsApp conectado y listo
📩 Mensaje recibido de Usuario (521234567890@c.us): ¿Qué eventos tengo hoy?...
📤 Respuesta enviada a 521234567890@c.us
```

Los logs incluyen:
- Estado de conexión de WhatsApp
- Mensajes recibidos y enviados
- Errores de comunicación con el backend
- Timeouts y reintentos

## 🛡️ Seguridad

### Filtro de Números

Puedes restringir quién puede usar el bot:

```env
# Solo estos números pueden enviar mensajes
ALLOWED_NUMBERS=521234567890,521098765432
```

### Ignorar Automáticamente

El servicio ignora:
- ✅ Mensajes de grupos
- ✅ Mensajes propios (para evitar loops)
- ✅ Números no autorizados (si hay filtro)

## 🐛 Troubleshooting

### "Backend no disponible"

**Error**: `❌ Backend no disponible en http://localhost:8000`

**Solución**:
1. Verifica que el backend esté corriendo:
   ```bash
   curl http://localhost:8000/health
   ```
2. Verifica el puerto en `.env`:
   ```env
   BACKEND_URL=http://localhost:8000
   ```

### "Timeout esperando respuesta"

**Error**: `❌ Timeout esperando respuesta del backend`

**Solución**:
1. Aumenta el timeout en `.env`:
   ```env
   API_TIMEOUT=120000  # 2 minutos
   ```
2. Verifica que el backend no esté sobrecargado

### "Error de autenticación"

**Error**: `❌ Error de autenticación`

**Solución**:
1. Elimina la sesión guardada:
   ```bash
   rm -rf session/
   ```
2. Reinicia el servicio y vuelve a escanear el QR

### "QR no aparece"

**Solución**:
1. Verifica que no haya otra instancia corriendo
2. Elimina la sesión:
   ```bash
   rm -rf session/
   ```
3. Reinicia

## 📦 Estructura de Archivos

```
whatsapp-service/
├── src/
│   ├── index.js         # Servidor principal
│   ├── api-client.js    # Cliente HTTP para backend
│   └── logger.js        # Sistema de logs
├── session/             # Sesión de WhatsApp (generada automáticamente)
├── logs/                # Logs del servicio
├── .env                 # Configuración
├── package.json         # Dependencias Node.js
└── README.md           # Este archivo
```

## 🔄 Actualizar Dependencias

```bash
npm install
```

## 🚫 Archivos Ignorados

El `.gitignore` excluye:
- `session/` - Sesión de WhatsApp (contiene credenciales)
- `logs/` - Logs del servicio
- `.env` - Configuración local
- `node_modules/` - Dependencias

## 📝 Variables de Entorno

| Variable | Descripción | Default |
|----------|-------------|---------|
| `BACKEND_URL` | URL del backend Python | `http://localhost:8000` |
| `HTTP_PORT` | Puerto del servidor HTTP | `3001` |
| `SESSION_PATH` | Ruta para guardar sesión | `./session` |
| `API_TIMEOUT` | Timeout para llamadas (ms) | `60000` |
| `LOG_LEVEL` | Nivel de logs | `debug` |
| `ALLOWED_NUMBERS` | Números permitidos | `""` (todos) |

## 🎯 Casos de Uso

### 1. Usuario pregunta por eventos
```
Usuario: "¿Qué eventos tengo hoy?"
Agente: "Tienes una cita con el dentista hoy a las 8:00 PM..."
```

### 2. Usuario crea evento
```
Usuario: "Agenda una reunión mañana a las 10am"
Agente: "Listo, agendé tu reunión para mañana 26/01 a las 10:00 AM."
```

### 3. Usuario actualiza evento
```
Usuario: "Cambia la reunión de mañana para las 11am"
Agente: "Perfecto, cambié la reunión de 10:00 AM a 11:00 AM."
```

### 4. Usuario elimina evento
```
Usuario: "Elimina la reunión de mañana"
Agente: "Eliminé la reunión del 26/01. ¿Necesitas algo más?"
```

## 🚀 Producción

Para producción, considera:

1. **Usar PM2 para gestión de procesos**
   ```bash
   npm install -g pm2
   pm2 start src/index.js --name whatsapp-calendar
   pm2 save
   pm2 startup
   ```

2. **Variables de entorno en producción**
   ```env
   BACKEND_URL=https://tu-backend.com
   LOG_LEVEL=info
   ALLOWED_NUMBERS=521234567890,521098765432
   ```

3. **Monitoreo**
   - Configura alertas para `/health` endpoint
   - Monitorea logs con PM2: `pm2 logs whatsapp-calendar`

## 📄 Licencia

Parte del proyecto Calendar AI Agent
