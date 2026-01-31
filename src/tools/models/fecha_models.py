"""
Modelos Pydantic para validación de fechas y horas.

Aseguran formato correcto y reglas de negocio (horario laboral, fechas futuras, etc).
"""

from pydantic import BaseModel, Field, validator
from datetime import datetime, time, timedelta
from typing import Optional

# Constantes de configuración de la clínica
CLINIC_CLOSED_DAYS = ['tuesday', 'wednesday']  # Días de cierre de la clínica
MAX_ADVANCE_DAYS = 90  # Máximo de días para agendar por adelantado


class FechaCita(BaseModel):
    """
    Fecha en formato YYYY-MM-DD validada automáticamente.
    
    Reglas:
    - Debe ser fecha futura (no pasada)
    - No más de 90 días adelante
    - Formato estricto YYYY-MM-DD
    """
    
    fecha: str = Field(
        ..., 
        pattern=r'^\d{4}-\d{2}-\d{2}$',
        description="Fecha en formato YYYY-MM-DD (ejemplo: 2026-01-31). SIEMPRE usar este formato exacto.",
        examples=["2026-01-31", "2026-02-15"]
    )
    
    @validator('fecha')
    def validar_fecha_futura_y_rango(cls, v):
        """Validar que sea fecha futura dentro de ventana permitida."""
        try:
            fecha = datetime.strptime(v, '%Y-%m-%d').date()
        except ValueError:
            raise ValueError(
                f"Fecha '{v}' tiene formato inválido. Use YYYY-MM-DD (ejemplo: 2026-01-31)"
            )
        
        hoy = datetime.now().date()
        
        # No puede ser pasada
        if fecha < hoy:
            raise ValueError(
                f"Fecha {v} ya pasó. Use una fecha futura a partir de {hoy.strftime('%Y-%m-%d')}"
            )
        
        # No más de 3 meses adelante
        max_fecha = hoy + timedelta(days=MAX_ADVANCE_DAYS)
        if fecha > max_fecha:
            raise ValueError(
                f"No se pueden agendar citas con más de 3 meses de anticipación. "
                f"Máximo hasta {max_fecha.strftime('%Y-%m-%d')}"
            )
        
        # No agendar martes ni miércoles (clínica cerrada)
        dia_semana = fecha.strftime('%A').lower()
        if dia_semana in CLINIC_CLOSED_DAYS:
            dias_texto = 'martes' if dia_semana == 'tuesday' else 'miércoles'
            raise ValueError(
                f"La clínica no atiende los {dias_texto}. "
                f"Elija lunes, jueves, viernes, sábado o domingo"
            )
        
        return v


class HoraCita(BaseModel):
    """
    Hora en formato HH:MM dentro de horario laboral.
    
    Reglas:
    - Formato 24h: HH:MM
    - Entre 8:30 AM - 6:30 PM (lunes-viernes)
    - Entre 10:30 AM - 5:30 PM (sábado-domingo)
    - Solo en intervalos de 30 minutos (:00 o :30)
    """
    
    hora: str = Field(
        ...,
        pattern=r'^([01]\d|2[0-3]):[0-5]\d$',
        description="Hora en formato 24h HH:MM (ejemplo: 14:30 para 2:30 PM, 09:00 para 9:00 AM)",
        examples=["09:00", "14:30", "16:00"]
    )
    
    dia_semana: Optional[str] = Field(
        None,
        description="Día de la semana para validar horario correcto"
    )
    
    @validator('hora')
    def validar_horario_laboral(cls, v, values):
        """Validar que esté dentro de horario de atención."""
        try:
            hora_obj = datetime.strptime(v, '%H:%M').time()
        except ValueError:
            raise ValueError(
                f"Hora '{v}' tiene formato inválido. Use HH:MM en formato 24h (ejemplo: 14:30)"
            )
        
        # Obtener día de la semana si se proporcionó
        dia_semana = values.get('dia_semana', '').lower()
        
        # Horarios según día
        if dia_semana in ['saturday', 'sunday', 'sábado', 'domingo']:
            apertura = time(10, 30)
            cierre = time(17, 30)
            horario_texto = "10:30 AM - 5:30 PM"
        else:  # Lunes-viernes por defecto
            apertura = time(8, 30)
            cierre = time(18, 30)
            horario_texto = "8:30 AM - 6:30 PM"
        
        if hora_obj < apertura or hora_obj > cierre:
            raise ValueError(
                f"Hora {v} fuera del horario de atención ({horario_texto}). "
                f"Elija una hora entre {apertura.strftime('%H:%M')} y {cierre.strftime('%H:%M')}"
            )
        
        # Validar que sea múltiplo de 30 min
        if hora_obj.minute not in [0, 30]:
            raise ValueError(
                f"Las citas solo se agendan cada 30 minutos. "
                f"Use minutos :00 o :30 (ejemplo: 14:00 o 14:30, no {v})"
            )
        
        return v


class FechaRango(BaseModel):
    """
    Rango de fechas para búsquedas y reportes.
    
    Reglas:
    - fecha_inicio debe ser <= fecha_fin
    - Ambas en formato YYYY-MM-DD
    """
    
    fecha_inicio: str = Field(
        ...,
        pattern=r'^\d{4}-\d{2}-\d{2}$',
        description="Fecha inicial del rango en formato YYYY-MM-DD"
    )
    
    fecha_fin: str = Field(
        ...,
        pattern=r'^\d{4}-\d{2}-\d{2}$',
        description="Fecha final del rango en formato YYYY-MM-DD"
    )
    
    @validator('fecha_fin')
    def validar_rango(cls, v, values):
        """Validar que fecha_fin >= fecha_inicio."""
        if 'fecha_inicio' not in values:
            return v
        
        inicio = datetime.strptime(values['fecha_inicio'], '%Y-%m-%d').date()
        fin = datetime.strptime(v, '%Y-%m-%d').date()
        
        if fin < inicio:
            raise ValueError(
                f"Fecha final ({v}) no puede ser anterior a fecha inicial ({values['fecha_inicio']})"
            )
        
        return v
