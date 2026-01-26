"""
Utilidades de Tiempo para Mexicali, BC (America/Tijuana)

Gestiona toda la lógica de fechas y horas usando Pendulum.
Zona horaria fija: America/Tijuana (PST/PDT)
"""

import pendulum
from pendulum import DateTime
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Zona horaria de Mexicali, Baja California
TIMEZONE_MEXICALI = 'America/Tijuana'


def get_current_time() -> DateTime:
    """
    Obtiene la fecha y hora actual en Mexicali, BC
    
    Returns:
        DateTime: Fecha/hora actual con zona horaria de Mexicali
        
    Example:
        >>> now = get_current_time()
        >>> print(now)
        2026-01-23T14:30:00-08:00
    """
    return pendulum.now(TIMEZONE_MEXICALI)


def get_time_context() -> str:
    """
    Genera contexto de tiempo legible para el LLM
    
    Returns:
        str: Contexto formateado en español
        
    Example:
        "Hoy es jueves, 23 de enero de 2026 y son las 14:30 en Mexicali, BC."
    """
    now = get_current_time()
    
    # Nombres de días en español
    dias = {
        'Monday': 'lunes',
        'Tuesday': 'martes',
        'Wednesday': 'miércoles',
        'Thursday': 'jueves',
        'Friday': 'viernes',
        'Saturday': 'sábado',
        'Sunday': 'domingo'
    }
    
    # Nombres de meses en español
    meses = {
        1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril',
        5: 'mayo', 6: 'junio', 7: 'julio', 8: 'agosto',
        9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre'
    }
    
    dia_semana = dias.get(now.format('dddd'), now.format('dddd'))
    mes = meses.get(now.month, now.format('MMMM'))
    
    contexto = (
        f"Hoy es {dia_semana}, {now.day} de {mes} de {now.year} "
        f"y son las {now.format('HH:mm')} en Mexicali, BC."
    )
    
    return contexto


def parse_relative_time(text: str) -> Optional[DateTime]:
    """
    Parsea expresiones relativas de tiempo en español
    
    Args:
        text: Texto con expresión temporal ("hoy", "mañana", "próximo lunes")
        
    Returns:
        DateTime: Fecha/hora parseada o None si no se pudo parsear
        
    Examples:
        >>> parse_relative_time("hoy")
        2026-01-23T00:00:00-08:00
        
        >>> parse_relative_time("mañana a las 3pm")
        2026-01-24T15:00:00-08:00
    """
    now = get_current_time()
    text_lower = text.lower()
    
    # Mapeo de expresiones comunes
    if 'hoy' in text_lower:
        return now.start_of('day')
    
    if 'mañana' in text_lower or 'mañana' in text_lower:
        return now.add(days=1).start_of('day')
    
    if 'pasado mañana' in text_lower:
        return now.add(days=2).start_of('day')
    
    if 'próximo' in text_lower or 'proximo' in text_lower:
        # Días de la semana
        dias_semana = {
            'lunes': 0, 'martes': 1, 'miércoles': 2, 'miercoles': 2,
            'jueves': 3, 'viernes': 4, 'sábado': 5, 'sabado': 5, 'domingo': 6
        }
        
        for dia, num in dias_semana.items():
            if dia in text_lower:
                # Encontrar el próximo día de la semana
                dias_hasta = (num - now.day_of_week) % 7
                if dias_hasta == 0:
                    dias_hasta = 7  # Próximo, no hoy
                return now.add(days=dias_hasta).start_of('day')
    
    # Intentar parseo con pendulum (maneja muchos formatos)
    try:
        parsed = pendulum.parse(text, tz=TIMEZONE_MEXICALI)
        return parsed
    except:
        return None


def format_to_rfc3339(dt: DateTime) -> str:
    """
    Formatea DateTime a RFC3339 para Google Calendar API
    
    Args:
        dt: DateTime con zona horaria
        
    Returns:
        str: Fecha en formato RFC3339 con offset
        
    Example:
        >>> dt = pendulum.parse('2026-01-24 15:00', tz='America/Tijuana')
        >>> format_to_rfc3339(dt)
        '2026-01-24T15:00:00-08:00'
    """
    return dt.to_rfc3339_string()


def create_event_time(
    date_str: str,
    time_str: Optional[str] = None,
    duration_minutes: int = 60
) -> dict:
    """
    Crea diccionario de tiempo para eventos de Google Calendar
    
    Args:
        date_str: Fecha en formato "YYYY-MM-DD" o expresión relativa
        time_str: Hora en formato "HH:MM" (opcional)
        duration_minutes: Duración del evento en minutos
        
    Returns:
        dict: Con 'start' y 'end' en formato RFC3339
        
    Example:
        >>> create_event_time("2026-01-24", "15:00", 60)
        {
            'start': '2026-01-24T15:00:00-08:00',
            'end': '2026-01-24T16:00:00-08:00'
        }
    """
    # Parsear fecha base
    base_dt = parse_relative_time(date_str)
    if base_dt is None:
        base_dt = pendulum.parse(date_str, tz=TIMEZONE_MEXICALI)
    
    # Agregar hora si se proporciona
    if time_str:
        hora, minuto = map(int, time_str.split(':'))
        base_dt = base_dt.at(hora, minuto, 0)
    
    # Calcular fin
    end_dt = base_dt.add(minutes=duration_minutes)
    
    return {
        'start': format_to_rfc3339(base_dt),
        'end': format_to_rfc3339(end_dt)
    }


def get_timezone_offset() -> str:
    """
    Obtiene el offset actual de zona horaria de Mexicali
    
    Returns:
        str: Offset en formato "+HH:MM" o "-HH:MM"
        
    Example:
        >>> get_timezone_offset()
        '-08:00'  # PST
        '-07:00'  # PDT (horario de verano)
    """
    now = get_current_time()
    return now.format('ZZ')


def get_date_range(days_ahead: int = 7) -> tuple[str, str]:
    """
    Obtiene rango de fechas desde hoy hasta N días adelante
    
    Args:
        days_ahead: Número de días hacia adelante
        
    Returns:
        tuple: (fecha_inicio_rfc3339, fecha_fin_rfc3339)
    """
    now = get_current_time()
    start = now.start_of('day')
    end = now.add(days=days_ahead).end_of('day')
    
    return (format_to_rfc3339(start), format_to_rfc3339(end))


if __name__ == "__main__":
    # Tests
    print("\n" + "="*70)
    print("🧪 TESTS DE UTILIDADES DE TIEMPO (Mexicali, BC)")
    print("="*70 + "\n")
    
    # Test 1: Tiempo actual
    print("📅 Tiempo actual:")
    now = get_current_time()
    print(f"   {now}")
    print(f"   RFC3339: {format_to_rfc3339(now)}")
    print(f"   Offset: {get_timezone_offset()}")
    
    # Test 2: Contexto para LLM
    print("\n💬 Contexto para LLM:")
    print(f"   {get_time_context()}")
    
    # Test 3: Parseo relativo
    print("\n🔍 Parseo de expresiones relativas:")
    expresiones = ["hoy", "mañana", "próximo lunes"]
    for expr in expresiones:
        parsed = parse_relative_time(expr)
        if parsed:
            print(f"   '{expr}' → {parsed.format('dddd, DD/MM/YYYY')}")
    
    # Test 4: Crear evento
    print("\n📆 Crear tiempo de evento:")
    event_time = create_event_time("mañana", "15:00", 60)
    print(f"   Inicio: {event_time['start']}")
    print(f"   Fin: {event_time['end']}")
    
    # Test 5: Rango de fechas
    print("\n📊 Rango de 7 días:")
    start, end = get_date_range(7)
    print(f"   Desde: {start}")
    print(f"   Hasta: {end}")
    
    print("\n✅ Todos los tests completados\n")
