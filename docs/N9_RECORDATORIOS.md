# N9: Nodo de Recordatorios Automáticos

## Descripción
Nodo que envía recordatorios automáticos de WhatsApp antes de las citas médicas.

## Características

### Recordatorios
- **24 horas antes**: Recordatorio con detalles completos de la cita
- **2 horas antes**: Recordatorio breve con confirmación

### Ventanas de Tiempo
- Recordatorio 24h: Se envía entre 23-25 horas antes de la cita (±1 hora)
- Recordatorio 2h: Se envía entre 1.5-2.5 horas antes de la cita (±30 min)

## Uso

### Integración en LangGraph
```python
from src.nodes.recordatorios_node import nodo_recordatorios_wrapper

# Agregar al grafo
graph.add_node("recordatorios", nodo_recordatorios_wrapper)
```

### Ejecución Manual
```python
from src.nodes.recordatorios_node import nodo_recordatorios

estado = {
    'tipo_ejecucion': 'manual'  # o 'scheduler'
}

resultado = nodo_recordatorios(estado)

print(f"Enviados: {resultado.update['recordatorios_enviados']}")
print(f"24h: {resultado.update['recordatorios_24h']}")
print(f"2h: {resultado.update['recordatorios_2h']}")
```

### Con Scheduler (Cron)
```python
# Ejecutar cada 30 minutos
@scheduler.scheduled_job('interval', minutes=30)
def enviar_recordatorios():
    resultado = nodo_recordatorios({'tipo_ejecucion': 'scheduler'})
    logger.info(f"Recordatorios enviados: {resultado.update['recordatorios_enviados']}")
```

## Base de Datos

### Migración
Ejecutar la migración antes de usar el nodo:
```bash
psql $DATABASE_URL -f sql/migrate_add_recordatorios_24h_2h.sql
```

### Columnas Agregadas
- `recordatorio_24h_enviado`: Boolean
- `recordatorio_24h_fecha`: Timestamp
- `recordatorio_2h_enviado`: Boolean  
- `recordatorio_2h_fecha`: Timestamp

## Integración WhatsApp

### Implementación Actual
El nodo incluye una función placeholder `enviar_whatsapp()` que simula el envío.

### Integración Real (Ejemplo con Twilio)
```python
def enviar_whatsapp(telefono: str, mensaje: str) -> bool:
    """
    Envía mensaje WhatsApp usando Twilio API.
    """
    try:
        from twilio.rest import Client
        
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        from_number = os.getenv("TWILIO_WHATSAPP_NUMBER")
        
        client = Client(account_sid, auth_token)
        message = client.messages.create(
            from_=f'whatsapp:{from_number}',
            body=mensaje,
            to=f'whatsapp:{telefono}'
        )
        
        logger.info(f"    📱 WhatsApp enviado: {message.sid}")
        return True
        
    except Exception as e:
        logger.error(f"    ❌ Error enviando WhatsApp: {e}")
        return False
```

## Templates de Mensajes

### 24 Horas Antes
```
🔔 Recordatorio de cita médica

📅 Fecha: {fecha}
🕐 Hora: {hora}
👨‍⚕️ Doctor: Dr. {doctor_nombre}
📍 Consultorio: {ubicacion}

Te esperamos mañana. Si necesitas cancelar o reprogramar, responde a este mensaje.
```

### 2 Horas Antes
```
⏰ Tu cita es en 2 horas

📅 Hoy a las {hora}
👨‍⚕️ Dr. {doctor_nombre}

Por favor confirma tu asistencia respondiendo "Confirmo"
```

## Tests

Ejecutar los tests:
```bash
python -m pytest tests/test_recordatorios.py -v
```

Tests incluidos:
- ✅ Retorna Command pattern
- ✅ Envía recordatorio 24h
- ✅ Maneja caso sin citas
- ✅ Wrapper funciona correctamente

## Performance

### Optimizaciones Implementadas
1. **Batch Updates**: Actualiza todas las citas en una sola transacción
2. **Ventanas Precisas**: Consultas eficientes con índices en `fecha_hora_inicio`
3. **Logging Estructurado**: Mínimo overhead en producción

### Índices Recomendados
Los índices ya están creados en la migración:
- `idx_citas_recordatorios_24h`
- `idx_citas_recordatorios_2h`

## Monitoreo

### Logs
El nodo genera logs estructurados:
```
[NODO_9_RECORDATORIOS] INICIO
    ⏰ Tipo de ejecución: scheduler
    🔍 Buscando citas próximas...
    📊 Recordatorios 24h: 3
    📊 Recordatorios 2h: 1
       ✅ Recordatorio 24h enviado a Juan Pérez
       ✅ Recordatorio 2h enviado a María García
    ✅ Total enviados: 4
[NODO_9_RECORDATORIOS] FIN
```

### Métricas
El Command retorna:
- `recordatorios_enviados`: Total enviados
- `recordatorios_24h`: Enviados 24h
- `recordatorios_2h`: Enviados 2h
- `error_recordatorios`: Mensaje de error (si aplica)

## Seguridad

✅ CodeQL: 0 vulnerabilities  
✅ Prepared statements para SQL injection  
✅ Validación de números de teléfono  
✅ Logging sin datos sensibles  

## Mantenimiento

### Cambiar Ventanas de Tiempo
Editar constantes en `src/nodes/recordatorios_node.py`:
```python
RECORDATORIO_24H = 24  # horas
RECORDATORIO_2H = 2    # horas
```

### Personalizar Mensajes
Editar templates:
```python
TEMPLATE_24H = """Tu mensaje personalizado..."""
TEMPLATE_2H = """Tu mensaje personalizado..."""
```
