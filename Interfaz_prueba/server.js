/**
 * Simulador WhatsApp HTTP Server
 * ===============================
 * 
 * Servidor HTTP que simula el comportamiento de whatsapp-service
 * pero con una interfaz web para pruebas del sistema médico.
 * 
 * Endpoints:
 * - GET  /             - Interfaz web del simulador
 * - POST /api/message  - Enviar mensaje al backend (mismo formato que WhatsApp)
 * - GET  /api/status   - Estado del servidor y backend
 * - GET  /api/health   - Health check
 */

require('dotenv').config();
const express = require('express');
const cors = require('cors');
const axios = require('axios');
const path = require('path');

// ============================================================================
// CONFIGURACIÓN
// ============================================================================

const CONFIG = {
    PORT: process.env.PORT || 3002,
    BACKEND_URL: process.env.BACKEND_URL || 'http://localhost:8000',
    API_TIMEOUT: parseInt(process.env.API_TIMEOUT || '180000'),
    CORS_ORIGINS: process.env.CORS_ORIGINS 
        ? process.env.CORS_ORIGINS.split(',').map(o => o.trim())
        : ['http://localhost:3002', 'http://127.0.0.1:3002']
};

// ============================================================================
// EXPRESS APP
// ============================================================================

const app = express();

// Middlewares
app.use(cors({
    origin: CONFIG.CORS_ORIGINS,
    credentials: true
}));
app.use(express.json());
app.use(express.static(__dirname)); // Servir archivos estáticos (HTML, CSS, JS)

// Logger middleware
app.use((req, res, next) => {
    console.log(`[${new Date().toISOString()}] ${req.method} ${req.path}`);
    next();
});

// ============================================================================
// CLIENTE AXIOS PARA BACKEND
// ============================================================================

const backendClient = axios.create({
    baseURL: CONFIG.BACKEND_URL,
    timeout: CONFIG.API_TIMEOUT,
    headers: {
        'Content-Type': 'application/json'
    }
});

// ============================================================================
// ENDPOINTS - INTERFAZ WEB
// ============================================================================

/**
 * GET / - Interfaz principal del simulador
 */
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'index.html'));
});

// ============================================================================
// ENDPOINTS - API SIMULADOR
// ============================================================================

/**
 * POST /api/message
 * Envía mensaje al backend con el mismo formato que whatsapp-service
 * 
 * Body esperado:
 * {
 *   "chat_id": "573001234567@c.us",
 *   "message": "Hola, necesito agendar una cita",
 *   "sender_name": "Juan Pérez",
 *   "timestamp": "2026-01-30T14:30:00.000Z",
 *   "thread_id": "573001234567"
 * }
 */
app.post('/api/message', async (req, res) => {
    try {
        const { chat_id, message, sender_name, timestamp, thread_id } = req.body;

        // Validación
        if (!chat_id || !message) {
            return res.status(400).json({
                error: 'Se requieren campos: chat_id, message',
                details: 'chat_id y message son obligatorios'
            });
        }

        // Log del mensaje recibido
        console.log(`📩 Mensaje de ${sender_name || 'Usuario'} (${chat_id}): ${message.substring(0, 50)}...`);

        // Preparar payload exacto que espera el backend
        const payload = {
            chat_id: chat_id,
            message: message,
            sender_name: sender_name || 'Usuario Simulador',
            timestamp: timestamp || new Date().toISOString(),
            thread_id: thread_id || chat_id.replace('@c.us', '')
        };

        // Enviar al backend Python
        const response = await backendClient.post('/api/whatsapp-agent/message', payload);

        console.log(`📤 Respuesta del backend: ${response.data.response?.substring(0, 50)}...`);

        // Retornar respuesta del backend
        res.json({
            success: true,
            response: response.data.response || 'Respuesta recibida',
            backend_data: response.data
        });

    } catch (error) {
        console.error('❌ Error procesando mensaje:', error.message);

        if (error.code === 'ECONNREFUSED') {
            return res.status(503).json({
                error: 'backend_unavailable',
                message: `Backend no disponible en ${CONFIG.BACKEND_URL}`,
                details: 'Asegúrate de que el servidor Python esté ejecutándose'
            });
        }

        if (error.response) {
            return res.status(error.response.status).json({
                error: 'backend_error',
                message: error.response.data?.detail || 'Error del backend',
                details: error.response.data
            });
        }

        if (error.code === 'ETIMEDOUT' || error.code === 'ECONNABORTED') {
            return res.status(504).json({
                error: 'timeout',
                message: 'Timeout esperando respuesta del backend',
                details: `El backend tardó más de ${CONFIG.API_TIMEOUT}ms en responder`
            });
        }

        res.status(500).json({
            error: 'internal_error',
            message: error.message
        });
    }
});

/**
 * GET /api/status
 * Estado del simulador y conexión con backend
 */
app.get('/api/status', async (req, res) => {
    let backendStatus = 'unknown';
    let backendDetails = null;

    try {
        const response = await backendClient.get('/health', { timeout: 5000 });
        backendStatus = response.status === 200 ? 'healthy' : 'unhealthy';
        backendDetails = response.data;
    } catch (error) {
        backendStatus = 'unreachable';
        backendDetails = { error: error.message };
    }

    res.json({
        service: 'simulador-whatsapp',
        version: '1.0.0',
        status: 'running',
        backend: {
            url: CONFIG.BACKEND_URL,
            status: backendStatus,
            details: backendDetails
        },
        config: {
            port: CONFIG.PORT,
            cors_origins: CONFIG.CORS_ORIGINS,
            api_timeout: CONFIG.API_TIMEOUT
        },
        timestamp: new Date().toISOString()
    });
});

/**
 * GET /api/health
 * Health check simple
 */
app.get('/api/health', (req, res) => {
    res.json({
        status: 'ok',
        service: 'simulador-whatsapp',
        timestamp: new Date().toISOString()
    });
});

/**
 * GET /api/patients/:phone
 * Buscar paciente por teléfono (proxy al backend)
 */
app.get('/api/patients/:phone', async (req, res) => {
    try {
        const { phone } = req.params;
        const cleanPhone = phone.replace('@c.us', '').replace(/\D/g, '');

        const response = await backendClient.get(`/api/whatsapp-agent/patient/${cleanPhone}`);
        res.json(response.data);

    } catch (error) {
        if (error.response?.status === 404) {
            return res.status(404).json({
                error: 'not_found',
                message: 'Paciente no encontrado'
            });
        }

        res.status(500).json({
            error: 'backend_error',
            message: error.message
        });
    }
});

/**
 * POST /api/simulate-time
 * Simular fecha/hora para pruebas (opcional)
 */
app.post('/api/simulate-time', (req, res) => {
    const { date, time } = req.body;

    if (!date || !time) {
        return res.status(400).json({
            error: 'Se requieren "date" y "time"',
            example: { date: '2026-02-15', time: '14:30' }
        });
    }

    // Aquí podrías guardar en memoria o BD la fecha simulada
    // Por ahora solo confirmamos que se recibió
    res.json({
        success: true,
        simulated_datetime: `${date}T${time}:00.000Z`,
        message: 'Fecha simulada configurada (solo en memoria del frontend)'
    });
});

// ============================================================================
// ERROR HANDLERS
// ============================================================================

// 404 handler
app.use((req, res) => {
    res.status(404).json({
        error: 'not_found',
        message: `Endpoint no encontrado: ${req.method} ${req.path}`,
        available_endpoints: [
            'GET  /',
            'POST /api/message',
            'GET  /api/status',
            'GET  /api/health',
            'GET  /api/patients/:phone',
            'POST /api/simulate-time'
        ]
    });
});

// Error handler general
app.use((err, req, res, next) => {
    console.error('Error no manejado:', err);
    res.status(500).json({
        error: 'internal_server_error',
        message: err.message
    });
});

// ============================================================================
// INICIO DEL SERVIDOR
// ============================================================================

async function checkBackend() {
    try {
        await backendClient.get('/health', { timeout: 5000 });
        console.log(`✅ Backend disponible en ${CONFIG.BACKEND_URL}`);
        return true;
    } catch (error) {
        console.warn(`⚠️  Backend no disponible en ${CONFIG.BACKEND_URL}`);
        console.warn(`   El simulador funcionará, pero no podrá procesar mensajes`);
        return false;
    }
}

async function start() {
    console.log('\n' + '='.repeat(60));
    console.log('🚀 Iniciando Simulador WhatsApp HTTP Server');
    console.log('='.repeat(60));
    console.log(`   Puerto: ${CONFIG.PORT}`);
    console.log(`   Backend: ${CONFIG.BACKEND_URL}`);
    console.log(`   CORS: ${CONFIG.CORS_ORIGINS.join(', ')}`);
    console.log('='.repeat(60) + '\n');

    // Verificar backend
    await checkBackend();

    // Iniciar servidor
    app.listen(CONFIG.PORT, () => {
        console.log(`\n✅ Servidor escuchando en puerto ${CONFIG.PORT}`);
        console.log(`\n📱 Abrir simulador en:`);
        console.log(`   http://localhost:${CONFIG.PORT}`);
        console.log(`   http://127.0.0.1:${CONFIG.PORT}\n`);
    });
}

// Manejo de señales
process.on('SIGINT', () => {
    console.log('\n\n👋 Cerrando servidor...');
    process.exit(0);
});

process.on('SIGTERM', () => {
    console.log('\n\n👋 Cerrando servidor...');
    process.exit(0);
});

// Iniciar
start().catch((error) => {
    console.error('❌ Error fatal:', error);
    process.exit(1);
});
