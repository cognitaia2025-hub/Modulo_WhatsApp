# 🎯 PROMPT: IMPLEMENTAR ETAPA 3 - FLUJO INTELIGENTE CON LLM

## 📍 Objetivo

Integrar **clasificación inteligente** y **manejo conversacional** usando LLM (DeepSeek/Claude) para diferenciar entre solicitudes personales, médicas y chat casual.

---

## 📋 Componentes a Implementar

### 1. **Nodo de Filtrado Inteligente** (MODIFICAR)
**Archivo:** `src/nodes/filtrado_inteligente_node.py`

Usar LLM para clasificar mensajes en:
- `personal` - Eventos de calendario personal
- `medica` - Solicitudes médicas (solo doctores)
- `chat` - Conversación casual

**Validación post-LLM:**
- Pacientes externos → SOLO pueden hacer `solicitud_cita_paciente`
- Doctores → acceso completo

---

### 2. **Nodo de Recuperación Médica** (CREAR)
**Archivo:** `src/nodes/recuperacion_medica_node.py`

Recuperar contexto médico relevante:
- Pacientes recientes (últimos 10)
- Citas del día
- Búsqueda semántica en historiales (con embeddings)
- Estadísticas del doctor

**Sin LLM:** Consultas SQL + búsqueda vectorial

---

### 3. **Actualizar Nodo de Selección de Herramientas** (MODIFICAR)
**Archivo:** `src/nodes/seleccion_herramientas_node.py`

Agregar **12 herramientas médicas** al pool:
- `crear_paciente_medico`
- `buscar_pacientes_doctor`
- `consultar_slots_disponibles`
- `agendar_cita_medica_completa`
- etc.

**Reglas:**
- Doctores → todas las herramientas
- Pacientes externos → SOLO agendamiento y consulta de slots
- LLM decide qué usar según contexto

---

### 4. **Nodo de Ejecución Médica** (CREAR)
**Archivo:** `src/nodes/ejecucion_medica_node.py`

Ejecutar herramientas médicas con validaciones:
- Verificar permisos (doctor vs paciente)
- Agregar `doctor_phone` automáticamente
- Actualizar `control_turnos` después de agendar
- Manejo robusto de errores

**Sin LLM:** Ejecución determinística

---

### 5. **Migración de Base de Datos** (CREAR)
**Archivo:** `sql/migrate_etapa_3_flujo_inteligente.sql`

- Actualizar `historiales_medicos` con columna `embedding vector(384)`
- Índice HNSW para búsqueda vectorial rápida
- Vista `resumen_clasificaciones` para métricas

---

## 🧪 TESTING (OBLIGATORIO)

**Ubicación:** `tests/Etapa_3/`

**Archivos requeridos:**
```
tests/Etapa_3/
├── test_filtrado_inteligente.py         (20 tests)
├── test_recuperacion_medica.py          (15 tests)
├── test_seleccion_herramientas_llm.py   (20 tests)
├── test_ejecucion_medica.py             (15 tests)
├── test_integration_etapa3.py           (10 tests)
└── README.md
```

**Total mínimo:** 80 tests

---

### 🚨 REGLA CRÍTICA DE TESTING

**❌ NO modifiques el test para que pase**  
**✅ Repara el CÓDIGO si el test falla**

Solo modifica el test si:
- Está mal configurado
- Es un bug del test mismo
- Necesita ajuste de timeout/mock

**Si el código no cumple con el test → arregla el CÓDIGO**

---

### Tests Prioritarios

#### `test_filtrado_inteligente.py` (20 tests)
```python
def test_clasificar_solicitud_medica_doctor():
    """Doctor dice 'mi paciente Juan' → clasificacion='medica'"""

def test_clasificar_solicitud_personal():
    """Usuario dice 'mi cita del viernes' → clasificacion='personal'"""

def test_clasificar_chat_casual():
    """Usuario dice 'hola' → clasificacion='chat'"""

def test_paciente_externo_solo_solicitud_cita():
    """Paciente externo → siempre 'solicitud_cita_paciente'"""

def test_fallback_claude_si_deepseek_falla():
    """Si DeepSeek falla → usar Claude automáticamente"""

# + 15 tests más (edge cases, timeouts, validaciones)
```

#### `test_seleccion_herramientas_llm.py` (20 tests)
```python
def test_llm_selecciona_agendar_cita():
    """LLM detecta 'quiero cita' → selecciona 'agendar_cita_medica_completa'"""

def test_paciente_externo_herramientas_limitadas():
    """Paciente solo puede usar 2 herramientas: agendar y consultar"""

def test_doctor_acceso_completo():
    """Doctor puede usar todas las 18 herramientas"""

def test_herramientas_ejecutadas_en_orden():
    """Si LLM dice orden [1, 2, 3] → ejecutar en ese orden"""

# + 16 tests más
```

#### `test_integration_etapa3.py` (10 tests)
```python
def test_flujo_completo_doctor():
    """Doctor: mensaje → clasificar → recuperar contexto → seleccionar herramienta → ejecutar"""

def test_flujo_completo_paciente():
    """Paciente: mensaje → clasificar → mostrar opciones → agendar"""

def test_fallback_llm_funciona():
    """Si DeepSeek falla en cualquier punto → Claude toma el control"""

# + 7 tests más
```

---

## 📖 Referencias

### Código Existente
- `src/nodes/filtrado_inteligente_node.py` - Ya existe, solo actualizar
- `src/nodes/seleccion_herramientas_node.py` - Ya existe, agregar herramientas médicas
- `src/medical/turnos.py` - Usar para asignación automática

### Documentación Oficial
- **LangChain:** https://python.langchain.com/docs/integrations/chat/
- **DeepSeek API:** https://platform.deepseek.com/docs
- **pgvector:** https://github.com/pgvector/pgvector
- **pytest-mock:** https://pytest-mock.readthedocs.io/

### Ejemplo de Etapas Anteriores
- `tests/Etapa_1/` - Testing de nodos automatizados
- `tests/Etapa_2/` - Validaciones sin LLM
- `src/nodes/identificacion_usuario_node.py` - Estructura de nodos

---

## ✅ Criterios de Aceptación

### Código
- [ ] 4 nodos implementados/modificados
- [ ] LLM con fallback (DeepSeek → Claude)
- [ ] 12 herramientas médicas agregadas
- [ ] Migración SQL ejecutable
- [ ] Type hints y docstrings completos
- [ ] Logging apropiado

### Testing
- [ ] Mínimo 80 tests implementados
- [ ] 100% de tests pasando
- [ ] Cobertura >95% en código nuevo
- [ ] Tests con mocks de LLM (no llamadas reales)
- [ ] README.md de tests completo

### Documentación
- [ ] `docs/ETAPA_3_COMPLETADA.md`
- [ ] `RESUMEN_ETAPA_3.md`
- [ ] `tests/Etapa_3/README.md`
- [ ] Scripts de ejecución

---

## 🚀 Orden de Implementación

1. **Migración SQL** (`sql/migrate_etapa_3_flujo_inteligente.sql`)
2. **Nodo Filtrado Inteligente** (modificar)
3. **Nodo Recuperación Médica** (crear)
4. **Tests de nodos individuales** (40 tests)
5. **Nodo Selección Herramientas** (modificar)
6. **Nodo Ejecución Médica** (crear)
7. **Tests de integración** (40 tests)
8. **Documentación y scripts**

---

## ⚠️ Errores Comunes a Evitar

### ❌ NO hacer:
1. **Modificar tests para que pasen** → Arreglar el código
2. **Llamadas reales a LLM en tests** → Usar mocks
3. **Hardcodear respuestas de LLM** → Usar fixtures realistas
4. **Ignorar timeouts** → LLM puede tardar, manejar con `timeout=30`
5. **No validar permisos** → Pacientes NO deben acceder a todo

### ✅ SÍ hacer:
1. **Usar pytest-mock** para simular respuestas de LLM
2. **Validar permisos** en cada herramienta
3. **Testear fallback** DeepSeek → Claude
4. **Manejo robusto** de errores de API
5. **Logging detallado** para debugging

---

## 📊 Fixtures de Testing

```python
# tests/Etapa_3/conftest.py
import pytest
from unittest.mock import Mock

@pytest.fixture
def mock_deepseek_response():
    """Mock de respuesta de DeepSeek"""
    return {
        "clasificacion": "medica",
        "confianza": 0.95,
        "razonamiento": "Solicitud de cita médica",
        "requiere_herramientas": True
    }

@pytest.fixture
def mock_llm_clasificacion(mocker):
    """Mock del LLM para clasificación"""
    mock = mocker.patch('src.nodes.filtrado_inteligente_node.llm_with_fallback')
    mock.invoke.return_value = Mock(content='{"clasificacion": "medica"}')
    return mock

@pytest.fixture
def estado_con_doctor():
    """Estado del grafo con usuario tipo doctor"""
    return {
        "messages": [HumanMessage(content="mi paciente Juan necesita cita")],
        "tipo_usuario": "doctor",
        "doctor_id": 1,
        "user_id": "+526641234567"
    }

@pytest.fixture
def estado_con_paciente():
    """Estado del grafo con paciente externo"""
    return {
        "messages": [HumanMessage(content="quiero una cita")],
        "tipo_usuario": "paciente_externo",
        "doctor_id": None,
        "user_id": "+526649876543"
    }
```

---

## 🎯 Meta de Calidad

**Etapa 1:** 99/100 (A+)  
**Etapa 2:** Código 98/100, Tests 0/100 → 59/100 (F)  
**Etapa 3:** Mantener estándar de Etapa 1

**Objetivo:** 95+ / 100 (A)

---

## 📞 Si Tienes Dudas

1. **Arquitectura:** `docs/PLAN_ESTRUCTURADO_IMPLEMENTACION.md` líneas 554-800
2. **Testing:** Revisar `tests/Etapa_1/` como ejemplo
3. **LLM:** Ver `src/nodes/seleccion_herramientas_node.py` existente
4. **Prompts:** Consultar ejemplos en el plan

---

**¡Comienza! El código de Etapa 2 fue excelente, solo le faltaron tests. Ahora hazlo completo desde el inicio.**

---

**Fecha:** 2026-01-28  
**Prioridad:** 🟠 ALTA  
**Dependencias:** Etapas 0, 1, 2 completadas
