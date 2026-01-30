# 🎯 PROMPT DE IMPLEMENTACIÓN - ETAPA 2: SISTEMA DE TURNOS AUTOMÁTICO

**Fecha:** 28 de Enero de 2026  
**Prioridad:** 🟠 ALTA  
**Dependencias:** Etapa 1 (Identificación de Usuarios) completada  
**Duración estimada:** 4-5 días

---

## 📋 OBJETIVO GENERAL

Implementar un sistema de asignación automática de doctores basado en **turnos rotativos equitativos** que alterne entre dos doctores (Santiago y Joana) sin revelar el doctor asignado hasta la confirmación de la cita.

---

## 🎯 REQUERIMIENTOS FUNCIONALES

### Sistema de Turnos:
1. **Alternancia automática** entre Doctor Santiago (ID=1) y Doctora Joana (ID=2)
2. **Asignación equitativa** de citas entre ambos doctores
3. **Fallback automático:** Si el doctor del turno está ocupado, asignar al otro doctor
4. **NO revelar** el doctor asignado durante la consulta de disponibilidad
5. **Revelar doctor** solo en la confirmación final de la cita

### Validación de Disponibilidad:
1. Verificar **horario de atención** del doctor (tabla `disponibilidad_medica`)
2. Detectar **conflictos** con citas existentes (evitar double-booking)
3. Validar que el doctor esté **activo** y disponible
4. Generar slots de **1 hora** de duración (8:30 AM - 6:30 PM)

---

## 📊 COMPONENTES A IMPLEMENTAR

### ✅ FASE 2.1: Base de Datos para Turnos

#### **BD2.1 - Tabla de Control de Turnos** 🟢 CREAR
**Archivo:** `sql/migrate_etapa_2_turnos.sql`

**Propósito:** Mantener estado del sistema de turnos

**Schema:**
```sql
CREATE TABLE control_turnos (
    id SERIAL PRIMARY KEY,
    ultimo_doctor_id INTEGER REFERENCES doctores(id),
    timestamp TIMESTAMP DEFAULT NOW(),
    citas_santiago INTEGER DEFAULT 0,
    citas_joana INTEGER DEFAULT 0,
    total_turnos_asignados INTEGER DEFAULT 0
);

-- Insertar registro inicial (comienza con Doctor Santiago)
INSERT INTO control_turnos (ultimo_doctor_id, citas_santiago, citas_joana)
VALUES (NULL, 0, 0);
```

**Índices recomendados:**
```sql
CREATE INDEX idx_control_turnos_ultimo ON control_turnos(ultimo_doctor_id);
```

---

#### **BD2.2 - Validar Tabla de Disponibilidad Médica** ✅ VALIDAR
**Archivo:** Revisar si existe en `sql/migrate_medical_system.sql`

**Campos requeridos:**
```sql
CREATE TABLE IF NOT EXISTS disponibilidad_medica (
    id SERIAL PRIMARY KEY,
    doctor_id INTEGER REFERENCES doctores(id),
    dia_semana INTEGER CHECK (dia_semana >= 0 AND dia_semana <= 6),
    hora_inicio TIME NOT NULL,
    hora_fin TIME NOT NULL,
    disponible BOOLEAN DEFAULT TRUE,
    duracion_cita INTEGER DEFAULT 60,  -- minutos
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Validaciones:**
- `dia_semana`: 0=Lunes, 6=Domingo
- Horario clínica: Jueves-Lunes (días 3,4,5,6,0)
- Horario atención: 8:30 AM - 6:30 PM

**Tarea:** Si la tabla no existe, créala. Si existe, valida que tenga todos los campos.

---

#### **BD2.3 - Actualizar Tabla de Citas Médicas** 🔧 MODIFICAR
**Archivo:** `sql/migrate_etapa_2_turnos.sql`

**Nuevas columnas:**
```sql
ALTER TABLE citas_medicas
ADD COLUMN IF NOT EXISTS fue_asignacion_automatica BOOLEAN DEFAULT TRUE,
ADD COLUMN IF NOT EXISTS doctor_turno_original INTEGER REFERENCES doctores(id),
ADD COLUMN IF NOT EXISTS razon_reasignacion VARCHAR;
```

**Propósito de las columnas:**
- `fue_asignacion_automatica`: TRUE si fue por sistema de turnos, FALSE si manual
- `doctor_turno_original`: Doctor que tenía el turno inicialmente
- `razon_reasignacion`: 'ocupado', 'no_disponible', 'solicitud_especifica', NULL

**Índice crítico para detección de conflictos:**
```sql
CREATE INDEX IF NOT EXISTS idx_citas_doctor_fecha_estado
ON citas_medicas(doctor_id, fecha_hora_inicio, estado)
WHERE estado IN ('programada', 'confirmada', 'en_curso');
```

---

### ✅ FASE 2.2: Herramientas de Gestión de Turnos

#### **T2.1 - Obtener Siguiente Doctor en Turno** 🟢 CREAR
**Archivo:** `src/medical/turnos.py`

**Función principal:**
```python
def obtener_siguiente_doctor_turno() -> Dict[str, Any]:
    """
    Obtiene el doctor que corresponde al turno actual según alternancia.
    
    Lógica:
    1. Consulta tabla control_turnos (siempre hay 1 registro)
    2. Si ultimo_doctor_id == 1 (Santiago) → retorna 2 (Joana)
    3. Si ultimo_doctor_id == 2 (Joana) → retorna 1 (Santiago)
    4. Si NULL (primera vez) → retorna 1 (Santiago)
    
    Returns:
        {
            "doctor_id": int,
            "nombre_completo": str,
            "especialidad": str,
            "total_citas_asignadas": int
        }
    
    Nota: NO actualiza la BD, solo consulta.
    """
```

**⚠️ IMPORTANTE - Sin LLM:** Esta es lógica determinística pura (SQL + if/else)

**Tecnologías recomendadas:**
- **PostgreSQL + psycopg3** (consistente con Etapa 1)
- **Consulta con JOIN** para obtener info del doctor en una sola query
- **Manejo de errores** si no hay doctores en BD

**Documentación oficial:**
- [psycopg3 Connection](https://www.psycopg.org/psycopg3/docs/api/connections.html)
- [PostgreSQL Cursors](https://www.postgresql.org/docs/current/plpgsql-cursors.html)

---

#### **T2.2 - Validar Disponibilidad de Doctor** 🟢 CREAR
**Archivo:** `src/medical/disponibilidad.py`

**Función principal:**
```python
def check_doctor_availability(
    doctor_id: int, 
    fecha_hora_inicio: datetime, 
    fecha_hora_fin: datetime
) -> Dict[str, Any]:
    """
    Verifica si un doctor está disponible en el horario solicitado.
    
    Validaciones:
    1. Horario de atención configurado (tabla disponibilidad_medica)
    2. Sin citas conflictivas (tabla citas_medicas)
    3. Doctor activo (tabla doctores)
    4. Día dentro de horario de clínica (Jueves-Lunes)
    
    Returns:
        {
            "disponible": bool,
            "razon": str,  # Si no disponible: "ocupado", "fuera_de_horario", "dia_cerrado"
            "conflicto_con": Optional[int]  # ID de cita que genera conflicto
        }
    """
```

**Algoritmo de detección de conflictos:**
```sql
-- Detectar overlap entre rangos de tiempo
SELECT id FROM citas_medicas
WHERE doctor_id = ?
  AND estado IN ('programada', 'confirmada', 'en_curso')
  AND (
    -- Caso 1: Cita existente empieza antes y termina después del inicio
    (fecha_hora_inicio <= ? AND fecha_hora_fin > ?)
    OR
    -- Caso 2: Cita existente empieza durante el rango solicitado
    (fecha_hora_inicio >= ? AND fecha_hora_inicio < ?)
  );
```

**Tecnologías recomendadas:**
- **datetime de Python** para manipulación de fechas
- **pytz** para manejo de timezones (America/Tijuana)
- **PostgreSQL OVERLAPS** o lógica manual de rangos

**Documentación oficial:**
- [Python datetime](https://docs.python.org/3/library/datetime.html)
- [PostgreSQL Range Types](https://www.postgresql.org/docs/current/rangetypes.html)
- [psycopg3 Date/Time adaptation](https://www.psycopg.org/psycopg3/docs/basic/adapt.html#date-time-types)

---

#### **T2.3 - Generar Slots Disponibles con Turnos** 🟢 CREAR
**Archivo:** `src/medical/slots.py`

**Función principal:**
```python
def generar_slots_con_turnos(dias_adelante: int = 7) -> List[Dict[str, Any]]:
    """
    Genera slots de disponibilidad aplicando sistema de turnos.
    
    Algoritmo:
    1. Para cada día (hoy + dias_adelante):
       - Verificar si es día de atención (Jueves-Lunes)
       - Generar slots de 1 hora (8:30-18:30)
    
    2. Para cada slot:
       - Determinar doctor por turno (T2.1)
       - Verificar disponibilidad del doctor del turno (T2.2)
       - Si ocupado → intentar con el otro doctor
       - Si ambos ocupados → skip slot
    
    3. Agregar slot a resultado (SIN revelar doctor)
    
    Returns:
        [
            {
                "fecha": "2026-01-30",
                "hora_inicio": "08:30",
                "hora_fin": "09:30",
                "doctor_asignado_id": 1,  # INTERNO - no exponer en API
                "turno_numero": 1,
                "slot_id": "2026-01-30T08:30"
            }
        ]
    
    Nota: El campo doctor_asignado_id NO debe exponerse al frontend.
    """
```

**⚠️ CRUCIAL - No revelar doctor:**
```python
# ❌ MAL - No hacer esto:
return {"doctor_nombre": "Santiago de Jesús Ornelas Reynoso"}

# ✅ BIEN - Solo exponer horarios:
return {
    "fecha": "2026-01-30",
    "hora_inicio": "08:30",
    "hora_fin": "09:30"
    # NO incluir doctor_id ni nombre
}
```

**Tecnologías recomendadas:**
- **datetime.timedelta** para generar rangos de tiempo
- **itertools** para iteraciones eficientes
- **Lógica funcional** para mantener código limpio

**Documentación oficial:**
- [Python timedelta](https://docs.python.org/3/library/datetime.html#timedelta-objects)
- [Python itertools](https://docs.python.org/3/library/itertools.html)

---

### ✅ FASE 2.3: Integración con Agendamiento

#### **T2.4 - Actualizar Control de Turnos** 🟢 CREAR
**Archivo:** `src/medical/turnos.py`

**Función auxiliar:**
```python
def actualizar_control_turnos(doctor_id: int) -> bool:
    """
    Actualiza el estado de turnos después de asignar una cita.
    
    Lógica:
    1. UPDATE control_turnos SET ultimo_doctor_id = doctor_id
    2. Incrementar contador del doctor (citas_santiago o citas_joana)
    3. Incrementar total_turnos_asignados
    4. UPDATE timestamp = NOW()
    
    Args:
        doctor_id: ID del doctor que recibió la cita
    
    Returns:
        True si se actualizó correctamente
    """
```

**Ejemplo de query:**
```sql
UPDATE control_turnos
SET 
    ultimo_doctor_id = ?,
    citas_santiago = CASE WHEN ? = 1 THEN citas_santiago + 1 ELSE citas_santiago END,
    citas_joana = CASE WHEN ? = 2 THEN citas_joana + 1 ELSE citas_joana END,
    total_turnos_asignados = total_turnos_asignados + 1,
    timestamp = NOW()
WHERE id = (SELECT MAX(id) FROM control_turnos);  -- Solo hay 1 registro
```

---

#### **T2.5 - Modificar Herramienta de Agendamiento** 🔄 MODIFICAR
**Archivo:** `src/medical/tools.py`

**Actualizar función existente:**
```python
@tool
def agendar_cita_medica_completa(
    paciente_phone: str,
    fecha_hora_inicio: str,  # ISO 8601: "2026-01-30T10:30:00"
    tipo_consulta: str = "seguimiento",
    motivo: Optional[str] = None
) -> str:
    """
    Agenda una cita médica aplicando el sistema de turnos automático.
    
    NUEVO FLUJO (ETAPA 2):
    1. Parsear fecha_hora_inicio a datetime
    2. Determinar doctor por turno (T2.1)
    3. Verificar disponibilidad del doctor del turno (T2.2)
    4. Si ocupado → asignar al otro doctor automáticamente
    5. Si ambos ocupados → retornar error
    6. Crear registro en BD (tabla citas_medicas)
    7. Sincronizar con Google Calendar del doctor asignado
    8. Actualizar control_turnos (T2.4)
    9. REVELAR doctor en mensaje de confirmación
    
    Args:
        paciente_phone: Teléfono del paciente (+526641234567)
        fecha_hora_inicio: Fecha y hora en ISO 8601
        tipo_consulta: "primera_vez", "seguimiento", "urgencia"
        motivo: Descripción breve del motivo
    
    Returns:
        Mensaje de confirmación con nombre del doctor asignado
    """
```

**Ejemplo de respuesta:**
```python
return f"""✅ ¡Cita agendada exitosamente!

📅 {fecha_legible}
🕐 {hora_inicio} - {hora_fin}
👨‍⚕️ {doctor_nombre_completo}
🏥 {especialidad}
📝 Tipo: {tipo_consulta.title()}

📱 Te enviaré un recordatorio 24 horas antes.
📍 Dirección: {direccion_consultorio}"""
```

**⚠️ IMPORTANTE:** Solo revelar doctor **después** de confirmar la cita.

---

## 🧪 TESTING - SUITE OBLIGATORIA

### **Test Suite:** `tests/Etapa_2/`

#### Estructura recomendada:
```
tests/Etapa_2/
├── README.md                              # Documentación de tests
├── test_turnos.py                         # 15 tests de sistema de turnos
├── test_disponibilidad.py                 # 15 tests de validación
├── test_slots.py                          # 15 tests de generación de slots
├── test_agendamiento_turnos.py            # 15 tests de integración
└── test_integration_etapa2.py             # 10 tests end-to-end
```

#### Casos de Prueba Mínimos:

**test_turnos.py (15 tests):**
- ✅ Alternancia correcta entre doctores
- ✅ Primera asignación (NULL → Santiago)
- ✅ Actualización de contadores
- ✅ Persistencia de estado
- ✅ Consulta de doctor sin actualizar BD

**test_disponibilidad.py (15 tests):**
- ✅ Detección de conflictos de horario
- ✅ Validación de horario de atención
- ✅ Validación de día de clínica
- ✅ Doctor no disponible
- ✅ Horario fuera de rango

**test_slots.py (15 tests):**
- ✅ Generación de slots válidos
- ✅ Filtrado de días cerrados
- ✅ Aplicación de turnos
- ✅ Fallback a otro doctor
- ✅ No revelar doctor en output

**test_agendamiento_turnos.py (15 tests):**
- ✅ Agendamiento con turno asignado
- ✅ Agendamiento con reasignación
- ✅ Actualización de control_turnos
- ✅ Sincronización con Google Calendar
- ✅ Revelación de doctor en confirmación

**test_integration_etapa2.py (10 tests):**
- ✅ Flujo completo: consulta → agendamiento → confirmación
- ✅ Múltiples agendamientos consecutivos
- ✅ Equidad de distribución
- ✅ Manejo de errores

**Meta:** Mínimo 70 tests con cobertura >95%

---

## 📚 DOCUMENTACIÓN REQUERIDA

### Archivos a crear:
1. **`docs/ETAPA_2_COMPLETADA.md`** - Reporte final detallado
2. **`RESUMEN_ETAPA_2.md`** - Resumen ejecutivo
3. **`tests/Etapa_2/README.md`** - Guía de tests
4. **Docstrings en todas las funciones**

### Scripts de ejecución:
1. **`ejecutar_migracion_etapa2.py`** - Migración SQL
2. **`ejecutar_migracion_etapa2.bat`** - Script Windows
3. **`ejecutar_tests_etapa2.py`** - Runner de tests
4. **`ejecutar_etapa2_completa.py`** - TODO-EN-UNO

---

## 🎯 MEJORES PRÁCTICAS

### Base de Datos:
1. ✅ Usar **transacciones** para operaciones críticas
   ```python
   with psycopg.connect(DATABASE_URL) as conn:
       with conn.transaction():
           # Operaciones atómicas aquí
   ```

2. ✅ Migraciones **idempotentes** (IF NOT EXISTS, IF EXISTS)
3. ✅ Índices en columnas de búsqueda frecuente
4. ✅ Constraints para integridad de datos

**Documentación oficial:**
- [PostgreSQL Transactions](https://www.postgresql.org/docs/current/tutorial-transactions.html)
- [psycopg3 Transactions](https://www.psycopg.org/psycopg3/docs/basic/transactions.html)

### Código Python:
1. ✅ **Type hints** en todas las funciones
   ```python
   from typing import Dict, List, Optional
   def mi_funcion(param: int) -> Dict[str, Any]:
   ```

2. ✅ **Logging estructurado** para debugging
   ```python
   logger.info(f"🔄 Turno: Doctor {doctor_id} | Total: {total}")
   ```

3. ✅ **Manejo de errores robusto**
   ```python
   try:
       resultado = operacion_critica()
   except psycopg.Error as e:
       logger.error(f"❌ Error BD: {e}")
       return {"error": "Database error"}
   ```

**Documentación oficial:**
- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [Python Logging](https://docs.python.org/3/library/logging.html)

### Fechas y Horas:
1. ✅ Usar **timezone-aware datetimes**
   ```python
   import pytz
   tz = pytz.timezone("America/Tijuana")
   fecha_local = datetime.now(tz)
   ```

2. ✅ Almacenar en UTC en BD, mostrar en timezone local
3. ✅ Validar rangos de fechas

**Documentación oficial:**
- [pytz Documentation](https://pythonhosted.org/pytz/)
- [PostgreSQL Timestamp with timezone](https://www.postgresql.org/docs/current/datatype-datetime.html)

### Testing:
1. ✅ Usar **fixtures de pytest** para setup
   ```python
   @pytest.fixture
   def db_connection():
       conn = psycopg.connect(TEST_DATABASE_URL)
       yield conn
       conn.close()
   ```

2. ✅ **Test de integración** con BD de prueba
3. ✅ **Mocks** para Google Calendar API

**Documentación oficial:**
- [pytest Documentation](https://docs.pytest.org/en/stable/)
- [pytest Fixtures](https://docs.pytest.org/en/stable/fixture.html)

---

## 📖 DOCUMENTACIÓN OFICIAL RECOMENDADA

### Tecnologías Core:
- **PostgreSQL 16:** https://www.postgresql.org/docs/16/
- **psycopg3:** https://www.psycopg.org/psycopg3/docs/
- **Python datetime:** https://docs.python.org/3/library/datetime.html
- **pytest:** https://docs.pytest.org/en/stable/

### APIs y Servicios:
- **Google Calendar API:** https://developers.google.com/calendar/api/v3/reference
- **Python Type Hints:** https://docs.python.org/3/library/typing.html

### Conceptos Avanzados:
- **Transacciones ACID:** https://en.wikipedia.org/wiki/ACID
- **PostgreSQL MVCC:** https://www.postgresql.org/docs/current/mvcc-intro.html
- **Timezone Best Practices:** https://www.postgresql.org/docs/current/datetime-best-practices.html

---

## 🚨 ERRORES COMUNES A EVITAR

### ❌ NO HACER:
1. **Revelar doctor antes de confirmación**
   ```python
   # ❌ MAL
   return {"doctor": "Santiago", "slots": [...]}
   ```

2. **Ignorar conflictos de horario**
   ```python
   # ❌ MAL - puede generar double-booking
   db.add(nueva_cita)
   db.commit()  # Sin verificar disponibilidad
   ```

3. **No actualizar control_turnos**
   ```python
   # ❌ MAL - rompe el sistema de turnos
   cita = crear_cita(doctor_id)
   # Faltó: actualizar_control_turnos(doctor_id)
   ```

4. **Olvidar timezone**
   ```python
   # ❌ MAL - datetime naive
   ahora = datetime.now()
   
   # ✅ BIEN - datetime aware
   ahora = datetime.now(pytz.timezone("America/Tijuana"))
   ```

5. **SQL injection**
   ```python
   # ❌ MAL - vulnerable
   query = f"SELECT * FROM citas WHERE id = {user_input}"
   
   # ✅ BIEN - parametrizado
   cur.execute("SELECT * FROM citas WHERE id = %s", (user_input,))
   ```

---

## ✅ CRITERIOS DE ACEPTACIÓN

### Funcionalidad:
- [ ] Sistema alterna correctamente entre doctores
- [ ] No se revelan doctores antes de confirmación
- [ ] Se detectan conflictos de horario
- [ ] Fallback funciona si doctor está ocupado
- [ ] Control de turnos se actualiza correctamente

### Base de Datos:
- [ ] Migración ejecuta sin errores
- [ ] Índices creados correctamente
- [ ] Constraints validan integridad
- [ ] Tabla control_turnos tiene 1 registro

### Testing:
- [ ] Mínimo 70 tests implementados
- [ ] Todos los tests pasan (100%)
- [ ] Cobertura >95% en código nuevo

### Documentación:
- [ ] Reporte ETAPA_2_COMPLETADA.md
- [ ] Resumen ejecutivo
- [ ] README de tests
- [ ] Scripts de ejecución

### Código:
- [ ] Type hints en todas las funciones
- [ ] Docstrings completos
- [ ] Logging apropiado
- [ ] Manejo de errores robusto
- [ ] Sin código hardcodeado (usar configuración)

---

## 🎖️ REFERENCIA DE CALIDAD

**Usar ETAPA 1 como estándar de calidad:**
- Calificación: 99/100 (A+)
- 63 tests, 100% pasados
- Documentación profesional
- Scripts de ejecución completos

**Meta para ETAPA 2:** Mantener o superar la calidad de ETAPA 1

---

## 📞 CONSULTAS Y AYUDA

### Si tienes dudas sobre:
1. **Arquitectura:** Consultar `docs/PLAN_ESTRUCTURADO_IMPLEMENTACION.md`
2. **Base de Datos:** Revisar `sql/migrate_medical_system.sql`
3. **Etapa 1:** Revisar `docs/ETAPA_1_COMPLETADA.md`
4. **Testing:** Revisar `tests/Etapa_1/`

### Documentación del proyecto:
- `docs/DOCUMENTACION_SISTEMA_CALENDARIO.md` - Documentación general
- `RESUMEN_ETAPA_1.md` - Implementación anterior
- `~/.copilot/session-state/.../EVALUACION_ETAPAS_0_1.md` - Evaluación de calidad

---

## 🎯 COMENZAR IMPLEMENTACIÓN

### Orden recomendado:
1. **Crear migración SQL** (`sql/migrate_etapa_2_turnos.sql`)
2. **Implementar T2.1** (obtener_siguiente_doctor_turno)
3. **Implementar T2.2** (check_doctor_availability)
4. **Implementar T2.3** (generar_slots_con_turnos)
5. **Implementar T2.4** (actualizar_control_turnos)
6. **Modificar T2.5** (agendar_cita_medica_completa)
7. **Crear suite de tests** (70+ tests)
8. **Documentación** (reportes + scripts)
9. **Validación final** (ejecutar todo)

### Comando inicial:
```bash
# 1. Crear estructura
mkdir -p src/medical tests/Etapa_2 sql

# 2. Crear archivos base
touch sql/migrate_etapa_2_turnos.sql
touch src/medical/turnos.py
touch src/medical/disponibilidad.py
touch src/medical/slots.py
touch tests/Etapa_2/test_turnos.py

# 3. Ejecutar migración
python ejecutar_migracion_etapa2.py

# 4. Comenzar implementación
# ... (tu código aquí)
```

---

**¡Buena suerte con la implementación!** 🚀

Recuerda: **Calidad sobre velocidad**. Es mejor tomarse el tiempo necesario para hacerlo bien que apresurarse y tener bugs.

---

**Autor:** Sistema de Supervisión  
**Versión:** 1.0  
**Última Actualización:** 2026-01-28
