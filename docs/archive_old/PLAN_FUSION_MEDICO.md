# 🔄 Plan de Fusión: Sistema Híbrido + Patrones Médicos Comprobados

## 📋 Resumen Ejecutivo

Fusión estratégica de los patrones del repositorio `devalentineomonya/health-care-management-system-python-fastapi` con nuestro sistema híbrido WhatsApp + LangGraph para crear una plataforma médica completa y escalable.

---

## 📊 Comparativa de Esquemas: Actual vs. FastAPI Reference

### 🎯 **1. Esquemas de Base de Datos**

#### **1.1 Tabla Usuarios - Fusión Requerida**

**🟢 NUESTRO ACTUAL (phone-based):**
```sql
usuarios (
    phone_number VARCHAR PK,
    display_name,
    es_admin BOOLEAN,
    tipo_usuario ENUM('personal', 'doctor'),
    especialidad VARCHAR,
    num_licencia VARCHAR,
    timezone,
    preferencias JSONB
)
```

**🔵 FASTAPI REFERENCE (id-based):**
```sql
users (
    id SERIAL PK,
    username VARCHAR UNIQUE,
    email VARCHAR UNIQUE,
    hashed_password VARCHAR,
    role ENUM('admin', 'doctor', 'patient', 'staff'),
    is_active BOOLEAN DEFAULT TRUE,
    reference_id INTEGER  -- FK to patients/doctors
)

doctors (
    id SERIAL PK,
    first_name VARCHAR,
    last_name VARCHAR,
    email VARCHAR UNIQUE,
    phone VARCHAR,
    specialization VARCHAR
)

patients (
    id SERIAL PK,
    first_name VARCHAR,
    last_name VARCHAR,
    date_of_birth DATE,
    email VARCHAR UNIQUE,
    phone VARCHAR,
    address VARCHAR,
    insurance_provider VARCHAR,
    insurance_id VARCHAR
)
```

**⚡ PROPUESTA FUSIONADA (lo mejor de ambos):**
```sql
-- Tabla principal mantiene phone como PK para WhatsApp
usuarios (
    phone_number VARCHAR PK,
    display_name VARCHAR,
    email VARCHAR UNIQUE,
    hashed_password VARCHAR, -- NUEVO para autenticación web
    es_admin BOOLEAN DEFAULT FALSE,
    tipo_usuario ENUM('personal', 'doctor', 'paciente', 'staff'),
    is_active BOOLEAN DEFAULT TRUE,
    timezone VARCHAR DEFAULT 'America/Tijuana',
    preferencias JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    last_seen TIMESTAMP
);

-- Tabla doctores especializada - NUEVA
doctores (
    id SERIAL PK,
    phone_number VARCHAR REFERENCES usuarios(phone_number),
    especialidad VARCHAR NOT NULL,
    num_licencia VARCHAR UNIQUE,
    horario_atencion JSONB, -- {"lunes": {"inicio": "09:00", "fin": "17:00"}}
    direccion_consultorio VARCHAR,
    tarifa_consulta DECIMAL(10,2),
    años_experiencia INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Tabla pacientes especializada - NUEVA  
pacientes (
    id SERIAL PK,
    doctor_id INTEGER REFERENCES doctores(id),
    nombre_completo VARCHAR NOT NULL,
    telefono VARCHAR UNIQUE,
    email VARCHAR,
    fecha_nacimiento DATE,
    genero ENUM('masculino', 'femenino', 'otro'),
    direccion TEXT,
    contacto_emergencia JSONB,
    seguro_medico VARCHAR,
    numero_seguro VARCHAR,
    alergias TEXT,
    medicamentos_actuales TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    ultima_cita TIMESTAMP
);
```

#### **1.2 Sistema de Disponibilidad - ADAPTACIÓN DIRECTA**

**🔵 FASTAPI REFERENCE:**
```sql
availabilities (
    id SERIAL PK,
    doctor_id INTEGER FK,
    day_of_week INTEGER, -- 0=Monday, 6=Sunday
    start_time TIME,
    end_time TIME,
    is_available BOOLEAN DEFAULT TRUE
)
```

**⚡ ADAPTACIÓN A NUESTRO SISTEMA:**
```sql
disponibilidad_medica (
    id SERIAL PK,
    doctor_id INTEGER REFERENCES doctores(id),
    dia_semana INTEGER CHECK (dia_semana >= 0 AND dia_semana <= 6),
    hora_inicio TIME NOT NULL,
    hora_fin TIME NOT NULL,
    disponible BOOLEAN DEFAULT TRUE,
    duracion_cita INTEGER DEFAULT 30, -- minutos por cita
    max_pacientes_dia INTEGER DEFAULT 16,
    notas VARCHAR,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_disponibilidad_doctor_dia ON disponibilidad_medica(doctor_id, dia_semana);
```

#### **1.3 Citas Médicas - FUSIÓN HÍBRIDA**

**🟢 NUESTRO ACTUAL:**
```sql
citas_medicas (
    id SERIAL PK,
    doctor_id VARCHAR FK usuarios.phone_number,
    paciente_id INT FK pacientes.id,
    fecha_hora TIMESTAMP,
    duracion INT,
    estado ENUM,
    google_event_id VARCHAR
)
```

**🔵 FASTAPI REFERENCE:**
```sql
appointments (
    id SERIAL PK,
    patient_id INTEGER FK,
    doctor_id INTEGER FK,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    status VARCHAR,
    notes TEXT
)
```

**⚡ PROPUESTA FUSIONADA:**
```sql
citas_medicas (
    id SERIAL PK,
    doctor_id INTEGER REFERENCES doctores(id),
    paciente_id INTEGER REFERENCES pacientes(id),
    fecha_hora_inicio TIMESTAMP NOT NULL,
    fecha_hora_fin TIMESTAMP NOT NULL,
    tipo_consulta ENUM('primera_vez', 'seguimiento', 'urgencia', 'revision') DEFAULT 'seguimiento',
    estado ENUM('programada', 'confirmada', 'en_curso', 'completada', 'cancelada', 'no_asistio') DEFAULT 'programada',
    motivo_consulta TEXT,
    sintomas_principales TEXT,
    diagnostico TEXT,
    tratamiento_prescrito JSONB,
    medicamentos JSONB,
    proxima_cita DATE,
    notas_privadas TEXT, -- Solo para el doctor
    google_event_id VARCHAR, -- Para sincronización
    costo_consulta DECIMAL(10,2),
    metodo_pago ENUM('efectivo', 'tarjeta', 'transferencia', 'seguro'),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_citas_doctor_fecha ON citas_medicas(doctor_id, fecha_hora_inicio);
CREATE INDEX idx_citas_paciente_fecha ON citas_medicas(paciente_id, fecha_hora_inicio);
CREATE INDEX idx_citas_estado ON citas_medicas(estado);
```

#### **1.4 Historial Médico - NUEVO ROBUSTO**

**🔵 ADAPTACIÓN FASTAPI REFERENCE:**
```sql
historiales_medicos (
    id SERIAL PK,
    paciente_id INTEGER REFERENCES pacientes(id),
    cita_id INTEGER REFERENCES citas_medicas(id),
    fecha_consulta DATE NOT NULL,
    peso DECIMAL(5,2),
    altura DECIMAL(5,2),
    presion_arterial VARCHAR, -- "120/80"
    frecuencia_cardiaca INTEGER,
    temperatura DECIMAL(4,2),
    diagnostico_principal TEXT NOT NULL,
    diagnosticos_secundarios TEXT[],
    sintomas TEXT,
    exploracion_fisica TEXT,
    estudios_laboratorio JSONB,
    tratamiento_prescrito TEXT,
    medicamentos JSONB,
    indicaciones_generales TEXT,
    fecha_proxima_revision DATE,
    archivos_adjuntos JSONB, -- URLs de estudios, radiografías, etc.
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_historial_paciente_fecha ON historiales_medicos(paciente_id, fecha_consulta DESC);
```

---

## 🛠️ **2. Herramientas Médicas - Fusión con LangGraph**

### **2.1 Herramientas Existentes (6) + Nuevas (12)**

**📱 ACTUALES (Google Calendar):**
- `list_calendar_events`
- `create_calendar_event` 
- `update_calendar_event`
- `delete_calendar_event`
- `search_calendar_events`
- `postpone_calendar_event`

**🏥 NUEVAS MÉDICAS (basadas en FastAPI patterns):**

```python
# 1. Gestión de Pacientes
@tool
def crear_paciente(
    doctor_phone: str,
    nombre: str,
    telefono: str,
    email: str = None,
    fecha_nacimiento: str = None,
    genero: str = None,
    direccion: str = None,
    seguro_medico: str = None,
    alergias: str = None
) -> str:
    """Registra un nuevo paciente en la base de datos médica"""

@tool  
def buscar_paciente(
    doctor_phone: str,
    busqueda: str  # nombre, teléfono, o ID
) -> str:
    """Busca pacientes por nombre, teléfono o ID"""

@tool
def actualizar_paciente(
    doctor_phone: str,
    paciente_id: int,
    **campos_actualizar
) -> str:
    """Actualiza información de un paciente existente"""

# 2. Gestión de Disponibilidad
@tool
def configurar_horarios_doctor(
    doctor_phone: str,
    horarios: dict  # {"lunes": {"inicio": "09:00", "fin": "17:00"}}
) -> str:
    """Configura los horarios de disponibilidad del doctor"""

@tool
def buscar_slots_disponibles(
    doctor_phone: str,
    fecha: str,
    duracion: int = 30
) -> str:
    """Encuentra slots disponibles para una fecha específica"""

# 3. Gestión de Citas
@tool
def agendar_cita_medica(
    doctor_phone: str,
    paciente_id: int,
    fecha_hora: str,
    tipo_consulta: str,
    motivo: str = None
) -> str:
    """Agenda una nueva cita médica con validaciones de disponibilidad"""

@tool
def modificar_cita_medica(
    doctor_phone: str,
    cita_id: int,
    **campos_modificar
) -> str:
    """Modifica una cita existente (fecha, estado, notas)"""

@tool
def cancelar_cita_medica(
    doctor_phone: str,
    cita_id: int,
    motivo_cancelacion: str
) -> str:
    """Cancela una cita y libera el slot de tiempo"""

# 4. Consulta Médica
@tool
def registrar_consulta(
    doctor_phone: str,
    cita_id: int,
    diagnostico: str,
    tratamiento: dict,
    medicamentos: list = None,
    proxima_cita: str = None
) -> str:
    """Registra los resultados de una consulta médica"""

@tool
def consultar_historial_paciente(
    doctor_phone: str,
    paciente_id: int,
    limite_registros: int = 10
) -> str:
    """Consulta el historial médico completo de un paciente"""

# 5. Reportes y Analytics  
@tool
def generar_reporte_doctor(
    doctor_phone: str,
    tipo_reporte: str,  # "citas_dia", "pacientes_mes", "ingresos"
    fecha_inicio: str = None,
    fecha_fin: str = None
) -> str:
    """Genera reportes de actividad médica"""

@tool  
def obtener_estadisticas_consultas(
    doctor_phone: str,
    periodo: str = "mes"  # "dia", "semana", "mes"
) -> str:
    """Obtiene estadísticas de consultas y productividad"""
```

---

## ⚙️ **3. Algoritmos Adaptados - Detección de Conflictos**

### **3.1 Validación de Disponibilidad (FastAPI → LangGraph)**

```python
# Adaptación directa del algoritmo FastAPI
def check_doctor_availability(doctor_id: int, start_time: datetime, end_time: datetime) -> bool:
    """Verifica si el doctor está disponible en el horario solicitado"""
    day_of_week = start_time.weekday()
    
    # Consulta disponibilidad configurada
    availability = db.query(DisponibilidadMedica).filter(
        DisponibilidadMedica.doctor_id == doctor_id,
        DisponibilidadMedica.dia_semana == day_of_week,
        DisponibilidadMedica.disponible == True,
        DisponibilidadMedica.hora_inicio <= start_time.time(),
        DisponibilidadMedica.hora_fin >= end_time.time()
    ).first()
    
    return availability is not None

def check_appointment_conflicts(doctor_id: int, start_time: datetime, 
                              end_time: datetime, exclude_cita_id: int = None) -> bool:
    """Detecta conflictos con citas existentes"""
    query = db.query(CitasMedicas).filter(
        CitasMedicas.doctor_id == doctor_id,
        CitasMedicas.estado.in_(['programada', 'confirmada', 'en_curso']),
        or_(
            # Conflicto: Nueva cita inicia durante cita existente
            and_(
                CitasMedicas.fecha_hora_inicio <= start_time,
                CitasMedicas.fecha_hora_fin > start_time
            ),
            # Conflicto: Nueva cita termina durante cita existente  
            and_(
                CitasMedicas.fecha_hora_inicio < end_time,
                CitasMedicas.fecha_hora_fin >= end_time
            ),
            # Conflicto: Nueva cita envuelve cita existente
            and_(
                CitasMedicas.fecha_hora_inicio >= start_time,
                CitasMedicas.fecha_hora_fin <= end_time
            )
        )
    )
    
    if exclude_cita_id:
        query = query.filter(CitasMedicas.id != exclude_cita_id)
        
    return query.count() > 0
```

### **3.2 Generador de Slots Disponibles**

```python
def generate_available_slots(doctor_id: int, fecha: date, duracion_minutos: int = 30) -> List[Dict]:
    """Genera slots disponibles basado en horarios y citas existentes"""
    day_of_week = fecha.weekday()
    
    # Obtener disponibilidad del doctor
    disponibilidades = db.query(DisponibilidadMedica).filter(
        DisponibilidadMedica.doctor_id == doctor_id,
        DisponibilidadMedica.dia_semana == day_of_week,
        DisponibilidadMedica.disponible == True
    ).all()
    
    if not disponibilidades:
        return []
    
    # Obtener citas existentes del día
    start_of_day = datetime.combine(fecha, time.min)
    end_of_day = datetime.combine(fecha, time.max)
    
    citas_existentes = db.query(CitasMedicas).filter(
        CitasMedicas.doctor_id == doctor_id,
        CitasMedicas.fecha_hora_inicio >= start_of_day,
        CitasMedicas.fecha_hora_fin <= end_of_day,
        CitasMedicas.estado != 'cancelada'
    ).all()
    
    slots_disponibles = []
    
    for disponibilidad in disponibilidades:
        current_time = datetime.combine(fecha, disponibilidad.hora_inicio)
        end_time = datetime.combine(fecha, disponibilidad.hora_fin)
        
        while current_time + timedelta(minutes=duracion_minutos) <= end_time:
            slot_end = current_time + timedelta(minutes=duracion_minutos)
            
            # Verificar si el slot no tiene conflictos
            tiene_conflicto = False
            for cita in citas_existentes:
                if (current_time < cita.fecha_hora_fin and slot_end > cita.fecha_hora_inicio):
                    tiene_conflicto = True
                    break
            
            if not tiene_conflicto:
                slots_disponibles.append({
                    "inicio": current_time.isoformat(),
                    "fin": slot_end.isoformat(),
                    "disponible": True,
                    "duracion_minutos": duracion_minutos
                })
            
            current_time = slot_end
    
    return slots_disponibles
```

---

## 🌊 **4. Flujo de Datos Híbrido - Integración LangGraph**

### **4.1 Modificación del Nodo de Filtrado (N2)**

```python
# Actualización del nodo de clasificación inteligente
def clasificar_solicitud_medica(mensaje: str, user_info: dict) -> str:
    """Clasifica si la solicitud es personal, médica, o chat casual"""
    
    # Patrones médicos específicos
    patrones_medicos = [
        r"paciente|consulta|cita médica|historial|diagnóstico",
        r"agendar|cancelar|reprogramar.*(cita|consulta)",
        r"doctor|médico|especialidad|tratamiento",
        r"síntomas|medicamento|receta|presión|temperatura",
        r"disponibilidad|horario.*(consulta|atención)",
        r"seguro médico|facturación|honorarios"
    ]
    
    # Patrones personales
    patrones_personales = [
        r"mi (cita|evento|reunión|compromiso)",
        r"(crear|agendar|recordar).*(evento|cita personal)",
        r"calendario personal|agenda personal"
    ]
    
    if user_info.get("tipo_usuario") == "doctor":
        # Los doctores pueden hacer ambas operaciones
        for patron in patrones_medicos:
            if re.search(patron, mensaje.lower()):
                return "medica"
        for patron in patrones_personales:
            if re.search(patron, mensaje.lower()):
                return "personal"
    else:
        # Los usuarios regulares solo calendario personal
        return "personal"
        
    return "chat"  # Conversación casual
```

### **4.2 Nodo de Recuperación Médica (N3B)**

```python
def recuperar_contexto_medico(doctor_phone: str, query: str) -> Dict:
    """Recupera contexto relevante de BD médica para LLM"""
    
    # 1. Búsqueda en pacientes recientes
    pacientes_recientes = db.query(Pacientes).filter(
        Pacientes.doctor_id == get_doctor_id(doctor_phone)
    ).order_by(Pacientes.ultima_cita.desc()).limit(10).all()
    
    # 2. Citas del día actual
    hoy = date.today()
    citas_hoy = db.query(CitasMedicas).filter(
        CitasMedicas.doctor_id == get_doctor_id(doctor_phone),
        func.date(CitasMedicas.fecha_hora_inicio) == hoy,
        CitasMedicas.estado.in_(['programada', 'confirmada'])
    ).all()
    
    # 3. Embedding search en historiales médicos
    if query:
        embedding_query = generate_embedding(query)
        historiales_similares = buscar_vectorial_historiales(
            doctor_id=get_doctor_id(doctor_phone),
            embedding=embedding_query,
            limit=5
        )
    else:
        historiales_similares = []
    
    contexto = {
        "pacientes_recientes": [
            {
                "id": p.id,
                "nombre": p.nombre_completo,
                "telefono": p.telefono,
                "ultima_cita": p.ultima_cita.isoformat() if p.ultima_cita else None,
                "alergias": p.alergias
            } for p in pacientes_recientes
        ],
        "citas_hoy": [
            {
                "id": c.id,
                "paciente": get_patient_name(c.paciente_id),
                "hora": c.fecha_hora_inicio.time().isoformat(),
                "tipo": c.tipo_consulta,
                "estado": c.estado
            } for c in citas_hoy
        ],
        "historiales_relevantes": historiales_similares,
        "estadisticas_doctor": get_doctor_stats(get_doctor_id(doctor_phone))
    }
    
    return contexto
```

### **4.3 Sincronizador Híbrido Mejorado (N8)**

```python
def sincronizar_bd_calendar(cita_medica: CitasMedicas) -> Dict:
    """Sincroniza cita médica con Google Calendar manteniendo BD como source of truth"""
    
    try:
        # 1. Preparar evento para Google Calendar
        doctor_info = get_doctor_info(cita_medica.doctor_id)
        paciente_info = get_patient_info(cita_medica.paciente_id)
        
        evento_gcal = {
            'summary': f'Consulta - {paciente_info.nombre_completo}',
            'description': f'''
                Paciente: {paciente_info.nombre_completo}
                Teléfono: {paciente_info.telefono}
                Tipo: {cita_medica.tipo_consulta}
                Motivo: {cita_medica.motivo_consulta or "No especificado"}
                
                ID Cita: {cita_medica.id}
                ''',
            'start': {
                'dateTime': cita_medica.fecha_hora_inicio.isoformat(),
                'timeZone': 'America/Tijuana'
            },
            'end': {
                'dateTime': cita_medica.fecha_hora_fin.isoformat(),
                'timeZone': 'America/Tijuana'
            },
            'extendedProperties': {
                'private': {
                    'tipo': 'cita_medica',
                    'cita_id': str(cita_medica.id),
                    'doctor_phone': doctor_info.phone_number,
                    'paciente_id': str(cita_medica.paciente_id)
                }
            }
        }
        
        # 2. Crear/Actualizar en Google Calendar
        if cita_medica.google_event_id:
            # Actualizar evento existente
            evento_actualizado = calendar_service.events().update(
                calendarId=CALENDAR_ID,
                eventId=cita_medica.google_event_id,
                body=evento_gcal
            ).execute()
            
        else:
            # Crear nuevo evento
            evento_creado = calendar_service.events().insert(
                calendarId=CALENDAR_ID,
                body=evento_gcal
            ).execute()
            
            # Actualizar BD con Google Event ID
            cita_medica.google_event_id = evento_creado['id']
            db.commit()
        
        # 3. Registrar sincronización exitosa
        db.add(SincronizacionCalendar(
            cita_id=cita_medica.id,
            google_event_id=cita_medica.google_event_id,
            estado='sincronizada',
            ultimo_intento=datetime.now()
        ))
        db.commit()
        
        return {"status": "success", "event_id": cita_medica.google_event_id}
        
    except Exception as e:
        # 4. Manejar errores sin afectar BD médica
        db.add(SincronizacionCalendar(
            cita_id=cita_medica.id,
            estado='error',
            error_message=str(e),
            ultimo_intento=datetime.now(),
            siguiente_reintento=datetime.now() + timedelta(minutes=15)
        ))
        db.commit()
        
        return {"status": "error", "message": str(e)}
```

---

## 📝 **5. Scripts de Migración - Implementación Paso a Paso**

### **5.1 Script de Migración Tablas Médicas**

```sql
-- sql/migrate_medical_system.sql

-- 1. Actualizar tabla usuarios existente
ALTER TABLE usuarios 
ADD COLUMN email VARCHAR UNIQUE,
ADD COLUMN hashed_password VARCHAR,
ADD COLUMN is_active BOOLEAN DEFAULT TRUE;

UPDATE usuarios SET tipo_usuario = 'doctor' WHERE especialidad IS NOT NULL;

-- 2. Crear tabla doctores especializada
CREATE TABLE doctores (
    id SERIAL PRIMARY KEY,
    phone_number VARCHAR REFERENCES usuarios(phone_number),
    especialidad VARCHAR NOT NULL,
    num_licencia VARCHAR UNIQUE,
    horario_atencion JSONB DEFAULT '{}',
    direccion_consultorio VARCHAR,
    tarifa_consulta DECIMAL(10,2),
    años_experiencia INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Migrar doctores existentes
INSERT INTO doctores (phone_number, especialidad, num_licencia)
SELECT phone_number, especialidad, num_licencia 
FROM usuarios 
WHERE tipo_usuario = 'doctor';

-- 3. Crear tabla pacientes
CREATE TABLE pacientes (
    id SERIAL PRIMARY KEY,
    doctor_id INTEGER REFERENCES doctores(id),
    nombre_completo VARCHAR NOT NULL,
    telefono VARCHAR UNIQUE,
    email VARCHAR,
    fecha_nacimiento DATE,
    genero VARCHAR CHECK (genero IN ('masculino', 'femenino', 'otro')),
    direccion TEXT,
    contacto_emergencia JSONB DEFAULT '{}',
    seguro_medico VARCHAR,
    numero_seguro VARCHAR,
    alergias TEXT,
    medicamentos_actuales TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    ultima_cita TIMESTAMP
);

-- 4. Crear tabla disponibilidad médica
CREATE TABLE disponibilidad_medica (
    id SERIAL PRIMARY KEY,
    doctor_id INTEGER REFERENCES doctores(id),
    dia_semana INTEGER CHECK (dia_semana >= 0 AND dia_semana <= 6),
    hora_inicio TIME NOT NULL,
    hora_fin TIME NOT NULL,
    disponible BOOLEAN DEFAULT TRUE,
    duracion_cita INTEGER DEFAULT 30,
    max_pacientes_dia INTEGER DEFAULT 16,
    notas VARCHAR,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 5. Actualizar tabla citas médicas existente
ALTER TABLE citas_medicas 
ADD COLUMN tipo_consulta VARCHAR DEFAULT 'seguimiento' 
    CHECK (tipo_consulta IN ('primera_vez', 'seguimiento', 'urgencia', 'revision')),
ADD COLUMN motivo_consulta TEXT,
ADD COLUMN sintomas_principales TEXT,
ADD COLUMN diagnostico TEXT,
ADD COLUMN tratamiento_prescrito JSONB DEFAULT '{}',
ADD COLUMN medicamentos JSONB DEFAULT '[]',
ADD COLUMN proxima_cita DATE,
ADD COLUMN notas_privadas TEXT,
ADD COLUMN costo_consulta DECIMAL(10,2),
ADD COLUMN metodo_pago VARCHAR DEFAULT 'efectivo'
    CHECK (metodo_pago IN ('efectivo', 'tarjeta', 'transferencia', 'seguro'));

-- Actualizar estados de citas
ALTER TABLE citas_medicas 
ALTER COLUMN estado TYPE VARCHAR,
ADD CONSTRAINT check_estado 
    CHECK (estado IN ('programada', 'confirmada', 'en_curso', 'completada', 'cancelada', 'no_asistio'));

-- 6. Crear tabla historiales médicos
CREATE TABLE historiales_medicos (
    id SERIAL PRIMARY KEY,
    paciente_id INTEGER REFERENCES pacientes(id),
    cita_id INTEGER REFERENCES citas_medicas(id),
    fecha_consulta DATE NOT NULL,
    peso DECIMAL(5,2),
    altura DECIMAL(5,2),
    presion_arterial VARCHAR,
    frecuencia_cardiaca INTEGER,
    temperatura DECIMAL(4,2),
    diagnostico_principal TEXT NOT NULL,
    diagnosticos_secundarios TEXT[],
    sintomas TEXT,
    exploracion_fisica TEXT,
    estudios_laboratorio JSONB DEFAULT '{}',
    tratamiento_prescrito TEXT,
    medicamentos JSONB DEFAULT '[]',
    indicaciones_generales TEXT,
    fecha_proxima_revision DATE,
    archivos_adjuntos JSONB DEFAULT '[]',
    created_at TIMESTAMP DEFAULT NOW()
);

-- 7. Crear índices para rendimiento
CREATE INDEX idx_doctores_phone ON doctores(phone_number);
CREATE INDEX idx_pacientes_doctor ON pacientes(doctor_id);
CREATE INDEX idx_pacientes_telefono ON pacientes(telefono);
CREATE INDEX idx_disponibilidad_doctor_dia ON disponibilidad_medica(doctor_id, dia_semana);
CREATE INDEX idx_citas_doctor_fecha ON citas_medicas(doctor_id, fecha_hora_inicio);
CREATE INDEX idx_citas_paciente ON citas_medicas(paciente_id);
CREATE INDEX idx_citas_estado ON citas_medicas(estado);
CREATE INDEX idx_historial_paciente_fecha ON historiales_medicos(paciente_id, fecha_consulta DESC);

-- 8. Actualizar Foreign Keys existentes
-- Actualizar citas médicas para usar doctor_id en lugar de phone
ALTER TABLE citas_medicas 
ADD COLUMN new_doctor_id INTEGER;

UPDATE citas_medicas 
SET new_doctor_id = d.id 
FROM doctores d 
WHERE citas_medicas.doctor_id = d.phone_number;

ALTER TABLE citas_medicas 
DROP COLUMN doctor_id,
RENAME COLUMN new_doctor_id TO doctor_id,
ADD FOREIGN KEY (doctor_id) REFERENCES doctores(id);
```

### **5.2 Script de Herramientas Médicas**

```python
# src/medical_tools.py

from typing import Dict, List, Optional
from datetime import datetime, date, time
import json
from langchain_core.tools import tool
from .database.db_medical import (
    get_doctor_by_phone, create_patient, search_patients,
    schedule_appointment, check_availability, get_available_slots
)

@tool
def crear_paciente_medico(
    doctor_phone: str,
    nombre_completo: str,
    telefono: str,
    email: str = None,
    fecha_nacimiento: str = None,
    genero: str = None,
    direccion: str = None,
    seguro_medico: str = None,
    alergias: str = None
) -> str:
    """
    Registra un nuevo paciente en el sistema médico.
    
    Args:
        doctor_phone: Número de teléfono del doctor
        nombre_completo: Nombre completo del paciente
        telefono: Teléfono del paciente (único)
        email: Email del paciente (opcional)
        fecha_nacimiento: Fecha en formato YYYY-MM-DD (opcional)
        genero: masculino, femenino, otro (opcional)
        direccion: Dirección completa (opcional)
        seguro_medico: Nombre del seguro médico (opcional)
        alergias: Alergias conocidas (opcional)
        
    Returns:
        Mensaje de confirmación con ID del paciente creado
    """
    try:
        doctor = get_doctor_by_phone(doctor_phone)
        if not doctor:
            return f"❌ Error: Doctor con teléfono {doctor_phone} no encontrado"
            
        patient_data = {
            "doctor_id": doctor.id,
            "nombre_completo": nombre_completo,
            "telefono": telefono,
            "email": email,
            "genero": genero,
            "direccion": direccion,
            "seguro_medico": seguro_medico,
            "alergias": alergias
        }
        
        if fecha_nacimiento:
            try:
                patient_data["fecha_nacimiento"] = datetime.strptime(fecha_nacimiento, "%Y-%m-%d").date()
            except ValueError:
                return "❌ Error: Fecha de nacimiento debe estar en formato YYYY-MM-DD"
        
        paciente = create_patient(patient_data)
        
        return f"""✅ Paciente registrado exitosamente:
        
👤 **{paciente.nombre_completo}** (ID: {paciente.id})
📱 Teléfono: {paciente.telefono}
📧 Email: {paciente.email or 'No registrado'}
🏥 Seguro: {paciente.seguro_medico or 'No especificado'}
⚠️ Alergias: {paciente.alergias or 'Ninguna registrada'}

El paciente ha sido asignado al Dr. {doctor.phone_number}"""
        
    except Exception as e:
        return f"❌ Error al registrar paciente: {str(e)}"

@tool
def buscar_pacientes_doctor(
    doctor_phone: str,
    busqueda: str
) -> str:
    """
    Busca pacientes del doctor por nombre, teléfono o ID.
    
    Args:
        doctor_phone: Número de teléfono del doctor
        busqueda: Término de búsqueda (nombre, teléfono, o ID)
        
    Returns:
        Lista de pacientes encontrados con información básica
    """
    try:
        doctor = get_doctor_by_phone(doctor_phone)
        if not doctor:
            return f"❌ Error: Doctor con teléfono {doctor_phone} no encontrado"
            
        pacientes = search_patients(doctor.id, busqueda)
        
        if not pacientes:
            return f"🔍 No se encontraron pacientes que coincidan con '{busqueda}'"
            
        resultado = f"🔍 **Pacientes encontrados ({len(pacientes)}):**\n\n"
        
        for p in pacientes:
            resultado += f"""📋 **{p.nombre_completo}** (ID: {p.id})
📱 Teléfono: {p.telefono}
📧 Email: {p.email or 'No registrado'}
📅 Última cita: {p.ultima_cita.strftime('%d/%m/%Y') if p.ultima_cita else 'Sin citas previas'}
⚠️ Alergias: {p.alergias or 'Ninguna'}

---

"""
        
        return resultado.strip()
        
    except Exception as e:
        return f"❌ Error en búsqueda: {str(e)}"

@tool
def consultar_slots_disponibles(
    doctor_phone: str,
    fecha: str,
    duracion_minutos: int = 30
) -> str:
    """
    Consulta los horarios disponibles del doctor para una fecha específica.
    
    Args:
        doctor_phone: Número de teléfono del doctor
        fecha: Fecha en formato YYYY-MM-DD
        duracion_minutos: Duración de la cita en minutos (default: 30)
        
    Returns:
        Lista de horarios disponibles para agendar citas
    """
    try:
        doctor = get_doctor_by_phone(doctor_phone)
        if not doctor:
            return f"❌ Error: Doctor con teléfono {doctor_phone} no encontrado"
            
        fecha_obj = datetime.strptime(fecha, "%Y-%m-%d").date()
        if fecha_obj < date.today():
            return "❌ Error: No se pueden consultar fechas pasadas"
            
        slots = get_available_slots(doctor.id, fecha_obj, duracion_minutos)
        
        if not slots:
            return f"📅 No hay horarios disponibles para el {fecha_obj.strftime('%d/%m/%Y')}"
            
        resultado = f"""📅 **Horarios disponibles - {fecha_obj.strftime('%A %d/%m/%Y')}:**

"""
        
        for slot in slots:
            inicio = datetime.fromisoformat(slot['inicio']).time()
            fin = datetime.fromisoformat(slot['fin']).time()
            resultado += f"🕐 {inicio.strftime('%H:%M')} - {fin.strftime('%H:%M')} ({duracion_minutos} min)\n"
            
        resultado += f"\n✅ Total: **{len(slots)} horarios disponibles**"
        
        return resultado
        
    except ValueError:
        return "❌ Error: Fecha debe estar en formato YYYY-MM-DD"
    except Exception as e:
        return f"❌ Error al consultar disponibilidad: {str(e)}"

@tool
def agendar_cita_medica_completa(
    doctor_phone: str,
    paciente_id: int,
    fecha_hora: str,  # "YYYY-MM-DD HH:MM"
    tipo_consulta: str = "seguimiento",
    motivo_consulta: str = None,
    duracion_minutos: int = 30
) -> str:
    """
    Agenda una nueva cita médica con validaciones completas.
    
    Args:
        doctor_phone: Número de teléfono del doctor
        paciente_id: ID del paciente
        fecha_hora: Fecha y hora en formato "YYYY-MM-DD HH:MM"
        tipo_consulta: primera_vez, seguimiento, urgencia, revision
        motivo_consulta: Motivo de la consulta (opcional)
        duracion_minutos: Duración en minutos (default: 30)
        
    Returns:
        Confirmación de la cita agendada o mensaje de error
    """
    try:
        doctor = get_doctor_by_phone(doctor_phone)
        if not doctor:
            return f"❌ Error: Doctor con teléfono {doctor_phone} no encontrado"
            
        # Validar fecha y hora
        inicio = datetime.strptime(fecha_hora, "%Y-%m-%d %H:%M")
        fin = inicio + timedelta(minutes=duracion_minutos)
        
        if inicio < datetime.now():
            return "❌ Error: No se pueden agendar citas en fechas pasadas"
            
        # Verificar disponibilidad
        if not check_availability(doctor.id, inicio, fin):
            return f"❌ Doctor no disponible en horario {inicio.strftime('%d/%m/%Y %H:%M')}"
            
        # Verificar conflictos
        if has_appointment_conflicts(doctor.id, inicio, fin):
            return f"❌ Ya existe una cita en horario {inicio.strftime('%d/%m/%Y %H:%M')}"
            
        # Crear cita
        cita_data = {
            "doctor_id": doctor.id,
            "paciente_id": paciente_id,
            "fecha_hora_inicio": inicio,
            "fecha_hora_fin": fin,
            "tipo_consulta": tipo_consulta,
            "motivo_consulta": motivo_consulta,
            "estado": "programada"
        }
        
        cita = schedule_appointment(cita_data)
        
        # Sincronizar con Google Calendar en background
        sync_to_google_calendar.delay(cita.id)
        
        paciente = get_patient_by_id(paciente_id)
        
        return f"""✅ **Cita agendada exitosamente**

📋 **Detalles de la cita:**
🆔 ID Cita: {cita.id}
👤 Paciente: {paciente.nombre_completo}
📱 Teléfono: {paciente.telefono}
📅 Fecha: {inicio.strftime('%A %d/%m/%Y')}
🕐 Hora: {inicio.strftime('%H:%M')} - {fin.strftime('%H:%M')}
⏱️ Duración: {duracion_minutos} minutos
🏥 Tipo: {tipo_consulta.title()}
📝 Motivo: {motivo_consulta or 'No especificado'}

La cita se ha sincronizado automáticamente con Google Calendar."""
        
    except ValueError:
        return "❌ Error: Fecha debe estar en formato 'YYYY-MM-DD HH:MM'"
    except Exception as e:
        return f"❌ Error al agendar cita: {str(e)}"
```

---

## 🎯 **6. Plan de Implementación - Roadmap**

### **Fase 1: Fundación (Semana 1-2)**
1. ✅ **Migración de BD**: Ejecutar `migrate_medical_system.sql`
2. ✅ **Creación de herramientas médicas básicas**: 6 herramientas core
3. ✅ **Actualización del Node 2**: Clasificación médica vs personal
4. ✅ **Testing**: Validar estructura BD y herramientas básicas

### **Fase 2: Core Médico (Semana 3-4)**
1. ✅ **Node 3B**: Recuperación de contexto médico
2. ✅ **Node 5B**: Ejecución de herramientas médicas
3. ✅ **Algoritmos de validación**: Disponibilidad y conflictos
4. ✅ **Testing**: Flujo completo de agendamiento

### **Fase 3: Sincronización (Semana 5-6)**
1. ✅ **Node 8**: Sincronizador híbrido mejorado
2. ✅ **Background jobs**: Workers para sincronización automática
3. ✅ **Manejo de errores**: Tolerancia a fallos de Google Calendar
4. ✅ **Monitoring**: Logs y métricas de sincronización

### **Fase 4: Features Avanzadas (Semana 7-8)**
1. ✅ **Historiales médicos**: Embeddings y búsqueda vectorial
2. ✅ **Reportes y analytics**: 12 herramientas médicas completas
3. ✅ **Notificaciones**: WhatsApp automáticas para recordatorios
4. ✅ **Dashboard web**: Panel de control para doctores

### **Fase 5: Producción (Semana 9-10)**
1. ✅ **Testing de carga**: Validar con múltiples doctores
2. ✅ **Security audit**: Verificar permisos y accesos
3. ✅ **Documentation**: Guías de uso para doctores
4. ✅ **Deployment**: Lanzamiento en producción

---

## 🔧 **7. Comandos de Implementación Inmediata**

```bash
# 1. Ejecutar migración de BD
psql -h localhost -p 5434 -U postgres -d postgres -f sql/migrate_medical_system.sql

# 2. Crear directorio de herramientas médicas
mkdir -p src/medical/
touch src/medical/__init__.py
touch src/medical/tools.py
touch src/medical/crud.py
touch src/medical/models.py

# 3. Actualizar requirements.txt
echo "bcrypt>=4.0.0" >> requirements.txt
echo "passlib[bcrypt]>=1.7.4" >> requirements.txt

# 4. Crear tests médicos
mkdir -p tests/medical/
touch tests/medical/test_medical_tools.py
touch tests/medical/test_medical_flows.py
```

---

## ✅ **Conclusión del Plan de Fusión**

Esta fusión combina **lo mejor de ambos mundos**:

- **💪 Robustez**: Algoritmos probados de FastAPI para gestión médica
- **🚀 Innovación**: Integración WhatsApp + LangGraph única en el mercado  
- **🔒 Seguridad**: Permisos multinivel y validaciones médicas
- **📈 Escalabilidad**: Arquitectura híbrida que soporta crecimiento
- **🩺 Especialización**: Herramientas médicas específicas y completas

**Resultado final**: Un sistema híbrido que funciona como **asistente personal** para usuarios regulares y como **plataforma médica completa** para doctores, todo a través de WhatsApp con la confiabilidad de patrones comprobados en producción.