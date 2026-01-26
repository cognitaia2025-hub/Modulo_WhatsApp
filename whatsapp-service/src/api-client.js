/**
 * API Client - Conexión con Backend Python
 * =========================================
 *
 * Envía mensajes al agente LangGraph en el backend.
 */

const axios = require('axios');
const logger = require('./logger');

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';
const TIMEOUT = parseInt(process.env.API_TIMEOUT || '180000'); // 3 minutos para respuestas complejas

// Cliente axios configurado
const apiClient = axios.create({
    baseURL: BACKEND_URL,
    timeout: TIMEOUT,
    headers: {
        'Content-Type': 'application/json',
    }
});

/**
 * Envía mensaje al agente LangGraph
 *
 * @param {Object} data - Datos del mensaje
 * @param {string} data.chat_id - ID del chat de WhatsApp
 * @param {string} data.message - Contenido del mensaje
 * @param {string} data.sender_name - Nombre del remitente
 * @param {string} data.timestamp - Timestamp ISO
 * @returns {Promise<Object>} Respuesta del agente
 */
async function sendToAgent(data) {
    try {
        logger.debug(`Enviando al agente: ${JSON.stringify(data).substring(0, 200)}...`);

        const response = await apiClient.post('/api/whatsapp-agent/message', {
            chat_id: data.chat_id,
            message: data.message,
            sender_name: data.sender_name,
            timestamp: data.timestamp,
            // Thread ID para memoria por conversación
            thread_id: data.chat_id.replace('@c.us', '')
        });

        logger.debug(`Respuesta del agente: ${JSON.stringify(response.data).substring(0, 200)}...`);

        return response.data;

    } catch (error) {
        if (error.code === 'ECONNREFUSED') {
            logger.error(`❌ Backend no disponible en ${BACKEND_URL}`);
            return {
                error: 'backend_unavailable',
                response: null
            };
        }

        if (error.response) {
            // Error del servidor
            logger.error(`❌ Error del backend: ${error.response.status} - ${JSON.stringify(error.response.data)}`);
            return {
                error: error.response.data?.detail || 'server_error',
                response: null
            };
        }

        if (error.code === 'ETIMEDOUT' || error.code === 'ECONNABORTED') {
            logger.error(`❌ Timeout esperando respuesta del backend`);
            return {
                error: 'timeout',
                response: null
            };
        }

        logger.error(`❌ Error inesperado: ${error.message}`);
        return {
            error: error.message,
            response: null
        };
    }
}

/**
 * Verifica si el backend está disponible
 *
 * @returns {Promise<boolean>}
 */
async function checkBackendHealth() {
    try {
        const response = await apiClient.get('/health', { timeout: 5000 });
        return response.status === 200;
    } catch (error) {
        logger.warn(`Backend health check falló: ${error.message}`);
        return false;
    }
}

/**
 * Obtiene información de un paciente por teléfono
 *
 * @param {string} phone - Número de teléfono
 * @returns {Promise<Object|null>}
 */
async function getPatientByPhone(phone) {
    try {
        // Limpiar número
        const cleanPhone = phone.replace('@c.us', '').replace(/\D/g, '');

        const response = await apiClient.get(`/api/whatsapp-agent/patient/${cleanPhone}`);
        return response.data;

    } catch (error) {
        if (error.response?.status === 404) {
            return null; // Paciente no encontrado
        }
        logger.error(`Error buscando paciente: ${error.message}`);
        return null;
    }
}

module.exports = {
    sendToAgent,
    checkBackendHealth,
    getPatientByPhone
};
