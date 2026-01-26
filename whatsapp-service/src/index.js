/**
 * Podoskin WhatsApp Service
 * =========================
 *
 * Servicio aislado que conecta WhatsApp con el agente LangGraph de Python.
 *
 * Flujo:
 * 1. Recibe mensaje de WhatsApp
 * 2. Envía al backend Python via HTTP
 * 3. Recibe respuesta del agente
 * 4. Envía respuesta por WhatsApp
 */

require('dotenv').config();
const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const express = require('express');
const { sendToAgent, checkBackendHealth } = require('./api-client');
const logger = require('./logger');

// ============================================================================
// CONFIGURACIÓN
// ============================================================================

const CONFIG = {
    BACKEND_URL: process.env.BACKEND_URL || 'http://localhost:8000',
    HTTP_PORT: process.env.HTTP_PORT || 3001,
    SESSION_PATH: process.env.SESSION_PATH || './session',
    ALLOWED_NUMBERS: process.env.ALLOWED_NUMBERS ? process.env.ALLOWED_NUMBERS.split(',').filter(n => n.trim()) : [], // Vacío = todos
};

// ============================================================================
// CLIENTE WHATSAPP
// ============================================================================

const client = new Client({
    authStrategy: new LocalAuth({
        dataPath: CONFIG.SESSION_PATH
    }),
    webVersionCache: {
        type: 'none' // Deshabilitar cache para evitar errores de versión
    },
    puppeteer: {
        headless: true,
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--no-first-run',
            '--no-zygote',
            '--disable-gpu'
        ]
    }
});

// Estado del servicio
let serviceStatus = {
    whatsapp: 'disconnected',
    backend: 'unknown',
    qrCode: null,
    lastMessage: null
};

// ============================================================================
// EVENTOS WHATSAPP
// ============================================================================

client.on('qr', (qr) => {
    logger.info('📱 Escanea el código QR para conectar WhatsApp');
    qrcode.generate(qr, { small: true });
    serviceStatus.qrCode = qr;
    serviceStatus.whatsapp = 'waiting_qr';
});

client.on('ready', () => {
    logger.info('✅ WhatsApp conectado y listo');
    serviceStatus.whatsapp = 'connected';
    serviceStatus.qrCode = null;
});

client.on('authenticated', () => {
    logger.info('🔐 Sesión autenticada');
});

client.on('auth_failure', (msg) => {
    logger.error('❌ Error de autenticación:', msg);
    serviceStatus.whatsapp = 'auth_failed';
});

client.on('disconnected', (reason) => {
    logger.warn('⚠️ WhatsApp desconectado:', reason);
    serviceStatus.whatsapp = 'disconnected';
});

// ============================================================================
// MANEJO DE MENSAJES
// ============================================================================

client.on('message', async (message) => {
    try {
        // Ignorar mensajes de grupos
        if (message.from.includes('@g.us')) {
            logger.debug('Mensaje de grupo ignorado');
            return;
        }

        // Ignorar mensajes propios
        if (message.fromMe) {
            return;
        }

        // Filtrar números si hay lista blanca
        if (CONFIG.ALLOWED_NUMBERS.length > 0) {
            const senderNumber = message.from.replace('@c.us', '');
            if (!CONFIG.ALLOWED_NUMBERS.includes(senderNumber)) {
                logger.debug(`Número no permitido: ${senderNumber}`);
                return;
            }
        }

        const chatId = message.from;
        const messageBody = message.body;
        const senderName = message._data.notifyName || 'Usuario';

        logger.info(`📩 Mensaje recibido de ${senderName} (${chatId}): ${messageBody.substring(0, 50)}...`);

        serviceStatus.lastMessage = {
            from: chatId,
            body: messageBody.substring(0, 100),
            timestamp: new Date().toISOString()
        };

        // Enviar "escribiendo..." (solo si es posible)
        try {
            const chat = await message.getChat();
            await chat.sendStateTyping();
        } catch (e) {
            logger.debug('No se pudo enviar estado de escritura');
        }

        // Enviar al agente Python
        const response = await sendToAgent({
            chat_id: chatId,
            message: messageBody,
            sender_name: senderName,
            timestamp: new Date().toISOString()
        });

        // Enviar respuesta - Con sendSeen: false para evitar el bug
        if (response && response.response) {
            try {
                // SOLUCIÓN: Usar sendSeen: false en options
                await client.sendMessage(chatId, response.response, {
                    sendSeen: false  // Evita el bug de markedUnread
                });
                logger.info(`📤 Respuesta enviada a  ${chatId}`);
            } catch (sendError) {
                logger.error(`❌ Error enviando respuesta: ${sendError.message}`);
                logger.debug(`Stack: ${sendError.stack}`);
            }
        } else if (response && response.error) {
            logger.error(`Error del agente: ${response.error}`);
        }

    } catch (error) {
        logger.error('Error procesando mensaje:', error);
        // No intentar enviar mensaje de error para evitar más fallos
    }
});

// ============================================================================
// SERVIDOR HTTP (Para status y control)
// ============================================================================

const app = express();
app.use(express.json());

// Status del servicio
app.get('/status', async (req, res) => {
    // Verificar backend
    const backendHealthy = await checkBackendHealth();
    serviceStatus.backend = backendHealthy ? 'healthy' : 'unhealthy';

    res.json({
        service: 'podoskin-whatsapp',
        ...serviceStatus,
        config: {
            backend_url: CONFIG.BACKEND_URL,
            allowed_numbers: CONFIG.ALLOWED_NUMBERS.length || 'all'
        }
    });
});

// Obtener QR como texto
app.get('/qr', (req, res) => {
    if (serviceStatus.qrCode) {
        res.json({ qr: serviceStatus.qrCode });
    } else if (serviceStatus.whatsapp === 'connected') {
        res.json({ message: 'Ya conectado, no se requiere QR' });
    } else {
        res.status(404).json({ error: 'QR no disponible' });
    }
});

// Enviar mensaje manualmente (para testing)
app.post('/send', async (req, res) => {
    try {
        const { to, message } = req.body;

        if (!to || !message) {
            return res.status(400).json({ error: 'Se requiere "to" y "message"' });
        }

        // Formatear número
        const chatId = to.includes('@c.us') ? to : `${to}@c.us`;

        await client.sendMessage(chatId, message);

        res.json({ success: true, sent_to: chatId });
    } catch (error) {
        logger.error('Error enviando mensaje:', error);
        res.status(500).json({ error: error.message });
    }
});

// Health check
app.get('/health', (req, res) => {
    res.json({ status: 'ok', whatsapp: serviceStatus.whatsapp });
});

// ============================================================================
// INICIO
// ============================================================================

async function start() {
    logger.info('🚀 Iniciando Podoskin WhatsApp Service...');
    logger.info(`   Backend URL: ${CONFIG.BACKEND_URL}`);
    logger.info(`   HTTP Port: ${CONFIG.HTTP_PORT}`);

    // Verificar backend
    const backendHealthy = await checkBackendHealth();
    if (!backendHealthy) {
        logger.warn('⚠️ Backend no disponible, continuando de todos modos...');
    }

    // Iniciar servidor HTTP
    app.listen(CONFIG.HTTP_PORT, () => {
        logger.info(`📡 Servidor HTTP escuchando en puerto ${CONFIG.HTTP_PORT}`);
    });

    // Iniciar cliente WhatsApp
    logger.info('📱 Inicializando cliente WhatsApp...');
    await client.initialize();
}

// Manejo de señales
process.on('SIGINT', async () => {
    logger.info('Cerrando servicio...');
    await client.destroy();
    process.exit(0);
});

start().catch((error) => {
    logger.error('Error fatal:', error);
    process.exit(1);
});
