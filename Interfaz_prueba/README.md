# 🏥 Simulador de Interfaz WhatsApp - Sistema Médico de Citas

Esta interfaz permite simular conversaciones de WhatsApp con el sistema médico completo para probar todas las funcionalidades: agendamiento, cancelación, consultas, reportes médicos y más.

## 🚀 Cómo usar el simulador

### 1. **Iniciar el Backend Médico**

**IMPORTANTE**: El sistema médico debe estar ejecutándose antes de usar el simulador.

#### Opción A: Script completo (Recomendado)
```powershell
# Desde la raíz del proyecto
.\start_project_whatsapp.ps1
```

#### Opción B: Solo backend
```bash
# Desde la raíz del proyecto  
python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

### 2. **Abrir el Simulador**
- Abre el archivo `index.html` en cualquier navegador moderno
- Verifica que el indicador de estado muestre "🟢 Conectado"

## 🩺 Funcionalidades del Sistema Médico

### 👥 Panel de Usuarios (Izquierda)

**Tipos de usuarios disponibles:**

#### 🏥 **DOCTORES**
- **Dr. Santiago Ornelas** (Medicina General)
- **Dra. Joana Médica** (Medicina General)

**Pueden hacer:**
- Consultar su agenda: "¿Qué citas tengo hoy?"
- Buscar pacientes: "Buscar paciente María López"
- Reagendar citas: "Mover cita de Juan Pérez al viernes"
- Ver reportes: "Dame un reporte de esta semana"
- Registrar consultas: "Paciente atendido, diagnóstico gripe"

#### 🏃‍♂️ **PACIENTES**
- **Juan Pérez García** (Control mensual)
- **María López Hernández** (Primera consulta)
- **Carlos Ruiz Mendoza** (Seguimiento post-op)
- **Ana Martín Torres** (Control presión)

**Pueden hacer:**
- Solicitar citas: "Necesito una cita"
- Consultar sus citas: "¿Cuándo es mi próxima cita?"
- Cancelar/reagendar: "Quiero cancelar mi cita del martes"

#### ⚙️ **ADMINISTRADOR**
- **Admin Sistema** (Acceso completo)

**Puede hacer:**
- Reportes generales: "Estadísticas de esta semana"
- Analytics: "¿Cuántos pacientes atendimos?"
- Gestión del sistema: "Balance de carga de doctores"

### 💬 Chat Central (Centro)

- **Simulación realista** de WhatsApp con indicador de "escribiendo..."
- **Respuestas automáticas** del sistema médico
- **Historial de conversación** por usuario
- **Timestamps** reales o simulados

### ⏰ Simulador de Fecha/Hora (Derecha)

- **Pruebas temporales**: Simula citas en fechas específicas
- **Control de disponibilidad**: Verifica horarios médicos
- **Recordatorios**: Prueba notificaciones 24h antes

### ✏️ Quick Replies

**Sugerencias inteligentes** según el tipo de usuario:

**Para Pacientes:**
- "Hola, necesito agendar una cita"
- "¿Cuándo tienen disponibilidad?"
- "Quiero cancelar mi cita del martes"

**Para Doctores:**
- "¿Cuántas citas tengo hoy?"
- "Buscar paciente María López"
- "Dame un reporte de la semana"

**Para Admin:**
- "Estadísticas de cancelaciones"
- "Balance de carga de doctores"

## 📡 Conexión con el Sistema Real

### Endpoints utilizados:

```
🔹 Backend Principal: http://localhost:8000
🔹 Health Check: GET /health
🔹 Mensajes WhatsApp: POST /api/whatsapp-agent/message
```

### Formato de mensajes:

```json
{
    "chat_id": "526649876543@c.us",
    "message": "¿Qué citas tengo hoy?",
    "sender_name": "Dr. Santiago Ornelas",
    "timestamp": "2026-01-29T10:30:00Z",
    "thread_id": "526649876543"
}
```

## 🧪 Casos de Prueba Sugeridos

### 📋 **Flujo de Paciente Nuevo**
1. Seleccionar "Juan Pérez García"
2. Escribir: "Hola, necesito agendar una cita"
3. Seguir el flujo conversacional del recepcionista
4. Verificar sincronización con Google Calendar

### 📋 **Flujo de Doctor**
1. Seleccionar "Dr. Santiago Ornelas"  
2. Escribir: "¿Cuántas citas tengo mañana?"
3. Probar: "Buscar paciente María López"
4. Verificar acceso a herramientas médicas

### 📋 **Flujo de Reportes**
1. Seleccionar "Admin Sistema"
2. Escribir: "Reporte de citas de hoy"
3. Probar analytics: "¿Cuántos pacientes nuevos esta semana?"

### 📋 **Sistema de Turnos**
1. Con **MÚLTIPLES pacientes**, solicitar citas simultaneas
2. Verificar distribución equitativa entre doctores
3. Confirmar turnos rotativos funcionando

## 🔧 Configuración Avanzada

### Personalizar Usuarios

1. Click en **"Editar Usuarios"**
2. Modificar el JSON con nuevos usuarios:

```json
{
    "pacientes": [
        {
            "nombre": "Nuevo Paciente",
            "telefono": "+526647777777",
            "chat_id": "526647777777@c.us",
            "color": "#FF5722",
            "descripcion": "Paciente VIP"
        }
    ]
}
```

3. **Guardar cambios** para actualizar la interfaz

### Simular Horarios Específicos

1. **Configurar fecha/hora** en el panel derecho
2. **Aplicar** para que todos los mensajes usen ese timestamp
3. **Probar disponibilidades** médicas específicas

## 🚨 Solución de Problemas

### ❌ "No se pudo conectar con el backend"

1. **Verificar que el servidor esté corriendo**:
   ```bash
   curl http://localhost:8000/health
   ```

2. **Iniciar el backend**:
   ```powershell
   .\start_project_whatsapp.ps1
   ```

3. **Click en "Verificar Servidor"** en la interfaz

### ❌ Respuestas vacías o errores

1. **Revisar logs del backend** en la terminal
2. **Verificar PostgreSQL** esté corriendo
3. **Comprobar variables de entorno** (.env configurado)

### ❌ Usuarios no se guardan

1. **Verificar formato JSON** válido en el editor
2. **Revisar permisos** del navegador (localStorage)
3. **Recargar página** si persiste el problema

## 🎯 Objetivos de Testing

### ✅ **Funcionalidades a Validar**

- [ ] **Identificación automática** de usuarios (doctor vs paciente)
- [ ] **Sistema de turnos** equitativo entre doctores  
- [ ] **Agendamiento conversacional** con recepcionista IA
- [ ] **Sincronización** con Google Calendar
- [ ] **Búsqueda de pacientes** por nombre/teléfono
- [ ] **Reportes y analytics** médicos
- [ ] **Recordatorios automáticos** 24h antes
- [ ] **Manejo de errores** y reconexión
- [ ] **Clasificación inteligente** de mensajes (LLM)
- [ ] **Herramientas médicas** especializadas

### 📊 **Métricas Esperadas**

- **Tiempo de respuesta**: < 3 segundos
- **Precisión de clasificación**: > 95%
- **Disponibilidad del sistema**: 99%
- **Sincronización exitosa**: > 98%

## 🔗 Enlaces Útiles

- **📚 Documentación completa**: `../docs/`
- **🧪 Tests automatizados**: `../tests/`
- **🛠 Backend código**: `../src/`
- **📱 Servicio WhatsApp real**: `../whatsapp-service/`

---

## 💡 Notas del Desarrollador

Esta interfaz simula **exactamente** el comportamiento del sistema real de WhatsApp. Todos los endpoints, formatos y respuestas son idénticos al entorno de producción.

**Úsala para:**
- ✅ Probar nuevas funcionalidades
- ✅ Demostrar el sistema a stakeholders  
- ✅ Debugging y troubleshooting
- ✅ Training de usuarios finales
- ✅ Validación de casos de uso

¡El simulador es tu ambiente de pruebas seguro antes de tocar producción! 🚀
    "timestamp": "2026-01-28T10:30:00Z",
    "thread_id": "521234567890"
}
```

## 🎨 Quick Replies

Dependiendo del tipo de usuario seleccionado (Paciente o Doctor), aparecerán sugerencias de mensajes rápidos en el panel derecho para facilitar las pruebas.
