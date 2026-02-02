# 📋 BRD - Asistente de WhatsApp para Citas Médicas

## Documento de Requerimientos de Negocio

**Proyecto:** Sistema de Agendamiento de Citas por WhatsApp  
**Versión:** 1.0  
**Fecha:** 30 de Enero 2026  
**Para replicar en:** N8N o cualquier herramienta de automatización

---

## 🎯 ¿Qué es este sistema?

Es un **asistente automático** que responde por WhatsApp para ayudar a pacientes y doctores a agendar, cancelar y consultar citas médicas. El paciente escribe como si hablara con una persona real, y el sistema entiende qué necesita y lo hace automáticamente.

---

## 👥 ¿Quiénes lo usan?

| Usuario | ¿Qué puede hacer? |
|---------|-------------------|
| **Paciente** | Agendar cita para sí mismo, cancelar, preguntar horarios |
| **Doctor** | Agendar citas para sus pacientes, ver su agenda del día, buscar pacientes |
| **Administrador** | Todo lo anterior + reportes y configuración |

---

## 📱 ¿Cómo funciona? (Flujo completo)

### PASO 1: Recibir el mensaje
- Alguien escribe un mensaje por WhatsApp
- El sistema lo recibe automáticamente

### PASO 2: Identificar quién escribe
- El sistema busca el número de teléfono en la base de datos
- Si es nuevo, lo registra como paciente
- Si ya existe, sabe si es paciente, doctor o admin
- **Pregunta clave:** ¿Ya te conozco? ¿Quién eres?

### PASO 3: Recordar la conversación anterior
- Si esta persona ya escribió antes (últimas 24 horas), el sistema recuerda de qué estaban hablando
- Ejemplo: Si ayer preguntó por horarios del viernes, hoy recuerda eso
- **Pregunta clave:** ¿De qué estábamos hablando?

### PASO 4: Entender qué quiere
- El sistema lee el mensaje y decide:
  - ¿Quiere una **cita médica**? (agendar, cancelar, consultar)
  - ¿Quiere algo **personal**? (recordatorio, evento)
  - ¿Solo está **saludando**? (hola, gracias, adiós)
- **Pregunta clave:** ¿Qué tipo de solicitud es?

### PASO 5: Buscar información necesaria
- Dependiendo de qué pidió, busca lo que necesita:
  - Si pide cita: busca horarios disponibles del doctor
  - Si cancela: busca la cita existente
  - Si pregunta: busca la información solicitada
- **Pregunta clave:** ¿Qué información necesito para responder?

### PASO 6: Pedir datos faltantes (Slot Filling)
- Si faltan datos para completar la acción, los pide uno por uno de forma natural:
  - "¿Para qué día te gustaría la cita?"
  - "¿En la mañana o en la tarde?"
  - "¿A qué hora específica?"
- **Pregunta clave:** ¿Tengo todo lo que necesito?

### PASO 7: Ejecutar la acción
- Una vez que tiene todos los datos, hace la acción:
  - Crea la cita en el calendario
  - Cancela la cita
  - Modifica el horario
  - etc.
- **Pregunta clave:** ¿Ya puedo hacerlo?

### PASO 8: Confirmar al usuario
- Responde confirmando lo que hizo:
  - "Listo! Tu cita quedó agendada para el viernes 15 de febrero a las 3:00 PM con el Dr. García"
- **Pregunta clave:** ¿Cómo le digo que ya está listo?

### PASO 9: Guardar en memoria
- Guarda esta conversación para recordarla después
- **Pregunta clave:** ¿Qué debo recordar para la próxima vez?

### PASO 10: Sincronizar con Google Calendar
- Actualiza el Google Calendar del doctor con la nueva cita
- **Pregunta clave:** ¿Está sincronizado con el calendario real?

---

## 💬 Ejemplos de Conversaciones

### Ejemplo 1: Paciente agenda cita

```
👤 Paciente: Hola, necesito una cita
🤖 Sistema: ¡Hola Juan! ¿Para qué día te gustaría la cita?
👤 Paciente: Para mañana
🤖 Sistema: Perfecto, para mañana. ¿Prefieres en la mañana o en la tarde?
👤 Paciente: En la tarde
🤖 Sistema: Tengo disponibilidad a las 2:00 PM, 3:00 PM y 4:00 PM. ¿Cuál prefieres?
👤 Paciente: A las 3
🤖 Sistema: ¡Perfecto! Tu cita quedó agendada para mañana viernes a las 3:00 PM con el Dr. Ornelas. Te llegará un recordatorio. ¿Necesitas algo más?
```

### Ejemplo 2: Paciente cancela cita

```
👤 Paciente: Necesito cancelar mi cita
🤖 Sistema: Veo que tienes una cita el viernes a las 3:00 PM. ¿Es esa la que quieres cancelar?
👤 Paciente: Sí, esa
🤖 Sistema: Listo, tu cita ha sido cancelada. ¿Quieres reagendar para otro día?
👤 Paciente: No, gracias
🤖 Sistema: De acuerdo. Cuando necesites una nueva cita, aquí estoy. ¡Que tengas buen día!
```

### Ejemplo 3: Doctor consulta su agenda

```
👨‍⚕️ Doctor: ¿Cuántas citas tengo hoy?
🤖 Sistema: Buenos días Dr. Ornelas. Hoy tienes 5 citas programadas:
   • 9:00 AM - Juan Pérez
   • 10:00 AM - María López
   • 11:30 AM - Carlos Ruiz
   • 3:00 PM - Ana García
   • 4:30 PM - Pedro Sánchez
¿Necesitas información de algún paciente en particular?
```

### Ejemplo 4: Doctor agenda para paciente

```
👨‍⚕️ Doctor: Agenda cita para María López mañana a las 10
🤖 Sistema: Perfecto. He agendado cita para María López mañana a las 10:00 AM. Le enviaré confirmación por WhatsApp. ¿Necesitas algo más?
```

---

## 🔧 Acciones que puede hacer el sistema

### Para Citas:
| Acción | Descripción |
|--------|-------------|
| **Agendar cita** | Crear una nueva cita médica |
| **Cancelar cita** | Eliminar una cita existente |
| **Reagendar cita** | Cambiar fecha/hora de una cita |
| **Consultar citas** | Ver citas programadas |
| **Buscar disponibilidad** | Ver horarios libres |

### Para Información:
| Acción | Descripción |
|--------|-------------|
| **Ver agenda del día** | Lista de citas del día (para doctores) |
| **Buscar paciente** | Encontrar información de un paciente |
| **Ver historial** | Consultar citas anteriores |

### Para Recordatorios:
| Acción | Descripción |
|--------|-------------|
| **Enviar recordatorio** | Notificar al paciente sobre su cita |
| **Confirmar asistencia** | Preguntar si asistirá a la cita |

---

## 📊 Datos que necesita el sistema

### Para agendar una cita se necesita:
1. **¿Quién?** - Nombre del paciente (o teléfono)
2. **¿Cuándo?** - Fecha de la cita
3. **¿A qué hora?** - Hora específica o preferencia (mañana/tarde)
4. **¿Con quién?** - Doctor (si hay varios)

### Para cancelar una cita se necesita:
1. **¿Cuál cita?** - Identificar la cita a cancelar

### Para consultar disponibilidad se necesita:
1. **¿Qué día?** - Fecha a consultar
2. **¿Con quién?** - Doctor específico (opcional)

---

## 🧠 Cómo entiende los mensajes

El sistema puede entender muchas formas de decir lo mismo:

### Para fechas:
- "mañana" → Día siguiente
- "el viernes" → Próximo viernes
- "la próxima semana" → Lunes de la próxima semana
- "15 de febrero" → Fecha específica
- "en 3 días" → Calcula la fecha

### Para horas:
- "en la mañana" → 9:00 AM - 12:00 PM
- "en la tarde" → 2:00 PM - 6:00 PM
- "a las 3" → 3:00 PM
- "temprano" → Primera hora disponible

### Para acciones:
- "quiero cita" / "necesito agendar" / "puedo sacar cita" → AGENDAR
- "cancelar" / "no voy a poder" / "quitar mi cita" → CANCELAR
- "cambiar" / "mover" / "reagendar" → REAGENDAR
- "qué horarios hay" / "cuándo puedo" → CONSULTAR DISPONIBILIDAD

---

## 📦 Información que guarda el sistema

### Del Paciente:
- Nombre completo
- Teléfono (WhatsApp)
- Historial de citas
- Preferencias (si prefiere mañana o tarde)

### Del Doctor:
- Nombre y especialidad
- Horarios de trabajo
- Días disponibles
- Citas programadas

### De las Citas:
- Paciente
- Doctor
- Fecha y hora
- Estado (confirmada, cancelada, completada)
- Notas

### De las Conversaciones:
- Mensajes recientes (últimas 24 horas)
- Contexto de la conversación
- Memoria a largo plazo (datos importantes)

---

## ⚠️ Reglas de Negocio

### Horarios:
- Solo se pueden agendar citas en horario laboral (8 AM - 6 PM)
- No se pueden agendar citas en fin de semana (configurable)
- Mínimo 1 hora entre citas

### Cancelaciones:
- Se puede cancelar hasta 2 horas antes de la cita
- Si cancela muy tarde, se registra

### Confirmaciones:
- El sistema envía recordatorio 24 horas antes
- El sistema envía recordatorio 1 hora antes

### Permisos:
- Paciente solo puede ver/modificar SUS citas
- Doctor puede ver/modificar citas de SUS pacientes
- Admin puede ver/modificar TODO

---

## 🔄 Flujo para N8N (Simplificado)

### Trigger:
```
[Webhook WhatsApp] → Recibe mensaje
```

### Nodos principales:
```
1. [Buscar Usuario] → ¿Existe en BD?
   ├── NO → [Crear Usuario Nuevo]
   └── SÍ → Continuar

2. [Buscar Conversación Anterior] → ¿Hay contexto previo?

3. [Clasificar Intención] → ¿Qué tipo de solicitud es?
   ├── AGENDAR → Flujo de agendamiento
   ├── CANCELAR → Flujo de cancelación
   ├── CONSULTAR → Flujo de consulta
   └── CHAT → Respuesta conversacional

4. [Flujo Agendamiento]:
   ├── [Verificar datos completos]
   │   ├── Falta fecha → [Preguntar fecha]
   │   ├── Falta hora → [Preguntar hora]
   │   └── Completo → Continuar
   ├── [Buscar disponibilidad]
   ├── [Crear cita en BD]
   ├── [Sincronizar Google Calendar]
   └── [Enviar confirmación]

5. [Guardar Conversación] → Memoria

6. [Responder WhatsApp] → Envía mensaje
```

---

## ✅ Checklist de Funcionalidades

### Básicas (MVP):
- [ ] Recibir mensajes de WhatsApp
- [ ] Identificar usuario por teléfono
- [ ] Registrar usuarios nuevos
- [ ] Entender intención del mensaje
- [ ] Agendar cita nueva
- [ ] Cancelar cita existente
- [ ] Consultar disponibilidad
- [ ] Responder por WhatsApp

### Intermedias:
- [ ] Recordar conversaciones anteriores
- [ ] Pedir datos faltantes naturalmente
- [ ] Sincronizar con Google Calendar
- [ ] Enviar recordatorios automáticos
- [ ] Permitir reagendar citas

### Avanzadas:
- [ ] Búsqueda inteligente de pacientes
- [ ] Reportes para doctores
- [ ] Múltiples doctores
- [ ] Preferencias de horario por paciente
- [ ] Memoria a largo plazo

---

## 📞 Mensajes de Error

| Situación | Respuesta del sistema |
|-----------|----------------------|
| No hay disponibilidad | "Lo siento, no hay horarios disponibles para ese día. ¿Te funciona otro día?" |
| Cita no encontrada | "No encontré ninguna cita a tu nombre. ¿Quieres agendar una nueva?" |
| Fuera de horario | "Ese horario está fuera del horario de atención. ¿Prefieres en la mañana o en la tarde?" |
| Error del sistema | "Disculpa, tuve un problema. ¿Puedes intentar de nuevo?" |
| No entendí | "No entendí bien. ¿Quieres agendar, cancelar o consultar una cita?" |

---

## 🎨 Personalización del Tono

El asistente debe ser:
- **Amigable** - Usar emojis ocasionalmente, ser cálido
- **Profesional** - No usar lenguaje coloquial excesivo
- **Eficiente** - Ir al punto, no dar vueltas
- **Empático** - Entender si el paciente está preocupado o tiene prisa

### Ejemplos de tono:
- ✅ "¡Perfecto! Tu cita quedó agendada para mañana a las 3 PM 📅"
- ❌ "OK, agendado."
- ✅ "Entiendo que necesitas cancelar. No hay problema, ya está cancelada."
- ❌ "Cancelado. Bye."

---

## 📈 Métricas a Medir

| Métrica | Descripción |
|---------|-------------|
| Citas agendadas por día | ¿Cuántas citas se agendan? |
| Tasa de cancelación | ¿Qué % de citas se cancelan? |
| Tiempo de respuesta | ¿Cuánto tarda en responder? |
| Mensajes por cita | ¿Cuántos mensajes se necesitan para agendar? |
| Usuarios nuevos | ¿Cuántos pacientes nuevos por día? |

---

## 🚀 Próximos Pasos para N8N

1. **Crear webhook** para recibir mensajes de WhatsApp
2. **Conectar base de datos** (PostgreSQL o la que uses)
3. **Configurar OpenAI/Claude** para entender mensajes
4. **Crear flujos** para cada tipo de solicitud
5. **Conectar Google Calendar** para sincronización
6. **Probar** con casos reales
7. **Ajustar** según feedback

---

**Fin del documento BRD**

*Este documento describe QUÉ debe hacer el sistema, no CÓMO se hace técnicamente. Para la implementación técnica, consultar la documentación de desarrollo.*
