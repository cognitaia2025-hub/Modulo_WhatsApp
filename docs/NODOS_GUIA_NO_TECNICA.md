# 🤖 Guía de Nodos del Sistema - Lenguaje Simple

> **Para personas sin conocimientos técnicos**  
> Esta guía explica cómo funciona cada parte del sistema de asistente de WhatsApp

---

## 🎯 ¿Qué es un Nodo?

Un **nodo** es como una estación en una cadena de montaje. Cada nodo tiene una tarea específica que hacer. Cuando llega un mensaje de WhatsApp, pasa por varios nodos en orden, y cada uno hace su trabajo hasta que finalmente se envía la respuesta.

**Piensa en ello como:**
- 📨 Llega un mensaje → 
- 🔄 Pasa por varios nodos (cada uno hace algo) → 
- ✅ Sale una respuesta

---

## 📋 Nodos del Sistema (En orden de ejecución)

### 1. 🆔 Nodo de Identificación de Usuario

**¿Qué hace?**  
Identifica quién está escribiendo por WhatsApp.

**¿Cómo funciona?**
- Lee el número de teléfono de quien escribe
- Busca si ya está registrado en el sistema
- Si es nuevo, lo registra automáticamente
- Identifica si es:
  - 👨‍⚕️ **Doctor** (puede agendar para pacientes)
  - 👤 **Paciente** (puede agendar para sí mismo)
  - 👑 **Administrador** (puede hacer todo)
  - 🙋 **Usuario personal** (usa calendario personal)

**Ejemplo:**
- Juan escribe por primera vez → Se registra como "paciente"
- Dr. García escribe → Se identifica como "doctor"

**¿Usa inteligencia artificial?** ❌ No  
Simplemente busca en la base de datos.

---

### 2. 💾 Nodo de Caché de Sesión

**¿Qué hace?**  
Recuerda la conversación anterior para dar contexto.

**¿Cómo funciona?**
- Busca si ya habías hablado antes en las últimas 24 horas
- Si sí, recupera los últimos mensajes
- Esto ayuda a que el asistente entienda el contexto

**Ejemplo:**
- Tú: "Quiero agendar una cita"
- Asistente: "¿Para qué día?"
- Tú: "Para mañana" ← El sistema recuerda que estamos hablando de citas

**¿Usa inteligencia artificial?** ❌ No  
Solo recupera información guardada.

---

### 3. 🧠 Nodo de Clasificación Inteligente

**¿Qué hace?**  
Decide de qué tipo es tu solicitud.

**¿Cómo funciona?**
- Lee tu mensaje
- Decide si estás pidiendo:
  - 🏥 **Cita médica** ("agendar consulta con doctor")
  - 📅 **Evento personal** ("recordarme comprar pan")
  - 💬 **Conversación casual** ("hola", "gracias")

**Ejemplo:**
- "Necesito cita para mi paciente" → **Médica**
- "Recordarme llamar a mamá" → **Personal**
- "Buenos días" → **Chat casual**

**¿Usa inteligencia artificial?** ✅ Sí  
Un modelo de IA lee el mensaje y lo clasifica.

---

### 4. 🔍 Nodo de Recuperación de Contexto

**¿Qué hace?**  
Busca información relevante de conversaciones pasadas.

**¿Cómo funciona?**  
Hay DOS versiones según tu solicitud:

#### 4A. Recuperación Personal
- Si pides algo personal (calendario, recordatorios)
- Busca tus eventos anteriores, recordatorios, etc.

#### 4B. Recuperación Médica
- Si pides algo médico (solo para doctores)
- Busca:
  - Lista de tus pacientes
  - Citas del día
  - Historiales médicos relevantes
  - Estadísticas de tu consultorio

**Ejemplo para doctor:**
- Escribes: "¿Cuántas citas tengo hoy?"
- El nodo busca: Tus citas programadas para hoy
- Respuesta: "Tienes 5 citas hoy: Juan a las 9:00, María a las 10:00..."

**¿Usa inteligencia artificial?** ✅ Sí (parcial)  
Usa IA para búsqueda inteligente en historiales, pero la mayoría son búsquedas normales.

---

### 5. 🛠️ Nodo de Selección de Herramientas

**¿Qué hace?**  
Decide qué acciones tomar para completar tu solicitud.

**¿Cómo funciona?**
- Lee tu mensaje
- Lee el contexto recuperado
- Decide qué herramientas usar (crear cita, buscar fecha, enviar recordatorio, etc.)
- Puede elegir varias herramientas si es necesario

**Ejemplo:**
- Tú: "Agendar cita para Juan mañana a las 3 PM"
- Nodo decide usar:
  1. Herramienta "buscar disponibilidad"
  2. Herramienta "crear cita médica"
  3. Herramienta "enviar confirmación"

**¿Usa inteligencia artificial?** ✅ Sí  
La IA elige las mejores herramientas para tu solicitud.

---

### 6. ⚙️ Nodo de Ejecución

**¿Qué hace?**  
Ejecuta las acciones decididas en el nodo anterior.

**¿Cómo funciona?**  
Hay DOS versiones:

#### 6A. Ejecución Personal
- Ejecuta acciones en tu calendario personal (Google Calendar)
- Crea eventos, busca fechas, actualiza recordatorios

#### 6B. Ejecución Médica
- Ejecuta acciones médicas:
  - Crear citas
  - Buscar pacientes
  - Actualizar historiales
  - Generar reportes

**Ejemplo médico:**
1. Crea la cita en la base de datos
2. Asigna automáticamente el doctor en turno
3. Verifica que no haya conflictos de horario
4. Envía confirmación al paciente

**¿Usa inteligencia artificial?** ❌ No  
Solo ejecuta las acciones de forma automática.

---

### 7. 🎙️ Nodo de Recepcionista Virtual

**¿Qué hace?**  
Mantiene una conversación paso a paso para agendar citas (solo para pacientes).

**¿Cómo funciona?**
1. Pregunta tu nombre
2. Muestra fechas y horarios disponibles
3. Pide que elijas una opción (A, B, C)
4. Confirma los detalles
5. Agenda la cita

**Ejemplo de conversación:**
```
Paciente: "Necesito una cita"
Sistema: "¡Claro! ¿Cuál es tu nombre completo?"

Paciente: "Juan Pérez"
Sistema: "Gracias Juan. Tenemos estos horarios:
         A) Mañana viernes 10:00 AM
         B) Lunes 31 a las 2:00 PM
         C) Martes 1 a las 4:00 PM
         ¿Cuál prefieres?"

Paciente: "La B"
Sistema: "Perfecto! Confirmado para lunes 31 a las 2:00 PM.
         Te recordaremos 24h antes."
```

**¿Usa inteligencia artificial?** ✅ Sí  
La IA mantiene la conversación natural y extrae la información.

---

### 8. 📝 Nodo de Generación de Respuesta

**¿Qué hace?**  
Crea la respuesta final que recibirás por WhatsApp.

**¿Cómo funciona?**
- Toma los resultados de todos los nodos anteriores
- Los resume en un mensaje claro y amigable
- Agrega emojis y formato bonito
- Envía el mensaje por WhatsApp

**Ejemplo:**
```
✅ ¡Listo! He agendado tu cita:

📅 Lunes 31 de Enero
🕐 2:00 PM - 2:30 PM
👨‍⚕️ Dr. Santiago Ornelas
📍 Consultorio #101

💬 Te recordaré 24 horas antes.
¿Necesitas algo más?
```

**¿Usa inteligencia artificial?** ✅ Sí  
La IA escribe respuestas naturales y amigables.

---

### 9. 💾 Nodo de Memoria a Largo Plazo

**¿Qué hace?**  
Guarda un resumen de la conversación para el futuro.

**¿Cómo funciona?**
- Crea un resumen corto de lo que pasó
- Lo guarda en la memoria del sistema
- Más tarde, cuando preguntes algo relacionado, puede recordarlo

**Ejemplo:**
- Hoy: "Agendé cita para Juan el lunes"
- En 2 semanas: "¿Cuándo fue la última cita de Juan?"
- Sistema: "Su última cita fue el lunes 31 de enero a las 2 PM"

**¿Usa inteligencia artificial?** ✅ Sí  
Usa IA para crear el resumen y búsqueda inteligente.

---

### 10. 🔄 Nodo de Sincronización con Google

**¿Qué hace?**  
Sincroniza las citas médicas con Google Calendar.

**¿Cómo funciona?**
- Cuando se crea una cita en el sistema
- Este nodo la agrega automáticamente a Google Calendar
- Si hay error, reintenta hasta 5 veces
- Mantiene ambos calendarios actualizados

**¿Para qué sirve?**
- Los doctores pueden ver sus citas en Google Calendar
- Se puede compartir el calendario con recepcionistas
- Las citas aparecen en teléfono, computadora, etc.

**¿Usa inteligencia artificial?** ❌ No  
Solo conecta con Google Calendar automáticamente.

---

## 🔄 Flujo Completo de un Mensaje

### Ejemplo: Paciente pide cita

```
1. 🆔 Identificación → "Es Juan Pérez, paciente nuevo"
2. 💾 Caché → "No tiene conversación previa"
3. 🧠 Clasificación → "Solicitud médica: agendar cita"
4. 🔍 Recuperación → "No hay contexto previo"
5. 🛠️ Selección → "Usar: buscar_horarios + recepcionista"
6. 🎙️ Recepcionista → Conversación paso a paso
7. ⚙️ Ejecución → Crea la cita, asigna doctor
8. 🔄 Sincronización → Agrega a Google Calendar
9. 📝 Respuesta → "✅ Cita confirmada para..."
10. 💾 Memoria → Guarda "Juan agendó cita el 31"
```

### Ejemplo: Doctor consulta agenda

```
1. 🆔 Identificación → "Es Dr. García, doctor"
2. 💾 Caché → "Habló hace 2 horas"
3. 🧠 Clasificación → "Solicitud médica: consultar agenda"
4. 🔍 Recuperación → Busca sus citas del día
5. 🛠️ Selección → "Usar: listar_citas_hoy"
6. ⚙️ Ejecución → Consulta base de datos
7. 📝 Respuesta → "Tienes 5 citas hoy: ..."
8. 💾 Memoria → Guarda "Doctor consultó agenda"
```

---

## ⚡ Tipos de Nodos

### 🤖 Nodos Automáticos (Sin IA)
- ✅ Más rápidos
- ✅ Más confiables
- ✅ Siempre dan el mismo resultado
- Ejemplos: Identificación, Caché, Ejecución

### 🧠 Nodos Inteligentes (Con IA)
- ✅ Entienden lenguaje natural
- ✅ Se adaptan a diferentes formas de hablar
- ✅ Pueden razonar y decidir
- Ejemplos: Clasificación, Selección, Recepcionista, Respuesta

---

## 🎯 Resumen para Entender Rápido

| Nodo | ¿Qué hace en una oración? | ¿Usa IA? |
|------|--------------------------|----------|
| 🆔 Identificación | "¿Quién eres?" | ❌ |
| 💾 Caché | "¿De qué hablamos antes?" | ❌ |
| 🧠 Clasificación | "¿Qué tipo de solicitud es?" | ✅ |
| 🔍 Recuperación | "¿Qué información relevante hay?" | ✅ |
| 🛠️ Selección | "¿Qué herramientas necesito?" | ✅ |
| ⚙️ Ejecución | "Hacer las acciones" | ❌ |
| 🎙️ Recepcionista | "Conversar para agendar" | ✅ |
| 📝 Respuesta | "Crear mensaje final" | ✅ |
| 💾 Memoria | "Recordar para el futuro" | ✅ |
| 🔄 Sincronización | "Actualizar Google Calendar" | ❌ |

---

## 💡 Preguntas Frecuentes

**¿Por qué tantos nodos?**  
Cada nodo hace una cosa bien. Es más fácil mantener y mejorar el sistema así.

**¿Todos los mensajes pasan por todos los nodos?**  
No siempre. Dependiendo del tipo de solicitud, algunos nodos se saltan.

**¿Qué pasa si un nodo falla?**  
El sistema tiene protecciones. Si algo falla, intenta de nuevo o usa un método alternativo.

**¿Dónde se guarda la información?**  
En una base de datos PostgreSQL segura y encriptada.

**¿Es seguro?**  
Sí. Toda la información está protegida y solo los usuarios autorizados pueden acceder.

---

**Documento actualizado:** 30 de Enero de 2026  
**Versión del sistema:** 2.0 (Consolidado)
