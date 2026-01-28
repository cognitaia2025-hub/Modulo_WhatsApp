# 📋 Plan Estructurado de Implementación - Sistema Híbrido WhatsApp

**Fecha de creación:** 27 de Enero de 2026
**Estado del proyecto:** 65% completado (Fases 1-2 completadas)
**Objetivo:** Sistema híbrido de calendario personal + gestión médica con turnos automáticos

---

## 📊 LEYENDA DE COMPONENTES

### Tipos de Nodos:
- 🤖 **Nodo Automatizado** - Sin LLM, lógica determinística (validaciones, BD, caché)
- 🧠 **Nodo Inteligente** - Con LLM, procesamiento de lenguaje natural

### Tipos de Herramientas:
- 📅 **Herramienta Calendario** - Google Calendar API
- 🏥 **Herramienta Médica** - Gestión de pacientes/citas/historiales
- 🔧 **Herramienta Sistema** - Utilities, validaciones, conversiones

### Tipos de Bases de Datos:
- 🗄️ **Tabla Relacional** - PostgreSQL
- 🧮 **Tabla Vectorial** - pgvector para embeddings
- 💾 **Store** - LangGraph Store para caché

### Estados de Componente:
- ✅ **COMPLETADO** - Ya implementado y funcional
- 🟢 **CREAR** - Componente nuevo a implementar
- 🔄 **MODIFICAR** - Componente existente a actualizar
- 🔧 **ACTUALIZAR** - Mejora/extensión de funcionalidad existente

---

# 🎯 ETAPA 0: SEGURIDAD Y CORRECCIONES CRÍTICAS

**Objetivo:** Corregir vulnerabilidades críticas antes de continuar desarrollo
**Duración estimada:** 1-2 días
**Prioridad:** 🔴 CRÍTICA

---

## FASE 0.1: Gestión de Credenciales y Secrets

### 🤖 Nodos Automatizados

#### N0.1 - Nodo de Configuración Segura
- **Estado:** 🟢 CREAR
- **Archivo:** `src/config/secure_config.py`
- **Responsabilidad:** Cargar y validar variables de entorno obligatorias
- **Lógica:**
  ```python
  def validar_configuracion():
      required_vars = [
          'POSTGRES_PASSWORD',
          'DEEPSEEK_API_KEY',
          'ANTHROPIC_API_KEY',
          'GOOGLE_SERVICE_ACCOUNT_FILE',
          'GOOGLE_CALENDAR_ID'
      ]
      for var in required_vars:
          if not os.getenv(var):
              raise ConfigurationError(f"{var} no configurada")
  ```
- **Inputs:** Variables de entorno
- **Outputs:** Configuración validada
- **Sin LLM:** Pura validación determinística

### 🔧 Herramientas Sistema

#### T0.1 - Herramienta de Rotación de Credenciales
- **Estado:** 🟢 CREAR
- **Archivo:** `scripts/rotate_credentials.py`
- **Función:** Eliminar credenciales del historial Git
- **Comando:**
  ```bash
  python scripts/rotate_credentials.py --file "pro-core-466508-u7-76f56aed8c8b.json"
  ```

#### T0.2 - Herramienta de Validación de .gitignore
- **Estado:** 🟢 CREAR
- **Archivo:** `scripts/validate_gitignore.py`
- **Función:** Verificar que archivos sensibles no estén trackeados
- **Output:** Lista de archivos en riesgo

### 🗄️ Bases de Datos

#### BD0.1 - Tabla de Configuración Segura
- **Estado:** 🟢 CREAR
- **Nombre:** `configuracion_sistema`
- **Schema:**
  ```sql
  CREATE TABLE configuracion_sistema (
      id SERIAL PRIMARY KEY,
      clave VARCHAR(100) UNIQUE NOT NULL,
      valor_encriptado TEXT NOT NULL,
      descripcion TEXT,
      ultima_rotacion TIMESTAMP DEFAULT NOW(),
      rotacion_requerida BOOLEAN DEFAULT FALSE
  );
  ```
- **Uso:** Almacenar configuraciones sensibles encriptadas

---

## FASE 0.2: Rate Limiting y Protección de APIs

### 🤖 Nodos Automatizados

#### N0.2 - Nodo de Rate Limiting
- **Estado:** 🟢 CREAR
- **Archivo:** `src/middleware/rate_limiter.py`
- **Responsabilidad:** Limitar llamadas a APIs externas
- **Límites:**
  - Google Calendar: 10 requests/segundo
  - DeepSeek: 20 requests/minuto
  - WhatsApp Business: 80 requests/segundo
- **Tecnología:** `ratelimit` library
- **Sin LLM:** Lógica de contadores y ventanas de tiempo

### 🔧 Herramientas Sistema

#### T0.3 - Decorator de Rate Limiting
- **Estado:** 🟢 CREAR
- **Archivo:** `src/decorators/rate_limit.py`
- **Uso:**
  ```python
  @rate_limit(calls=10, period=1)
  def ejecutar_herramienta_google(tool_id, params):
      return TOOL_MAPPING[tool_id].invoke(params)
  ```

---

# 🎯 ETAPA 1: IDENTIFICACIÓN DE USUARIOS Y DOCTORES

**Objetivo:** Sistema identifica y diferencia entre usuarios personales, doctores y pacientes
**Duración estimada:** 3-4 días
**Prioridad:** 🟠 ALTA

---

## FASE 1.1: Nodo de Identificación y Registro

### 🤖 Nodos Automatizados

#### N0 - Nodo de Identificación de Usuario
- **Estado:** 🟢 CREAR
- **Archivo:** `src/nodes/identificacion_usuario_node.py`
- **Posición en grafo:** Primer nodo, antes del caché
- **Responsabilidad:**
  - Extraer número de teléfono del mensaje WhatsApp
  - Consultar BD para identificar usuario
  - Auto-registrar si es usuario nuevo
  - Determinar tipo: personal/doctor/paciente
- **Inputs:**
  - `mensaje_whatsapp` con metadata de teléfono
- **Outputs:**
  - `user_info`: dict con datos del usuario
  - `tipo_usuario`: enum('personal', 'doctor', 'paciente')
  - `es_admin`: boolean
- **Sin LLM:** Consultas SQL determinísticas

**Flujo del nodo:**
```
1. Extraer phone_number del mensaje
2. SELECT * FROM usuarios WHERE phone_number = ?
3. Si NO existe:
   → INSERT nuevo usuario con tipo='paciente_externo'
4. Si existe y tipo='doctor':
   → Cargar perfil de tabla doctores
5. Actualizar last_seen
6. Agregar info al estado del grafo
```

### 🗄️ Bases de Datos

#### BD1.1 - Actualización de Tabla Usuarios
- **Estado:** 🔧 ACTUALIZAR
- **Nombre:** `usuarios`
- **Cambios:**
  ```sql
  ALTER TABLE usuarios
  ADD COLUMN email VARCHAR UNIQUE,
  ADD COLUMN hashed_password VARCHAR,
  ADD COLUMN is_active BOOLEAN DEFAULT TRUE,
  ADD COLUMN tipo_usuario VARCHAR DEFAULT 'personal'
      CHECK (tipo_usuario IN ('personal', 'doctor', 'paciente_externo', 'admin'));

  -- Índice para búsquedas rápidas
  CREATE INDEX idx_usuarios_tipo ON usuarios(tipo_usuario);
  CREATE INDEX idx_usuarios_phone ON usuarios(phone_number);
  ```

#### BD1.2 - Tabla de Doctores (Ya existe, validar)
- **Estado:** ✅ COMPLETADO
- **Nombre:** `doctores`
- **Validar campos:**
  - `phone_number` FK a usuarios
  - `nombre_completo`
  - `especialidad`
  - `horario_atencion` JSONB
  - `orden_turno` INTEGER
  - `total_citas_asignadas` INTEGER

#### BD1.3 - Tabla de Pacientes Externos
- **Estado:** 🔄 MODIFICAR
- **Nombre:** `pacientes` (renombrar a `pacientes_externos`)
- **Actualización:**
  ```sql
  ALTER TABLE pacientes RENAME TO pacientes_externos;

  ALTER TABLE pacientes_externos
  ADD COLUMN es_usuario_registrado BOOLEAN DEFAULT FALSE,
  ADD COLUMN user_phone_fk VARCHAR REFERENCES usuarios(phone_number);
  ```

---

## FASE 1.2: Estado del Grafo Actualizado

### 🤖 Nodos Automatizados

#### N0.1 - Actualización del Estado
- **Estado:** 🔄 MODIFICAR
- **Archivo:** `src/state/agent_state.py`
- **Cambios:**
  ```python
  class WhatsAppAgentState(TypedDict):
      # Campos existentes
      user_id: str
      session_id: str
      thread_id: str
      messages: List[BaseMessage]

      # NUEVOS campos para identificación
      user_info: Dict[str, Any]  # Info completa del usuario
      tipo_usuario: str  # 'personal', 'doctor', 'paciente_externo'
      es_admin: bool
      doctor_id: Optional[int]  # Si es doctor, su ID en tabla doctores
      paciente_id: Optional[int]  # Si es paciente, su ID

      # Campos existentes...
      contexto_episodico: Dict[str, Any]
      herramientas_seleccionadas: List[str]
      ultimo_listado: List[Dict]
  ```

---

# 🎯 ETAPA 2: SISTEMA DE TURNOS AUTOMÁTICO

**Objetivo:** Implementar asignación automática de doctores por turnos
**Duración estimada:** 4-5 días
**Prioridad:** 🟠 ALTA

---

## FASE 2.1: Base de Datos para Turnos

### 🗄️ Bases de Datos

#### BD2.1 - Tabla de Control de Turnos
- **Estado:** 🟢 CREAR
- **Nombre:** `control_turnos`
- **Schema:**
  ```sql
  CREATE TABLE control_turnos (
      id SERIAL PRIMARY KEY,
      ultimo_doctor_id INTEGER REFERENCES doctores(id),
      timestamp TIMESTAMP DEFAULT NOW(),
      citas_santiago INTEGER DEFAULT 0,
      citas_joana INTEGER DEFAULT 0,
      total_turnos_asignados INTEGER DEFAULT 0
  );

  -- Insertar registro inicial
  INSERT INTO control_turnos (ultimo_doctor_id, citas_santiago, citas_joana)
  VALUES (NULL, 0, 0);
  ```

#### BD2.2 - Tabla de Disponibilidad Médica (Validar)
- **Estado:** ✅ COMPLETADO
- **Nombre:** `disponibilidad_medica`
- **Validar estructura:**
  ```sql
  -- Debe tener:
  doctor_id INTEGER REFERENCES doctores(id)
  dia_semana INTEGER CHECK (0-6)
  hora_inicio TIME
  hora_fin TIME
  disponible BOOLEAN
  duracion_cita INTEGER DEFAULT 60
  ```

#### BD2.3 - Tabla de Citas Médicas Actualizada
- **Estado:** 🔧 ACTUALIZAR
- **Nombre:** `citas_medicas`
- **Cambios:**
  ```sql
  ALTER TABLE citas_medicas
  ADD COLUMN fue_asignacion_automatica BOOLEAN DEFAULT TRUE,
  ADD COLUMN doctor_turno_original INTEGER REFERENCES doctores(id),
  ADD COLUMN razon_reasignacion VARCHAR;

  -- Índice para búsquedas de conflictos
  CREATE INDEX idx_citas_doctor_fecha_estado
  ON citas_medicas(doctor_id, fecha_hora_inicio, estado)
  WHERE estado IN ('programada', 'confirmada', 'en_curso');
  ```

---

## FASE 2.2: Herramientas de Gestión de Turnos

### 🔧 Herramientas Sistema

#### T2.1 - Obtener Siguiente Doctor en Turno
- **Estado:** 🟢 CREAR
- **Archivo:** `src/medical/turnos.py`
- **Función:** `obtener_siguiente_doctor_turno()`
- **Lógica:**
  ```python
  def obtener_siguiente_doctor_turno() -> Dict:
      """
      Alterna entre Santiago (id=1) y Joana (id=2)
      Return: {
          "doctor_id": 1,
          "nombre": "Santiago de Jesús Ornelas Reynoso",
          "es_su_turno": True,
          "total_asignadas": 47
      }
      """
      control = db.query(ControlTurnos).first()
      if control.ultimo_doctor_id == 1:
          proximo = 2  # Joana
      else:
          proximo = 1  # Santiago

      doctor = db.query(Doctores).filter(id == proximo).first()
      return {
          "doctor_id": doctor.id,
          "nombre": doctor.nombre_completo,
          "es_su_turno": True,
          "total_asignadas": doctor.total_citas_asignadas
      }
  ```
- **Sin LLM:** Lógica determinística de alternancia

#### T2.2 - Validar Disponibilidad de Doctor
- **Estado:** 🟢 CREAR
- **Archivo:** `src/medical/disponibilidad.py`
- **Función:** `check_doctor_availability(doctor_id, fecha_hora_inicio, fecha_hora_fin)`
- **Lógica:**
  ```python
  def check_doctor_availability(doctor_id: int, inicio: datetime, fin: datetime) -> bool:
      """
      Verifica:
      1. Horario de atención configurado
      2. No hay cita existente en ese horario
      3. Doctor está activo
      """
      # 1. Verificar horario
      dia_semana = inicio.weekday()
      disponibilidad = db.query(DisponibilidadMedica).filter(
          DisponibilidadMedica.doctor_id == doctor_id,
          DisponibilidadMedica.dia_semana == dia_semana,
          DisponibilidadMedica.disponible == True,
          DisponibilidadMedica.hora_inicio <= inicio.time(),
          DisponibilidadMedica.hora_fin >= fin.time()
      ).first()

      if not disponibilidad:
          return False

      # 2. Verificar conflictos
      conflictos = db.query(CitasMedicas).filter(
          CitasMedicas.doctor_id == doctor_id,
          CitasMedicas.estado.in_(['programada', 'confirmada', 'en_curso']),
          or_(
              and_(CitasMedicas.fecha_hora_inicio <= inicio, CitasMedicas.fecha_hora_fin > inicio),
              and_(CitasMedicas.fecha_hora_inicio < fin, CitasMedicas.fecha_hora_fin >= fin)
          )
      ).count()

      return conflictos == 0
  ```
- **Sin LLM:** Consultas SQL y validaciones lógicas

#### T2.3 - Generar Slots Disponibles con Turnos
- **Estado:** 🟢 CREAR
- **Archivo:** `src/medical/slots.py`
- **Función:** `generar_slots_con_turnos(dias_adelante=7)`
- **Lógica:**
  ```python
  def generar_slots_con_turnos(dias_adelante: int = 7) -> List[Dict]:
      """
      Para cada slot de 1 hora (8:30-18:30):
      1. Determina doctor por turno
      2. Verifica disponibilidad del doctor del turno
      3. Si ocupado, intenta con el otro doctor
      4. Si ambos ocupados, skip slot

      Return: [
          {
              "fecha": "2026-01-30",
              "hora_inicio": "08:30",
              "hora_fin": "09:30",
              "doctor_asignado_id": 1,
              "doctor_nombre": "Santiago",  # Interno, no se muestra
              "turno_numero": 1
          }
      ]
      """
      slots_disponibles = []
      hoy = date.today()

      for dia_offset in range(dias_adelante):
          fecha = hoy + timedelta(days=dia_offset)
          dia_semana = fecha.weekday()

          # Solo jueves a lunes (3,4,5,6,0)
          if dia_semana not in [3, 4, 5, 6, 0]:
              continue

          # Generar slots de 8:30 a 18:30
          hora_inicio = time(8, 30)
          hora_fin = time(18, 30)

          current_time = datetime.combine(fecha, hora_inicio)
          end_time = datetime.combine(fecha, hora_fin)

          turno_contador = 1

          while current_time + timedelta(hours=1) <= end_time:
              slot_fin = current_time + timedelta(hours=1)

              # Determinar doctor por turno
              doctor_turno = obtener_siguiente_doctor_turno()

              # Verificar disponibilidad
              if check_doctor_availability(doctor_turno['doctor_id'], current_time, slot_fin):
                  doctor_asignado = doctor_turno
              else:
                  # Intentar con el otro doctor
                  otro_doctor_id = 2 if doctor_turno['doctor_id'] == 1 else 1
                  if check_doctor_availability(otro_doctor_id, current_time, slot_fin):
                      doctor_asignado = get_doctor_info(otro_doctor_id)
                  else:
                      # Ambos ocupados, skip
                      current_time = slot_fin
                      turno_contador += 1
                      continue

              slots_disponibles.append({
                  "fecha": fecha.isoformat(),
                  "hora_inicio": current_time.time().isoformat(),
                  "hora_fin": slot_fin.time().isoformat(),
                  "doctor_asignado_id": doctor_asignado['doctor_id'],
                  "doctor_nombre": doctor_asignado['nombre'],  # NO se muestra al paciente
                  "turno_numero": turno_contador
              })

              current_time = slot_fin
              turno_contador += 1

      return slots_disponibles
  ```
- **Sin LLM:** Algoritmo determinístico de slots y turnos

---

## FASE 2.3: Herramientas de Agendamiento con Turnos

### 🏥 Herramientas Médicas

#### T2.4 - Agendar Cita con Sistema de Turnos
- **Estado:** 🔄 MODIFICAR
- **Archivo:** `src/medical/tools.py`
- **Función:** `agendar_cita_medica_completa()`
- **Cambios:**
  ```python
  @tool
  def agendar_cita_medica_completa(
      paciente_phone: str,
      fecha_hora_inicio: str,
      tipo_consulta: str = "seguimiento",
      motivo: str = None
  ) -> str:
      """
      NUEVA LÓGICA con turnos automáticos:
      1. Determina doctor por turno
      2. Verifica disponibilidad del doctor del turno
      3. Si ocupado, asigna al otro doctor automáticamente
      4. Agenda en BD
      5. Sincroniza con Google Calendar del doctor asignado
      6. Actualiza control_turnos
      7. Revela doctor en confirmación
      """
      inicio = datetime.fromisoformat(fecha_hora_inicio)
      fin = inicio + timedelta(hours=1)

      # 1. Doctor por turno
      doctor_turno = obtener_siguiente_doctor_turno()

      # 2. Verificar disponibilidad
      if check_doctor_availability(doctor_turno['doctor_id'], inicio, fin):
          doctor_final = doctor_turno
          reasignado = False
      else:
          # 3. Reasignar al otro doctor
          otro_id = 2 if doctor_turno['doctor_id'] == 1 else 1
          if check_doctor_availability(otro_id, inicio, fin):
              doctor_final = get_doctor_info(otro_id)
              reasignado = True
          else:
              return "❌ Horario no disponible con ningún doctor"

      # 4. Crear cita en BD
      paciente = get_paciente_by_phone(paciente_phone)
      cita = CitasMedicas(
          doctor_id=doctor_final['doctor_id'],
          paciente_id=paciente.id,
          fecha_hora_inicio=inicio,
          fecha_hora_fin=fin,
          tipo_consulta=tipo_consulta,
          motivo_consulta=motivo,
          estado='programada',
          fue_asignacion_automatica=True,
          doctor_turno_original=doctor_turno['doctor_id'],
          razon_reasignacion='ocupado' if reasignado else None
      )
      db.add(cita)
      db.commit()

      # 5. Sincronizar con Google Calendar
      sync_to_google_calendar(cita.id)

      # 6. Actualizar control de turnos
      actualizar_control_turnos(doctor_final['doctor_id'])

      # 7. Confirmación con doctor asignado
      return f"""✅ ¡Cita agendada exitosamente!

  📅 {inicio.strftime('%A %d de %B, %Y')}
  🕐 {inicio.strftime('%H:%M')} - {fin.strftime('%H:%M')}
  👨‍⚕️ {doctor_final['nombre']}
  📝 Tipo: {tipo_consulta.title()}

  📱 Te recordaré 24 horas antes automáticamente."""
  ```
- **Sin LLM:** Toda la lógica es determinística

---

# 🎯 ETAPA 3: FLUJO INTELIGENTE - NODOS CON LLM

**Objetivo:** Integrar clasificación inteligente y manejo conversacional
**Duración estimada:** 5-6 días
**Prioridad:** 🟠 ALTA

---

## FASE 3.1: Clasificación Inteligente de Solicitudes

### 🧠 Nodos Inteligentes (CON LLM)

#### N2 - Nodo de Filtrado Inteligente (Modificar)
- **Estado:** 🔄 MODIFICAR
- **Archivo:** `src/nodes/filtrado_inteligente_node.py`
- **Responsabilidad:** Clasificar mensaje en: personal, médico, o chat casual
- **LLM:** DeepSeek (primario) / Claude (fallback)
- **Inputs:**
  - `mensaje_usuario`: str
  - `tipo_usuario`: str (de N0)
  - `contexto_episodico`: dict
- **Outputs:**
  - `clasificacion`: enum('personal', 'medica', 'chat')
  - `requiere_herramientas`: boolean
  - `herramientas_sugeridas`: List[str]

**Prompt del LLM:**
```python
prompt = f"""Clasifica la siguiente solicitud de {tipo_usuario}:

Mensaje: "{mensaje_usuario}"

Contexto del usuario:
- Tipo: {tipo_usuario}
- Historial reciente: {contexto_reciente}

PATRONES DE CLASIFICACIÓN:

MÉDICA (si tipo_usuario == 'doctor'):
- "mi paciente Juan necesita cita"
- "agendar consulta para mañana"
- "revisar historial de María"
- "cuántas citas tengo hoy"
- Palabras clave: paciente, consulta, cita médica, historial, diagnóstico

PERSONAL (cualquier usuario):
- "mi cita del viernes" (refiriéndose a sí mismo)
- "recordarme comprar medicamentos"
- "agendar evento personal"
- Palabras clave: mi cita, mi evento, mi reunión

CHAT (conversación casual):
- "hola"
- "gracias"
- "cómo estás"

Responde en JSON:
{{
  "clasificacion": "medica" | "personal" | "chat",
  "confianza": 0.0-1.0,
  "razonamiento": "breve explicación",
  "requiere_herramientas": true | false
}}"""

respuesta = llm_with_fallback.invoke(prompt)
```

**Lógica post-LLM:**
```python
def filtrado_inteligente_node(state: WhatsAppAgentState) -> Dict:
    tipo_usuario = state['tipo_usuario']
    mensaje = state['messages'][-1].content

    # Usar LLM para clasificar
    clasificacion_llm = clasificar_con_llm(mensaje, tipo_usuario)

    # Validaciones adicionales
    if tipo_usuario == 'paciente_externo':
        # Pacientes externos SOLO pueden solicitar citas
        if clasificacion_llm['clasificacion'] == 'medica':
            clasificacion_final = 'solicitud_cita_paciente'
        else:
            clasificacion_final = 'chat'
    else:
        clasificacion_final = clasificacion_llm['clasificacion']

    return {
        **state,
        'clasificacion': clasificacion_final,
        'requiere_herramientas': clasificacion_llm['requiere_herramientas']
    }
```

---

## FASE 3.2: Recuperación de Contexto Diferenciada

### 🧠 Nodos Inteligentes (CON LLM)

#### N3A - Nodo de Recuperación Episódica Personal (Existente)
- **Estado:** ✅ COMPLETADO
- **Archivo:** `src/nodes/recuperacion_episodica_node.py`
- **Responsabilidad:** Recuperar memorias de calendario personal
- **Cuando se ejecuta:** Si clasificacion == 'personal'
- **Sin cambios:** Ya funciona correctamente

#### N3B - Nodo de Recuperación Médica (NUEVO)
- **Estado:** 🟢 CREAR
- **Archivo:** `src/nodes/recuperacion_medica_node.py`
- **Responsabilidad:** Recuperar contexto médico relevante
- **LLM:** DeepSeek para búsqueda semántica
- **Inputs:**
  - `mensaje_usuario`: str
  - `doctor_id`: int (si es doctor)
  - `clasificacion`: 'medica'
- **Outputs:**
  - `contexto_medico`: dict con:
    - `pacientes_recientes`: List[Dict]
    - `citas_hoy`: List[Dict]
    - `historiales_relevantes`: List[Dict]
    - `estadisticas_doctor`: Dict

**Lógica del nodo:**
```python
def recuperacion_medica_node(state: WhatsAppAgentState) -> Dict:
    doctor_id = state['doctor_id']
    mensaje = state['messages'][-1].content

    # 1. Pacientes recientes (últimos 10)
    pacientes = db.query(PacientesExternos).filter(
        doctor_id == doctor_id
    ).order_by(ultima_cita.desc()).limit(10).all()

    # 2. Citas del día
    hoy = date.today()
    citas_hoy = db.query(CitasMedicas).filter(
        doctor_id == doctor_id,
        func.date(fecha_hora_inicio) == hoy,
        estado.in_(['programada', 'confirmada'])
    ).all()

    # 3. Búsqueda semántica en historiales (CON LLM)
    if "historial" in mensaje.lower() or "paciente" in mensaje.lower():
        # Generar embedding del mensaje
        embedding_query = generate_embedding(mensaje)

        # Buscar en tabla historiales_medicos (con pgvector)
        historiales = db.query(HistorialesMedicos).filter(
            paciente_id.in_([p.id for p in pacientes])
        ).order_by(
            embedding.cosine_distance(embedding_query)
        ).limit(5).all()
    else:
        historiales = []

    # 4. Estadísticas del doctor
    stats = {
        "total_pacientes": db.query(PacientesExternos).filter(doctor_id == doctor_id).count(),
        "citas_hoy": len(citas_hoy),
        "citas_semana": get_citas_semana(doctor_id)
    }

    return {
        **state,
        'contexto_medico': {
            'pacientes_recientes': [serialize_paciente(p) for p in pacientes],
            'citas_hoy': [serialize_cita(c) for c in citas_hoy],
            'historiales_relevantes': [serialize_historial(h) for h in historiales],
            'estadisticas_doctor': stats
        }
    }
```

### 🧮 Bases de Datos Vectoriales

#### BD3.1 - Tabla de Embeddings de Historiales Médicos
- **Estado:** 🟢 CREAR
- **Nombre:** `historiales_medicos` (actualizar con embeddings)
- **Cambios:**
  ```sql
  ALTER TABLE historiales_medicos
  ADD COLUMN embedding vector(384);

  -- Índice HNSW para búsqueda rápida
  CREATE INDEX idx_historiales_embedding
  ON historiales_medicos
  USING hnsw (embedding vector_cosine_ops);
  ```

---

## FASE 3.3: Selección Inteligente de Herramientas

### 🧠 Nodos Inteligentes (CON LLM)

#### N4 - Nodo de Selección de Herramientas (Modificar)
- **Estado:** 🔄 MODIFICAR
- **Archivo:** `src/nodes/seleccion_herramientas_node.py`
- **Responsabilidad:** LLM decide qué herramientas usar
- **LLM:** DeepSeek (primario) / Claude (fallback)
- **Cambios:** Agregar herramientas médicas al pool

**Herramientas disponibles actualizadas:**
```python
HERRAMIENTAS_DISPONIBLES = {
    # Calendario Personal (6) - EXISTENTES
    'list_calendar_events': {
        'descripcion': 'Listar eventos de calendario personal',
        'parametros': ['fecha_inicio', 'fecha_fin'],
        'tipo': 'personal'
    },
    'create_calendar_event': {
        'descripcion': 'Crear evento en calendario personal',
        'parametros': ['titulo', 'fecha_hora', 'duracion'],
        'tipo': 'personal'
    },
    # ... otras 4 herramientas de calendario

    # Herramientas Médicas (12) - NUEVAS
    'crear_paciente_medico': {
        'descripcion': 'Registrar nuevo paciente',
        'parametros': ['nombre', 'telefono', 'doctor_phone'],
        'tipo': 'medica',
        'requiere_doctor': True
    },
    'buscar_pacientes_doctor': {
        'descripcion': 'Buscar pacientes por nombre/teléfono',
        'parametros': ['doctor_phone', 'busqueda'],
        'tipo': 'medica',
        'requiere_doctor': True
    },
    'consultar_slots_disponibles': {
        'descripcion': 'Ver horarios disponibles con turnos automáticos',
        'parametros': ['fecha', 'duracion'],
        'tipo': 'medica',
        'requiere_doctor': True
    },
    'agendar_cita_medica_completa': {
        'descripcion': 'Agendar cita con asignación automática de doctor',
        'parametros': ['paciente_phone', 'fecha_hora', 'tipo_consulta'],
        'tipo': 'medica',
        'requiere_doctor': False  # Pacientes externos pueden usarla
    },
    # ... otras 8 herramientas médicas
}
```

**Prompt del LLM actualizado:**
```python
prompt = f"""Eres un asistente especializado en calendario y gestión médica.

Usuario: {tipo_usuario}
Clasificación: {clasificacion}
Mensaje: "{mensaje_usuario}"

Contexto disponible:
{json.dumps(contexto_medico if clasificacion == 'medica' else contexto_episodico)}

HERRAMIENTAS DISPONIBLES:
{json.dumps(HERRAMIENTAS_DISPONIBLES, indent=2)}

REGLAS:
1. Si clasificacion == 'medica' Y tipo_usuario == 'doctor':
   → Puede usar herramientas médicas y personales
2. Si clasificacion == 'personal':
   → Solo herramientas de calendario personal
3. Si tipo_usuario == 'paciente_externo':
   → SOLO 'agendar_cita_medica_completa' y 'consultar_slots_disponibles'

IMPORTANTE:
- Para solicitudes de cita de pacientes: usar 'agendar_cita_medica_completa'
- Sistema asigna doctor por turnos automáticamente (NO el LLM)
- Para buscar disponibilidad: usar 'consultar_slots_disponibles' (NO especifica doctor)

Responde en JSON con las herramientas a ejecutar:
{{
  "herramientas": [
    {{
      "tool_id": "nombre_herramienta",
      "parametros": {{"param1": "valor1"}},
      "orden": 1
    }}
  ],
  "mensaje_usuario": "Explicación amigable de qué vas a hacer"
}}"""

respuesta_llm = llm_with_fallback.invoke(prompt)
```

---

## FASE 3.4: Ejecución de Herramientas Diferenciada

### 🤖 Nodos Automatizados

#### N5A - Nodo de Ejecución Personal (Existente)
- **Estado:** ✅ COMPLETADO
- **Archivo:** `src/nodes/ejecucion_herramientas_node.py`
- **Responsabilidad:** Ejecutar herramientas de calendario personal
- **Cuando:** Si clasificacion == 'personal'
- **Sin cambios:** Ya funciona

#### N5B - Nodo de Ejecución Médica (NUEVO)
- **Estado:** 🟢 CREAR
- **Archivo:** `src/nodes/ejecucion_medica_node.py`
- **Responsabilidad:** Ejecutar herramientas médicas con validaciones
- **Sin LLM:** Ejecución determinística de herramientas
- **Inputs:**
  - `herramientas_seleccionadas`: List[Dict]
  - `doctor_id` o `paciente_id`
  - `contexto_medico`: Dict
- **Outputs:**
  - `resultados_ejecucion`: List[Dict]
  - `errores`: List[str]

**Lógica del nodo:**
```python
def ejecucion_medica_node(state: WhatsAppAgentState) -> Dict:
    herramientas = state['herramientas_seleccionadas']
    doctor_id = state.get('doctor_id')
    tipo_usuario = state['tipo_usuario']

    resultados = []

    for herramienta in herramientas:
        tool_id = herramienta['tool_id']
        params = herramienta['parametros']

        # Validaciones de seguridad
        if tool_id in HERRAMIENTAS_REQUIEREN_DOCTOR:
            if tipo_usuario != 'doctor':
                resultados.append({
                    'success': False,
                    'error': 'No tienes permisos para esta operación',
                    'tool_id': tool_id
                })
                continue

        # Agregar doctor_phone automáticamente si es doctor
        if tipo_usuario == 'doctor':
            params['doctor_phone'] = state['user_id']

        # Ejecutar herramienta
        try:
            resultado = HERRAMIENTAS_MEDICAS[tool_id].invoke(params)

            # Si es agendamiento, registrar en control_turnos
            if tool_id == 'agendar_cita_medica_completa' and resultado['success']:
                actualizar_control_turnos(resultado['doctor_asignado_id'])

            resultados.append({
                'success': True,
                'data': resultado,
                'tool_id': tool_id
            })

        except Exception as e:
            logger.error(f"Error ejecutando {tool_id}: {e}")
            resultados.append({
                'success': False,
                'error': str(e),
                'tool_id': tool_id
            })

    return {
        **state,
        'resultados_ejecucion': resultados
    }
```

---

# 🎯 ETAPA 4: FLUJO DE RECEPCIONISTA PARA PACIENTES

**Objetivo:** Flujo conversacional completo para pacientes externos
**Duración estimada:** 4-5 días
**Prioridad:** 🟡 MEDIA

---

## FASE 4.1: Nodo Conversacional de Recepcionista

### 🧠 Nodos Inteligentes (CON LLM)

#### N6R - Nodo de Recepcionista Conversacional (NUEVO)
- **Estado:** 🟢 CREAR
- **Archivo:** `src/nodes/recepcionista_node.py`
- **Responsabilidad:** Manejar conversación completa de agendamiento
- **LLM:** DeepSeek para respuestas naturales
- **Inputs:**
  - `mensaje_usuario`: str
  - `paciente_phone`: str
  - `estado_conversacion`: str
  - `slots_disponibles`: List[Dict] (si ya se buscaron)
- **Outputs:**
  - `respuesta_recepcionista`: str
  - `nuevo_estado_conversacion`: str
  - `accion_requerida`: str

**Estados de conversación:**
```python
ESTADOS_CONVERSACION = {
    'inicial': 'Paciente acaba de solicitar cita',
    'solicitando_nombre': 'Paciente nuevo, pedir nombre',
    'mostrando_opciones': 'Se mostraron slots disponibles',
    'esperando_seleccion': 'Esperando que paciente escoja A/B/C',
    'confirmando': 'Agendando cita',
    'completado': 'Cita agendada exitosamente',
    'error': 'Ocurrió un error, manejarlo'
}
```

**Flujo del nodo:**
```python
def recepcionista_node(state: WhatsAppAgentState) -> Dict:
    estado_conv = state.get('estado_conversacion', 'inicial')
    mensaje = state['messages'][-1].content
    paciente_phone = state['user_id']

    if estado_conv == 'inicial':
        # 1. Verificar si paciente existe
        paciente = get_paciente_by_phone(paciente_phone)

        if not paciente:
            # Pedir nombre
            respuesta = "¡Hola! Veo que es tu primera vez. ¿Cuál es tu nombre completo?"
            nuevo_estado = 'solicitando_nombre'
        else:
            # Buscar disponibilidad directamente
            slots = generar_slots_con_turnos(dias_adelante=7)
            respuesta = formatear_opciones_slots(slots[:3])  # Mostrar 3 opciones
            nuevo_estado = 'esperando_seleccion'

    elif estado_conv == 'solicitando_nombre':
        # Registrar paciente
        nombre = extraer_nombre_con_llm(mensaje)
        paciente = registrar_paciente_externo(paciente_phone, nombre)

        # Buscar disponibilidad
        slots = generar_slots_con_turnos(dias_adelante=7)
        respuesta = f"Gracias {nombre}! " + formatear_opciones_slots(slots[:3])
        nuevo_estado = 'esperando_seleccion'

    elif estado_conv == 'esperando_seleccion':
        # Procesar selección (A, B, C, etc.)
        seleccion = extraer_seleccion(mensaje)  # A → 0, B → 1, C → 2

        if seleccion is None:
            respuesta = "Por favor escoge una opción escribiendo A, B, o C"
            nuevo_estado = 'esperando_seleccion'
        else:
            # Agendar cita
            slots = state['slots_disponibles']
            slot_elegido = slots[seleccion]

            resultado = agendar_cita_medica_completa(
                paciente_phone=paciente_phone,
                fecha_hora_inicio=f"{slot_elegido['fecha']} {slot_elegido['hora_inicio']}",
                tipo_consulta='primera_vez'
            )

            respuesta = resultado  # Mensaje de confirmación con doctor asignado
            nuevo_estado = 'completado'

    return {
        **state,
        'respuesta_recepcionista': respuesta,
        'estado_conversacion': nuevo_estado
    }

def formatear_opciones_slots(slots: List[Dict]) -> str:
    """Formatea slots sin mencionar doctores (asignados internamente)"""
    opciones_letras = ['A', 'B', 'C', 'D', 'E']

    respuesta = "🗓️ **Opciones disponibles:**\n\n"

    for i, slot in enumerate(slots):
        fecha_obj = date.fromisoformat(slot['fecha'])
        dia_nombre = fecha_obj.strftime('%A')
        fecha_formato = fecha_obj.strftime('%d de %B')

        respuesta += f"{opciones_letras[i]}) {dia_nombre} {fecha_formato} - "
        respuesta += f"{slot['hora_inicio']} a {slot['hora_fin']}\n"

    respuesta += "\n¿Cuál te conviene más? Responde con la letra (A, B, C...)"

    return respuesta
```

### 🔧 Herramientas Sistema

#### T4.1 - Extraer Nombre con LLM
- **Estado:** 🟢 CREAR
- **Archivo:** `src/utils/nlp_extractors.py`
- **Función:** `extraer_nombre_con_llm(mensaje: str) -> str`
- **LLM:** DeepSeek
- **Uso:**
  ```python
  mensaje = "Me llamo Juan Pérez García"
  nombre = extraer_nombre_con_llm(mensaje)
  # → "Juan Pérez García"
  ```

#### T4.2 - Extraer Selección (A/B/C)
- **Estado:** 🟢 CREAR
- **Archivo:** `src/utils/nlp_extractors.py`
- **Función:** `extraer_seleccion(mensaje: str) -> Optional[int]`
- **Sin LLM:** Regex simple
- **Uso:**
  ```python
  mensaje = "la opción B por favor"
  seleccion = extraer_seleccion(mensaje)
  # → 1 (índice del array)
  ```

---

# 🎯 ETAPA 5: SINCRONIZACIÓN HÍBRIDA BD ↔ GOOGLE CALENDAR

**Objetivo:** BD médica es source of truth, Google Calendar es visualización
**Duración estimada:** 4-5 días
**Prioridad:** 🟡 MEDIA

---

## FASE 5.1: Nodo de Sincronización

### 🤖 Nodos Automatizados

#### N8 - Nodo Sincronizador Híbrido (NUEVO)
- **Estado:** 🟢 CREAR
- **Archivo:** `src/nodes/sincronizador_hibrido_node.py`
- **Responsabilidad:** Sincronizar citas médicas a Google Calendar
- **Sin LLM:** Llamadas a API determinísticas
- **Inputs:**
  - `cita_id`: int
  - `operacion`: enum('crear', 'actualizar', 'cancelar')
- **Outputs:**
  - `google_event_id`: str
  - `sincronizado`: boolean
  - `error_sincronizacion`: Optional[str]

**Lógica del nodo:**
```python
def sincronizador_hibrido_node(state: WhatsAppAgentState) -> Dict:
    """
    BD médica es source of truth
    Google Calendar es solo visualización
    """
    cita_id = state.get('cita_id_creada')

    if not cita_id:
        return state  # No hay nada que sincronizar

    try:
        # 1. Obtener cita de BD
        cita = db.query(CitasMedicas).filter(id == cita_id).first()
        doctor = db.query(Doctores).filter(id == cita.doctor_id).first()
        paciente = db.query(PacientesExternos).filter(id == cita.paciente_id).first()

        # 2. Preparar evento para Google Calendar
        evento_gcal = {
            'summary': f'Consulta - {paciente.nombre_completo}',
            'description': f'''
                Paciente: {paciente.nombre_completo}
                Teléfono: {paciente.telefono}
                Tipo: {cita.tipo_consulta}
                Motivo: {cita.motivo_consulta or "No especificado"}

                🤖 Cita agendada automáticamente por turnos
                ID Cita: {cita.id}
                Sistema: WhatsApp Agent
            ''',
            'start': {
                'dateTime': cita.fecha_hora_inicio.isoformat(),
                'timeZone': 'America/Tijuana'
            },
            'end': {
                'dateTime': cita.fecha_hora_fin.isoformat(),
                'timeZone': 'America/Tijuana'
            },
            'extendedProperties': {
                'private': {
                    'tipo': 'cita_medica',
                    'cita_id': str(cita.id),
                    'doctor_phone': doctor.phone_number,
                    'paciente_id': str(cita.paciente_id),
                    'sistema': 'whatsapp_agent'
                }
            },
            'colorId': '11'  # Color rojo para citas médicas
        }

        # 3. Crear en Google Calendar
        if cita.google_event_id:
            # Actualizar evento existente
            evento = calendar_service.events().update(
                calendarId=CALENDAR_ID,
                eventId=cita.google_event_id,
                body=evento_gcal
            ).execute()
        else:
            # Crear nuevo evento
            evento = calendar_service.events().insert(
                calendarId=CALENDAR_ID,
                body=evento_gcal
            ).execute()

            # Actualizar BD con Google Event ID
            cita.google_event_id = evento['id']
            db.commit()

        # 4. Registrar sincronización exitosa
        db.add(SincronizacionCalendar(
            cita_id=cita.id,
            google_event_id=evento['id'],
            estado='sincronizada',
            ultimo_intento=datetime.now(),
            intentos=1
        ))
        db.commit()

        logger.info(f"✅ Cita {cita_id} sincronizada a Google Calendar")

        return {
            **state,
            'google_event_id': evento['id'],
            'sincronizado': True
        }

    except Exception as e:
        logger.error(f"❌ Error sincronizando cita {cita_id}: {e}")

        # Registrar error PERO mantener cita en BD
        db.add(SincronizacionCalendar(
            cita_id=cita_id,
            estado='error',
            error_message=str(e),
            ultimo_intento=datetime.now(),
            siguiente_reintento=datetime.now() + timedelta(minutes=15),
            intentos=1
        ))
        db.commit()

        return {
            **state,
            'sincronizado': False,
            'error_sincronizacion': str(e)
        }
```

### 🗄️ Bases de Datos

#### BD5.1 - Tabla de Sincronización
- **Estado:** 🟢 CREAR
- **Nombre:** `sincronizacion_calendar`
- **Schema:**
  ```sql
  CREATE TABLE sincronizacion_calendar (
      id SERIAL PRIMARY KEY,
      cita_id INTEGER REFERENCES citas_medicas(id),
      google_event_id VARCHAR,
      estado VARCHAR CHECK (estado IN ('sincronizada', 'pendiente', 'error', 'reintentando')),
      ultimo_intento TIMESTAMP DEFAULT NOW(),
      siguiente_reintento TIMESTAMP,
      intentos INTEGER DEFAULT 0,
      error_message TEXT,
      metadata JSONB DEFAULT '{}'
  );

  CREATE INDEX idx_sync_cita ON sincronizacion_calendar(cita_id);
  CREATE INDEX idx_sync_estado ON sincronizacion_calendar(estado);
  ```

---

## FASE 5.2: Workers de Sincronización en Background

### 🤖 Nodos Automatizados

#### N8.1 - Worker de Reintento de Sincronización
- **Estado:** 🟢 CREAR
- **Archivo:** `src/background/sync_retry_worker.py`
- **Responsabilidad:** Reintentar sincronizaciones fallidas
- **Sin LLM:** Cron job determinístico
- **Ejecución:** Cada 15 minutos

**Lógica del worker:**
```python
import schedule
import time

def retry_failed_syncs():
    """
    Worker que se ejecuta cada 15 minutos
    Reintenta sincronizaciones fallidas
    """
    # 1. Buscar sincronizaciones pendientes o con error
    sync_pendientes = db.query(SincronizacionCalendar).filter(
        or_(
            and_(estado == 'error', intentos < 3),
            estado == 'pendiente'
        ),
        or_(
            siguiente_reintento == None,
            siguiente_reintento <= datetime.now()
        )
    ).all()

    logger.info(f"🔄 Reintentando {len(sync_pendientes)} sincronizaciones...")

    for sync in sync_pendientes:
        try:
            # 2. Obtener cita
            cita = db.query(CitasMedicas).filter(id == sync.cita_id).first()

            # 3. Reintentar sincronización
            resultado = sincronizar_cita_a_calendar(cita)

            if resultado['success']:
                # Actualizar estado
                sync.estado = 'sincronizada'
                sync.google_event_id = resultado['google_event_id']
                sync.ultimo_intento = datetime.now()
                sync.intentos += 1
                logger.info(f"✅ Cita {sync.cita_id} sincronizada en reintento")
            else:
                # Incrementar intentos
                sync.intentos += 1
                sync.ultimo_intento = datetime.now()
                sync.siguiente_reintento = datetime.now() + timedelta(minutes=15 * sync.intentos)

                if sync.intentos >= 3:
                    # Después de 3 intentos, marcar como error permanente
                    sync.estado = 'error'
                    logger.error(f"❌ Cita {sync.cita_id} falló después de 3 intentos")

            db.commit()

        except Exception as e:
            logger.error(f"Error en reintento de sync {sync.id}: {e}")
            continue

# Programar ejecución
schedule.every(15).minutes.do(retry_failed_syncs)

def run_worker():
    logger.info("🚀 Worker de sincronización iniciado")
    while True:
        schedule.run_pending()
        time.sleep(60)  # Verificar cada minuto

if __name__ == '__main__':
    run_worker()
```

---

# 🎯 ETAPA 6: RECORDATORIOS AUTOMÁTICOS

**Objetivo:** Enviar recordatorios por WhatsApp 24 horas antes de citas
**Duración estimada:** 3-4 días
**Prioridad:** 🟡 MEDIA

---

## FASE 6.1: Sistema de Recordatorios

### 🤖 Nodos Automatizados

#### N9 - Nodo de Recordatorios (NUEVO)
- **Estado:** 🟢 CREAR
- **Archivo:** `src/background/recordatorios_scheduler.py`
- **Responsabilidad:** Enviar recordatorios automáticos
- **Sin LLM:** Cron job determinístico
- **Ejecución:** Cada hora

**Lógica del scheduler:**
```python
import schedule
from datetime import datetime, timedelta

def enviar_recordatorios():
    """
    Ejecuta cada hora
    Envía recordatorios a pacientes con citas en 24h
    """
    # 1. Calcular ventana de tiempo (23-24 horas antes)
    ahora = datetime.now()
    ventana_inicio = ahora + timedelta(hours=23)
    ventana_fin = ahora + timedelta(hours=24)

    # 2. Buscar citas en esa ventana sin recordatorio enviado
    citas_pendientes = db.query(CitasMedicas).filter(
        CitasMedicas.fecha_hora_inicio >= ventana_inicio,
        CitasMedicas.fecha_hora_inicio <= ventana_fin,
        CitasMedicas.estado.in_(['programada', 'confirmada']),
        CitasMedicas.recordatorio_enviado == False
    ).all()

    logger.info(f"📱 Enviando {len(citas_pendientes)} recordatorios...")

    for cita in citas_pendientes:
        try:
            # 3. Obtener datos de la cita
            paciente = db.query(PacientesExternos).filter(id == cita.paciente_id).first()
            doctor = db.query(Doctores).filter(id == cita.doctor_id).first()

            # 4. Formatear mensaje de recordatorio
            fecha_cita = cita.fecha_hora_inicio
            mensaje = f"""🔔 **Recordatorio de Cita**

Hola {paciente.nombre_completo}! Te recordamos que tienes:

📅 Mañana {fecha_cita.strftime('%A %d de %B')}
🕐 {fecha_cita.strftime('%H:%M')} a {cita.fecha_hora_fin.strftime('%H:%M')}
👨‍⚕️ {doctor.nombre_completo}
📍 [Dirección del consultorio]

💬 Si necesitas cancelar, responde 'cancelar cita'

¡Te esperamos!"""

            # 5. Enviar vía WhatsApp
            enviar_mensaje_whatsapp(
                destinatario=paciente.telefono,
                mensaje=mensaje
            )

            # 6. Marcar como enviado
            cita.recordatorio_enviado = True
            db.commit()

            logger.info(f"✅ Recordatorio enviado a {paciente.nombre_completo}")

        except Exception as e:
            logger.error(f"❌ Error enviando recordatorio cita {cita.id}: {e}")
            continue

# Programar ejecución
schedule.every(1).hours.do(enviar_recordatorios)

def run_scheduler():
    logger.info("🚀 Scheduler de recordatorios iniciado")
    while True:
        schedule.run_pending()
        time.sleep(300)  # Verificar cada 5 minutos

if __name__ == '__main__':
    run_scheduler()
```

### 🔧 Herramientas Sistema

#### T6.1 - Enviar Mensaje WhatsApp
- **Estado:** 🔄 MODIFICAR
- **Archivo:** `whatsapp-service/src/index.js`
- **Función:** Agregar endpoint para envío programado
- **Cambios:**
  ```javascript
  // Nuevo endpoint para recordatorios
  app.post('/api/send-reminder', async (req, res) => {
      const { destinatario, mensaje } = req.body;

      try {
          const chatId = `${destinatario}@c.us`;
          await client.sendMessage(chatId, mensaje);

          res.json({ success: true });
      } catch (error) {
          res.status(500).json({ success: false, error: error.message });
      }
  });
  ```

---

# 🎯 ETAPA 7: HERRAMIENTAS MÉDICAS AVANZADAS

**Objetivo:** Implementar 6 herramientas adicionales para gestión completa
**Duración estimada:** 5-6 días
**Prioridad:** 🟢 BAJA (después de sistema básico funcionando)

---

## FASE 7.1: Gestión de Historiales Médicos

### 🏥 Herramientas Médicas Avanzadas

#### T7.1 - Registrar Consulta Médica
- **Estado:** 🟢 CREAR
- **Archivo:** `src/medical/advanced_tools.py`
- **Función:** `registrar_consulta()`
- **Uso:**
  ```python
  @tool
  def registrar_consulta(
      doctor_phone: str,
      cita_id: int,
      diagnostico_principal: str,
      sintomas: str,
      tratamiento: str,
      medicamentos: List[Dict],
      proxima_cita: str = None
  ) -> str:
      """
      Registra resultados de consulta en historial médico
      """
      # Actualizar estado de cita a 'completada'
      cita = db.query(CitasMedicas).filter(id == cita_id).first()
      cita.estado = 'completada'
      cita.diagnostico = diagnostico_principal
      cita.tratamiento_prescrito = tratamiento

      # Crear registro en historiales_medicos
      historial = HistorialesMedicos(
          paciente_id=cita.paciente_id,
          cita_id=cita_id,
          fecha_consulta=cita.fecha_hora_inicio.date(),
          diagnostico_principal=diagnostico_principal,
          sintomas=sintomas,
          tratamiento_prescrito=tratamiento,
          medicamentos=medicamentos
      )

      # Generar embedding del historial (para búsqueda semántica)
      texto_embedding = f"{diagnostico_principal} {sintomas} {tratamiento}"
      historial.embedding = generate_embedding(texto_embedding)

      db.add(historial)
      db.commit()

      return f"✅ Consulta registrada exitosamente (ID: {historial.id})"
  ```

#### T7.2 - Consultar Historial Médico
- **Estado:** 🟢 CREAR
- **Archivo:** `src/medical/advanced_tools.py`
- **Función:** `consultar_historial_paciente()`
- **Con búsqueda semántica:**
  ```python
  @tool
  def consultar_historial_paciente(
      doctor_phone: str,
      paciente_id: int,
      busqueda: str = None,
      limite: int = 10
  ) -> str:
      """
      Consulta historial médico completo o búsqueda específica
      """
      if busqueda:
          # Búsqueda semántica con embeddings
          embedding_query = generate_embedding(busqueda)

          historiales = db.query(HistorialesMedicos).filter(
              paciente_id == paciente_id
          ).order_by(
              HistorialesMedicos.embedding.cosine_distance(embedding_query)
          ).limit(limite).all()
      else:
          # Historial completo ordenado por fecha
          historiales = db.query(HistorialesMedicos).filter(
              paciente_id == paciente_id
          ).order_by(
              HistorialesMedicos.fecha_consulta.desc()
          ).limit(limite).all()

      return formatear_historial(historiales)
  ```

### 🧮 Bases de Datos Vectoriales (Actualizar)

#### BD7.1 - Embeddings en Historiales (Ya creado en FASE 3.2)
- **Estado:** ✅ COMPLETADO
- Validar que la columna `embedding vector(384)` existe

---

## FASE 7.2: Reportes y Analytics

### 🏥 Herramientas Médicas Avanzadas

#### T7.3 - Generar Reporte de Actividad
- **Estado:** 🟢 CREAR
- **Archivo:** `src/medical/reports.py`
- **Función:** `generar_reporte_doctor()`
- **Tipos de reportes:**
  ```python
  @tool
  def generar_reporte_doctor(
      doctor_phone: str,
      tipo_reporte: str,  # 'citas_dia', 'citas_mes', 'ingresos'
      fecha_inicio: str = None,
      fecha_fin: str = None
  ) -> str:
      """
      Genera reportes de actividad médica
      """
      doctor = get_doctor_by_phone(doctor_phone)

      if tipo_reporte == 'citas_dia':
          return reporte_citas_dia(doctor.id)
      elif tipo_reporte == 'citas_mes':
          return reporte_citas_mes(doctor.id, fecha_inicio, fecha_fin)
      elif tipo_reporte == 'ingresos':
          return reporte_ingresos(doctor.id, fecha_inicio, fecha_fin)

  def reporte_citas_dia(doctor_id: int) -> str:
      hoy = date.today()
      citas = db.query(CitasMedicas).filter(
          doctor_id == doctor_id,
          func.date(fecha_hora_inicio) == hoy
      ).all()

      return f"""📊 **Reporte del Día**

  📅 {hoy.strftime('%A %d de %B, %Y')}

  📈 Total de citas: {len(citas)}
  ✅ Completadas: {sum(1 for c in citas if c.estado == 'completada')}
  ⏳ Pendientes: {sum(1 for c in citas if c.estado in ['programada', 'confirmada'])}
  ❌ Canceladas: {sum(1 for c in citas if c.estado == 'cancelada')}

  {formatear_lista_citas(citas)}"""
  ```

#### T7.4 - Obtener Estadísticas de Consultas
- **Estado:** 🟢 CREAR
- **Archivo:** `src/medical/analytics.py`
- **Función:** `obtener_estadisticas_consultas()`
- **Métricas:**
  ```python
  @tool
  def obtener_estadisticas_consultas(
      doctor_phone: str,
      periodo: str = "mes"  # 'dia', 'semana', 'mes'
  ) -> str:
      """
      Obtiene estadísticas de productividad
      """
      doctor = get_doctor_by_phone(doctor_phone)

      # Calcular rango de fechas
      if periodo == 'dia':
          inicio = datetime.now().replace(hour=0, minute=0)
          fin = datetime.now()
      elif periodo == 'semana':
          inicio = datetime.now() - timedelta(days=7)
          fin = datetime.now()
      elif periodo == 'mes':
          inicio = datetime.now() - timedelta(days=30)
          fin = datetime.now()

      # Consultas
      total_citas = db.query(CitasMedicas).filter(
          doctor_id == doctor.id,
          fecha_hora_inicio >= inicio,
          fecha_hora_inicio <= fin
      ).count()

      citas_completadas = db.query(CitasMedicas).filter(
          doctor_id == doctor.id,
          fecha_hora_inicio >= inicio,
          fecha_hora_inicio <= fin,
          estado == 'completada'
      ).count()

      no_asistieron = db.query(CitasMedicas).filter(
          doctor_id == doctor.id,
          fecha_hora_inicio >= inicio,
          fecha_hora_inicio <= fin,
          estado == 'no_asistio'
      ).count()

      tasa_asistencia = (citas_completadas / total_citas * 100) if total_citas > 0 else 0

      return f"""📊 **Estadísticas - {periodo.title()}**

  📈 Total de citas: {total_citas}
  ✅ Completadas: {citas_completadas}
  ❌ No asistieron: {no_asistieron}
  📊 Tasa de asistencia: {tasa_asistencia:.1f}%

  👥 Pacientes únicos: {contar_pacientes_unicos(doctor.id, inicio, fin)}
  🔄 Pacientes recurrentes: {contar_pacientes_recurrentes(doctor.id, inicio, fin)}"""
  ```

---

# 🎯 ETAPA 8: ACTUALIZACIÓN DEL GRAFO LANGGRAPH

**Objetivo:** Integrar todos los nodos nuevos en el flujo del grafo
**Duración estimada:** 2-3 días
**Prioridad:** 🔴 CRÍTICA (después de tener nodos implementados)

---

## FASE 8.1: Definición del Grafo Actualizado

### 🤖 Grafo LangGraph

#### G1 - Actualización del Grafo Principal
- **Estado:** 🔄 MODIFICAR
- **Archivo:** `src/graph_whatsapp.py`
- **Cambios:** Agregar nodos y rutas condicionales

**Flujo actualizado:**
```python
from langgraph.graph import StateGraph, END

# Crear grafo
workflow = StateGraph(WhatsAppAgentState)

# ==================== NODOS ====================

# N0 - Identificación (NUEVO)
workflow.add_node("identificacion_usuario", identificacion_usuario_node)

# N1 - Caché (EXISTENTE)
workflow.add_node("cache_sesion", nodo_cache_sesion)

# N2 - Filtrado Inteligente (MODIFICADO)
workflow.add_node("filtrado_inteligente", filtrado_inteligente_node)

# N3A - Recuperación Personal (EXISTENTE)
workflow.add_node("recuperacion_episodica", recuperacion_episodica_node)

# N3B - Recuperación Médica (NUEVO)
workflow.add_node("recuperacion_medica", recuperacion_medica_node)

# N4 - Selección Herramientas (MODIFICADO)
workflow.add_node("seleccion_herramientas", seleccion_herramientas_node)

# N5A - Ejecución Personal (EXISTENTE)
workflow.add_node("ejecucion_herramientas", ejecucion_herramientas_node)

# N5B - Ejecución Médica (NUEVO)
workflow.add_node("ejecucion_medica", ejecucion_medica_node)

# N6R - Recepcionista (NUEVO)
workflow.add_node("recepcionista", recepcionista_node)

# N6 - Generación Resumen (EXISTENTE)
workflow.add_node("generacion_resumen", generacion_resumen_node)

# N7 - Persistencia (EXISTENTE)
workflow.add_node("persistencia_episodica", persistencia_episodica_node)

# N8 - Sincronizador Híbrido (NUEVO)
workflow.add_node("sincronizador_hibrido", sincronizador_hibrido_node)

# ==================== PUNTO DE ENTRADA ====================
workflow.set_entry_point("identificacion_usuario")

# ==================== RUTAS CONDICIONALES ====================

# N0 → N1 (siempre)
workflow.add_edge("identificacion_usuario", "cache_sesion")

# N1 → N2 (siempre)
workflow.add_edge("cache_sesion", "filtrado_inteligente")

# N2 → ? (según clasificación y tipo de usuario)
def decidir_flujo_clasificacion(state: WhatsAppAgentState) -> str:
    clasificacion = state['clasificacion']
    tipo_usuario = state['tipo_usuario']

    if clasificacion == 'solicitud_cita_paciente':
        # Paciente externo solicita cita
        return "recepcionista"
    elif clasificacion == 'medica' and tipo_usuario == 'doctor':
        # Doctor con operación médica
        return "recuperacion_medica"
    elif clasificacion == 'personal':
        # Calendario personal
        return "recuperacion_episodica"
    else:
        # Chat casual (sin herramientas)
        return "generacion_resumen"

workflow.add_conditional_edges(
    "filtrado_inteligente",
    decidir_flujo_clasificacion,
    {
        "recepcionista": "recepcionista",
        "recuperacion_medica": "recuperacion_medica",
        "recuperacion_episodica": "recuperacion_episodica",
        "generacion_resumen": "generacion_resumen"
    }
)

# N3A → N4 (personal)
workflow.add_edge("recuperacion_episodica", "seleccion_herramientas")

# N3B → N4 (médica)
workflow.add_edge("recuperacion_medica", "seleccion_herramientas")

# N4 → ? (según herramientas seleccionadas)
def decidir_tipo_ejecucion(state: WhatsAppAgentState) -> str:
    herramientas = state['herramientas_seleccionadas']

    if not herramientas:
        return "generacion_resumen"

    # Verificar si hay herramientas médicas
    hay_medicas = any(h['tipo'] == 'medica' for h in herramientas)

    if hay_medicas:
        return "ejecucion_medica"
    else:
        return "ejecucion_herramientas"

workflow.add_conditional_edges(
    "seleccion_herramientas",
    decidir_tipo_ejecucion,
    {
        "ejecucion_medica": "ejecucion_medica",
        "ejecucion_herramientas": "ejecucion_herramientas",
        "generacion_resumen": "generacion_resumen"
    }
)

# N5A → N6 (personal)
workflow.add_edge("ejecucion_herramientas", "generacion_resumen")

# N5B → N8 → N6 (médica con sincronización)
workflow.add_edge("ejecucion_medica", "sincronizador_hibrido")
workflow.add_edge("sincronizador_hibrido", "generacion_resumen")

# N6R → N8 → N6 (recepcionista con sincronización)
def decidir_despues_recepcionista(state: WhatsAppAgentState) -> str:
    estado_conv = state['estado_conversacion']

    if estado_conv == 'completado':
        # Cita agendada, sincronizar
        return "sincronizador_hibrido"
    else:
        # Conversación en proceso, generar respuesta
        return "generacion_resumen"

workflow.add_conditional_edges(
    "recepcionista",
    decidir_despues_recepcionista,
    {
        "sincronizador_hibrido": "sincronizador_hibrido",
        "generacion_resumen": "generacion_resumen"
    }
)

# N6 → N7 (siempre)
workflow.add_edge("generacion_resumen", "persistencia_episodica")

# N7 → END (siempre)
workflow.add_edge("persistencia_episodica", END)

# ==================== COMPILAR GRAFO ====================
app = workflow.compile()
```

---

# 📊 RESUMEN GENERAL DE COMPONENTES

## Nodos Totales: 12

### 🤖 Nodos Automatizados (Sin LLM): 7
1. ✅ N0 - Identificación de Usuario (CREAR)
2. ✅ N1 - Caché de Sesión (EXISTENTE)
3. 🟢 N5B - Ejecución Médica (CREAR)
4. 🟢 N8 - Sincronizador Híbrido (CREAR)
5. 🟢 N8.1 - Worker de Reintento (CREAR)
6. 🟢 N9 - Scheduler de Recordatorios (CREAR)
7. 🟢 N0.1 - Configuración Segura (CREAR)

### 🧠 Nodos Inteligentes (Con LLM): 5
1. 🔄 N2 - Filtrado Inteligente (MODIFICAR)
2. 🟢 N3B - Recuperación Médica (CREAR)
3. 🔄 N4 - Selección de Herramientas (MODIFICAR)
4. 🟢 N6R - Recepcionista Conversacional (CREAR)
5. ✅ N6 - Generación Resumen (EXISTENTE)

---

## Herramientas Totales: 24

### 📅 Herramientas Calendario (6): ✅ COMPLETADAS
- `list_calendar_events`
- `create_calendar_event`
- `update_calendar_event`
- `delete_calendar_event`
- `search_calendar_events`
- `postpone_calendar_event`

### 🏥 Herramientas Médicas Básicas (6): ✅ COMPLETADAS
- `crear_paciente_medico`
- `buscar_pacientes_doctor`
- `consultar_slots_disponibles` (CON turnos automáticos)
- `agendar_cita_medica_completa` (CON turnos automáticos)
- `modificar_cita_medica`
- `cancelar_cita_medica`

### 🏥 Herramientas Médicas Avanzadas (6): 🟢 CREAR
- `registrar_consulta`
- `consultar_historial_paciente`
- `actualizar_disponibilidad_doctor`
- `generar_reporte_doctor`
- `obtener_estadisticas_consultas`
- `buscar_citas_por_periodo`

### 🔧 Herramientas Sistema (6): 🟢 CREAR
- `obtener_siguiente_doctor_turno`
- `validar_disponibilidad_doctor`
- `generar_slots_con_turnos`
- `extraer_nombre_con_llm`
- `extraer_seleccion`
- `actualizar_control_turnos`

---

## Bases de Datos Totales: 15 tablas

### 🗄️ Tablas Relacionales (12)
1. ✅ `usuarios` (ACTUALIZAR)
2. ✅ `doctores` (COMPLETADO)
3. 🔄 `pacientes_externos` (MODIFICAR - renombrar)
4. 🟢 `control_turnos` (CREAR)
5. ✅ `disponibilidad_medica` (COMPLETADO)
6. 🔧 `citas_medicas` (ACTUALIZAR)
7. ✅ `historiales_medicos` (COMPLETADO)
8. 🟢 `sincronizacion_calendar` (CREAR)
9. ✅ `herramientas_disponibles` (COMPLETADO)
10. ✅ `user_sessions` (COMPLETADO)
11. ✅ `auditoria_conversaciones` (COMPLETADO)
12. 🟢 `configuracion_sistema` (CREAR - seguridad)

### 🧮 Tablas Vectoriales (2)
1. ✅ `memoria_episodica` con embeddings (COMPLETADO)
2. 🔧 `historiales_medicos` con embeddings (ACTUALIZAR)

### 💾 Stores LangGraph (1)
1. ✅ `checkpoints` (LangGraph automático)

---

# 📅 CRONOGRAMA ESTIMADO

| Etapa | Duración | Prioridad | Dependencias |
|-------|----------|-----------|--------------|
| **ETAPA 0: Seguridad** | 1-2 días | 🔴 CRÍTICA | Ninguna |
| **ETAPA 1: Identificación** | 3-4 días | 🟠 ALTA | ETAPA 0 |
| **ETAPA 2: Turnos Automáticos** | 4-5 días | 🟠 ALTA | ETAPA 1 |
| **ETAPA 3: Flujo Inteligente** | 5-6 días | 🟠 ALTA | ETAPA 2 |
| **ETAPA 4: Recepcionista** | 4-5 días | 🟡 MEDIA | ETAPA 3 |
| **ETAPA 5: Sincronización** | 4-5 días | 🟡 MEDIA | ETAPA 4 |
| **ETAPA 6: Recordatorios** | 3-4 días | 🟡 MEDIA | ETAPA 5 |
| **ETAPA 7: Herramientas Avanzadas** | 5-6 días | 🟢 BAJA | ETAPA 3 |
| **ETAPA 8: Grafo Actualizado** | 2-3 días | 🔴 CRÍTICA | Todas |
| **TOTAL** | **31-40 días** | | |

---

# 🎯 PRÓXIMO PASO INMEDIATO

**Comenzar con ETAPA 0 - FASE 0.1:**
1. Crear `src/config/secure_config.py`
2. Rotar credenciales de Google Cloud
3. Mover todas las configuraciones a `.env`
4. Validar que ningún archivo sensible esté trackeado

**Comando para iniciar:**
```bash
# 1. Crear estructura de seguridad
mkdir -p src/config scripts

# 2. Rotar credenciales
python scripts/rotate_credentials.py --file "pro-core-466508-u7-76f56aed8c8b.json"

# 3. Crear .env con todas las variables
cp .env.example .env
# Editar .env con credenciales correctas
```

---

**Fecha de finalización estimada del plan:** 11 de Marzo de 2026
**Documento creado por:** Claude Sonnet 4.5
**Última actualización:** 27 de Enero de 2026
