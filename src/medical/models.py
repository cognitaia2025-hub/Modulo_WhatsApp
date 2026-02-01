# Medical Database Models
# SQLAlchemy models para el sistema médico híbrido

from sqlalchemy import Column, Integer, String, DateTime, Date, Time, Text, Boolean, DECIMAL, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()

# Enums para el sistema médico
class TipoConsulta(enum.Enum):
    primera_vez = "primera_vez"
    seguimiento = "seguimiento" 
    urgencia = "urgencia"
    revision = "revision"

class EstadoCita(enum.Enum):
    programada = "programada"
    confirmada = "confirmada"
    en_curso = "en_curso"
    completada = "completada"
    cancelada = "cancelada"
    no_asistio = "no_asistio"

class Genero(enum.Enum):
    masculino = "masculino"
    femenino = "femenino"
    otro = "otro"

class MetodoPago(enum.Enum):
    efectivo = "efectivo"
    tarjeta = "tarjeta"
    transferencia = "transferencia"
    seguro = "seguro"

class EstadoSincronizacion(enum.Enum):
    pendiente = "pendiente"
    sincronizada = "sincronizada"
    error = "error"
    reintentando = "reintentando"
    error_permanente = "error_permanente"

class Doctores(Base):
    __tablename__ = 'doctores'
    
    id = Column(Integer, primary_key=True)
    phone_number = Column(String, ForeignKey('usuarios.phone_number'), nullable=False)
    nombre_completo = Column(String, nullable=True)
    especialidad = Column(String, nullable=False)
    num_licencia = Column(String, unique=True)
    horario_atencion = Column(JSONB, default={})
    direccion_consultorio = Column(String)
    tarifa_consulta = Column(DECIMAL(10,2))
    años_experiencia = Column(Integer, default=0)
    orden_turno = Column(Integer, default=0)
    total_citas_asignadas = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    
    # Relaciones
    pacientes = relationship("Pacientes", back_populates="doctor")
    citas = relationship("CitasMedicas", back_populates="doctor")
    disponibilidad = relationship("DisponibilidadMedica", back_populates="doctor")

class Pacientes(Base):
    __tablename__ = 'pacientes'
    
    id = Column(Integer, primary_key=True)
    doctor_id = Column(Integer, ForeignKey('doctores.id'), nullable=False)
    nombre_completo = Column(String, nullable=False)
    telefono = Column(String, unique=True)
    email = Column(String)
    fecha_nacimiento = Column(Date)
    genero = Column(Enum(Genero))
    direccion = Column(Text)
    contacto_emergencia = Column(JSONB, default={})
    seguro_medico = Column(String)
    numero_seguro = Column(String)
    alergias = Column(Text)
    medicamentos_actuales = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    ultima_cita = Column(DateTime)
    
    # Relaciones
    doctor = relationship("Doctores", back_populates="pacientes")
    citas = relationship("CitasMedicas", back_populates="paciente")
    historiales = relationship("HistorialesMedicos", back_populates="paciente")

class DisponibilidadMedica(Base):
    __tablename__ = 'disponibilidad_medica'
    
    id = Column(Integer, primary_key=True)
    doctor_id = Column(Integer, ForeignKey('doctores.id'), nullable=False)
    dia_semana = Column(Integer, nullable=False)  # 0=Lunes, 6=Domingo
    hora_inicio = Column(Time, nullable=False)
    hora_fin = Column(Time, nullable=False)
    disponible = Column(Boolean, default=True)
    duracion_cita = Column(Integer, default=30)  # minutos
    max_pacientes_dia = Column(Integer, default=16)
    notas = Column(String)
    created_at = Column(DateTime, default=datetime.now)
    
    # Relaciones
    doctor = relationship("Doctores", back_populates="disponibilidad")

class CitasMedicas(Base):
    __tablename__ = 'citas_medicas'
    
    id = Column(Integer, primary_key=True)
    doctor_id = Column(Integer, ForeignKey('doctores.id'), nullable=False)
    paciente_id = Column(Integer, ForeignKey('pacientes.id'), nullable=False)
    fecha_hora_inicio = Column(DateTime, nullable=False)
    fecha_hora_fin = Column(DateTime, nullable=False)
    tipo_consulta = Column(Enum(TipoConsulta), default=TipoConsulta.seguimiento)
    estado = Column(Enum(EstadoCita), default=EstadoCita.programada)
    motivo_consulta = Column(Text)
    sintomas_principales = Column(Text)
    diagnostico = Column(Text)
    tratamiento_prescrito = Column(JSONB, default={})
    medicamentos = Column(JSONB, default=[])
    proxima_cita = Column(Date)
    notas_privadas = Column(Text)
    google_event_id = Column(String)
    sincronizada_google = Column(Boolean, default=False)
    costo_consulta = Column(DECIMAL(10,2))
    metodo_pago = Column(Enum(MetodoPago), default=MetodoPago.efectivo)
    # Columnas para recordatorios (Etapa 6)
    recordatorio_enviado = Column(Boolean, default=False)
    recordatorio_fecha_envio = Column(DateTime)
    recordatorio_intentos = Column(Integer, default=0)
    # Columnas para recordatorios específicos 24h y 2h (Etapa 9)
    recordatorio_24h_enviado = Column(Boolean, default=False)
    recordatorio_24h_fecha = Column(DateTime)
    recordatorio_2h_enviado = Column(Boolean, default=False)
    recordatorio_2h_fecha = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relaciones
    doctor = relationship("Doctores", back_populates="citas")
    paciente = relationship("Pacientes", back_populates="citas")
    historial = relationship("HistorialesMedicos", back_populates="cita", uselist=False)
    sincronizacion = relationship("SincronizacionCalendar", back_populates="cita", uselist=False)

class HistorialesMedicos(Base):
    __tablename__ = 'historiales_medicos'
    
    id = Column(Integer, primary_key=True)
    paciente_id = Column(Integer, ForeignKey('pacientes.id'), nullable=False)
    cita_id = Column(Integer, ForeignKey('citas_medicas.id'))
    fecha_consulta = Column(Date, nullable=False)
    peso = Column(DECIMAL(5,2))
    altura = Column(DECIMAL(5,2))
    presion_arterial = Column(String)  # "120/80"
    frecuencia_cardiaca = Column(Integer)
    temperatura = Column(DECIMAL(4,2))
    diagnostico_principal = Column(Text, nullable=False)
    diagnosticos_secundarios = Column(JSONB, default=[])
    sintomas = Column(Text)
    exploracion_fisica = Column(Text)
    estudios_laboratorio = Column(JSONB, default={})
    tratamiento_prescrito = Column(Text)
    medicamentos = Column(JSONB, default=[])
    indicaciones_generales = Column(Text)
    fecha_proxima_revision = Column(Date)
    archivos_adjuntos = Column(JSONB, default=[])
    created_at = Column(DateTime, default=datetime.now)
    
    # Relaciones
    paciente = relationship("Pacientes", back_populates="historiales")
    cita = relationship("CitasMedicas", back_populates="historial")

class SincronizacionCalendar(Base):
    __tablename__ = 'sincronizacion_calendar'
    
    id = Column(Integer, primary_key=True)
    cita_id = Column(Integer, ForeignKey('citas_medicas.id'), nullable=False)
    google_event_id = Column(String)
    estado = Column(Enum(EstadoSincronizacion), default=EstadoSincronizacion.pendiente)
    ultimo_intento = Column(DateTime, default=datetime.now)
    siguiente_reintento = Column(DateTime)
    intentos = Column(Integer, default=0)
    max_intentos = Column(Integer, default=5)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relaciones
    cita = relationship("CitasMedicas", back_populates="sincronizacion")