

---

```
Implementa 3 mejoras de arquitectura en el repositorio para mejorar DX (Developer Experience), reducir errores de LLM y acelerar tests.

# Contexto
Este es un sistema multi-agente de WhatsApp usando LangGraph. Actualmente tiene:
- Nodos Maya Detective (paciente y doctor) que responden consultas básicas
- Herramientas de agendamiento que validan manualmente
- Tests que dependen de PostgreSQL real

# Objetivo
Implementar 3 mejoras arquitectónicas aprendidas de pareshraut/Langgraph-agents:
1. langgraph.json para configuración centralizada
2. Pydantic validation en tools para reducir errores de LLM
3. CSV fixtures para tests más rápidos y confiables

---

## MEJORA 1: langgraph.json - Configuración Centralizada

### Crear archivo: langgraph.json (raíz del proyecto)

```json
{
  "graphs": {
    "whatsapp-production": {
      "path": "./src/graph_whatsapp.py:crear_grafo_whatsapp",
      "description": "Grafo principal de WhatsApp con todos los nodos (Maya + Router + Herramientas)"
    }
  },
  "env": ".env",
  "python_version": "3.11",
  "dependencies": ["."]
}
```

### Beneficios
- LangGraph Studio detecta automáticamente el grafo
- Config de BD viene de .env (no hardcoded)
- Base para múltiples grafos en el futuro (test, staging, etc)

---

## MEJORA 2: Pydantic Validation en Tools

### Estructura de archivos a crear:

```
src/tools/
├── __init__.py                  (actualizar exports)
├── models/                      (carpeta nueva)
│   ├── __init__.py             (nuevo)
│   ├── fecha_models.py         (nuevo)
│   └── paciente_models.py      (nuevo)
└── agendamiento_tools.py       (modificar existente)
```

---

### A. Crear: src/tools/models/__init__.py

```python
"""
Modelos Pydantic para validación de herramientas.

Estos modelos aseguran que el LLM pase datos en formato correcto
ANTES de ejecutar las tools, reduciendo reintentos y errores.
"""

from .fecha_models import FechaCita, HoraCita, FechaRango
from .paciente_models import DatosPaciente, TelefonoPaciente

__all__ = [
    'FechaCita',
    'HoraCita', 
    'FechaRango',
    'DatosPaciente',
    'TelefonoPaciente'
]
```

---

### B. Crear: src/tools/models/fecha_models.py

```python
"""
Modelos Pydantic para validación de fechas y horas.

Aseguran formato correcto y reglas de negocio (horario laboral, fechas futuras, etc).
"""

from pydantic import BaseModel, Field, validator
from datetime import datetime, time, timedelta
import pendulum
from typing import Optional


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
        max_fecha = hoy + timedelta(days=90)
        if fecha > max_fecha:
            raise ValueError(
                f"No se pueden agendar citas con más de 3 meses de anticipación. "
                f"Máximo hasta {max_fecha.strftime('%Y-%m-%d')}"
            )
        
        # No agendar martes ni miércoles (clínica cerrada)
        dia_semana = fecha.strftime('%A').lower()
        if dia_semana in ['tuesday', 'wednesday']:
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
```

---

### C. Crear: src/tools/models/paciente_models.py

```python
"""
Modelos Pydantic para validación de datos de pacientes.
"""

from pydantic import BaseModel, Field, validator
import re


class TelefonoPaciente(BaseModel):
    """
    Número de teléfono en formato internacional.
    
    Reglas:
    - Formato: +52XXXXXXXXXX (México)
    - 10 dígitos después del +52
    """
    
    telefono: str = Field(
        ...,
        pattern=r'^\+52\d{10}$',
        description="Teléfono en formato internacional +52XXXXXXXXXX (ejemplo: +526641234567)",
        examples=["+526641234567", "+526642345678"]
    )
    
    @validator('telefono')
    def validar_formato_telefono(cls, v):
        """Validar formato de teléfono mexicano."""
        if not re.match(r'^\+52\d{10}$', v):
            raise ValueError(
                f"Teléfono '{v}' tiene formato inválido. "
                f"Use formato internacional: +52 seguido de 10 dígitos (ejemplo: +526641234567)"
            )
        return v


class DatosPaciente(BaseModel):
    """
    Datos básicos de un paciente para registro.
    
    Reglas:
    - Nombre completo (mínimo 3 caracteres)
    - Teléfono validado
    """
    
    nombre_completo: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="Nombre completo del paciente (mínimo 3 caracteres)"
    )
    
    telefono: TelefonoPaciente = Field(
        ...,
        description="Número de teléfono del paciente"
    )
    
    @validator('nombre_completo')
    def validar_nombre(cls, v):
        """Validar que el nombre tenga formato válido."""
        v = v.strip()
        
        if len(v) < 3:
            raise ValueError("Nombre debe tener al menos 3 caracteres")
        
        # Solo letras, espacios y acentos
        if not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$', v):
            raise ValueError(
                "Nombre solo debe contener letras y espacios (sin números ni símbolos)"
            )
        
        return v
```

---

### D. Modificar: src/tools/agendamiento_tools.py

Buscar las tools existentes como `agendar_cita_paciente` y actualizarlas para usar Pydantic:

```python
"""
Herramientas de agendamiento de citas.

IMPORTANTE: Estas tools usan Pydantic para validación automática.
El LLM debe pasar datos en formato correcto o recibirá error descriptivo.
"""

from langchain_core.tools import tool
from .models import FechaCita, HoraCita, DatosPaciente
import psycopg
import os
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@tool
def agendar_cita_paciente(
    fecha: FechaCita,
    hora: HoraCita,
    paciente_id: int,
    motivo: str
) -> str:
    """
    Agenda una cita médica para un paciente existente.
    
    Esta herramienta valida automáticamente:
    - Formato de fecha (YYYY-MM-DD)
    - Fecha sea futura (no pasada)
    - Formato de hora (HH:MM en 24h)
    - Hora dentro del horario laboral
    - Hora en intervalos de 30 minutos
    
    Args:
        fecha: Fecha de la cita (FechaCita validado)
        hora: Hora de la cita (HoraCita validado)
        paciente_id: ID del paciente en la base de datos
        motivo: Motivo de la consulta
        
    Returns:
        Mensaje de confirmación con ID de cita
        
    Examples:
        >>> agendar_cita_paciente(
        ...     fecha=FechaCita(fecha="2026-02-15"),
        ...     hora=HoraCita(hora="14:30"),
        ...     paciente_id=123,
        ...     motivo="Consulta general"
        ... )
        "✅ Cita 456 agendada para 2026-02-15 a las 14:30"
    """
    
    # Si llegamos aquí, Pydantic ya validó todo ✅
    # No necesitamos try/except para validación de formato
    
    try:
        DATABASE_URL = os.getenv("DATABASE_URL")
        
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                # Verificar que el paciente existe
                cur.execute("SELECT id FROM pacientes WHERE id = %s", (paciente_id,))
                if not cur.fetchone():
                    return f"❌ Error: No existe paciente con ID {paciente_id}"
                
                # Verificar disponibilidad del horario
                fecha_hora = f"{fecha.fecha} {hora.hora}:00"
                cur.execute("""
                    SELECT id FROM citas_medicas 
                    WHERE fecha_hora_inicio = %s 
                    AND estado != 'cancelada'
                """, (fecha_hora,))
                
                if cur.fetchone():
                    return f"❌ El horario {fecha.fecha} a las {hora.hora} ya está ocupado. Elija otro horario."
                
                # Insertar cita
                query = """
                    INSERT INTO citas_medicas 
                    (paciente_id, fecha_hora_inicio, motivo_consulta, estado, created_at)
                    VALUES (%s, %s, %s, 'agendada', NOW())
                    RETURNING id
                """
                
                cur.execute(query, (paciente_id, fecha_hora, motivo))
                cita_id = cur.fetchone()[0]
                conn.commit()
                
                logger.info(f"Cita {cita_id} agendada para paciente {paciente_id} el {fecha_hora}")
                
                return f"✅ Cita {cita_id} agendada exitosamente para {fecha.fecha} a las {hora.hora}. Motivo: {motivo}"
                
    except psycopg.Error as e:
        logger.error(f"Error de base de datos al agendar cita: {e}")
        return f"❌ Error al agendar cita. Por favor intente nuevamente."
    
    except Exception as e:
        logger.error(f"Error inesperado al agendar cita: {e}")
        return f"❌ Error inesperado. Por favor contacte al administrador."


@tool
def reagendar_cita(
    cita_id: int,
    nueva_fecha: FechaCita,
    nueva_hora: HoraCita
) -> str:
    """
    Reagenda una cita existente a nueva fecha/hora.
    
    Valida automáticamente el nuevo horario con Pydantic.
    
    Args:
        cita_id: ID de la cita a reagendar
        nueva_fecha: Nueva fecha (validada por Pydantic)
        nueva_hora: Nueva hora (validada por Pydantic)
        
    Returns:
        Mensaje de confirmación
    """
    
    try:
        DATABASE_URL = os.getenv("DATABASE_URL")
        
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                # Verificar que la cita existe
                cur.execute("""
                    SELECT id, estado 
                    FROM citas_medicas 
                    WHERE id = %s
                """, (cita_id,))
                
                result = cur.fetchone()
                if not result:
                    return f"❌ No existe cita con ID {cita_id}"
                
                if result[1] == 'completada':
                    return f"❌ No se puede reagendar una cita ya completada"
                
                # Verificar disponibilidad del nuevo horario
                nueva_fecha_hora = f"{nueva_fecha.fecha} {nueva_hora.hora}:00"
                cur.execute("""
                    SELECT id FROM citas_medicas 
                    WHERE fecha_hora_inicio = %s 
                    AND estado != 'cancelada'
                    AND id != %s
                """, (nueva_fecha_hora, cita_id))
                
                if cur.fetchone():
                    return f"❌ El horario {nueva_fecha.fecha} a las {nueva_hora.hora} ya está ocupado"
                
                # Actualizar cita
                cur.execute("""
                    UPDATE citas_medicas 
                    SET fecha_hora_inicio = %s,
                        updated_at = NOW()
                    WHERE id = %s
                """, (nueva_fecha_hora, cita_id))
                
                conn.commit()
                
                logger.info(f"Cita {cita_id} reagendada a {nueva_fecha_hora}")
                
                return f"✅ Cita {cita_id} reagendada para {nueva_fecha.fecha} a las {nueva_hora.hora}"
                
    except Exception as e:
        logger.error(f"Error al reagendar cita: {e}")
        return f"❌ Error al reagendar. Intente nuevamente."


@tool
def cancelar_cita(cita_id: int, motivo_cancelacion: str = "") -> str:
    """
    Cancela una cita existente.
    
    Args:
        cita_id: ID de la cita a cancelar
        motivo_cancelacion: Motivo opcional de la cancelación
        
    Returns:
        Mensaje de confirmación
    """
    
    try:
        DATABASE_URL = os.getenv("DATABASE_URL")
        
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                # Verificar que existe
                cur.execute("""
                    SELECT id, estado, fecha_hora_inicio 
                    FROM citas_medicas 
                    WHERE id = %s
                """, (cita_id,))
                
                result = cur.fetchone()
                if not result:
                    return f"❌ No existe cita con ID {cita_id}"
                
                if result[1] == 'cancelada':
                    return f"⚠️ La cita {cita_id} ya estaba cancelada"
                
                if result[1] == 'completada':
                    return f"❌ No se puede cancelar una cita ya completada"
                
                # Cancelar
                cur.execute("""
                    UPDATE citas_medicas 
                    SET estado = 'cancelada',
                        motivo_cancelacion = %s,
                        updated_at = NOW()
                    WHERE id = %s
                """, (motivo_cancelacion, cita_id))
                
                conn.commit()
                
                logger.info(f"Cita {cita_id} cancelada. Motivo: {motivo_cancelacion}")
                
                return f"✅ Cita {cita_id} cancelada exitosamente"
                
    except Exception as e:
        logger.error(f"Error al cancelar cita: {e}")
        return f"❌ Error al cancelar. Intente nuevamente."
```

---

### E. Actualizar: src/tools/__init__.py

```python
"""
Herramientas (tools) para los agentes.

Todas las tools usan Pydantic validation para asegurar formato correcto
antes de ejecutar, reduciendo errores del LLM.
"""

from .agendamiento_tools import (
    agendar_cita_paciente,
    reagendar_cita,
    cancelar_cita
)

from .models import (
    FechaCita,
    HoraCita,
    DatosPaciente,
    TelefonoPaciente
)

__all__ = [
    'agendar_cita_paciente',
    'reagendar_cita',
    'cancelar_cita',
    'FechaCita',
    'HoraCita',
    'DatosPaciente',
    'TelefonoPaciente'
]
```

---

## MEJORA 3: CSV Fixtures para Tests

### Estructura de archivos a crear:

```
tests/
├── fixtures/                           (carpeta nueva)
│   ├── README.md                       (nuevo - documentación)
│   ├── citas_doctor_1.csv             (nuevo)
│   ├── citas_doctor_sin_citas.csv     (nuevo)
│   ├── citas_doctor_muchas.csv        (nuevo)
│   ├── pacientes_ejemplo.csv          (nuevo)
│   └── doctores_ejemplo.csv           (nuevo)
└── test_maya_detective_doctor.py      (modificar)
```

---

### A. Crear: tests/fixtures/README.md

```markdown
# Test Fixtures

Datos de prueba en formato CSV para tests rápidos sin depender de PostgreSQL real.

## Uso

```python
import pandas as pd

@pytest.fixture
def mock_citas():
    return pd.read_csv('tests/fixtures/citas_doctor_1.csv')

def test_algo(mock_citas):
    total = len(mock_citas)
    assert total == 8
```

## Archivos

- **citas_doctor_1.csv**: Doctor con 8 citas (3 completadas, 5 pendientes)
- **citas_doctor_sin_citas.csv**: Doctor sin citas (día libre)
- **citas_doctor_muchas.csv**: Doctor con 15 citas (caso edge)
- **pacientes_ejemplo.csv**: 10 pacientes de prueba
- **doctores_ejemplo.csv**: 3 doctores de prueba

## Crear nuevo fixture

1. Copiar un CSV existente
2. Modificar datos según el escenario a probar
3. Usar en test con `pd.read_csv()`
```

---

### B. Crear: tests/fixtures/citas_doctor_1.csv

```csv
id,doctor_id,paciente_id,paciente_nombre,fecha_hora_inicio,estado,motivo_consulta
1,1,101,Juan Pérez,2026-01-31 09:00:00,completada,Consulta general
2,1,102,María García,2026-01-31 10:30:00,completada,Seguimiento
3,1,103,Carlos López,2026-01-31 11:45:00,completada,Podología
4,1,104,Ana Martínez,2026-01-31 14:30:00,agendada,Revisión
5,1,105,Roberto Sánchez,2026-01-31 15:30:00,agendada,Tratamiento
6,1,106,Laura Torres,2026-01-31 16:15:00,agendada,Control
7,1,107,Pedro Ramírez,2026-01-31 17:00:00,agendada,Consulta
8,1,108,Sofia Morales,2026-01-31 17:45:00,agendada,Seguimiento
```

---

### C. Crear: tests/fixtures/citas_doctor_sin_citas.csv

```csv
id,doctor_id,paciente_id,paciente_nombre,fecha_hora_inicio,estado,motivo_consulta
```

(Archivo vacío - solo header)

---

### D. Crear: tests/fixtures/citas_doctor_muchas.csv

```csv
id,doctor_id,paciente_id,paciente_nombre,fecha_hora_inicio,estado,motivo_consulta
1,1,101,Paciente 1,2026-01-31 08:30:00,completada,Consulta
2,1,102,Paciente 2,2026-01-31 09:00:00,completada,Consulta
3,1,103,Paciente 3,2026-01-31 09:30:00,completada,Consulta
4,1,104,Paciente 4,2026-01-31 10:00:00,completada,Consulta
5,1,105,Paciente 5,2026-01-31 10:30:00,completada,Consulta
6,1,106,Paciente 6,2026-01-31 11:00:00,agendada,Consulta
7,1,107,Paciente 7,2026-01-31 11:30:00,agendada,Consulta
8,1,108,Paciente 8,2026-01-31 14:00:00,agendada,Consulta
9,1,109,Paciente 9,2026-01-31 14:30:00,agendada,Consulta
10,1,110,Paciente 10,2026-01-31 15:00:00,agendada,Consulta
11,1,111,Paciente 11,2026-01-31 15:30:00,agendada,Consulta
12,1,112,Paciente 12,2026-01-31 16:00:00,agendada,Consulta
13,1,113,Paciente 13,2026-01-31 16:30:00,agendada,Consulta
14,1,114,Paciente 14,2026-01-31 17:00:00,agendada,Consulta
15,1,115,Paciente 15,2026-01-31 17:30:00,agendada,Consulta
```

---

### E. Crear: tests/fixtures/pacientes_ejemplo.csv

```csv
id,nombre_completo,phone_number,email,fecha_registro
101,Juan Pérez,+526641234567,juan@example.com,2025-01-15
102,María García,+526641234568,maria@example.com,2025-01-16
103,Carlos López,+526641234569,carlos@example.com,2025-01-17
104,Ana Martínez,+526641234570,ana@example.com,2025-01-18
105,Roberto Sánchez,+526641234571,roberto@example.com,2025-01-19
106,Laura Torres,+526641234572,laura@example.com,2025-01-20
107,Pedro Ramírez,+526641234573,pedro@example.com,2025-01-21
108,Sofia Morales,+526641234574,sofia@example.com,2025-01-22
109,Diego Hernández,+526641234575,diego@example.com,2025-01-23
110,Carmen Jiménez,+526641234576,carmen@example.com,2025-01-24
```

---

### F. Crear: tests/fixtures/doctores_ejemplo.csv

```csv
id,nombre_completo,especialidad,phone_number,email
1,Dr. Juan Santiago,Podología,+526641111111,santiago@podoskin.com
2,Dra. María Rodríguez,Dermatología,+526641111112,rodriguez@podoskin.com
3,Dr. Carlos Mendoza,Medicina General,+526641111113,mendoza@podoskin.com
```

---

### G. Crear helper: tests/helpers/csv_helpers.py

```python
"""
Helpers para trabajar con fixtures CSV en tests.
"""

import pandas as pd
from pathlib import Path
from typing import Dict, Any

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def crear_resumen_dia_desde_csv(df: pd.DataFrame) -> str:
    """
    Crea resumen del día del doctor desde CSV.
    
    Simula la función obtener_resumen_dia_doctor() pero usando datos CSV
    en lugar de query SQL real.
    
    Args:
        df: DataFrame con columnas: id, doctor_id, paciente_nombre, 
            fecha_hora_inicio, estado, motivo_consulta
            
    Returns:
        String formateado igual que obtener_resumen_dia_doctor()
    """
    if len(df) == 0:
        return """📊 TUS ESTADÍSTICAS HOY:
• No tienes citas agendadas para hoy
• Día libre 🎉"""
    
    total = len(df)
    completadas = len(df[df['estado'] == 'completada'])
    pendientes = len(df[df['estado'] == 'agendada'])
    canceladas = len(df[df['estado'] == 'cancelada'])
    
    resumen = f"""📊 TUS ESTADÍSTICAS HOY:
• Citas agendadas: {total}
• Completadas: {completadas}
• Pendientes: {pendientes}"""
    
    if canceladas > 0:
        resumen += f"\n• Canceladas: {canceladas}"
    
    # Próxima cita
    df_pendientes = df[df['estado'] == 'agendada'].sort_values('fecha_hora_inicio')
    
    if len(df_pendientes) > 0:
        proxima = df_pendientes.iloc[0]
        hora = proxima['fecha_hora_inicio'].split()[1][:5]
        
        resumen += f"""

🕐 PRÓXIMA CITA:
• Paciente: {proxima['paciente_nombre']}
• Hora: {hora} (en X min)"""
        
        if proxima.get('motivo_consulta'):
            resumen += f"\n• Motivo: {proxima['motivo_consulta']}"
    else:
        resumen += "\n\n🕐 No hay más citas pendientes hoy"
    
    # Lista de pacientes
    resumen += "\n\n👥 PACIENTES DEL DÍA:"
    for idx, row in df.iterrows():
        hora = row['fecha_hora_inicio'].split()[1][:5]
        emoji = "✓" if row['estado'] == "completada" else "⏳" if row['estado'] == "agendada" else "✗"
        resumen += f"\n{idx+1}. {row['paciente_nombre']} - {hora} {emoji}"
    
    return resumen


def load_fixture_csv(filename: str) -> pd.DataFrame:
    """
    Carga un fixture CSV desde tests/fixtures/.
    
    Args:
        filename: Nombre del archivo (ejemplo: "citas_doctor_1.csv")
        
    Returns:
        DataFrame con los datos
    """
    filepath = FIXTURES_DIR / filename
    if not filepath.exists():
        raise FileNotFoundError(f"Fixture no encontrado: {filepath}")
    
    return pd.read_csv(filepath)
```

---

### H. Modificar: tests/test_maya_detective_doctor.py

Agregar fixtures y usar CSVs:

```python
"""
Tests para Nodo 2B: Maya Detective de Intención - Doctores

Usa CSV fixtures en lugar de PostgreSQL real para tests más rápidos.
"""

import pytest
import pandas as pd
from unittest.mock import patch, Mock
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.types import Command

from src.nodes.maya_detective_doctor_node import (
    nodo_maya_detective_doctor,
    MayaResponseDoctor
)
from tests.helpers.csv_helpers import load_fixture_csv, crear_resumen_dia_desde_csv


# ==================== FIXTURES ====================

@pytest.fixture
def estado_base_doctor():
    """Estado base para tests de doctor."""
    return {
        'doctor_id': 1,
        'tipo_usuario': 'doctor',
        'messages': [HumanMessage(content="Hola")],
        'estado_conversacion': 'inicial'
    }


@pytest.fixture
def mock_citas_doctor_1():
    """Doctor con 8 citas (3 completadas, 5 pendientes)."""
    return load_fixture_csv('citas_doctor_1.csv')


@pytest.fixture
def mock_citas_sin_citas():
    """Doctor sin citas hoy (día libre)."""
    return load_fixture_csv('citas_doctor_sin_citas.csv')


@pytest.fixture
def mock_citas_muchas():
    """Doctor con 15 citas (caso edge)."""
    return load_fixture_csv('citas_doctor_muchas.csv')


# ==================== TESTS CON CSV ====================

@patch('src.nodes.maya_detective_doctor_node.structured_llm_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_resumen_dia_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_info_doctor')
def test_maya_responde_cuantas_citas_con_csv(
    mock_info,
    mock_resumen,
    mock_llm,
    estado_base_doctor,
    mock_citas_doctor_1
):
    """Maya responde cuántas citas tiene el doctor (usando CSV)."""
    
    # Setup mocks usando CSV
    mock_info.return_value = {
        'nombre_completo': 'Dr. Santiago',
        'especialidad': 'Podología'
    }
    mock_resumen.return_value = crear_resumen_dia_desde_csv(mock_citas_doctor_1)
    
    mock_llm.invoke.return_value = MayaResponseDoctor(
        accion="responder_directo",
        respuesta="Tienes 8 citas hoy. Has completado 3 y te quedan 5",
        razon="Stats del día desde CSV"
    )
    
    estado_base_doctor['messages'] = [HumanMessage(content="¿Cuántas citas tengo?")]
    
    # Ejecutar
    resultado = nodo_maya_detective_doctor(estado_base_doctor)
    
    # Validar usando datos del CSV
    total_esperado = len(mock_citas_doctor_1)
    completadas_esperadas = len(mock_citas_doctor_1[mock_citas_doctor_1['estado'] == 'completada'])
    
    assert resultado.goto == "generacion_resumen"
    assert f"{total_esperado} citas" in resultado.update['messages'][0].content
    assert f"completado {completadas_esperadas}" in resultado.update['messages'][0].content.lower()


@patch('src.nodes.maya_detective_doctor_node.structured_llm_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_resumen_dia_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_info_doctor')
def test_maya_sin_citas_hoy_con_csv(
    mock_info,
    mock_resumen,
    mock_llm,
    estado_base_doctor,
    mock_citas_sin_citas
):
    """Maya maneja correctamente día sin citas (usando CSV vacío)."""
    
    mock_info.return_value = {
        'nombre_completo': 'Dr. Santiago',
        'especialidad': 'Podología'
    }
    mock_resumen.return_value = crear_resumen_dia_desde_csv(mock_citas_sin_citas)
    
    mock_llm.invoke.return_value = MayaResponseDoctor(
        accion="responder_directo",
        respuesta="No tienes citas agendadas para hoy. Día libre! 🎉",
        razon="Sin citas según CSV"
    )
    
    estado_base_doctor['messages'] = [HumanMessage(content="¿Cuántas citas tengo?")]
    
    resultado = nodo_maya_detective_doctor(estado_base_doctor)
    
    assert "No tienes citas" in resultado.update['messages'][0].content
    assert len(mock_citas_sin_citas) == 0  # Verificar que fixture está vacío


@patch('src.nodes.maya_detective_doctor_node.structured_llm_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_resumen_dia_doctor')
@patch('src.nodes.maya_detective_doctor_node.obtener_info_doctor')
def test_maya_muchas_citas_con_csv(
    mock_info,
    mock_resumen,
    mock_llm,
    estado_base_doctor,
    mock_citas_muchas
):
    """Maya maneja correctamente día con muchas citas (usando CSV)."""
    
    mock_info.return_value = {
        'nombre_completo': 'Dr. Santiago',
        'especialidad': 'Podología'
    }
    mock_resumen.return_value = crear_resumen_dia_desde_csv(mock_citas_muchas)
    
    mock_llm.invoke.return_value = MayaResponseDoctor(
        accion="responder_directo",
        respuesta="Tienes 15 citas hoy. Has completado 5 y te quedan 10",
        razon="Muchas citas según CSV"
    )
    
    estado_base_doctor['messages'] = [HumanMessage(content="¿Cuántas citas tengo?")]
    
    resultado = nodo_maya_detective_doctor(estado_base_doctor)
    
    total = len(mock_citas_muchas)
    assert total == 15  # Verificar cantidad en fixture
    assert f"{total} citas" in resultado.update['messages'][0].content
```

---

## Criterios de Aceptación

### langgraph.json
- [x] Archivo creado en raíz del proyecto
- [x] Contiene referencia a crear_grafo_whatsapp
- [x] LangGraph Studio puede detectarlo automáticamente
- [x] Variables de entorno vienen de .env (no hardcoded)

### Pydantic Models
- [x] Carpeta src/tools/models/ creada
- [x] FechaCita valida formato YYYY-MM-DD y fecha futura
- [x] HoraCita valida formato HH:MM y horario laboral
- [x] Tools actualizadas usan Pydantic (agendar, reagendar, cancelar)
- [x] Errores de validación son descriptivos para el LLM
- [x] Tests existentes siguen pasando

### CSV Fixtures
- [x] Carpeta tests/fixtures/ creada con README
- [x] 5 CSVs de ejemplo creados (citas_doctor_1, sin_citas, muchas, pacientes, doctores)
- [x] Helper csv_helpers.py implementado
- [x] Al menos 3 tests usando CSV en lugar de BD real
- [x] Tests corren 10x más rápido que antes

## Impacto Esperado

| Métrica | Antes | Después | Mejora |
|---------|-------|---------|--------|
| Cambiar entre grafos | Modificar código | 1 click Studio | ⭐⭐⭐⭐⭐ |
| Errores tool LLM | 3-4 intentos | 1 intento | ⭐⭐⭐⭐⭐ |
| Velocidad tests | 5 seg | 0.5 seg | ⭐⭐⭐⭐⭐ |
| Setup CI/CD | 2 min | 10 seg | ⭐⭐⭐⭐ |

## Notas Técnicas

- Pydantic models se validan ANTES de ejecutar la tool (save tokens)
- CSV fixtures no requieren PostgreSQL corriendo (ideal para CI/CD)
- langgraph.json es el estándar de LangGraph Cloud para deployment
- Todas las mejoras son backward compatible (no rompen código existente)

Repositorio: cognitaia2025-hub/Modulo_WhatsApp
```

---
