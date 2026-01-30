# 🔧 Documentación Técnica de Nodos - Sistema WhatsApp Agent

> **Para desarrolladores y equipo técnico**  
> Especificaciones técnicas completas de cada nodo del grafo LangGraph

---

## 📐 Arquitectura General

**Framework:** LangGraph  
**Estado:** WhatsAppAgentState (TypedDict)  
**Patrón:** StateGraph con checkpointing PostgreSQL  
**LLM Principal:** DeepSeek-Chat  
**LLM Fallback:** Claude Sonnet 4.5

### Estado del Grafo (WhatsAppAgentState)

```python
class WhatsAppAgentState(TypedDict):
    # Mensajes y contexto
    messages: Annotated[List[BaseMessage], add_messages]
    user_id: str
    session_id: str
    
    # Identificación (Nodo 0)
    usuario_registrado: bool
    tipo_usuario: str  # 'personal', 'doctor', 'paciente_externo', 'admin'
    es_admin: bool
    usuario_info: Dict[str, Any]
    doctor_id: Optional[int]
    paciente_id: Optional[int]
    
    # Clasificación (Nodo 2)
    clasificacion: str  # 'personal', 'medica', 'chat'
    requiere_herramientas: bool
    
    # Recuperación de contexto (Nodos 3A/3B)
    contexto_episodico: List[Dict]
    contexto_medico: Dict[str, Any]
    
    # Selección y ejecución (Nodos 4, 5A/5B)
    herramientas_seleccionadas: List[Dict]
    resultados_ejecucion: List[Dict]
    
    # Recepcionista (Nodo 6R)
    estado_conversacion: str
    datos_temporales: Dict[str, Any]
    slots_disponibles: List[Dict]
    
    # Sincronización (Nodo 8)
    necesita_sincronizacion: bool
    google_event_id: Optional[str]
    
    # Salida final
    resumen: str
    accion_requerida: Optional[str]
```

---

## 🔢 N0 - Nodo de Identificación de Usuario

### Especificaciones

**Archivo:** `src/nodes/identificacion_usuario_node.py`  
**Tipo:** Nodo Automatizado (Sin LLM)  
**Posición:** Entry point del grafo  
**Duración promedio:** 50-100ms

### Firma de Función

```python
def nodo_identificacion_usuario(state: WhatsAppAgentState) -> WhatsAppAgentState:
    """
    Identifica el usuario por número de teléfono y carga su perfil.
    
    Args:
        state: Estado actual del grafo
        
    Returns:
        State actualizado con user_info, tipo_usuario, doctor_id, etc.
        
    Raises:
        psycopg.Error: Si falla la conexión a BD
    """
```

### Algoritmo

```python
1. Extraer phone_number de state['messages'][-1].additional_kwargs
2. Ejecutar consulta SQL:
   SELECT u.*, d.id as doctor_id, d.nombre_completo, d.especialidad
   FROM usuarios u
   LEFT JOIN doctores d ON d.phone_number = u.phone_number
   WHERE u.phone_number = %s

3. IF usuario_encontrado:
       state['usuario_registrado'] = True
       state['usuario_info'] = row_to_dict(result)
       state['tipo_usuario'] = result['tipo_usuario']
       state['es_admin'] = result['es_admin']
       state['doctor_id'] = result['doctor_id']
       UPDATE usuarios SET last_seen = NOW() WHERE phone_number = %s
   ELSE:
       es_admin = (phone_number == ADMIN_PHONE_NUMBER)
       tipo = 'admin' if es_admin else 'paciente_externo'
       
       INSERT INTO usuarios (phone_number, display_name, es_admin, tipo_usuario, ...)
       VALUES (%s, %s, %s, %s, ...)
       RETURNING *
       
       state['usuario_registrado'] = False
       state['usuario_info'] = created_user
       state['tipo_usuario'] = tipo
       state['es_admin'] = es_admin
       state['doctor_id'] = None

4. RETURN state
```

### Dependencias

```python
import psycopg
from src.config.database import DATABASE_URL
from src.state.agent_state import WhatsAppAgentState
```

### Tablas Relacionadas

- `usuarios` (lectura/escritura)
- `doctores` (lectura con LEFT JOIN)

### Índices Utilizados

- `idx_usuarios_phone` en usuarios(phone_number)
- `idx_doctores_phone` en doctores(phone_number)

### Tests

```python
# tests/Etapa_1/test_identificacion_node.py
test_usuario_nuevo_se_registra_automaticamente()
test_usuario_existente_se_identifica()
test_doctor_obtiene_doctor_id()
test_admin_se_detecta_correctamente()
```

---

## 💾 N1 - Nodo de Caché de Sesión

### Especificaciones

**Archivo:** `src/nodes/cache_sesion_node.py`  
**Tipo:** Nodo Automatizado (Sin LLM)  
**Duración promedio:** 30-80ms

### Firma de Función

```python
def nodo_cache_sesion(state: WhatsAppAgentState) -> WhatsAppAgentState:
    """
    Recupera mensajes de la sesión activa (< 24h inactividad).
    
    Args:
        state: Estado actual del grafo
        
    Returns:
        State con mensajes de cache agregados si existe sesión activa
    """
```

### Algoritmo

```python
1. user_id = state['user_id']
2. Ejecutar consulta SQL:
   SELECT thread_id, last_activity,
          EXTRACT(EPOCH FROM (NOW() - last_activity))/3600 as hours_inactive
   FROM user_sessions
   WHERE user_id = %s 
     AND last_activity > NOW() - INTERVAL '24 hours'
   ORDER BY last_activity DESC
   LIMIT 1

3. IF session_found AND hours_inactive < 24:
       thread_id = result['thread_id']
       messages_cache = langgraph_checkpoint.get_messages(thread_id)
       state['messages'] = messages_cache + state['messages']
       state['session_id'] = thread_id
       
       UPDATE user_sessions 
       SET last_activity = NOW(), messages_count = messages_count + 1
       WHERE user_id = %s AND thread_id = %s
   ELSE:
       thread_id = f"thread_{user_id}_{uuid4().hex[:8]}"
       state['session_id'] = thread_id
       
       INSERT INTO user_sessions (user_id, thread_id, phone_number, last_activity)
       VALUES (%s, %s, %s, NOW())

4. RETURN state
```

### Tablas Relacionadas

- `user_sessions` (lectura/escritura)
- `checkpoints` (LangGraph, lectura)

### Rolling Window Logic

```python
WINDOW_SIZE = 24  # horas
CLEANUP_THRESHOLD = 30  # días

# Sesión se considera activa si:
last_activity > NOW() - INTERVAL '24 hours'

# Limpieza automática de sesiones antiguas:
DELETE FROM user_sessions WHERE last_activity < NOW() - INTERVAL '30 days'
```

---

## 🧠 N2 - Nodo de Clasificación Inteligente

### Especificaciones

**Archivo:** `src/nodes/filtrado_inteligente_node.py`  
**Tipo:** Nodo Inteligente (CON LLM)  
**LLM:** DeepSeek-Chat  
**Duración promedio:** 800-1200ms

### Firma de Función

```python
def filtrado_inteligente_node(state: WhatsAppAgentState) -> WhatsAppAgentState:
    """
    Clasifica el mensaje en: personal, medica, o chat casual.
    
    Args:
        state: Estado actual del grafo
        
    Returns:
        State con clasificacion, requiere_herramientas
    """
```

### Prompt Template

```python
CLASIFICACION_PROMPT = """Clasifica la siguiente solicitud de {tipo_usuario}:

Mensaje: "{mensaje_usuario}"

Contexto del usuario:
- Tipo: {tipo_usuario}
- Registrado: {usuario_registrado}
- Historial reciente: {contexto_reciente}

PATRONES DE CLASIFICACIÓN:

MÉDICA (si tipo_usuario == 'doctor' o 'paciente_externo'):
- Palabras clave: paciente, consulta, cita médica, historial, diagnóstico
- Ejemplos: "mi paciente Juan necesita cita", "agendar consulta"

PERSONAL (cualquier usuario):
- Palabras clave: mi cita, mi evento, mi reunión, recordarme
- Ejemplos: "mi cita del viernes", "recordarme comprar"

CHAT (conversación casual):
- Ejemplos: "hola", "gracias", "cómo estás"

Responde SOLO con JSON válido:
{{
  "clasificacion": "medica" | "personal" | "chat",
  "confianza": 0.0-1.0,
  "razonamiento": "breve explicación",
  "requiere_herramientas": true | false
}}"""
```

### Algoritmo

```python
1. tipo_usuario = state['tipo_usuario']
2. mensaje = state['messages'][-1].content
3. contexto = get_recent_context(state['user_id'], limit=3)

4. prompt = CLASIFICACION_PROMPT.format(
       tipo_usuario=tipo_usuario,
       mensaje_usuario=mensaje,
       usuario_registrado=state['usuario_registrado'],
       contexto_reciente=json.dumps(contexto)
   )

5. TRY:
       response = llm_with_fallback.invoke(prompt)
       clasificacion = json.loads(response.content)
   EXCEPT (JSONDecodeError, ValidationError):
       # Fallback heurístico
       clasificacion = classify_with_keywords(mensaje, tipo_usuario)

6. # Validaciones de negocio
   IF tipo_usuario == 'paciente_externo':
       IF clasificacion['clasificacion'] == 'personal':
           clasificacion['clasificacion'] = 'medica'

7. state['clasificacion'] = clasificacion['clasificacion']
   state['requiere_herramientas'] = clasificacion['requiere_herramientas']

8. # Log para analytics
   INSERT INTO clasificaciones_llm (session_id, user_id, modelo, clasificacion, ...)
   VALUES (%s, %s, 'deepseek-chat', %s, ...)

9. RETURN state
```

### LLM Configuration

```python
llm_primary = ChatOpenAI(
    base_url="https://api.deepseek.com",
    api_key=DEEPSEEK_API_KEY,
    model="deepseek-chat",
    temperature=0.1,
    max_tokens=200
)

llm_fallback = ChatAnthropic(
    model="claude-sonnet-4.5",
    temperature=0.1,
    max_tokens=200
)

llm_with_fallback = llm_primary.with_fallbacks([llm_fallback])
```

### Tabla de Registro

```sql
CREATE TABLE clasificaciones_llm (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(200) NOT NULL,
    user_id VARCHAR(100) NOT NULL,
    modelo VARCHAR(50) NOT NULL,
    clasificacion VARCHAR(50) NOT NULL,
    confianza DECIMAL(3,2),
    mensaje_usuario TEXT NOT NULL,
    tiempo_respuesta_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 🔍 N3A - Nodo de Recuperación Episódica Personal

### Especificaciones

**Archivo:** `src/nodes/recuperacion_episodica_node.py`  
**Tipo:** Nodo Inteligente (CON LLM para búsqueda semántica)  
**Duración promedio:** 600-900ms

### Algoritmo

```python
1. user_id = state['user_id']
2. mensaje = state['messages'][-1].content
3. embedding = generate_embedding(mensaje)  # 384 dimensiones

4. # Búsqueda semántica con pgvector
   contexto = SELECT id, resumen, 
                     1 - (embedding <=> %s::vector) AS similarity,
                     metadata, timestamp
              FROM memoria_episodica
              WHERE user_id = %s
              ORDER BY embedding <=> %s::vector
              LIMIT 5

5. state['contexto_episodico'] = [
       {
           'resumen': row['resumen'],
           'similarity': row['similarity'],
           'fecha': row['metadata']['fecha'],
           'tipo': row['metadata']['tipo']
       }
       for row in contexto
   ]

6. RETURN state
```

### Función de Embedding

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

def generate_embedding(text: str) -> List[float]:
    """Genera embedding de 384 dimensiones"""
    embedding = model.encode(text, convert_to_numpy=True)
    return embedding.tolist()
```

---

## 🔍 N3B - Nodo de Recuperación Médica

### Especificaciones

**Archivo:** `src/nodes/recuperacion_medica_node.py`  
**Tipo:** Nodo Inteligente (híbrido)  
**Duración promedio:** 700-1000ms

### Algoritmo

```python
1. doctor_id = state['doctor_id']
2. mensaje = state['messages'][-1].content

3. # 1. Pacientes recientes (últimos 10)
   pacientes_recientes = SELECT id, nombre_completo, telefono, ultima_cita
                         FROM pacientes
                         WHERE doctor_id = %s
                         ORDER BY ultima_cita DESC NULLS LAST
                         LIMIT 10

4. # 2. Citas del día
   hoy = date.today()
   citas_hoy = SELECT c.id, c.fecha_hora_inicio, c.estado, c.motivo_consulta,
                      p.nombre_completo as paciente_nombre
               FROM citas_medicas c
               JOIN pacientes p ON c.paciente_id = p.id
               WHERE c.doctor_id = %s
                 AND DATE(c.fecha_hora_inicio) = %s
                 AND c.estado IN ('programada', 'confirmada')
               ORDER BY c.fecha_hora_inicio

5. # 3. Búsqueda semántica en historiales (SI MENCIONA)
   IF 'historial' in mensaje.lower() OR 'paciente' in mensaje.lower():
       embedding = generate_embedding(mensaje)
       historiales = SELECT h.id, h.diagnostico_principal, h.sintomas,
                            1 - (h.embedding <=> %s::vector) AS similarity,
                            p.nombre_completo
                     FROM historiales_medicos h
                     JOIN pacientes p ON h.paciente_id = p.id
                     WHERE p.doctor_id = %s
                       AND h.embedding IS NOT NULL
                     ORDER BY h.embedding <=> %s::vector
                     LIMIT 5

6. # 4. Estadísticas del doctor
   stats = {
       'total_pacientes': COUNT(pacientes WHERE doctor_id = %s),
       'citas_hoy': COUNT(citas_hoy),
       'citas_semana': COUNT(citas WHERE doctor_id = %s AND semana_actual)
   }

7. state['contexto_medico'] = {
       'pacientes_recientes': pacientes_recientes,
       'citas_hoy': citas_hoy,
       'historiales_relevantes': historiales if exists else [],
       'estadisticas': stats
   }

8. RETURN state
```

### Tablas Relacionadas

- `pacientes` (lectura)
- `citas_medicas` (lectura)
- `historiales_medicos` (lectura con búsqueda vectorial)

---

## 🛠️ N4 - Nodo de Selección de Herramientas

### Especificaciones

**Archivo:** `src/nodes/seleccion_herramientas_node.py`  
**Tipo:** Nodo Inteligente (CON LLM)  
**LLM:** DeepSeek-Chat  
**Duración promedio:** 900-1400ms

### Pool de Herramientas

```python
HERRAMIENTAS_DISPONIBLES = {
    # Calendario Personal (6)
    'list_calendar_events': {...},
    'create_calendar_event': {...},
    'update_calendar_event': {...},
    'delete_calendar_event': {...},
    'search_calendar_events': {...},
    'postpone_calendar_event': {...},
    
    # Médicas Básicas (6)
    'crear_paciente_medico': {...},
    'buscar_pacientes_doctor': {...},
    'consultar_slots_disponibles': {...},
    'agendar_cita_medica_completa': {...},
    'modificar_cita_medica': {...},
    'cancelar_cita_medica': {...},
    
    # Médicas Avanzadas (6)
    'registrar_consulta': {...},
    'consultar_historial_paciente': {...},
    'actualizar_disponibilidad_doctor': {...},
    'generar_reporte_doctor': {...},
    'obtener_estadisticas_consultas': {...},
    'buscar_citas_por_periodo': {...}
}
```

### Prompt Template

```python
SELECCION_PROMPT = """Eres un asistente especializado en calendario y gestión médica.

Usuario: {tipo_usuario}
Clasificación: {clasificacion}
Mensaje: "{mensaje_usuario}"

Contexto disponible:
{contexto_json}

HERRAMIENTAS DISPONIBLES:
{herramientas_json}

REGLAS ESTRICTAS:
1. Si clasificacion == 'medica' Y tipo_usuario == 'doctor':
   → Puede usar herramientas médicas y personales
   
2. Si clasificacion == 'personal':
   → Solo herramientas de calendario personal (list_, create_, update_, delete_, search_, postpone_)
   
3. Si tipo_usuario == 'paciente_externo':
   → SOLO 'agendar_cita_medica_completa' y 'consultar_slots_disponibles'
   → NO PUEDE usar herramientas de doctors
   
4. Si clasificacion == 'chat':
   → herramientas = []

IMPORTANTE - SISTEMA DE TURNOS:
- Para solicitudes de cita: usar 'agendar_cita_medica_completa'
- El sistema asigna doctor automáticamente por turnos (NO el LLM)
- Para buscar disponibilidad: usar 'consultar_slots_disponibles' (NO especifica doctor)

Responde SOLO con JSON válido:
{{
  "herramientas": [
    {{
      "tool_name": "nombre_herramienta",
      "parametros": {{...}},
      "razonamiento": "por qué esta herramienta"
    }}
  ],
  "mensaje_usuario": "Explicación amigable de qué vas a hacer"
}}

Si no se necesitan herramientas: {{"herramientas": [], "mensaje_usuario": "..."}}
"""
```

### Algoritmo

```python
1. clasificacion = state['clasificacion']
2. tipo_usuario = state['tipo_usuario']
3. mensaje = state['messages'][-1].content

4. # Filtrar herramientas permitidas según tipo_usuario
   herramientas_permitidas = filter_tools_by_user_type(
       HERRAMIENTAS_DISPONIBLES, 
       tipo_usuario, 
       clasificacion
   )

5. contexto = state.get('contexto_medico', state.get('contexto_episodico', {}))

6. prompt = SELECCION_PROMPT.format(
       tipo_usuario=tipo_usuario,
       clasificacion=clasificacion,
       mensaje_usuario=mensaje,
       contexto_json=json.dumps(contexto, indent=2, ensure_ascii=False),
       herramientas_json=json.dumps(herramientas_permitidas, indent=2)
   )

7. response = llm_with_fallback.invoke(prompt)
8. seleccion = json.loads(response.content)

9. # Validar que las herramientas seleccionadas están permitidas
   herramientas_validadas = []
   FOR tool IN seleccion['herramientas']:
       IF tool['tool_name'] IN herramientas_permitidas:
           herramientas_validadas.append(tool)
       ELSE:
           LOG_WARNING(f"LLM intentó usar herramienta no permitida: {tool['tool_name']}")

10. state['herramientas_seleccionadas'] = herramientas_validadas
    state['mensaje_preparacion'] = seleccion['mensaje_usuario']

11. RETURN state
```

---

## ⚙️ N5B - Nodo de Ejecución Médica

### Especificaciones

**Archivo:** `src/nodes/ejecucion_medica_node.py`  
**Tipo:** Nodo Automatizado (Sin LLM)  
**Duración promedio:** Variable (200-2000ms)

### Algoritmo

```python
def ejecucion_medica_node(state: WhatsAppAgentState) -> Dict:
    herramientas = state['herramientas_seleccionadas']
    doctor_id = state['doctor_id']
    resultados = []
    errores = []
    necesita_sync = False

    FOR tool_spec IN herramientas:
        tool_name = tool_spec['tool_name']
        parametros = tool_spec['parametros']
        
        TRY:
            # Validar permisos
            IF tool_name.startswith('doctor_') AND NOT doctor_id:
                RAISE PermissionError("Solo doctores pueden usar esta herramienta")
            
            # Agregar doctor_id automáticamente si es necesario
            IF tool_name IN TOOLS_REQUIRE_DOCTOR_ID:
                parametros['doctor_id'] = doctor_id
            
            # Ejecutar herramienta
            tool = TOOL_MAPPING[tool_name]
            resultado = tool.invoke(parametros)
            
            resultados.append({
                'tool_name': tool_name,
                'status': 'success',
                'resultado': resultado,
                'parametros_usados': parametros
            })
            
            # Marcar para sincronización si es necesario
            IF tool_name IN ['agendar_cita_medica_completa', 'modificar_cita_medica']:
                necesita_sync = True
                state['cita_id_para_sync'] = extract_cita_id(resultado)
                state['operacion_sync'] = 'crear' if 'agendar' in tool_name else 'actualizar'
            
            IF tool_name == 'cancelar_cita_medica':
                necesita_sync = True
                state['cita_id_para_sync'] = parametros.get('cita_id')
                state['operacion_sync'] = 'cancelar'
        
        EXCEPT Exception as e:
            errores.append({
                'tool_name': tool_name,
                'error': str(e),
                'parametros': parametros
            })
    
    state['resultados_ejecucion'] = resultados
    state['errores_ejecucion'] = errores
    state['necesita_sincronizacion'] = necesita_sync
    
    RETURN state
```

### Mapping de Herramientas

```python
from src.medical.tools import (
    crear_paciente_medico,
    buscar_pacientes_doctor,
    consultar_slots_disponibles,
    agendar_cita_medica_completa,
    # ... más herramientas
)

TOOL_MAPPING = {
    'crear_paciente_medico': crear_paciente_medico,
    'buscar_pacientes_doctor': buscar_pacientes_doctor,
    'consultar_slots_disponibles': consultar_slots_disponibles,
    'agendar_cita_medica_completa': agendar_cita_medica_completa,
    # ...
}

TOOLS_REQUIRE_DOCTOR_ID = [
    'buscar_pacientes_doctor',
    'consultar_slots_disponibles',
    'generar_reporte_doctor',
    # ...
]
```

---

## 🎙️ N6R - Nodo de Recepcionista Conversacional

### Especificaciones

**Archivo:** `src/nodes/recepcionista_node.py`  
**Tipo:** Nodo Inteligente (CON LLM)  
**LLM:** DeepSeek-Chat  
**Duración promedio:** 1000-1500ms

### Estados de Conversación

```python
ESTADOS_CONVERSACION = {
    'inicial': 'Paciente acaba de solicitar cita',
    'esperando_nombre': 'Pedimos nombre del paciente',
    'mostrando_slots': 'Mostramos opciones A/B/C',
    'esperando_seleccion': 'Esperando que elija A/B/C',
    'confirmando': 'Confirmando detalles antes de agendar',
    'completado': 'Cita agendada exitosamente',
    'error': 'Ocurrió un error'
}
```

### Algoritmo

```python
def recepcionista_node(state: WhatsAppAgentState) -> Dict:
    estado_conv = state.get('estado_conversacion', 'inicial')
    mensaje = state['messages'][-1].content
    datos_temp = state.get('datos_temporales', {})
    
    IF estado_conv == 'inicial':
        # Pedir nombre
        respuesta = "¡Hola! Claro, te ayudo a agendar una cita. ¿Cuál es tu nombre completo?"
        nuevo_estado = 'esperando_nombre'
    
    ELIF estado_conv == 'esperando_nombre':
        # Extraer nombre con LLM
        nombre = extraer_nombre_con_llm(mensaje)
        datos_temp['nombre_paciente'] = nombre
        
        # Consultar slots disponibles (próximos 7 días)
        slots = consultar_slots_disponibles.invoke({
            'dias_adelante': 7,
            'incluir_todos_doctores': True
        })
        
        # Formatear top 3 opciones (sin mencionar doctor)
        opciones_texto = formatear_opciones_slots(slots[:3])
        respuesta = f"Gracias {nombre}! 😊\n\nTenemos estos horarios disponibles:\n\n{opciones_texto}\n\n¿Cuál te acomoda mejor?"
        datos_temp['slots_mostrados'] = slots[:3]
        nuevo_estado = 'esperando_seleccion'
    
    ELIF estado_conv == 'esperando_seleccion':
        # Extraer selección (A/B/C)
        seleccion_idx = extraer_seleccion(mensaje)
        
        IF seleccion_idx IS None:
            respuesta = "Por favor elige A, B o C 😊"
            nuevo_estado = estado_conv  # Mantener estado
        ELSE:
            slot_elegido = datos_temp['slots_mostrados'][seleccion_idx]
            datos_temp['slot_elegido'] = slot_elegido
            
            # Confirmar
            respuesta = f"""Perfecto! Confirmo los datos:

📅 {slot_elegido['fecha_formateada']}
🕐 {slot_elegido['hora_inicio']} - {slot_elegido['hora_fin']}
👤 {datos_temp['nombre_paciente']}

¿Todo correcto? (Sí/No)"""
            nuevo_estado = 'confirmando'
    
    ELIF estado_conv == 'confirmando':
        confirmacion = detectar_confirmacion(mensaje)
        
        IF confirmacion == 'si':
            # Agendar cita
            slot = datos_temp['slot_elegido']
            resultado = agendar_cita_medica_completa.invoke({
                'paciente_nombre': datos_temp['nombre_paciente'],
                'paciente_telefono': state['user_id'],
                'fecha_hora_inicio': slot['datetime_inicio'],
                'fecha_hora_fin': slot['datetime_fin'],
                'tipo_consulta': 'primera_vez'
            })
            
            respuesta = f"""✅ ¡Cita confirmada!

📅 {slot['fecha_formateada']}
🕐 {slot['hora_inicio']} - {slot['hora_fin']}
👨‍⚕️ {resultado['doctor_nombre']}
📍 Consultorio #101

💬 Te recordaremos 24 horas antes.
¿Necesitas algo más?"""
            nuevo_estado = 'completado'
            
            state['necesita_sincronizacion'] = True
            state['cita_id_para_sync'] = resultado['cita_id']
            state['operacion_sync'] = 'crear'
        
        ELSE:
            respuesta = "Entendido. ¿Quieres elegir otra fecha? (Sí/No)"
            nuevo_estado = 'inicial'
    
    state['estado_conversacion'] = nuevo_estado
    state['datos_temporales'] = datos_temp
    state['respuesta_recepcionista'] = respuesta
    
    RETURN state
```

### Funciones Auxiliares

```python
def extraer_nombre_con_llm(mensaje: str) -> str:
    """Extrae nombre usando LLM"""
    prompt = f"""Extrae SOLO el nombre completo de este mensaje:
    "{mensaje}"
    
    Responde SOLO con el nombre, sin nada más."""
    
    response = llm.invoke(prompt)
    return response.content.strip()

def extraer_seleccion(mensaje: str) -> Optional[int]:
    """Extrae selección A/B/C con regex"""
    match = re.search(r'\b([ABC]|opci[oó]n\s*[ABC])\b', mensaje, re.IGNORECASE)
    if match:
        letra = match.group(1)[-1].upper()
        return {'A': 0, 'B': 1, 'C': 2}[letra]
    return None

def formatear_opciones_slots(slots: List[Dict]) -> str:
    """Formatea slots sin mencionar doctores"""
    opciones = []
    letras = ['A', 'B', 'C']
    for i, slot in enumerate(slots):
        opciones.append(
            f"{letras[i]}) {slot['dia_nombre']} {slot['dia']} de {slot['mes_nombre']} "
            f"a las {slot['hora_inicio']}"
        )
    return "\n".join(opciones)
```

---

## 📝 N6 - Nodo de Generación de Respuesta

### Especificaciones

**Archivo:** `src/nodes/generacion_resumen_node.py`  
**Tipo:** Nodo Inteligente (CON LLM)  
**LLM:** DeepSeek-Chat  
**Duración promedio:** 700-1100ms

### Algoritmo

```python
def generacion_resumen_node(state: WhatsAppAgentState) -> Dict:
    # Si ya hay respuesta del recepcionista, usarla
    IF 'respuesta_recepcionista' IN state:
        resumen_final = state['respuesta_recepcionista']
    ELSE:
        # Generar resumen de resultados de ejecución
        resultados = state.get('resultados_ejecucion', [])
        errores = state.get('errores_ejecucion', [])
        
        prompt = f"""Genera un resumen amigable y claro para WhatsApp.

Resultados de las acciones:
{json.dumps(resultados, indent=2, ensure_ascii=False)}

Errores (si existen):
{json.dumps(errores, indent=2, ensure_ascii=False)}

REGLAS:
1. Usa emojis apropiados
2. Sé conciso pero claro
3. Si hubo errores, explícalos de forma amigable
4. Menciona los datos clave (fechas, horas, nombres)
5. Pregunta si necesita algo más al final

Responde SOLO con el mensaje final, sin explicaciones."""

        response = llm.invoke(prompt)
        resumen_final = response.content
    
    state['resumen'] = resumen_final
    
    RETURN state
```

---

## 💾 N7 - Nodo de Persistencia Episódica

### Especificaciones

**Archivo:** `src/nodes/persistencia_episodica_node.py`  
**Tipo:** Nodo Inteligente (CON LLM para resumen)  
**Duración promedio:** 600-900ms

### Algoritmo

```python
def persistencia_episodica_node(state: WhatsAppAgentState) -> Dict:
    # Generar resumen de la conversación
    mensajes = state['messages'][-5:]  # Últimos 5 mensajes
    resumen = state.get('resumen', '')
    
    prompt = f"""Crea un resumen conciso (max 200 caracteres) de esta interacción:

Mensajes:
{format_messages_for_summary(mensajes)}

Resultado final:
{resumen}

El resumen debe incluir:
- Acción principal realizada
- Datos clave (fechas, nombres, resultados)
- Estado final

Formato: "[DD/MM/YYYY HH:MM] Acción: Detalles. Estado: Final."
Responde SOLO con el resumen."""

    response = llm.invoke(prompt)
    resumen_episodico = response.content.strip()
    
    # Generar embedding
    embedding = generate_embedding(resumen_episodico)
    
    # Guardar en BD
    metadata = {
        'tipo': state['clasificacion'],
        'session_id': state['session_id'],
        'fecha': datetime.now().isoformat(),
        'timezone': 'America/Tijuana'
    }
    
    INSERT INTO memoria_episodica (user_id, resumen, embedding, metadata, timestamp)
    VALUES (%s, %s, %s::vector, %s::jsonb, NOW())
    
    RETURN state
```

---

## 🔄 N8 - Nodo de Sincronización Híbrida

### Especificaciones

**Archivo:** `src/nodes/sincronizador_hibrido_node.py`  
**Tipo:** Nodo Automatizado (Sin LLM)  
**Duración promedio:** 500-1500ms (depende de Google API)

### Algoritmo

```python
def sincronizador_hibrido_node(state: WhatsAppAgentState) -> Dict:
    IF NOT state.get('necesita_sincronizacion', False):
        RETURN state
    
    cita_id = state['cita_id_para_sync']
    operacion = state['operacion_sync']  # 'crear', 'actualizar', 'cancelar'
    
    # Obtener datos de la cita de BD
    cita = SELECT c.*, d.nombre_completo as doctor_nombre, p.nombre_completo as paciente_nombre
           FROM citas_medicas c
           JOIN doctores d ON c.doctor_id = d.id
           JOIN pacientes p ON c.paciente_id = p.id
           WHERE c.id = %s
    
    TRY:
        IF operacion == 'crear':
            event = {
                'summary': f"Cita: {cita['paciente_nombre']}",
                'description': f"Paciente: {cita['paciente_nombre']}\nDoctor: {cita['doctor_nombre']}\nMotivo: {cita['motivo_consulta']}",
                'start': {
                    'dateTime': cita['fecha_hora_inicio'].isoformat(),
                    'timeZone': 'America/Tijuana'
                },
                'end': {
                    'dateTime': cita['fecha_hora_fin'].isoformat(),
                    'timeZone': 'America/Tijuana'
                }
            }
            
            result = calendar_service.events().insert(
                calendarId='primary',
                body=event
            ).execute()
            
            google_event_id = result['id']
            estado_sync = 'sincronizada'
            
            # Actualizar BD
            UPDATE citas_medicas 
            SET google_event_id = %s, sincronizada_google = TRUE
            WHERE id = %s
            
            INSERT INTO sincronizacion_calendar (cita_id, google_event_id, estado, ultimo_intento)
            VALUES (%s, %s, 'sincronizada', NOW())
        
        ELIF operacion == 'actualizar':
            # Código similar para actualizar
            ...
        
        ELIF operacion == 'cancelar':
            # Código similar para cancelar
            ...
        
        state['google_event_id'] = google_event_id
        state['error_sincronizacion'] = None
    
    EXCEPT HttpError as e:
        # Error de Google API
        estado_sync = 'error' if intentos < 3 else 'error_permanente'
        
        INSERT INTO sincronizacion_calendar (cita_id, estado, error_message, intentos, ultimo_intento)
        VALUES (%s, %s, %s, 1, NOW())
        ON CONFLICT (cita_id) DO UPDATE
        SET intentos = sincronizacion_calendar.intentos + 1,
            estado = %s,
            error_message = %s,
            ultimo_intento = NOW()
        
        state['error_sincronizacion'] = str(e)
    
    RETURN state
```

### Retry Logic

```python
# Worker de background: src/background/sync_retry_worker.py

def retry_failed_syncs():
    """Ejecutado cada 15 minutos por scheduler"""
    
    # Buscar sincronizaciones fallidas
    syncs_pendientes = SELECT * FROM sincronizacion_calendar
                       WHERE estado IN ('error', 'reintentando')
                         AND intentos < max_intentos
                         AND (siguiente_reintento IS NULL OR siguiente_reintento < NOW())
    
    FOR sync IN syncs_pendientes:
        TRY:
            # Reintentar sincronización
            sincronizar_cita(sync['cita_id'], sync['operacion'])
            
            UPDATE sincronizacion_calendar
            SET estado = 'sincronizada', ultimo_intento = NOW()
            WHERE id = sync['id']
        
        EXCEPT Exception as e:
            # Calcular backoff exponencial
            backoff_minutes = 2 ** sync['intentos']  # 2, 4, 8, 16, 32
            siguiente_reintento = NOW() + INTERVAL f'{backoff_minutes} minutes'
            
            UPDATE sincronizacion_calendar
            SET intentos = intentos + 1,
                estado = 'reintentando',
                error_message = %s,
                ultimo_intento = NOW(),
                siguiente_reintento = %s
            WHERE id = sync['id']
```

---

## 📊 Compilación del Grafo

### Estructura Final

```python
from langgraph.graph import StateGraph, END

workflow = StateGraph(WhatsAppAgentState)

# Agregar nodos
workflow.add_node("identificacion_usuario", nodo_identificacion_usuario)
workflow.add_node("cache_sesion", nodo_cache_sesion)
workflow.add_node("filtrado_inteligente", filtrado_inteligente_node)
workflow.add_node("recuperacion_episodica", recuperacion_episodica_node)
workflow.add_node("recuperacion_medica", recuperacion_medica_node)
workflow.add_node("seleccion_herramientas", seleccion_herramientas_node)
workflow.add_node("ejecucion_herramientas", ejecucion_herramientas_node)
workflow.add_node("ejecucion_medica", ejecucion_medica_node)
workflow.add_node("recepcionista", recepcionista_node)
workflow.add_node("generacion_resumen", generacion_resumen_node)
workflow.add_node("persistencia_episodica", persistencia_episodica_node)
workflow.add_node("sincronizador_hibrido", sincronizador_hibrido_node)

# Entry point
workflow.set_entry_point("identificacion_usuario")

# Rutas fijas
workflow.add_edge("identificacion_usuario", "cache_sesion")
workflow.add_edge("cache_sesion", "filtrado_inteligente")

# Ruta condicional: clasificación
def decidir_recuperacion(state):
    clasificacion = state['clasificacion']
    tipo_usuario = state['tipo_usuario']
    
    if clasificacion == 'chat':
        return "generacion_resumen"
    elif clasificacion == 'medica' and tipo_usuario in ['doctor', 'paciente_externo']:
        return "recuperacion_medica"
    else:
        return "recuperacion_episodica"

workflow.add_conditional_edges(
    "filtrado_inteligente",
    decidir_recuperacion,
    {
        "recuperacion_episodica": "recuperacion_episodica",
        "recuperacion_medica": "recuperacion_medica",
        "generacion_resumen": "generacion_resumen"
    }
)

# Rutas a selección
workflow.add_edge("recuperacion_episodica", "seleccion_herramientas")
workflow.add_edge("recuperacion_medica", "seleccion_herramientas")

# Ruta condicional: tipo de ejecución
def decidir_ejecucion(state):
    clasificacion = state['clasificacion']
    tipo_usuario = state['tipo_usuario']
    
    if not state.get('requiere_herramientas', False):
        return "generacion_resumen"
    elif tipo_usuario == 'paciente_externo':
        return "recepcionista"
    elif clasificacion == 'medica':
        return "ejecucion_medica"
    else:
        return "ejecucion_herramientas"

workflow.add_conditional_edges(
    "seleccion_herramientas",
    decidir_ejecucion,
    {
        "ejecucion_herramientas": "ejecucion_herramientas",
        "ejecucion_medica": "ejecucion_medica",
        "recepcionista": "recepcionista",
        "generacion_resumen": "generacion_resumen"
    }
)

# Rutas de ejecución a sincronización/resumen
workflow.add_edge("ejecucion_herramientas", "generacion_resumen")

def decidir_despues_medica(state):
    if state.get('necesita_sincronizacion', False):
        return "sincronizador_hibrido"
    return "generacion_resumen"

workflow.add_conditional_edges(
    "ejecucion_medica",
    decidir_despues_medica,
    {
        "sincronizador_hibrido": "sincronizador_hibrido",
        "generacion_resumen": "generacion_resumen"
    }
)

# Recepcionista
def decidir_despues_recepcionista(state):
    estado_conv = state.get('estado_conversacion')
    if estado_conv == 'completado':
        if state.get('necesita_sincronizacion', False):
            return "sincronizador_hibrido"
        return "generacion_resumen"
    return "generacion_resumen"

workflow.add_conditional_edges(
    "recepcionista",
    decidir_despues_recepcionista,
    {
        "sincronizador_hibrido": "sincronizador_hibrido",
        "generacion_resumen": "generacion_resumen"
    }
)

# Sincronización a resumen
workflow.add_edge("sincronizador_hibrido", "generacion_resumen")

# Resumen a persistencia
workflow.add_edge("generacion_resumen", "persistencia_episodica")

# Persistencia a END
workflow.add_edge("persistencia_episodica", END)

# Compilar con checkpointing
from langgraph.checkpoint.postgres import PostgresSaver

checkpointer = PostgresSaver.from_conn_string(DATABASE_URL)
app = workflow.compile(checkpointer=checkpointer)
```

---

## 📊 Métricas y Monitoring

### Tiempos Promedio por Nodo

| Nodo | Tiempo Promedio | Tipo |
|------|----------------|------|
| N0 - Identificación | 50-100ms | Automatizado |
| N1 - Caché | 30-80ms | Automatizado |
| N2 - Clasificación | 800-1200ms | LLM |
| N3A - Recuperación Personal | 600-900ms | LLM parcial |
| N3B - Recuperación Médica | 700-1000ms | LLM parcial |
| N4 - Selección | 900-1400ms | LLM |
| N5A - Ejecución Personal | 200-800ms | Automatizado |
| N5B - Ejecución Médica | 200-2000ms | Automatizado |
| N6R - Recepcionista | 1000-1500ms | LLM |
| N6 - Generación | 700-1100ms | LLM |
| N7 - Persistencia | 600-900ms | LLM parcial |
| N8 - Sincronización | 500-1500ms | Automatizado |

### Logging

```python
import logging

logger = logging.getLogger(__name__)

# En cada nodo:
logger.info(f"[NODO] Entrada: user_id={state['user_id']}, clasificacion={state.get('clasificacion')}")
logger.info(f"[NODO] Salida: status=success, datos_actualizados=[...]")
logger.error(f"[NODO] Error: {str(e)}", exc_info=True)
```

### Tabla de Métricas

```sql
CREATE TABLE metricas_nodos (
    id SERIAL PRIMARY KEY,
    nodo VARCHAR(50) NOT NULL,
    session_id VARCHAR(200),
    duracion_ms INTEGER,
    estado VARCHAR(20),  -- 'success', 'error'
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_metricas_nodo_fecha ON metricas_nodos(nodo, created_at DESC);
```

---

**Documento actualizado:** 30 de Enero de 2026  
**Versión:** 2.0  
**Framework:** LangGraph + PostgreSQL + DeepSeek + Google Calendar
