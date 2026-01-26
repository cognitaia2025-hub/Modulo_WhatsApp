# Sistema de Logging con Colores y Separadores

Este documento explica el nuevo sistema de logging mejorado implementado en el proyecto.

## 📋 Características

### 1. **Colores ANSI**
- 🔴 **Separadores**: Líneas rojas (`===`) que delimitan cada nodo
- 🟡 **Entrada/Salida de Nodos**: Mensajes amarillos con 📥/📤
- 🔵 **Mensajes del Usuario**: Texto azul/cyan con 👤
- 🟣 **Interacciones con LLM**: Magenta para prompts y respuestas con 🤖
- 🟢 **Logs INFO**: Verde
- 🔴 **Logs ERROR**: Rojo brillante

### 2. **Separadores Visuales**
Cada nodo tiene separadores claros de inicio y fin:
```
================================================================================
▶ [NODO_4_SELECCION_HERRAMIENTAS] - INICIO
================================================================================
... procesamiento ...
================================================================================
◀ [NODO_4_SELECCION_HERRAMIENTAS] - FIN
================================================================================
```

### 3. **Logs Estructurados**

#### Input/Output de Nodos
```python
📥 [NODO_4_SELECCION] INPUT:
messages: 5 mensajes
contexto_episodico: True

📤 [NODO_4_SELECCION] OUTPUT:
herramientas_seleccionadas: ['list_calendar_events']
```

#### Mensajes del Usuario
```python
👤 USUARIO: ¿Qué eventos tengo hoy?
```

#### Interacciones con LLM
```python
🤖 [DeepSeek/Claude] PROMPT ENVIADO:
Eres un selector de herramientas...

🤖 [DeepSeek/Claude] RESPUESTA RECIBIDA:
list_calendar_events
```

## 🚀 Uso

### Importar Funciones de Logging

```python
from src.utils.logging_config import (
    log_separator,
    log_node_io,
    log_user_message,
    log_llm_interaction,
    setup_colored_logging,
    clear_logs
)
```

### Configurar Logging en un Módulo

```python
import logging
from src.utils.logging_config import setup_colored_logging

# Configurar al inicio del archivo
logger = setup_colored_logging()

# O obtener logger específico del módulo
logger = logging.getLogger(__name__)
```

### Usar en un Nodo

```python
def mi_nodo(state: WhatsAppAgentState) -> Dict:
    # Separador de inicio
    log_separator(logger, "NODO_X_MI_NODO", "INICIO")
    
    # Log de input
    input_data = f"user_id: {state.get('user_id')}\nmensajes: {len(state.get('messages', []))}"
    log_node_io(logger, "INPUT", "NODO_X", input_data)
    
    # Log mensaje del usuario
    mensaje = extraer_ultimo_mensaje_usuario(state)
    log_user_message(logger, mensaje)
    
    # Procesar...
    
    # Log interacción con LLM
    prompt = "Mi prompt..."
    respuesta = llm.invoke(prompt)
    log_llm_interaction(logger, "DeepSeek", prompt, respuesta.content)
    
    # Log de output
    output_data = f"resultado: {resultado}"
    log_node_io(logger, "OUTPUT", "NODO_X", output_data)
    
    # Separador de fin
    log_separator(logger, "NODO_X_MI_NODO", "FIN")
    
    return {"resultado": resultado}
```

## 🧹 Limpiar Logs sin Reiniciar Backend

### Opción 1: Endpoint HTTP

```bash
# Usando curl
curl -X POST http://localhost:8000/clear-logs

# Usando Python
import requests
response = requests.post("http://localhost:8000/clear-logs")
print(response.json())
```

### Opción 2: Programáticamente

```python
from src.utils.logging_config import clear_logs

# Limpiar consola
clear_logs()
```

## 📝 Parámetros de Configuración

### `log_separator(logger, node_name, stage)`
- `logger`: Logger a usar
- `node_name`: Nombre del nodo (ej: "NODO_4_SELECCION")
- `stage`: "INICIO" o "FIN"

### `log_node_io(logger, direction, node_name, content, truncate=500)`
- `direction`: "INPUT" o "OUTPUT"
- `node_name`: Nombre corto del nodo
- `content`: Contenido a loggear
- `truncate`: Máximo de caracteres (0 = sin límite)

### `log_llm_interaction(logger, llm_name, prompt, response, truncate_prompt=1000, truncate_response=1000)`
- `llm_name`: Nombre del LLM (ej: "DeepSeek", "Claude")
- `prompt`: Prompt enviado
- `response`: Respuesta recibida
- `truncate_prompt`: Máximo caracteres del prompt
- `truncate_response`: Máximo caracteres de la respuesta

## 🎨 Colores Disponibles

```python
from src.utils.logging_config import LogColors

# Usar en logs personalizados
logger.info(f"{LogColors.USER}Mi mensaje azul{LogColors.RESET}")
logger.info(f"{LogColors.NODE_IO}Mi mensaje amarillo{LogColors.RESET}")
logger.info(f"{LogColors.SEPARATOR}Mi mensaje rojo{LogColors.RESET}")
```

## 📦 Dependencias

- `colorama`: Para colores ANSI en Windows/Linux/macOS

Instalación:
```bash
pip install colorama
```

## 🔧 Nodos Actualizados

Los siguientes nodos ya usan el nuevo sistema:

✅ **Nodo 3**: Recuperación Episódica  
✅ **Nodo 4**: Selección de Herramientas  
✅ **Nodo 5**: Ejecución de Herramientas + Orquestador  
✅ **app.py**: Endpoint principal + `/clear-logs`  
✅ **graph_whatsapp.py**: Configuración del grafo

## 🎯 Ejemplo Completo de Output

```
================================================================================
▶ [NODO_4_SELECCION_HERRAMIENTAS] - INICIO
================================================================================
📥 [NODO_4_SELECCION] INPUT:
messages: 3 mensajes
contexto_episodico: True

👤 USUARIO: ¿Qué eventos tengo hoy?

    📦 Herramientas disponibles: 5
    📖 Contexto episódico disponible: True

🤖 [DeepSeek/Claude] PROMPT ENVIADO:
Eres un selector de herramientas de calendario...
(800 caracteres)

🤖 [DeepSeek/Claude] RESPUESTA RECIBIDA:
list_calendar_events

    ✅ Herramientas seleccionadas: ['list_calendar_events']

📤 [NODO_4_SELECCION] OUTPUT:
herramientas_seleccionadas: ['list_calendar_events']

================================================================================
◀ [NODO_4_SELECCION_HERRAMIENTAS] - FIN
================================================================================
```

## 💡 Tips

1. **Truncar Prompts Largos**: Usa `truncate_prompt=800` para evitar logs enormes
2. **Logs Detallados en Desarrollo**: Usa `truncate=0` para ver contenido completo
3. **Limpiar Logs Frecuentemente**: Usa el endpoint `/clear-logs` para mantener la consola limpia
4. **Colores en CI/CD**: Los colores se desactivan automáticamente en ambientes sin TTY

## 🐛 Debugging

Si los colores no se muestran:

1. **Windows**: Asegúrate de tener Windows 10+ con soporte ANSI
2. **Terminal**: Usa una terminal moderna (Windows Terminal, iTerm2, etc.)
3. **IDE**: Configura tu IDE para soportar colores ANSI (VS Code lo hace por defecto)

Si necesitas desactivar colores:
```python
from colorama import init
init(strip=True)  # Remover todos los códigos ANSI
```

## 📚 Referencias

- [Colorama Documentation](https://github.com/tartley/colorama)
- [ANSI Escape Codes](https://en.wikipedia.org/wiki/ANSI_escape_code)
