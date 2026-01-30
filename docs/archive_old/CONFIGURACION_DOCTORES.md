# 📊 Configuración de Doctores - Sistema de Agendamiento

## 👨‍⚕️ **DOCTORES DISPONIBLES**

### **Doctor 1: Santiago de Jesús Ornelas Reynoso**
- **Especialidad:** Medicina General
- **Identificadores:** "Santiago", "Dr. Santiago", "Doctor Santiago"
- **Horarios:** Jue-Vie-Lun: 8:30 AM - 6:30 PM | Sáb-Dom: 10:30 AM - 5:30 PM
- **Duración citas:** 1 hora
- **Capacidad diaria:** ~10 citas (Jue-Vie-Lun) | ~7 citas (Sáb-Dom)

### **Doctor 2: Joana Ibeth Meraz Arregín** 
- **Especialidad:** Medicina General
- **Identificadores:** "Joana", "Dra. Joana", "Doctora Joana"
- **Horarios:** Jue-Vie-Lun: 8:30 AM - 6:30 PM | Sáb-Dom: 10:30 AM - 5:30 PM
- **Duración citas:** 1 hora
- **Capacidad diaria:** ~10 citas (Jue-Vie-Lun) | ~7 citas (Sáb-Dom)

---

## 🔄 **SISTEMA DE TURNOS AUTOMÁTICO**

### **Flujo Principal: Asignación Automática por Turnos**
```
Paciente: "Quiero agendar una cita"
Sistema: 
1. Busca TODOS los slots disponibles
2. Asigna doctor por turno a cada slot internamente
3. Si doctor del turno ocupado → asigna al otro doctor
4. Ofrece 3 horarios (SIN mencionar doctor todavía)

Paciente: "La opción B"
Sistema:
1. Verifica que doctor asignado siga disponible
2. Si cambió disponibilidad → reasigna automáticamente
3. Agenda y LUEGO revela qué doctor fue asignado
```

### **Lógica de Turnos:**
- **Turno Alterno:** Santiago → Joana → Santiago → Joana...
- **Prioridad:** Doctor al que le toca turno
- **Fallback:** Si doctor del turno ocupado → usa el otro disponible
- **Balanceo:** Contador de citas mantiene distribución equitativa

### **Ejemplo Real:**
```
Slot 8:30-9:30 Jueves:
→ Le toca a Santiago (turno 1)
→ Santiago disponible ✓ → Asignado a Santiago

Slot 9:30-10:30 Jueves:
→ Le toca a Joana (turno 2)  
→ Joana disponible ✓ → Asignado a Joana

Slot 10:30-11:30 Jueves:
→ Le toca a Santiago (turno 3)
→ Santiago ocupado ✗ → Verifica Joana disponible ✓ → Asignado a Joana
```

---

## 🗄️ **ESTRUCTURA DE BASE DE DATOS ACTUALIZADA**

### **Tabla doctores ampliada:**
```sql
CREATE TABLE doctores (
    id SERIAL PRIMARY KEY,
    phone_number VARCHAR FK usuarios(phone_number),
    nombre_completo VARCHAR NOT NULL,
    especialidad VARCHAR DEFAULT 'Medicina General',
    horario_atencion JSONB DEFAULT '{
        "jueves": {"inicio": "08:30", "fin": "18:30"},
        "viernes": {"inicio": "08:30", "fin": "18:30"},
        "sabado": {"inicio": "10:30", "fin": "17:30"},
        "domingo": {"inicio": "10:30", "fin": "17:30"},
        "lunes": {"inicio": "08:30", "fin": "18:30"}
    }',
    duracion_cita_default INTEGER DEFAULT 60,
    orden_turno INTEGER DEFAULT 0,
    total_citas_asignadas INTEGER DEFAULT 0,
    activo BOOLEAN DEFAULT TRUE
);

-- Insertar doctores iniciales con orden de turno
INSERT INTO doctores (nombre_completo, especialidad, orden_turno) VALUES 
('Santiago de Jesús Ornelas Reynoso', 'Medicina General', 1),
('Joana Ibeth Meraz Arregín', 'Medicina General', 2);

-- Tabla para control de turnos
CREATE TABLE control_turnos (
    id SERIAL PRIMARY KEY,
    ultimo_doctor_id INTEGER REFERENCES doctores(id),
    timestamp TIMESTAMP DEFAULT NOW(),
    citas_santiago INTEGER DEFAULT 0,
    citas_joana INTEGER DEFAULT 0
);

-- Inicializar control de turnos
INSERT INTO control_turnos (ultimo_doctor_id, citas_santiago, citas_joana) 
VALUES (NULL, 0, 0);
```

### **Tabla citas_pacientes actualizada:**
```sql
CREATE TABLE citas_pacientes (
    id SERIAL PRIMARY KEY,
    doctor_id INTEGER REFERENCES doctores(id),
    paciente_id INTEGER REFERENCES pacientes_externos(id), 
    fecha_hora_inicio TIMESTAMP NOT NULL,
    fecha_hora_fin TIMESTAMP NOT NULL,
    estado VARCHAR DEFAULT 'confirmada',
    recordatorio_enviado BOOLEAN DEFAULT FALSE,
    google_event_id VARCHAR,
    notas_sistema TEXT
);
```

---

## 🛠️ **HERRAMIENTAS ACTUALIZADAS - SISTEMA DE TURNOS**

### **1. Búsqueda de Disponibilidad con Asignación Automática**
```python
def buscar_disponibilidad_con_turnos(dias_adelante: int = 7) -> list:
    # 1. Genera TODOS los slots posibles (8:30-18:30, cada hora)
    # 2. Para cada slot:
    #    - Determina doctor por turno (alterna Santiago/Joana)
    #    - Verifica si doctor del turno está disponible
    #    - Si ocupado → intenta con el otro doctor
    #    - Si ambos ocupados → skip slot
    # 3. Return: [{
    #      "fecha": "2026-01-30", 
    #      "hora_inicio": "08:30", 
    #      "hora_fin": "09:30",
    #      "doctor_asignado_id": 1,
    #      "doctor_nombre": "Santiago" (interno, no se muestra todavía)
    #    }]
```

### **2. Obtener Siguiente Doctor en Turno**
```python
def obtener_siguiente_doctor_turno() -> dict:
    # Consulta control_turnos
    # Alterna entre Santiago y Joana para distribución equitativa
    # Return: {"doctor_id": 1, "nombre": "Santiago", "es_su_turno": True}
```

### **3. Agendamiento con Asignación Automática**
```python
def agendar_cita_paciente(paciente_phone: str, fecha_inicio: str, fecha_fin: str) -> dict:
    # 1. Determina doctor por turno automáticamente
    # 2. Verifica disponibilidad del doctor del turno
    # 3. Si ocupado → usa el otro doctor disponible
    # 4. Agenda en BD + Google Calendar del doctor asignado
    # 5. Actualiza control_turnos y contadores
    # Return: {
    #   "cita_id": 123, 
    #   "doctor_asignado": "Santiago de Jesús Ornelas Reynoso",
    #   "confirmada": True
    # }
```

### **4. Validar y Reasignar si Necesario**
```python
def validar_asignacion_doctor(slot_info: dict) -> dict:
    # Verifica disponibilidad en tiempo real antes de confirmar
    # Si doctor ya no disponible → reasigna automáticamente al otro
    # Return: {"doctor_final_id": 1, "cambio_doctor": False}
```

---

## 📱 **EJEMPLOS DE RESPUESTAS DEL SISTEMA - SIN MENCIONAR DOCTOR**

### **Opciones de disponibilidad (NO menciona doctores):**
```
Hola! Tengo estas opciones disponibles:

🗓️ Opciones disponibles:
A) Jueves 30 Enero - 8:30 AM a 9:30 AM
B) Viernes 31 Enero - 2:30 PM a 3:30 PM  
C) Sábado 1 Febrero - 11:30 AM a 12:30 PM

¿Cuál te conviene más? Responde A, B o C
```
**NOTA:** Sistema ya asignó doctor por turno internamente, pero NO lo menciona.

### **Confirmación (AHORA sí muestra doctor asignado):**
```
✅ ¡Listo! Tu cita está agendada:

📅 Viernes 31 Enero 2026
🕐 2:30 PM - 3:30 PM
👨‍⚕️ Dra. Joana Ibeth Meraz Arregín
📍 [Dirección Clínica]

📱 Te recordaré 24 horas antes automáticamente.
💬 Si necesitas cancelar, escribe 'cancelar cita'
```
**NOTA:** Doctor fue asignado automáticamente por sistema de turnos.

---

## ✅ **VALIDACIONES DE SEGURIDAD Y LÓGICA**

### **Sistema de Turnos:**
- Alterna automáticamente entre Santiago y Joana
- Mantiene contador de citas para balanceo equitativo
- Si doctor del turno no disponible → usa el otro automáticamente

### **Disponibilidad:**
- Verifica disponibilidad en tiempo real antes de confirmar
- Si ambos doctores ocupados en un horario → slot no se ofrece
- Reasignación automática si disponibilidad cambia

### **Transparencia:**
- Paciente NO elige doctor (asignación automática)
- Doctor se revela SOLO en confirmación final
- Sistema maneja lógica de turnos completamente en segundo plano

### **Capacidad Total:**
- **Jue-Vie-Lun:** 2 doctores × 10 citas/día × 3 días = 60 citas
- **Sáb-Dom:** 2 doctores × 7 citas/día × 2 días = 28 citas
- **TOTAL:** ~88 citas/semana
- Distribución equitativa automática entre Santiago y Joana
- Escalable para agregar más doctores al sistema de turnos

**🚀 SISTEMA DE TURNOS AUTOMÁTICO - PACIENTE SOLO ESCOGE HORARIO**