let usuarios = null;
let usuarioActivo = null;
let fechaSimulada = null;

const usuariosPorDefecto = {
    "pacientes": [
        { "nombre": "Juan Pérez", "telefono": "+526649876543", "chat_id": "526649876543@c.us", "color": "#25D366" },
        { "nombre": "María López", "telefono": "+526641234567", "chat_id": "526641234567@c.us", "color": "#00A884" },
        { "nombre": "Carlos Ruiz", "telefono": "+526645678901", "chat_id": "526645678901@c.us", "color": "#34B7F1" }
    ],
    "doctores": [
        { "nombre": "Dr. Santiago Ornelas", "telefono": "+526641111111", "chat_id": "526641111111@c.us", "especialidad": "Medicina General", "color": "#128C7E" },
        { "nombre": "Dra. Joana Médica", "telefono": "+526642222222", "chat_id": "526642222222@c.us", "especialidad": "Medicina General", "color": "#075E54" }
    ],
    "admin": { "nombre": "Administrador", "telefono": "+526641234567", "chat_id": "526641234567@c.us", "color": "#FF6B6B" }
};

const mensajesPrueba = {
    paciente: [ 
        "Hola, necesito agendar una cita", 
        "¿Cuándo tienen disponibilidad?", 
        "Quiero cancelar mi cita del martes",
        "¿A qué hora es mi próxima cita?",
        "Necesito reagendar para la próxima semana"
    ],
    doctor: [ 
        "¿Cuántas citas tengo hoy?", 
        "Buscar paciente María López",
        "Reagendar cita de Juan Pérez para mañana",
        "¿Qué pacientes tengo esta tarde?",
        "Registrar consulta completada para Carlos Ruiz",
        "Dame un reporte de la semana"
    ],
    admin: [ 
        "Reporte de citas de hoy", 
        "¿Cuántos pacientes atendimos esta semana?",
        "Estadísticas de cancelaciones",
        "¿Cómo está el balance de doctores?"
    ]
};

// Inicialización
document.addEventListener('DOMContentLoaded', () => {
    cargarUsuarios();
    configurarEventos();
    const hoy = new Date().toISOString().split('T')[0];
    document.getElementById('datePicker').value = hoy;
    document.getElementById('timePicker').value = "10:00";
});

function cargarUsuarios() {
    const data = localStorage.getItem('usuarios');
    usuarios = data ? JSON.parse(data) : usuariosPorDefecto;
    renderizarListaUsuarios();
}

function renderizarListaUsuarios() {
    const container = document.getElementById('userList');
    container.innerHTML = '';

    // Admin
    renderSection(container, 'ADMIN', [usuarios.admin]);
    // Pacientes
    renderSection(container, 'PACIENTES', usuarios.pacientes);
    // Doctores
    renderSection(container, 'DOCTORES', usuarios.doctores);
}

function renderSection(container, title, items) {
    const titleDiv = document.createElement('div');
    titleDiv.className = 'section-title';
    titleDiv.textContent = title;
    container.appendChild(titleDiv);

    items.forEach(user => {
        const div = document.createElement('div');
        div.className = 'user-item';
        if (usuarioActivo && usuarioActivo.chat_id === user.chat_id) div.classList.add('active');
        
        div.onclick = () => seleccionarUsuario(user);

        const initials = user.nombre.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
        
        div.innerHTML = `
            <div class="user-avatar" style="background-color: ${user.color || '#ccc'}">${initials}</div>
            <div class="user-info">
                <div class="user-name">${user.nombre}</div>
                <div class="user-phone">${user.telefono}</div>
            </div>
        `;
        container.appendChild(div);
    });
}

function seleccionarUsuario(user) {
    usuarioActivo = user;
    renderizarListaUsuarios();
    
    document.getElementById('chatTitle').textContent = `Chat con ${user.nombre}`;
    document.getElementById('chatMessages').innerHTML = '';
    
    // Update Quick Replies
    const qrContainer = document.getElementById('quickReplies');
    qrContainer.innerHTML = '';
    
    let tipo = 'paciente';
    if (usuarios.doctores.find(d => d.chat_id === user.chat_id)) tipo = 'doctor';
    if (usuarios.admin.chat_id === user.chat_id) tipo = 'admin';

    mensajesPrueba[tipo].forEach(text => {
        const btn = document.createElement('button');
        btn.className = 'reply-btn';
        btn.textContent = text;
        btn.onclick = () => {
            document.getElementById('messageInput').value = text;
            enviarMensajeConTipeo();
        };
        qrContainer.appendChild(btn);
    });
}

function configurarEventos() {
    document.getElementById('messageInput').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') enviarMensajeConTipeo();
    });

    document.getElementById('btnEnviar').onclick = enviarMensajeConTipeo;
    document.getElementById('btnAplicarFecha').onclick = aplicarFechaSimulada;
    document.getElementById('btnAhora').onclick = usarFechaActual;
    document.getElementById('btnEditarUsuarios').onclick = abrirEditorUsuarios;
    document.getElementById('btnLimpiarChat').onclick = limpiarChat;
    document.getElementById('btnVerificarConexion').onclick = verificarConexionBackend;
    document.getElementById('btnGuardarJSON').onclick = guardarUsuarios;
    document.getElementById('btnCerrarModal').onclick = cerrarModal;
    
    // Verificar conexión inicial
    verificarConexionBackend();
}

// FUNCIÓN DUPLICADA ELIMINADA - Se usa enviarMensajeConTipeo

function mostrarRespuestaBot(respuesta) {
    let text = "Sin respuesta del servidor";
    
    // Manejar diferentes formatos de respuesta
    if (respuesta.response) {
        text = respuesta.response;
    } else if (respuesta.reply) {
        text = respuesta.reply;
    } else if (respuesta.message) {
        text = respuesta.message;
    } else if (respuesta.error) {
        text = `❌ Error: ${respuesta.error}`;
    }
    
    agregarMensaje({
        sender: '🤖 Sistema Médico',
        text: text,
        timestamp: new Date().toISOString(),
        esBot: true
    });
}

function agregarMensaje({ sender, text, timestamp, esBot }) {
    const container = document.getElementById('chatMessages');
    const div = document.createElement('div');
    div.className = `message ${esBot ? 'received' : 'sent'}`;
    
    const date = new Date(timestamp);
    const timeStr = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    // Convertir saltos de línea a <br> para HTML
    const formattedText = text.replace(/\n/g, '<br>');

    div.innerHTML = `
        <div class="message-text">${formattedText}</div>
        <div class="message-time">${timeStr}</div>
    `;
    
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

// Simulador de Tiempo
function obtenerTimestampSimulado() {
    if (fechaSimulada) {
        return fechaSimulada.toISOString();
    }
    return new Date().toISOString();
}

function aplicarFechaSimulada() {
    const fecha = document.getElementById('datePicker').value;
    const hora = document.getElementById('timePicker').value;
    if (!fecha || !hora) return;
    
    fechaSimulada = new Date(`${fecha}T${hora}`);
    alert(`Fecha simulada activada: ${fechaSimulada.toLocaleString()}`);
}

function usarFechaActual() {
    fechaSimulada = null;
    const hoy = new Date().toISOString().split('T')[0];
    document.getElementById('datePicker').value = hoy;
    document.getElementById('timePicker').value = new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', hour12: false});
    alert('Usando fecha y hora real');
}

// Editor de Usuarios
function abrirEditorUsuarios() {
    const modal = document.getElementById('modalEditor');
    document.getElementById('jsonEditor').value = JSON.stringify(usuarios, null, 2);
    modal.style.display = 'block';
}

function cerrarModal() {
    document.getElementById('modalEditor').style.display = 'none';
}

function guardarUsuarios() {
    const jsonStr = document.getElementById('jsonEditor').value;
    try {
        const data = JSON.parse(jsonStr);
        localStorage.setItem('usuarios', JSON.stringify(data));
        usuarios = data;
        renderizarListaUsuarios();
        cerrarModal();
        alert('✅ Usuarios actualizados correctamente');
    } catch (e) {
        alert('❌ JSON inválido: ' + e.message);
    }
}

// Funciones adicionales para la interfaz médica

function limpiarChat() {
    document.getElementById('chatMessages').innerHTML = '';
}

async function verificarConexionBackend() {
    const statusDot = document.getElementById('statusDot');
    const statusText = document.getElementById('statusText');
    const serverStatus = document.getElementById('serverStatus');
    
    try {
        // Verificar servidor simulador primero
        const backendUrl = window.location.origin.replace('-3002.', '-8002.');
        const response = await fetch(`${backendUrl}/api/status`, {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' }
        });
        
        if (response.ok) {
            // Conectado directamente al backend
            if (statusDot) {
                statusDot.className = 'status-dot online';
                statusText.textContent = 'Conectado';
            }
            if (serverStatus) {
                serverStatus.textContent = '🟢 Activo';
            }
            
            console.log('✅ Backend disponible en puerto 8000');
        } else {
            throw new Error('Backend no disponible');
        }
    } catch (error) {
        console.warn('⚠️ No se pudo conectar al backend:', error);
        if (statusDot) {
            statusDot.className = 'status-dot offline';
            statusText.textContent = 'Desconectado';
        }
        if (serverStatus) serverStatus.textContent = '🔴 Backend Inactivo';
    }
}

// Agregar indicador visual de tipeo (simulado)
function mostrarIndicadorTipeo() {
    const container = document.getElementById('chatMessages');
    const div = document.createElement('div');
    div.className = 'message received typing-indicator';
    div.id = 'typing-indicator';
    
    div.innerHTML = `
        <div class="message-text">
            <div class="typing-dots">
                <span></span>
                <span></span>
                <span></span>
            </div>
            Sistema médico escribiendo...
        </div>
    `;
    
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function ocultarIndicadorTipeo() {
    const indicator = document.getElementById('typing-indicator');
    if (indicator) {
        indicator.remove();
    }
}

// Mejorar función enviarMensaje con indicador de tipeo
async function enviarMensajeConTipeo() {
    const input = document.getElementById('messageInput');
    const mensaje = input.value.trim();
    
    if (!mensaje || !usuarioActivo) return;
    
    input.value = '';
    
    const timestamp = obtenerTimestampSimulado();
    
    agregarMensaje({
        sender: usuarioActivo.nombre,
        text: mensaje,
        timestamp: timestamp,
        esBot: false
    });

    const payload = {
        chat_id: usuarioActivo.chat_id,
        message: mensaje,
        sender_name: usuarioActivo.nombre,
        timestamp: timestamp,
        thread_id: usuarioActivo.telefono.replace('+', '')
    };

    // Mostrar indicador de tipeo
    mostrarIndicadorTipeo();
    
    try {
        // Usar endpoint directo del backend
        const backendUrl = window.location.origin.replace('-3002.', '-8002.');
        const response = await fetch(`${backendUrl}/api/whatsapp-agent/message`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        // Simular delay de respuesta más realista
        await new Promise(resolve => setTimeout(resolve, 800));
        
        ocultarIndicadorTipeo();
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.message || errorData.error || 'Error del servidor');
        }
        
        const respuesta = await response.json();
        
        // Extraer la respuesta del backend
        if (respuesta.success && respuesta.response) {
            agregarMensaje({
                sender: '🤖 Sistema Médico',
                text: respuesta.response,
                timestamp: new Date().toISOString(),
                esBot: true
            });
        } else {
            throw new Error(respuesta.error || 'Sin respuesta del sistema');
        }
    } catch (error) {
        ocultarIndicadorTipeo();
        console.error('Error al enviar mensaje:', error);
        
        let errorMsg = '❌ Error de conexión. ';
        if (error.message.includes('backend_unavailable')) {
            errorMsg += 'El backend Python no está disponible. Inicia el servidor con: python app.py';
        } else if (error.message.includes('timeout')) {
            errorMsg += 'El servidor tardó mucho en responder. Intenta de nuevo.';
        } else {
            errorMsg += error.message;
        }
        
        agregarMensaje({
            sender: '❌ Sistema',
            text: errorMsg,
            timestamp: new Date().toISOString(),
            esBot: true
        });
    }
}

// Función principal de envío se usa enviarMensajeConTipeo directamente
