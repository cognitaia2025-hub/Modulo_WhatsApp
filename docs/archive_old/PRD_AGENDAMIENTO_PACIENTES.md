# 📋 PRD ENFOCADO: Sistema de Agendamiento de Pacientes

## 📦 **CONTEXTO: QUÉ YA FUNCIONA EN EL SISTEMA ACTUAL**

### **✅ INFRAESTRUCTURA OPERATIVA**
- **PostgreSQL en Docker:** Container `agente-whatsapp-db` en puerto 5434
- **Google Calendar API:** Integración funcionando con cuenta de servicio
- **WhatsApp Business:** Canal de comunicación activo
- **LangGraph:** Sistema de nodos funcionando para flujo personal
- **LLMs:** DeepSeek (primary) + Claude (backup) operativos

### **✅ FUNCIONALIDAD ACTUAL (CALENDARIO PERSONAL)**
- Doctor puede crear eventos personales vía WhatsApp
- Sistema lista, busca, actualiza y elimina eventos
- Google Calendar se sincroniza correctamente
- Memoria episódica guarda contexto de conversaciones
- 6 herramientas de calendario funcionando:
  - `create_event_tool`
  - `list_events_tool`
  - `search_calendar_events_tool`
  - `update_event_tool`
  - `delete_event_tool`
  - `postpone_event_tool`

### **✅ BASE DE DATOS ACTUAL**
- Tablas existentes:
  - `usuarios` - Usuarios del sistema
  - `memoria_episodica` - Historial de conversaciones
  - `user_sessions` - Sesiones activas
  - `auditoria_conversaciones` - Logs de auditoría
  - `herramientas_disponibles` - Registro de tools
- **7 Tablas médicas ya creadas** (Fase 1-3 completadas):
  - `doctores`
  - `pacientes`
  - `citas_medicas`
  - `sincronizacion_calendar`
  - (otras 3 tablas médicas)

### **✅ BACKEND MÉDICO PREPARADO**
- Módulo `src/medical/` implementado:
  - `models.py` - SQLAlchemy models
  - `crud.py` - Operaciones de BD
  - `tools.py` - 6 herramientas médicas básicas
- Herramientas médicas implementadas pero NO integradas en flujo:
  - `crear_paciente_medico`
  - `buscar_pacientes_doctor`
  - `consultar_slots_disponibles`
  - `agendar_cita_medica_completa`
  - `modificar_cita_medica`
  - `cancelar_cita_medica`

### **❌ LO QUE FALTA (OBJETIVO DE ESTE PRD)**
- **Sistema de turnos automático** para asignar doctores
- **Flujo de recepcionista** para pacientes externos
- **Integración al grafo** de las herramientas médicas
- **Nodos específicos** para flujo de pacientes
- **Recordatorios automáticos** programados

---

## 🎯 **OBJETIVO ESPECÍFICO**
**Funcionalidad:** Pacientes pueden solicitar citas vía WhatsApp  
**Rol Sistema:** Recepcionista automático que gestiona disponibilidad  
**Flujo Principal:** Solicitud → Búsqueda → Opciones → Elección → Agendamiento → Recordatorios automáticos

---

## 👥 **ROLES DEFINIDOS**

### **🩺 DOCTOR** (Sistema ya funciona)
- ✅ Tiene calendario personal funcionando
- ✅ Maneja su agenda directamente
- ✅ Ve citas agendadas automáticamente por el sistema

### **👤 PACIENTE** (Nueva funcionalidad)
- ❌ NO maneja agenda directamente
- ❌ NO escoge cuándo le recuerden
- ✅ SÍ puede solicitar citas
- ✅ SÍ puede escoger entre opciones disponibles

### **🤖 SISTEMA** (Recepcionista automático)
- Gestiona disponibilidad del doctor
- Ofrece opciones a pacientes (cantidad variable según disponibilidad)
- Agenda automáticamente
- Envía recordatorios automáticos

**⚙️ CONFIGURACIÓN HARDCODED:**
- Horarios: Jue-Vie-Lun 8:30 AM - 6:30 PM | Sáb-Dom 10:30 AM - 5:30 PM (fijo)
- Días: Jueves a Lunes (fijo)
- Duración citas: 1 hora (fijo)
- Recordatorios: 24h antes (fijo)

**🔄 DINÁMICO (NO hardcodear):**
- Días específicos ofrecidos (depende de disponibilidad real)
- Cantidad de opciones (2-5 según slots disponibles)
- Doctores asignados (sistema de turnos automático)

---

## 🔄 **FLUJO DE AGENDAMIENTO PACIENTE**

### **Paso 1: Solicitud del Paciente**
```
Paciente: "Hola, necesito una cita"
// o
Paciente: "Quiero agendar una consulta"
// o
Paciente: "Necesito que me atiendan el viernes por la tarde"
```

**NOTA:** Paciente NO elige doctor. Sistema asigna automáticamente por turno.

### **Paso 2: Sistema Recepcionista busca disponibilidad (CON TURNOS AUTOMÁTICOS)**
```
Sistema consulta:
1. Busca slots libres en próximos 7 días (todos los horarios)
2. Para cada slot disponible:
   - Determina a qué doctor le toca el turno
   - Verifica si ese doctor está disponible
   - Si doctor del turno ocupado → asigna al otro doctor
3. Ofrece 3 opciones de horarios (sistema ya decidió el doctor)
```

**LÓGICA DE TURNOS:**
- Sistema mantiene contador de turnos
- Alterna entre Santiago y Joana para distribución equitativa
- Si doctor del turno no disponible en ese horario → usa el otro

### **Paso 3: Sistema ofrece opciones**
```
Sistema: "Hola! Tengo estas opciones disponibles:

🗓️ **Opciones disponibles:**
A) Jueves 30 Enero - 8:30 AM a 9:30 AM
B) Viernes 31 Enero - 2:30 PM a 3:30 PM
C) Sábado 1 Febrero - 11:30 AM a 12:30 PM

¿Cuál te conviene más? Responde A, B o C"
```

**⚠️ IMPORTANTE - NO HARDCODEAR:**
- ❌ NO siempre son 3 opciones (pueden ser 2, 4, 5 según disponibilidad)
- ❌ NO siempre Jueves/Viernes/Sábado (depende de fecha actual y disponibilidad)
- ❌ NO siempre horarios 8:30/2:30/9:30 (usar slots realmente disponibles)
- ✅ SÍ hardcoded: Formato "A) B) C)", horarios en bloques de 1 hora, formato AM/PM

**NOTA:** Sistema NO menciona doctor. Ya decidió automáticamente por turnos.

### **Paso 4: Paciente escoge**
```
Paciente: "La opción B por favor"
```

### **Paso 5: Sistema agenda automáticamente**
```
Sistema:
1. Guarda cita en BD médica
2. Actualiza Google Calendar del doctor
3. Confirma al paciente
4. Programa recordatorio automático 24h antes
```

### **Paso 6: Confirmación automática**
```
Sistema: "✅ ¡Listo! Tu cita está agendada:

📅 **Viernes 31 Enero 2026**
🕐 **2:30 PM - 3:30 PM**
👨‍⚕️ **Dr. Santiago de Jesús Ornelas Reynoso**
📍 **[Dirección Clínica]**

📱 Te recordaré 24 horas antes automáticamente.
💬 Si necesitas cancelar, escribe 'cancelar cita'"
```

**⚠️ IMPORTANTE - NO HARDCODEAR:**
- ❌ NO siempre "Viernes 31 Enero" (usar fecha real seleccionada)
- ❌ NO siempre "2:30 PM" (usar hora real seleccionada)
- ❌ NO siempre "Dr. Santiago" (usar doctor asignado por turnos)
- ✅ SÍ hardcoded: Formato del mensaje, emojis, texto "24 horas antes", dirección clínica

**NOTA:** Doctor fue asignado automáticamente por sistema de turnos.

---

## 🗂️ **ARCHITECTURE TÉCNICA SIMPLIFICADA**

### **📊 Database Schema Específico**

```sql
-- Tabla doctores (configuración de disponibilidad)
doctores (
    id SERIAL PK,
    phone_number VARCHAR FK usuarios(phone_number),
    nombre_completo VARCHAR NOT NULL,
    especialidad VARCHAR,
    horario_atencion JSONB DEFAULT '{
        "jueves": {"inicio": "08:30", "fin": "18:30"},
        "viernes": {"inicio": "08:30", "fin": "18:30"},
        "sabado": {"inicio": "10:30", "fin": "17:30"},
        "domingo": {"inicio": "10:30", "fin": "17:30"},
        "lunes": {"inicio": "08:30", "fin": "18:30"}
    }', -- ✅ HARDCODED: Días y horarios específicos (Jue-Vie-Lun: 8:30-18:30, Sáb-Dom: 10:30-17:30)
    duracion_cita_default INTEGER DEFAULT 60, -- ✅ HARDCODED: 60 minutos por cita
    orden_turno INTEGER DEFAULT 0,
    total_citas_asignadas INTEGER DEFAULT 0,
    activo BOOLEAN DEFAULT TRUE
)

-- Datos iniciales de los 2 doctores
-- ✅ HARDCODED: Nombres específicos de los 2 doctores del sistema
INSERT INTO doctores (nombre_completo, especialidad, orden_turno) VALUES 
('Santiago de Jesús Ornelas Reynoso', 'Medicina General', 1),
('Joana Ibeth Meraz Arregín', 'Medicina General', 2);

-- Tabla control de turnos
CREATE TABLE control_turnos (
    id SERIAL PK,
    ultimo_doctor_id INTEGER FK doctores(id),
    timestamp TIMESTAMP DEFAULT NOW()
);

-- Tabla pacientes_externos (no usuarios del sistema)
pacientes_externos (
    id SERIAL PK,
    phone_number VARCHAR UNIQUE NOT NULL,
    nombre_completo VARCHAR NOT NULL,
    doctor_id INTEGER FK doctores(id),
    created_at TIMESTAMP DEFAULT NOW()
)

-- Tabla citas_pacientes (agendadas por el sistema)
citas_pacientes (
    id SERIAL PK,
    doctor_id INTEGER FK doctores(id),
    paciente_id INTEGER FK pacientes_externos(id),
    fecha_hora_inicio TIMESTAMP NOT NULL,
    fecha_hora_fin TIMESTAMP NOT NULL,
    estado VARCHAR DEFAULT 'confirmada',
    recordatorio_enviado BOOLEAN DEFAULT FALSE,
    google_event_id VARCHAR,
    notas_sistema TEXT
)
```

### **🛠️ Herramientas Específicas para Pacientes**

```python
# 4 Herramientas Recepcionista (nuevas)
recepcionista_tools = [
    buscar_disponibilidad_doctor,    # Busca slots libres
    registrar_paciente_externo,      # Registra paciente si no existe
    agendar_cita_paciente,          # Agenda cita automáticamente
    consultar_cita_paciente          # Paciente puede ver su cita
]
```

---

## 🚀 **ROADMAP DE IMPLEMENTACIÓN ENFOCADO**

### **🎯 FASE 1: HERRAMIENTAS RECEPCIONISTA**
**Duración:** 3-4 horas  
**Objetivo:** Sistema puede buscar disponibilidad y ofrecer opciones

#### **📝 Prompt para Implementación:**
```
CREAR HERRAMIENTAS RECEPCIONISTA PARA PACIENTES

CONTEXTO: Los pacientes NO son usuarios del sistema. Solo solicitan citas.
El sistema actúa como recepcionista que:
1. Busca disponibilidad del doctor
2. Ofrece 2-3 opciones al paciente  
3. Agenda automáticamente cuando paciente escoge

ARCHIVO A CREAR: src/recepcionista/tools.py

HERRAMIENTAS REQUERIDAS:

1. buscar_disponibilidad_con_turnos(dias_adelante: int = 7) -> List[dict]
   - Obtiene TODOS los slots posibles según día:
     * Jue-Vie-Lun: 8:30-18:30 (10 slots) ✅ HARDCODED
     * Sáb-Dom: 10:30-17:30 (7 slots) ✅ HARDCODED
   - Para cada slot:
     * Determina doctor por turno (alterna Santiago/Joana) ✅ HARDCODED (2 doctores)
     * Si doctor del turno ocupado → intenta con el otro doctor 🔄 DINÁMICO
     * Si ambos ocupados → slot no disponible 🔄 DINÁMICO
   - Return: [{"fecha": "2026-01-30", "hora_inicio": "08:30", "hora_fin": "09:30", "doctor_asignado_id": 1, "doctor_nombre": "Santiago"}]
   
   **⚠️ EJEMPLO ILUSTRATIVO:** Fecha y hora son ejemplos. Sistema debe calcular dinámicamente desde fecha actual.

2. registrar_paciente_externo(phone: str, nombre: str) -> dict
   - Si paciente no existe, lo crea en pacientes_externos
   - Si existe, actualiza última interacción
   - Return: {"paciente_id": 123, "es_nuevo": True}
   - NOTA: Doctor se asigna después al agendar, no al registrar

3. agendar_cita_paciente(paciente_phone: str, fecha_hora_inicio: str, fecha_hora_fin: str) -> dict
   - Determina doctor por turno automáticamente
   - Verifica que doctor del turno esté disponible
   - Si ocupado → usa el otro doctor disponible
   - Crea cita en citas_pacientes con doctor asignado
   - Crea evento en Google Calendar del doctor correcto
   - Actualiza control_turnos y contador
   - Programa recordatorio automático
   - Return: {"cita_id": 456, "doctor_asignado": "Santiago de Jesús Ornelas Reynoso", "confirmada": True}

4. obtener_siguiente_doctor_turno() -> dict
   - Consulta control_turnos para ver último doctor
   - Alterna entre doctores para distribución equitativa
   - Return: {"doctor_id": 1, "nombre": "Santiago de Jesús Ornelas Reynoso", "es_su_turno": True}

5. consultar_cita_paciente(paciente_phone: str) -> dict
   - Busca próxima cita del paciente
   - Return: {"fecha": "2026-01-30", "hora_inicio": "08:30", "hora_fin": "09:30", "doctor": "Santiago de Jesús Ornelas Reynoso"}
   
   **⚠️ EJEMPLO ILUSTRATIVO:** Todos los valores son ejemplos de formato. Sistema debe usar datos reales de BD.

VALIDACIONES:
- Solo doctores activos pueden recibir citas ✅ REGLA FIJA
- Sistema de turnos automático (alterna Santiago/Joana) ✅ LÓGICA FIJA
- Si doctor del turno ocupado → usa el otro disponible 🔄 DINÁMICO
- Si ambos doctores ocupados en el horario → slot no disponible 🔄 DINÁMICO
- Paciente solo puede tener 1 cita pendiente total ✅ REGLA FIJA
- Balanceo automático de carga entre doctores 🔄 DINÁMICO

FORMATO RESPUESTA NATURAL:
- Opciones en formato A, B, C... (SIN mencionar doctor) ✅ HARDCODED
- Fechas en español: "Jueves 30 Enero" ✅ HARDCODED (formato)
- Horarios en AM/PM formato simple: "8:30 AM a 9:30 AM" ✅ HARDCODED (formato)
- Solo días disponibles: jueves a lunes ✅ HARDCODED (días operativos)
- Doctor se revela DESPUÉS de que paciente escoge ✅ REGLA FIJA
- Citas de 1 hora en slots exactos ✅ HARDCODED (duración)

**⚠️ DINÁMICO (NO hardcodear):**
- Cantidad de opciones (depende de slots disponibles, NO siempre 3)
- Días específicos ofrecidos (calcular desde fecha actual, NO siempre Jueves/Viernes/Sábado)
- Horarios específicos (usar slots realmente libres, NO siempre 8:30/2:30/9:30)
- Letras de opciones (si hay 5 opciones: A-E, NO solo A-C)

LÓGICA INTERNA (no visible al paciente):
- Sistema ya asignó doctor por turno a cada slot
- Si paciente escoge slot donde doctor ocupado → reasigna automáticamente
- Confirmación final muestra doctor asignado
```

#### **🔧 Archivos a Crear:**
- `src/recepcionista/tools.py` [NUEVO]
- `src/recepcionista/__init__.py` [NUEVO]
- `src/recepcionista/crud.py` [NUEVO]

---

### **🎯 FASE 2: NODO RECEPCIONISTA**
**Duración:** 2-3 horas  
**Objetivo:** Flujo conversacional completo para pacientes

#### **📝 Prompt para Implementación:**
```
CREAR NODO RECEPCIONISTA CONVERSACIONAL

CONTEXTO: Paciente escribe al WhatsApp. Sistema detecta que es solicitud de cita.
Debe manejar conversación completa hasta agendar.

ARCHIVO A CREAR: src/nodes/recepcionista_node.py

FUNCIÓN PRINCIPAL: manejar_solicitud_paciente(mensaje: str, phone: str) -> str

FLUJO CONVERSACIONAL:
1. Detectar solicitud de cita
2. Preguntar nombre si es paciente nuevo
3. Buscar disponibilidad del doctor
4. Ofrecer 2-3 opciones en formato A, B, C
5. Procesar selección del paciente
6. Agendar automáticamente
7. Confirmar con detalles completos
8. Programar recordatorio

ESTADOS DE CONVERSACIÓN:
- "solicitando_cita": Paciente pidió cita, recopilar datos
- "esperando_seleccion": Se ofrecieron opciones de horarios, esperando A/B/C
- "confirmando": Agendando cita con doctor asignado automáticamente
- "completado": Cita agendada exitosamente

SISTEMA DE TURNOS AUTOMÁTICO:
- NO se pregunta con cuál doctor
- Sistema asigna por turno en segundo plano
- Paciente solo escoge horario
- Doctor se revela en confirmación final

MANEJO DE ERRORES:
- Doctor no disponible → "No hay citas disponibles esta semana"
- Selección inválida → "Por favor escribe A, B o C"
- Ya tiene cita → "Ya tienes una cita pendiente el [fecha]"

INTEGRACIÓN: 
- Usar herramientas de src/recepcionista/tools.py
- Guardar estado en memoria de conversación
- LLM para respuestas naturales en español
```

#### **🔧 Archivos a Crear:**
- `src/nodes/recepcionista_node.py` [NUEVO]

---

### **🎯 FASE 3: RECORDATORIOS AUTOMÁTICOS**
**Duración:** 2 horas  
**Objetivo:** Sistema envía recordatorios sin intervención

#### **📝 Prompt para Implementación:**
```
CREAR SISTEMA DE RECORDATORIOS AUTOMÁTICOS

CONTEXTO: Citas agendadas deben tener recordatorio automático 24h antes.
Pacientes NO pueden elegir cuándo les recuerden.

ARCHIVO A CREAR: src/recordatorios/scheduler.py

FUNCIONALIDAD:
1. Cron job que revisa citas próximas cada hora
2. Si cita es en 24h y recordatorio_enviado=False
3. Envía mensaje automático vía WhatsApp
4. Marca recordatorio_enviado=True

FORMATO RECORDATORIO:
"🔔 Recordatorio de Cita

Hola [nombre]! Te recordamos que tienes:

📅 Mañana [fecha] a las [hora]
👨‍⚕️ Dr. [nombre doctor]
📍 [dirección]

Si necesitas cancelar, responde 'cancelar'
¡Te esperamos!"

INTEGRACIÓN:
- Usar APScheduler para cron job
- Consultar citas_pacientes WHERE DATE(fecha_hora_inicio) = CURRENT_DATE + 1
- Enviar vía mismo sistema WhatsApp
```

#### **🔧 Archivos a Crear:**
- `src/recordatorios/scheduler.py` [NUEVO]
- `src/recordatorios/__init__.py` [NUEVO]

---

## ✅ **CRITERIOS DE ÉXITO**

### **Flujo Completo Funcional:**
1. ✅ Paciente: "Necesito una cita" (NO especifica doctor)
2. ✅ Sistema: Busca disponibilidad + asigna doctores por turnos internamente + ofrece N horarios A/B/C... (N variable)
3. ✅ Paciente: "La B" (escoge horario, NO doctor)
4. ✅ Sistema: Verifica turno → Si doctor del turno ocupado usa el otro → Agenda en BD + Google Calendar
5. ✅ Sistema: Confirma mostrando doctor asignado automáticamente
6. ✅ Sistema: Envía recordatorio 24h antes automáticamente

**⚠️ IMPORTANTE:** "3 horarios A/B/C" es ejemplo. Cantidad real depende de disponibilidad (pueden ser 2, 4, 5, etc.)

### **Validaciones:**
- ❌ Paciente no puede agendar directamente
- ❌ Paciente no puede elegir recordatorios
- ✅ Solo 1 cita pendiente por paciente
- ✅ Doctor ve citas en su Google Calendar
- ✅ BD es fuente de verdad

**🎯 ENFOQUE: Sistema Recepcionista que facilita agendamiento sin dar control directo a pacientes**

¿Empezamos con la **Fase 1 - Herramientas Recepcionista** para que el sistema pueda buscar disponibilidad y ofrecer opciones a los pacientes?