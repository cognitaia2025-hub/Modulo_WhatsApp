# 📋 PRD + Stack Tecnológico + Roadmap: Sistema de Agendamiento Híbrido WhatsApp

## 🎯 **EXECUTIVE SUMMARY**

**Producto:** Sistema de agendamiento médico híbrido que funciona vía WhatsApp  
**Objetivo Principal:** Calendario personal + gestión médica profesional en una sola interfaz  
**MVP Target:** Doctor puede agendar pacientes y gestionar agenda personal desde WhatsApp  
**Timeline:** 4 fases críticas, 2-3 días de implementación  
**Stack Core:** LangGraph + PostgreSQL + Google Calendar + WhatsApp + FastAPI patterns

---

## 🏗️ **STACK TECNOLÓGICO DEFINIDO**

### **📱 Frontend Interface**
- **WhatsApp Business API** - Canal de comunicación principal
- **Interfaz:** Conversacional natural en español
- **UX Pattern:** Chat inteligente con clasificación automática

### **🧠 AI & LLM Layer**
- **Primary LLM:** DeepSeek (deepseek-chat) - Terminología médica especializada
- **Backup LLM:** Claude 3.5 Haiku - Respuestas de emergencia
- **Temperature:** 0.7 (balance creatividad/precisión)
- **Timeout:** 20-25s primary, 15-20s backup
- **Embeddings:** sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 (384D)

### **🔄 Orchestration Engine**
- **Framework:** LangGraph (StateGraph)
- **Pattern:** Flujo bifurcado con nodos especializados
- **State Management:** MessagesState + custom state
- **Tools Integration:** 12 herramientas total (6 calendar + 6 medical)

### **🗄️ Database Layer**
- **Primary DB:** PostgreSQL 16+ en Docker
- **Port:** 5434
- **ORM:** SQLAlchemy 2.0 con async support
- **Vector Search:** pgvector para embeddings (384D)
- **Connection Pool:** 5-10 conexiones concurrentes

### **🔗 External Integrations**
- **Google Calendar API:** Cuenta de servicio, dual usage
- **Calendar ID:** 92d85abc... (Timezone: America/Tijuana)
- **Authentication:** Service Account JSON + OAuth2

### **🐳 Infrastructure**
- **Container:** Docker Compose
- **Database:** PostgreSQL oficial image
- **Network:** Internal Docker network
- **Persistence:** Named volumes para datos

---

## 📋 **PRODUCT REQUIREMENTS DOCUMENT**

### **🎯 Core User Stories**

#### **Como Doctor:**
1. **"Necesito agendar una cita para el paciente Juan el viernes a las 10am"**
   - Sistema detecta contexto médico
   - Busca/registra paciente si no existe
   - Valida disponibilidad del doctor
   - Agenda en BD médica + sincroniza Google Calendar
   - Confirma con detalles completos

2. **"Muéstrame mis citas de hoy"**
   - Distingue entre citas médicas vs eventos personales
   - Lista ordenada con paciente, hora, tipo consulta
   - Opción para modificar/cancelar

3. **"Busca el historial de la paciente María"**
   - Búsqueda inteligente por nombre/teléfono
   - Historial completo con citas previas
   - Diagnósticos y tratamientos anteriores

#### **Como Usuario Personal:**
1. **"Recordarme de mi cita dental el martes"**
   - Sistema detecta contexto personal
   - Crea evento en Google Calendar personal
   - Configurar recordatorios

2. **"Mueve mi reunión de mañana para el jueves"**
   - Busca evento en agenda personal
   - Reprograma sin afectar agenda médica

### **🔒 Security & Privacy Requirements**
- **Isolación de datos:** Cada doctor solo ve sus pacientes
- **HIPAA Compliance:** Logs auditables, encriptación de datos sensibles  
- **User Separation:** Phone number como clave primaria única
- **Session Management:** TTL 24h, limpieza automática

### **⚡ Performance Requirements**
- **Response Time:** < 3 segundos para operaciones simples
- **Database Queries:** < 500ms para búsquedas
- **LLM Response:** < 25 segundos (timeout configurado)
- **Concurrent Users:** 5-10 doctores simultáneos (MVP)

### **🎨 UX/UI Requirements**
- **Language:** Español mexicano natural
- **Tone:** Profesional pero amigable
- **Format:** Emojis para claridad, texto estructurado
- **Error Handling:** Mensajes claros en español, sin códigos técnicos

---

## 🗂️ **ARQUITECTURA TÉCNICA DETALLADA**

### **🔀 Flujo de Datos Principal**
```
WhatsApp Message → 
Node 0 (Identificación) → 
Node 1 (Cache/Session) → 
Node 2 (Clasificación) → 
    ├─ Personal: [3A → 4A → 5A → 6A → 7A]
    ├─ Médico:  [3B → 4B → 5B → 8 → 6B → 7B]  
    └─ Chat:    [Respuesta Directa]
```

### **📊 Database Schema Crítico**
```sql
-- Tabla principal usuarios (existente + actualizada)
usuarios (
    phone_number VARCHAR PK,
    tipo_usuario ENUM('personal', 'doctor'),
    es_admin BOOLEAN DEFAULT FALSE,
    email VARCHAR UNIQUE,
    created_at TIMESTAMP
)

-- Nueva tabla doctores (especializada)
doctores (
    id SERIAL PK,
    phone_number VARCHAR FK usuarios(phone_number),
    especialidad VARCHAR NOT NULL,
    num_licencia VARCHAR UNIQUE,
    horario_atencion JSONB DEFAULT '{}'
)

-- Nueva tabla citas_medicas (core del agendamiento)
citas_medicas (
    id SERIAL PK,
    doctor_id INTEGER FK doctores(id),
    paciente_id INTEGER FK pacientes(id),
    fecha_hora_inicio TIMESTAMP NOT NULL,
    fecha_hora_fin TIMESTAMP NOT NULL,
    estado VARCHAR DEFAULT 'programada',
    tipo_consulta VARCHAR DEFAULT 'seguimiento',
    google_event_id VARCHAR,
    notas_privadas TEXT
)
```

### **🛠️ Tools Architecture**
```python
# 6 Herramientas Google Calendar (existentes)
calendar_tools = [
    create_event_tool,
    list_events_tool,
    postpone_event_tool,
    update_event_tool,
    delete_event_tool,
    search_calendar_events_tool
]

# 6 Herramientas Médicas (nuevas)
medical_tools = [
    crear_paciente_medico,
    buscar_pacientes_doctor,
    consultar_slots_disponibles,
    agendar_cita_medica_completa,
    modificar_cita_medica,
    cancelar_cita_medica
]
```

---

## 🚀 **ROADMAP DE IMPLEMENTACIÓN POR FASES**

### **🎯 FASE 1: NODO CLASIFICADOR INTELIGENTE**
**Objetivo:** Sistema detecta automáticamente si el mensaje es personal, médico o chat  
**Duración:** 4-6 horas  
**Prioridad:** CRÍTICA - Sin esto el sistema no es híbrido

#### **📝 Prompt para Implementación:**
```
IMPLEMENTAR Node 2 - Clasificación Inteligente de Mensajes

CONTEXTO: Tienes un sistema LangGraph que actualmente solo maneja calendario personal. 
Necesitas agregar un nodo que clasifique mensajes en 3 categorías:

1. PERSONAL: "mi cita del viernes", "recordarme de la reunión"
2. MÉDICO: "el paciente Juan", "agendar consulta para María"  
3. CHAT: "hola", "cómo estás", "gracias"

ARCHIVO A CREAR: src/nodes/filtrado_inteligente_node.py

REQUERIMIENTOS TÉCNICOS:
- Función clasificar_solicitud(mensaje: str, user_info: dict) -> str
- Patterns regex para detección rápida
- Fallback a LLM para casos ambiguos
- Considera tipo_usuario (doctor puede hacer ambas)
- Return: "personal" | "medico" | "chat"

PATRONES MÉDICOS:
- paciente|consulta|cita médica|historial|diagnóstico
- doctor|médico|especialidad|tratamiento
- agendar.*consulta|buscar.*paciente

PATRONES PERSONALES:  
- mi (cita|evento|reunión)|agenda personal
- recordar.*evento|crear.*cita personal

CÓDIGO ESPECÍFICO REQUERIDO:
- Import re, logging
- Función con validaciones de entrada
- Logs detallados para debug
- Manejo de errores graceful
- Tests unitarios inline

INTEGRACIÓN: Debe conectarse entre Node 1 y los nodos 3A/3B existentes
```

#### **🔧 Archivos a Modificar:**
- `src/nodes/filtrado_inteligente_node.py` [NUEVO]
- `src/graph.py` [MODIFICAR - agregar nodo y rutas]

#### **✅ Criterio de Éxito:**
- Mensaje "mi cita" → flujo personal
- Mensaje "paciente Juan" → flujo médico
- Sistema híbrido funcional básico

---

### **🎯 FASE 2: NODOS MÉDICOS CORE**
**Objetivo:** Implementar flujo médico completo con herramientas  
**Duración:** 6-8 horas  
**Prioridad:** ALTA - Core del agendamiento médico

#### **📝 Prompt para Implementación:**
```
IMPLEMENTAR Nodos Médicos 3B, 4B, 5B para Flujo de Agendamiento

CONTEXTO: El sistema ya clasifica mensajes como médicos. Ahora necesitas el flujo 
completo para que doctores puedan agendar pacientes y gestionar citas.

ARCHIVOS A CREAR:
1. src/nodes/recuperacion_medica_node.py (Node 3B)
2. src/nodes/seleccion_herramientas_medicas_node.py (Node 4B)  
3. src/nodes/ejecucion_medica_node.py (Node 5B)

NODE 3B - RECUPERACIÓN MÉDICA:
- Función: recuperar_contexto_medico(user_phone: str, query: str)
- Consulta BD: doctores, pacientes, citas del doctor
- Embeddings search en historiales si necesario
- Return: contexto médico relevante para LLM

NODE 4B - SELECCIÓN HERRAMIENTAS MÉDICAS:
- Función: seleccionar_herramientas_medicas(mensaje, contexto, herramientas_disponibles)
- Input: 6 herramientas médicas disponibles
- LLM decide cuál(es) usar basado en intención
- Return: herramientas seleccionadas + parámetros

NODE 5B - EJECUCIÓN MÉDICA:
- Función: ejecutar_herramientas_medicas(herramientas_seleccionadas, parametros)
- Ejecuta herramientas médicas con validaciones
- Transacciones ACID para integridad
- Manejo de errores médicos específicos

PATRÓN REUTILIZACIÓN: Usar misma estructura que nodos 3A, 4A, 5A existentes
pero adaptados para BD médica en lugar de Google Calendar.

IMPORTS REQUERIDOS:
from ..medical.tools import get_medical_tools
from ..medical.crud import get_doctor_by_phone, search_patients
from ..database.db_config import get_db_session

VALIDACIONES CRÍTICAS:
- Doctor existe y está activo
- Pacientes pertenecen al doctor (seguridad)
- Validaciones médicas (horarios, conflictos)
- Logs auditables HIPAA
```

#### **🔧 Archivos a Modificar:**
- `src/nodes/recuperacion_medica_node.py` [NUEVO]
- `src/nodes/seleccion_herramientas_medicas_node.py` [NUEVO]
- `src/nodes/ejecucion_medica_node.py` [NUEVO]
- `src/graph.py` [MODIFICAR - integrar nodos médicos]

#### **✅ Criterio de Éxito:**
- Doctor puede registrar paciente nuevo
- Doctor puede agendar cita con validaciones
- Búsqueda de pacientes funciona
- Datos se guardan en BD correctamente

---

### **🎯 FASE 3: SINCRONIZADOR HÍBRIDO**
**Objetivo:** Citas médicas se reflejan automáticamente en Google Calendar  
**Duración:** 4-5 horas  
**Prioridad:** MEDIA - Mejora UX pero no bloquea funcionalidad

#### **📝 Prompt para Implementación:**
```
IMPLEMENTAR Node 8 - Sincronizador BD ↔ Google Calendar

CONTEXTO: Las citas médicas se crean en BD PostgreSQL. Necesitas que también 
aparezcan en Google Calendar del doctor para vista visual, pero la BD es 
la fuente de verdad.

ARCHIVO A CREAR: src/nodes/sincronizador_hibrido_node.py

FUNCIONALIDAD PRINCIPAL:
- Función: sincronizar_cita_medica(cita_id: int) -> dict
- Toma cita de BD médica
- Crea evento en Google Calendar con formato médico
- Actualiza tabla sincronizacion_calendar
- Manejo de errores sin afectar BD

FORMATO EVENTO GOOGLE:
summary: "Consulta - {paciente_name}"
description: "Paciente: {nombre}\nTipo: {tipo_consulta}\nID: {cita_id}"
extendedProperties.private.tipo: "cita_medica"
extendedProperties.private.cita_id: str(cita_id)

TOLERANCIA A FALLOS:
- Si Google Calendar falla, BD médica sigue funcionando
- Retry automático con exponential backoff
- Estado en sincronizacion_calendar: pendiente|sincronizada|error

INTEGRACIÓN:
- Se ejecuta después de Node 5B (ejecución médica)
- Solo para operaciones que crean/modifican citas
- No bloquea respuesta al usuario

IMPORTS CRÍTICOS:
from ..utilities import api_resource  # Google Calendar
from ..medical.crud import get_appointment_by_id, update_sync_record
from datetime import datetime, timedelta
```

#### **🔧 Archivos a Modificar:**
- `src/nodes/sincronizador_hibrido_node.py` [NUEVO]
- `src/graph.py` [MODIFICAR - agregar Node 8 en flujo médico]

#### **✅ Criterio de Éxito:**
- Cita creada en BD → aparece en Google Calendar
- Si Google falla, sistema médico sigue funcionando
- Doctor ve citas médicas en calendario visual

---

### **🎯 FASE 4: TESTING & OPTIMIZACIÓN**
**Objetivo:** Sistema completo funciona end-to-end sin errores  
**Duración:** 3-4 horas  
**Prioridad:** CRÍTICA - Validar que todo funciona

#### **📝 Prompt para Testing:**
```
IMPLEMENTAR Testing Completo del Sistema de Agendamiento

CONTEXTO: Sistema híbrido implementado. Necesitas validar que funciona 
end-to-end desde WhatsApp hasta BD y Google Calendar.

TEST SCENARIOS CRÍTICOS:

1. DOCTOR REGISTRA PACIENTE NUEVO:
Input: "Necesito registrar un paciente nuevo: Juan Pérez, teléfono 555-1234"
Expected: Paciente en BD + confirmación con ID

2. DOCTOR AGENDA CITA:
Input: "Agendar cita para Juan Pérez mañana a las 10am, consulta de seguimiento"
Expected: Cita en BD + Google Calendar + confirmación detallada

3. USUARIO PERSONAL:
Input: "Recordarme de mi cita dental el viernes"
Expected: Solo Google Calendar personal, no BD médica

4. BÚSQUEDA DE PACIENTES:
Input: "Buscar paciente Juan"
Expected: Lista de pacientes coincidentes con historial

5. MODIFICACIÓN DE CITA:
Input: "Cambiar la cita de Juan para las 11am"
Expected: Update en BD + Google Calendar + confirmación

TEST DE ERRORES:
- Paciente inexistente → mensaje claro
- Horario ocupado → validación y alternativas  
- Doctor inexistente → error seguro
- Google Calendar falla → BD funciona

ARCHIVO A CREAR: tests/test_sistema_completo.py

FUNCIÓN PRINCIPAL: test_flujo_agendamiento_completo()
- Crear doctor de prueba
- Registrar paciente
- Agendar cita
- Verificar BD y Google Calendar
- Cleanup automático
```

#### **🔧 Archivos a Crear:**
- `tests/test_sistema_completo.py` [NUEVO]
- `scripts/demo_agendamiento.py` [NUEVO - para demos]

#### **✅ Criterio de Éxito:**
- Todos los tests pasan
- Demo funciona sin errores
- Performance < 3 segundos
- Sistema listo para producción

---

## 🎯 **MILESTONE TRACKING**

### **📊 Definition of Done por Fase**

| Fase | Funcionalidad | Tests | Performance | Ready |
|------|---------------|-------|-------------|--------|
| **Fase 1** | Clasificación automática | Manual OK | N/A | ✅ |
| **Fase 2** | Agendamiento médico | Unitarios OK | < 2s | 🚧 |
| **Fase 3** | Sincronización | Integración OK | < 1s | ⏳ |
| **Fase 4** | Sistema completo | End-to-end OK | < 3s | ⏳ |

### **🚨 Riesgos Técnicos Identificados**

1. **Foreign Key Issues:** Relaciones doctores ↔ citas pueden fallar
   - **Mitigation:** Validaciones en CRUD antes de insert

2. **Google Calendar Rate Limits:** API puede rechazar requests
   - **Mitigation:** Queue + retry con exponential backoff

3. **LLM Timeout en Clasificación:** DeepSeek puede tardar > 25s
   - **Mitigation:** Fallback automático a Claude + patterns regex

4. **Concurrent Access:** Múltiples doctores agendando simultáneamente
   - **Mitigation:** Transacciones ACID + locks en slots críticos

---

## 🔧 **COMANDOS DE DESARROLLO**

### **🚀 Setup Inicial**
```bash
# Verificar estado actual
docker ps
docker exec -it agente-whatsapp-db psql -U admin -d agente_whatsapp -c "\dt"

# Instalar dependencias nuevas
pip install -r requirements.txt

# Test herramientas médicas
python -c "from src.medical.tools import get_medical_tools; print(len(get_medical_tools()))"
```

### **🧪 Testing por Fase**
```bash
# Fase 1 - Test clasificación
python tests/test_clasificacion.py

# Fase 2 - Test nodos médicos  
python tests/test_nodos_medicos.py

# Fase 3 - Test sincronización
python tests/test_sincronizacion.py

# Fase 4 - Test completo
python tests/test_sistema_completo.py
```

### **📊 Monitoring & Debug**
```bash
# Ver logs del sistema
tail -f logs/agendamiento.log

# Verificar BD en tiempo real
docker exec -it agente-whatsapp-db psql -U admin -d agente_whatsapp -c "
SELECT c.id, p.nombre_completo, c.fecha_hora_inicio, c.estado 
FROM citas_medicas c 
JOIN pacientes p ON c.paciente_id = p.id 
ORDER BY c.fecha_hora_inicio DESC LIMIT 5;"

# Estado de sincronización
docker exec -it agente-whatsapp-db psql -U admin -d agente_whatsapp -c "
SELECT estado, COUNT(*) FROM sincronizacion_calendar GROUP BY estado;"
```

---

## 📈 **SUCCESS METRICS**

### **📊 KPIs Técnicos**
- **Uptime:** > 99% (24/7 operacional)
- **Response Time:** < 3s promedio
- **Error Rate:** < 1% de requests
- **Data Integrity:** 0% pérdida de citas

### **👥 KPIs de Usuario**
- **Adoption:** Doctor usa sistema diariamente
- **Efficiency:** Reduce tiempo de agendamiento 50%
- **Accuracy:** 0% citas perdidas o duplicadas
- **UX:** Interfaz natural, sin entrenamiento requerido

### **🎯 MVP Success Criteria**
1. ✅ Doctor puede agendar cita médica desde WhatsApp
2. ✅ Sistema distingue citas médicas vs eventos personales
3. ✅ Citas aparecen en BD médica + Google Calendar
4. ✅ Búsqueda de pacientes funciona perfectamente
5. ✅ Sistema funciona 24/7 sin intervención manual

**🚀 READY FOR IMPLEMENTATION - FASE 1 START NOW! 🚀**