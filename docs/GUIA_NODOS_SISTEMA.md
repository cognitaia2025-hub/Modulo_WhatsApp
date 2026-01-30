# Guía del Sistema de Asistente WhatsApp

## ¿Cómo funciona el asistente?

Cuando un paciente o doctor envía un mensaje por WhatsApp, el sistema lo procesa a través de **13 pasos** (llamados "nodos") que trabajan en equipo para entender qué necesita la persona y darle la mejor respuesta posible.

Piensa en estos pasos como una recepcionista muy inteligente que:
1. Reconoce quién está llamando
2. Entiende qué necesita
3. Busca la información necesaria
4. Da una respuesta útil
5. Guarda notas para recordar la conversación

---

## Clasificación de Nodos

El sistema tiene **4 tipos de nodos**:

| Tipo | Descripción | Icono |
|------|-------------|-------|
| 🧠 **Inteligente (LLM)** | Usa inteligencia artificial para entender y generar texto | 🧠 |
| ⚡ **Automático** | Ejecuta lógica programada sin IA | ⚡ |
| 🔧 **Herramientas** | Ejecuta acciones como crear/modificar citas | 🔧 |
| 🗄️ **Base de Datos** | Lee o escribe en la base de datos | 🗄️ |
| 📅 **Google Calendar** | Se conecta con Google Calendar | 📅 |

---

## 🧠 NODOS INTELIGENTES (Usan IA/LLM)

Estos nodos utilizan modelos de inteligencia artificial (GPT-4, Claude) para entender el lenguaje natural y generar respuestas.

---

### 1. Clasificador Inteligente
📁 **Archivo:** `filtrado_inteligente_node.py`

🧠 **Tipo:** Inteligente (LLM)

**¿Qué hace?** Entiende qué tipo de ayuda necesita la persona analizando su mensaje con IA.

**Clasifica los mensajes en:**
- **Solicitud de cita:** "Quiero agendar una consulta"
- **Consulta médica:** "¿El doctor puede ver pacientes con diabetes?"
- **Agenda personal:** "¿Qué tengo programado mañana?" (solo doctores)
- **Conversación casual:** "Hola, buenos días"

**Ejemplo:** Si alguien escribe "necesito una cita para mañana", el sistema entiende que es una solicitud de cita y lo dirige al paso correcto.

---

### 2. Selector de Acciones
📁 **Archivo:** `seleccion_herramientas_node.py`

🧠 **Tipo:** Inteligente (LLM) + 🔧 Herramientas

**¿Qué hace?** Usa IA para decidir qué herramientas usar según lo que pidió el usuario.

**Herramientas disponibles:**
- Crear eventos en calendario
- Listar eventos existentes
- Modificar citas
- Cancelar citas
- Buscar horarios disponibles

**Ejemplo:** Si el doctor dice "agenda una reunión mañana a las 3pm", la IA analiza el mensaje y selecciona la herramienta de "crear evento".

---

### 3. Ejecutor de Calendario Personal
📁 **Archivo:** `ejecucion_herramientas_node.py`

🧠 **Tipo:** Inteligente (LLM) + 🔧 Herramientas + 📅 Google Calendar

**¿Qué hace?** Ejecuta las herramientas seleccionadas y usa IA para generar respuestas naturales con los resultados.

**Ejemplo:** Cuando un doctor dice "bloquea mi agenda de 2 a 4pm", este nodo:
1. Ejecuta la herramienta de crear evento
2. Usa IA para generar una respuesta amigable: "Listo! Tu agenda está bloqueada de 2 a 4pm"

**Uso:** Solo para doctores y personal.

---

### 4. Asistente Conversacional
📁 **Archivo:** `respuesta_conversacional_node.py`

🧠 **Tipo:** Inteligente (LLM)

**¿Qué hace?** Usa IA para responder mensajes de saludo, despedida o preguntas generales de forma natural y personalizada.

**Ejemplos:**
- "Hola" → "Hola Juan, ¿en qué puedo ayudarte hoy?"
- "Gracias" → "Con gusto! Estoy aquí para ayudarte"
- "¿Qué servicios ofrecen?" → Información general de la clínica

**Personalización:** La IA adapta el tono según si habla con un paciente, doctor o administrador.

---

### 5. Generador de Resumen
📁 **Archivo:** `generacion_resumen_node.py`

🧠 **Tipo:** Inteligente (LLM) + 🗄️ Base de Datos

**¿Qué hace?** Usa IA para crear un resumen breve e inteligente de cada conversación.

**Ejemplo de resumen generado:** "Juan solicitó cita. Se agendó para viernes 30 a las 09:30 con la Dra. Meraz."

**¿Para qué sirve?**
- Auditoría de conversaciones

- Recordar el contexto en futuras interacciones
- Estadísticas de uso del sistema

---

## ⚡ NODOS AUTOMÁTICOS (Sin IA)

Estos nodos ejecutan lógica programada sin necesidad de inteligencia artificial. Son más rápidos y predecibles.

---

### 6. Identificación del Usuario
📁 **Archivo:** `identificacion_usuario_node.py`

⚡ **Tipo:** Automático + 🗄️ Base de Datos

**¿Qué hace?** Reconoce quién está escribiendo buscando su número de teléfono en la base de datos.

**Ejemplo:** Cuando Juan Pérez envía un mensaje, el sistema busca su teléfono y recupera: nombre completo, tipo de usuario (paciente/doctor), historial de citas.

**Tipos de usuarios que reconoce:**
- Pacientes registrados
- Doctores de la clínica
- Administradores
- Personas nuevas (las registra automáticamente)

---

### 7. Memoria de Sesión
📁 **Archivo:** `session_manager.py` (en utils/)

⚡ **Tipo:** Automático + 🗄️ Base de Datos

**¿Qué hace?** Mantiene el contexto de conversación en una ventana de 24 horas usando checkpoints en la base de datos.

**Ejemplo:** Si Juan preguntó por citas hace 10 minutos y ahora responde "la opción B", el sistema recuerda que estaban hablando de horarios y no empieza de cero.

**Beneficio:** Conversaciones naturales y fluidas, como hablar con una persona real.

---

### 8. Buscador de Recuerdos Personales
📁 **Archivo:** `recuperacion_episodica_node.py`

⚡ **Tipo:** Automático + 🗄️ Base de Datos (pgvector)

**¿Qué hace?** Busca en la base de datos conversaciones pasadas relevantes usando búsqueda por similitud semántica (embeddings).

**Ejemplo:** Si el Dr. López pregunta "¿qué tenía pendiente?", busca en las notas de conversaciones anteriores usando vectores de similitud.

**Tecnología:** Usa pgvector para búsqueda semántica (no requiere LLM, solo embeddings pre-calculados).

---

### 9. Buscador de Información Médica
📁 **Archivo:** `recuperacion_medica_node.py`

⚡ **Tipo:** Automático + 🗄️ Base de Datos

**¿Qué hace?** Consulta la base de datos médica con queries SQL para obtener información de pacientes, citas e historiales.

**Ejemplo:** Cuando un doctor pregunta "¿cuántos pacientes atendí esta semana?", ejecuta queries en la base de datos médica.

**Información que puede consultar:**
- Historial de citas
- Datos de pacientes
- Estadísticas de consultas
- Información de doctores

---

### 10. Ejecutor de Calendario Médico
📁 **Archivo:** `ejecucion_medica_node.py`

⚡ **Tipo:** Automático + 🔧 Herramientas + 🗄️ Base de Datos

**¿Qué hace?** Ejecuta herramientas de calendario médico (crear citas, cancelar, modificar) directamente en la base de datos.

**Ejemplo:** Cuando se confirma una cita de un paciente, registra la cita en la tabla de citas médicas.

**Diferencia con ejecucion_herramientas:** Este es automático y enfocado en citas médicas. El otro usa LLM para generar respuestas.

---

### 11. Recepcionista Virtual
📁 **Archivo:** `recepcionista_node.py`

⚡ **Tipo:** Automático + 🗄️ Base de Datos

**¿Qué hace?** Guía a los pacientes paso a paso para agendar citas usando un flujo de estados predefinido (no requiere IA).

**Estados del flujo:**
1. `inicial` → Saluda al paciente
2. `solicitando_nombre` → Pide nombre si es nuevo
3. `mostrando_opciones` → Muestra horarios A, B, C
4. `esperando_seleccion` → Espera respuesta
5. `confirmando` → Agenda la cita
6. `completado` → Confirma con detalles

**Ejemplo de conversación:**
- Paciente: "Quiero una cita"
- Sistema: "Hola Juan! Estos son los horarios disponibles:
  A) Viernes 30, 08:30
  B) Viernes 30, 09:30
  C) Viernes 30, 10:30
  ¿Cuál prefieres?"
- Paciente: "B"
- Sistema: "Perfecto! Tu cita quedó agendada para el viernes 30 a las 09:30"

---

### 12. Guardián de Memoria
📁 **Archivo:** `persistencia_episodica_node.py`

⚡ **Tipo:** Automático + 🗄️ Base de Datos (pgvector)

**¿Qué hace?** Guarda los resúmenes generados en la base de datos para uso futuro, incluyendo embeddings para búsqueda semántica.

**Lo que guarda:**
- El resumen de la conversación
- Quién habló
- Cuándo fue
- Qué tipo de solicitud era
- Vector de embedding para búsqueda futura

**Beneficio:** El sistema "aprende" de cada conversación y puede dar mejor servicio en el futuro.

---

### 13. Sincronizador con Google Calendar
📁 **Archivo:** `sincronizador_hibrido_node.py`

⚡ **Tipo:** Automático + 📅 Google Calendar + 🗄️ Base de Datos

**¿Qué hace?** Sincroniza las citas entre la base de datos local y Google Calendar de forma automática.

**Ejemplo:** Cuando se agenda una cita, este nodo la crea también en el Google Calendar del doctor correspondiente.

**Arquitectura híbrida:**
- La base de datos es la fuente de verdad
- Google Calendar es solo para visualización
- Si falla Google, la cita sigue siendo válida en BD

---

## Tabla Resumen de Nodos

| # | Nombre | Archivo | 🧠 LLM | ⚡ Auto | 🔧 Herram. | 🗄️ BD | 📅 GCal |
|---|--------|---------|--------|--------|------------|-------|---------|
| 1 | Clasificador Inteligente | `filtrado_inteligente_node.py` | ✅ | | | | |
| 2 | Selector de Acciones | `seleccion_herramientas_node.py` | ✅ | | ✅ | | |
| 3 | Ejecutor Calendario Personal | `ejecucion_herramientas_node.py` | ✅ | | ✅ | | ✅ |
| 4 | Asistente Conversacional | `respuesta_conversacional_node.py` | ✅ | | | | |
| 5 | Generador de Resumen | `generacion_resumen_node.py` | ✅ | | | ✅ | |
| 6 | Identificación Usuario | `identificacion_usuario_node.py` | | ✅ | | ✅ | |
| 7 | Memoria de Sesión | `session_manager.py` | | ✅ | | ✅ | |
| 8 | Buscador Recuerdos | `recuperacion_episodica_node.py` | | ✅ | | ✅ | |
| 9 | Buscador Info Médica | `recuperacion_medica_node.py` | | ✅ | | ✅ | |
| 10 | Ejecutor Calendario Médico | `ejecucion_medica_node.py` | | ✅ | ✅ | ✅ | |
| 11 | Recepcionista Virtual | `recepcionista_node.py` | | ✅ | | ✅ | |
| 12 | Guardián de Memoria | `persistencia_episodica_node.py` | | ✅ | | ✅ | |
| 13 | Sincronizador Calendar | `sincronizador_hibrido_node.py` | | ✅ | | ✅ | ✅ |

**Totales:** 5 nodos con LLM | 8 nodos automáticos | 4 con herramientas | 11 con BD | 2 con Google Calendar

---

## Flujo de Ejemplo: Paciente Agenda Cita

```
Mensaje: "Hola, quiero una cita"
         ↓
[1] Identifica a Juan Pérez (paciente)
         ↓
[2] Recuerda que no hay conversación previa
         ↓
[3] Clasifica como "solicitud de cita"
         ↓
[9] Recepcionista muestra horarios A, B, C
         ↓
Mensaje: "B"
         ↓
[1] Identifica a Juan Pérez
         ↓
[2] Recuerda que estaba eligiendo horario
         ↓
[9] Recepcionista agenda la opción B
         ↓
[13] Sincroniza con Google Calendar
         ↓
[11] Genera resumen de la cita
         ↓
[12] Guarda en memoria
         ↓
Respuesta: "Tu cita quedó agendada para..."
```

---

## Flujo de Ejemplo: Doctor Consulta Agenda

```
Mensaje: "¿Qué citas tengo mañana?"
         ↓
[1] Identifica al Dr. López (doctor)
         ↓
[2] Verifica sesión activa
         ↓
[3] Clasifica como "agenda personal"
         ↓
[4] Busca en recuerdos del doctor
         ↓
[6] Selecciona herramienta "listar eventos"
         ↓
[7] Ejecuta consulta en calendario
         ↓
[11] Genera resumen
         ↓
[12] Guarda en memoria
         ↓
Respuesta: "Mañana tienes 5 citas programadas:
           08:30 - María García
           09:30 - Juan Pérez
           ..."
```

---

## Resumen de Capacidades

| Función | Pacientes | Doctores | Admin |
|---------|-----------|----------|-------|
| Agendar citas | ✅ | ✅ | ✅ |
| Cancelar citas | ✅ | ✅ | ✅ |
| Ver calendario | ❌ | ✅ | ✅ |
| Bloquear horarios | ❌ | ✅ | ✅ |
| Ver estadísticas | ❌ | ✅ | ✅ |
| Configurar sistema | ❌ | ❌ | ✅ |

---

## Preguntas Frecuentes

**¿El sistema funciona 24/7?**
Sí, el asistente está disponible las 24 horas, los 7 días de la semana.

**¿Qué pasa si el sistema no entiende un mensaje?**
El asistente pide amablemente que el usuario reformule su pregunta o ofrece opciones claras.

**¿Se guardan las conversaciones?**
Sí, se guardan resúmenes para mejorar el servicio. La información sensible está protegida.

**¿Puede un paciente ver citas de otros pacientes?**
No, cada usuario solo puede acceder a su propia información.

---

*Documento generado para facilitar la comprensión del sistema de asistente virtual de WhatsApp.*
