# ETAPA 8: ACTUALIZACIÓN DEL GRAFO LANGGRAPH

**Fecha de inicio:** 29 de Enero de 2026
**Duración estimada:** 3-4 días
**Prioridad:** 🔴 CRÍTICA (después de tener nodos implementados)

---

## 🎯 Objetivo General

Integrar **todos los nodos nuevos implementados en las Etapas 0-7** en el flujo del grafo LangGraph principal, actualizando:
- Punto de entrada del grafo
- Rutas condicionales entre nodos
- Funciones de decisión (routing)
- Manejo de estados entre transiciones
- Compilación final del grafo

---

## 📋 Componentes a Modificar

### 🔄 Archivo Principal

**`src/graph_whatsapp.py`** - Actualización completa del grafo

---

## 📝 Nodos del Sistema (Estado Actual)

### ✅ Nodos Implementados (Etapas 0-7)

#### Nodos Automatizados (Sin LLM)
1. **N0** - `identificacion_usuario_node` ✅ (Etapa 1)
2. **N1** - `nodo_cache_sesion` ✅ (Existente)
3. **N5B** - `ejecucion_medica_node` ✅ (Etapa 3)
4. **N7** - `persistencia_episodica_node` ✅ (Existente)
5. **N8** - `sincronizador_hibrido_node` ✅ (Etapa 5)

#### Nodos Inteligentes (Con LLM)
1. **N2** - `filtrado_inteligente_node` ✅ (Etapa 3)
2. **N3A** - `recuperacion_episodica_node` ✅ (Existente)
3. **N3B** - `recuperacion_medica_node` ✅ (Etapa 3)
4. **N4** - `seleccion_herramientas_node` ✅ (Etapa 3)
5. **N5A** - `ejecucion_herramientas_node` ✅ (Existente)
6. **N6R** - `recepcionista_node` ✅ (Etapa 4)
7. **N6** - `generacion_resumen_node` ✅ (Existente)

---

## 📝 Especificaciones Técnicas Detalladas

### Estructura del Grafo Actualizado

```python
# Archivo: src/graph_whatsapp.py

from langgraph.graph import StateGraph, END
from typing import Literal

from src.state.agent_state import WhatsAppAgentState

# Importar nodos
from src.nodes.identificacion_usuario_node import nodo_identificacion_usuario_wrapper
from src.nodes.cache_sesion_node import nodo_cache_sesion
from src.nodes.filtrado_inteligente_node import filtrado_inteligente_node
from src.nodes.recuperacion_episodica_node import recuperacion_episodica_node
from src.nodes.recuperacion_medica_node import recuperacion_medica_node
from src.nodes.seleccion_herramientas_node import seleccion_herramientas_node
from src.nodes.ejecucion_herramientas_node import ejecucion_herramientas_node
from src.nodes.ejecucion_medica_node import ejecucion_medica_node
from src.nodes.recepcionista_node import recepcionista_node
from src.nodes.generacion_resumen_node import generacion_resumen_node
from src.nodes.persistencia_episodica_node import persistencia_episodica_node
from src.nodes.sincronizador_hibrido_node import sincronizador_hibrido_node


def crear_grafo_whatsapp() -> StateGraph:
    """
    Crea y compila el grafo LangGraph completo del sistema WhatsApp.

    Flujo principal:
    1. Identificación de usuario (N0)
    2. Caché de sesión (N1)
    3. Filtrado inteligente (N2) - Clasifica intención
    4. Rutas condicionales según clasificación:
       - solicitud_cita_paciente → Recepcionista (N6R)
       - medica (doctor) → Recuperación Médica (N3B)
       - personal → Recuperación Episódica (N3A)
       - chat_casual → Generación Resumen (N6)
    5. Selección de herramientas (N4)
    6. Ejecución de herramientas (N5A o N5B)
    7. Sincronización Google Calendar (N8) si aplica
    8. Generación de resumen (N6)
    9. Persistencia episódica (N7)
    10. END

    Returns:
        Grafo compilado listo para usar
    """

    # ==================== CREAR GRAFO ====================
    workflow = StateGraph(WhatsAppAgentState)

    # ==================== AGREGAR NODOS ====================

    # N0 - Identificación de Usuario (ETAPA 1)
    workflow.add_node("identificacion_usuario", nodo_identificacion_usuario_wrapper)

    # N1 - Caché de Sesión (EXISTENTE)
    workflow.add_node("cache_sesion", nodo_cache_sesion)

    # N2 - Filtrado Inteligente (ETAPA 3)
    workflow.add_node("filtrado_inteligente", filtrado_inteligente_node)

    # N3A - Recuperación Episódica Personal (EXISTENTE)
    workflow.add_node("recuperacion_episodica", recuperacion_episodica_node)

    # N3B - Recuperación Médica (ETAPA 3)
    workflow.add_node("recuperacion_medica", recuperacion_medica_node)

    # N4 - Selección de Herramientas (ETAPA 3)
    workflow.add_node("seleccion_herramientas", seleccion_herramientas_node)

    # N5A - Ejecución Herramientas Personales (EXISTENTE)
    workflow.add_node("ejecucion_herramientas", ejecucion_herramientas_node)

    # N5B - Ejecución Herramientas Médicas (ETAPA 3)
    workflow.add_node("ejecucion_medica", ejecucion_medica_node)

    # N6R - Recepcionista Conversacional (ETAPA 4)
    workflow.add_node("recepcionista", recepcionista_node)

    # N6 - Generación de Resumen (EXISTENTE)
    workflow.add_node("generacion_resumen", generacion_resumen_node)

    # N7 - Persistencia Episódica (EXISTENTE)
    workflow.add_node("persistencia_episodica", persistencia_episodica_node)

    # N8 - Sincronizador Híbrido BD ↔ Google Calendar (ETAPA 5)
    workflow.add_node("sincronizador_hibrido", sincronizador_hibrido_node)

    # ==================== PUNTO DE ENTRADA ====================
    workflow.set_entry_point("identificacion_usuario")

    # ==================== RUTAS FIJAS ====================

    # N0 → N1 (siempre)
    workflow.add_edge("identificacion_usuario", "cache_sesion")

    # N1 → N2 (siempre)
    workflow.add_edge("cache_sesion", "filtrado_inteligente")

    # N3A → N4 (siempre)
    workflow.add_edge("recuperacion_episodica", "seleccion_herramientas")

    # N3B → N4 (siempre)
    workflow.add_edge("recuperacion_medica", "seleccion_herramientas")

    # N5A → N6 (siempre)
    workflow.add_edge("ejecucion_herramientas", "generacion_resumen")

    # N5B → N8 (siempre - sincronizar antes de generar resumen)
    workflow.add_edge("ejecucion_medica", "sincronizador_hibrido")

    # N8 → N6 (siempre)
    workflow.add_edge("sincronizador_hibrido", "generacion_resumen")

    # N6 → N7 (siempre)
    workflow.add_edge("generacion_resumen", "persistencia_episodica")

    # N7 → END (siempre)
    workflow.add_edge("persistencia_episodica", END)

    # ==================== RUTAS CONDICIONALES ====================

    # -------------------- DECISIÓN 1: Clasificación (N2) --------------------
    def decidir_flujo_clasificacion(state: WhatsAppAgentState) -> Literal[
        "recepcionista",
        "recuperacion_medica",
        "recuperacion_episodica",
        "generacion_resumen"
    ]:
        """
        Decide la ruta después del filtrado inteligente según:
        1. Clasificación de intención
        2. Tipo de usuario

        Reglas:
        - solicitud_cita_paciente → Recepcionista (flujo conversacional)
        - medica + doctor → Recuperación Médica (herramientas médicas)
        - personal → Recuperación Episódica (calendario personal)
        - chat_casual → Generación Resumen (sin herramientas)
        """
        clasificacion = state.get('clasificacion', 'chat_casual')
        tipo_usuario = state.get('tipo_usuario', 'paciente_externo')

        # Caso 1: Paciente externo solicita cita
        if clasificacion == 'solicitud_cita_paciente':
            return "recepcionista"

        # Caso 2: Doctor con operación médica
        elif clasificacion == 'medica' and tipo_usuario == 'doctor':
            return "recuperacion_medica"

        # Caso 3: Calendario personal (cualquier usuario)
        elif clasificacion == 'personal':
            return "recuperacion_episodica"

        # Caso 4: Chat casual o consulta (sin herramientas)
        else:
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

    # -------------------- DECISIÓN 2: Ejecución (N4) --------------------
    def decidir_tipo_ejecucion(state: WhatsAppAgentState) -> Literal[
        "ejecucion_medica",
        "ejecucion_herramientas",
        "generacion_resumen"
    ]:
        """
        Decide qué nodo de ejecución usar según herramientas seleccionadas.

        Reglas:
        - Sin herramientas → Generación Resumen
        - Hay herramientas médicas → Ejecución Médica (N5B)
        - Solo herramientas personales → Ejecución Personal (N5A)
        """
        herramientas = state.get('herramientas_seleccionadas', [])

        if not herramientas:
            return "generacion_resumen"

        # Verificar si hay herramientas médicas
        hay_medicas = any(
            h.get('tipo') == 'medica'
            for h in herramientas
            if isinstance(h, dict)
        )

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

    # -------------------- DECISIÓN 3: Recepcionista (N6R) --------------------
    def decidir_despues_recepcionista(state: WhatsAppAgentState) -> Literal[
        "sincronizador_hibrido",
        "generacion_resumen"
    ]:
        """
        Decide la ruta después del recepcionista según estado de conversación.

        Reglas:
        - completado (cita agendada) → Sincronizador (N8)
        - cualquier otro estado → Generación Resumen (N6)
        """
        estado_conv = state.get('estado_conversacion', 'inicial')

        if estado_conv == 'completado':
            # Cita agendada exitosamente, sincronizar con Google Calendar
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

    # ==================== COMPILAR GRAFO ====================
    app = workflow.compile()

    return app


# ==================== INSTANCIA GLOBAL ====================
# Esta será la instancia que se use en main.py
app = crear_grafo_whatsapp()
```

---

## 📊 Diagrama del Flujo Actualizado

```
┌─────────────────────────────────────────────────────────────────┐
│                    FLUJO GRAFO LANGGRAPH                        │
└─────────────────────────────────────────────────────────────────┘

                        ┌─────────────┐
                        │   START     │
                        └──────┬──────┘
                               │
                        ┌──────▼──────┐
                        │  N0: ID     │  Identificación Usuario
                        │  Usuario    │  (auto-registro si nuevo)
                        └──────┬──────┘
                               │
                        ┌──────▼──────┐
                        │  N1: Caché  │  Recuperar/Crear sesión
                        │  Sesión     │
                        └──────┬──────┘
                               │
                        ┌──────▼──────┐
                        │  N2: Filtro │  LLM clasifica intención
                        │  Inteligente│  (medica/personal/cita/casual)
                        └──────┬──────┘
                               │
                ┌──────────────┼──────────────┐
                │              │              │
         [solicitud_cita]  [medica+    [personal]  [chat_casual]
                │         doctor]         │              │
                │              │          │              │
         ┌──────▼──────┐ ┌────▼─────┐ ┌─▼──────┐       │
         │ N6R: Recepc │ │ N3B: Rec │ │ N3A:   │       │
         │ cionista    │ │ Médica   │ │ Rec    │       │
         └──────┬──────┘ └────┬─────┘ │ Episód │       │
                │              │       └─┬──────┘       │
                │              └────┬────┘              │
                │                   │                   │
                │            ┌──────▼──────┐            │
                │            │  N4: Selecc │            │
                │            │  Herramientas│           │
                │            └──────┬──────┘            │
                │                   │                   │
                │          ┌────────┴────────┐          │
                │          │                 │          │
                │    [hay_medicas]    [solo_personales] │
                │          │                 │          │
                │    ┌─────▼─────┐    ┌──────▼──────┐  │
                │    │ N5B: Ejec │    │ N5A: Ejec   │  │
                │    │ Médica    │    │ Personal    │  │
                │    └─────┬─────┘    └──────┬──────┘  │
                │          │                 │          │
                │    ┌─────▼─────┐           │          │
                │    │ N8: Sync  │           │          │
                │    │ Calendar  │           │          │
                │    └─────┬─────┘           │          │
                │          │                 │          │
         [completado]      └─────────────────┴──────────┘
                │                            │
         ┌──────▼──────┐                    │
         │ N8: Sync    │                    │
         │ Calendar    │                    │
         └──────┬──────┘                    │
                │                           │
                └───────────┬───────────────┘
                            │
                     ┌──────▼──────┐
                     │  N6: Gen    │  LLM genera respuesta
                     │  Resumen    │
                     └──────┬──────┘
                            │
                     ┌──────▼──────┐
                     │  N7: Persist│  Guardar en memoria
                     │  Episódica  │
                     └──────┬──────┘
                            │
                        ┌───▼───┐
                        │  END  │
                        └───────┘
```

---

## ✅ Criterios de Aceptación

- [ ] Todos los nodos están correctamente agregados al grafo
- [ ] Punto de entrada es `identificacion_usuario`
- [ ] Las 3 funciones de decisión están implementadas correctamente
- [ ] Rutas condicionales funcionan según las reglas especificadas
- [ ] Estado se propaga correctamente entre nodos
- [ ] El grafo compila sin errores
- [ ] Flujo completo funciona end-to-end
- [ ] Paciente externo → Recepcionista → Sincronización funciona
- [ ] Doctor → Recuperación Médica → Ejecución → Sincronización funciona
- [ ] Usuario normal → Recuperación Personal → Ejecución funciona
- [ ] Chat casual → Generación Resumen (sin herramientas) funciona

---

## 🧪 TESTS REQUERIDOS

### ⚠️ REGLA DE ORO: REPARAR CÓDIGO, NO TESTS

**CRÍTICO:** Si un test falla:
- ✅ **CORRECTO:** Reparar el código para que pase el test
- ❌ **INCORRECTO:** Modificar el test para que pase
- ⚖️ **ÚNICA EXCEPCIÓN:** Si el test tiene un error lógico evidente

---

### Tests Mínimos Obligatorios

**Ubicación:** `tests/Etapa_8/`

#### 1. test_grafo_compilacion.py (5 tests)
```python
def test_grafo_compila_correctamente()
def test_todos_los_nodos_agregados()
def test_punto_entrada_es_identificacion()
def test_rutas_fijas_correctas()
def test_rutas_condicionales_configuradas()
```

#### 2. test_decisiones_clasificacion.py (10 tests)
```python
def test_decision_solicitud_cita_paciente()
def test_decision_medica_doctor()
def test_decision_medica_no_doctor_falla()
def test_decision_personal()
def test_decision_chat_casual()
def test_decision_clasificacion_invalida()
def test_decision_sin_tipo_usuario()
def test_decision_paciente_externo_medica()
def test_decision_admin_personal()
def test_decision_estado_vacio()
```

#### 3. test_decisiones_ejecucion.py (8 tests)
```python
def test_decision_sin_herramientas()
def test_decision_solo_herramientas_personales()
def test_decision_solo_herramientas_medicas()
def test_decision_herramientas_mixtas()
def test_decision_herramientas_vacio()
def test_decision_herramientas_formato_invalido()
def test_decision_herramienta_sin_tipo()
def test_decision_multiples_medicas()
```

#### 4. test_decisiones_recepcionista.py (6 tests)
```python
def test_decision_recepcionista_completado()
def test_decision_recepcionista_inicial()
def test_decision_recepcionista_solicitando_nombre()
def test_decision_recepcionista_esperando_seleccion()
def test_decision_recepcionista_sin_estado()
def test_decision_recepcionista_estado_invalido()
```

#### 5. test_flujos_completos.py (12 tests)
```python
def test_flujo_paciente_externo_solicita_cita()
def test_flujo_doctor_registra_consulta()
def test_flujo_doctor_agenda_cita()
def test_flujo_usuario_calendario_personal()
def test_flujo_admin_chat_casual()
def test_flujo_paciente_externo_chat()
def test_flujo_doctor_reportes()
def test_flujo_doctor_buscar_pacientes()
def test_flujo_recepcionista_completo_con_sync()
def test_flujo_medico_completo_con_sync()
def test_flujo_personal_sin_sync()
def test_flujo_multiples_mensajes_misma_sesion()
```

#### 6. test_propagacion_estado.py (8 tests)
```python
def test_user_id_se_propaga()
def test_tipo_usuario_se_propaga()
def test_es_admin_se_propaga()
def test_clasificacion_se_propaga()
def test_herramientas_se_propagan()
def test_cita_id_se_propaga()
def test_estado_conversacion_se_propaga()
def test_mensaje_final_se_genera()
```

#### 7. test_integracion_grafo_completo.py (15 tests)
```python
def test_grafo_procesa_mensaje_paciente_nuevo()
def test_grafo_procesa_mensaje_doctor_existente()
def test_grafo_identifica_usuario_correctamente()
def test_grafo_cache_sesion_funciona()
def test_grafo_clasifica_intencion_correctamente()
def test_grafo_ejecuta_herramientas_correctamente()
def test_grafo_sincroniza_calendar_tras_cita()
def test_grafo_no_sincroniza_sin_cita()
def test_grafo_persiste_memoria_episodica()
def test_grafo_genera_respuesta_final()
def test_grafo_maneja_errores_gracefully()
def test_grafo_multiples_turnos_conversacion()
def test_grafo_timeout_no_ocurre()
def test_grafo_estado_final_consistente()
def test_grafo_logs_completos()
```

### Cobertura Mínima

**Meta: 85%+ de cobertura del grafo**

- ✅ Todas las rutas condicionales probadas
- ✅ Todos los flujos end-to-end probados
- ✅ Propagación de estado validada
- ✅ Manejo de errores en cada nodo
- ✅ Casos edge en decisiones

---

## 📚 Documentación Requerida

Al finalizar la etapa, crear:

### 1. `tests/Etapa_8/README.md`
```markdown
# Tests - ETAPA 8: Actualización Grafo LangGraph

## Ejecución
pytest tests/Etapa_8/ -v

## Tests de Integración (requieren BD y servicios)
pytest tests/Etapa_8/test_integracion_grafo_completo.py -v

## Cobertura
pytest tests/Etapa_8/ --cov=src/graph_whatsapp

## Estructura
[Descripción de tests por archivo]
```

### 2. `docs/ETAPA_8_COMPLETADA.md`
```markdown
# ✅ ETAPA 8 COMPLETADA: Actualización Grafo LangGraph

**Fecha de inicio:** [fecha]
**Fecha de finalización:** [fecha]
**Duración real:** X días

## Nodos Integrados
[Lista de 12 nodos con descripción]

## Rutas Implementadas
- Rutas fijas: X
- Rutas condicionales: 3
- Funciones de decisión: 3

## Tests Ejecutados
Total: X tests
Pasando: X (100%)
Cobertura: X%

## Flujos Validados
[Lista de flujos completos probados]

## Problemas Encontrados y Resueltos
[Documentar problemas]
```

### 3. `docs/ARQUITECTURA_GRAFO_FINAL.md`
```markdown
# 🏗️ Arquitectura del Grafo LangGraph - Sistema WhatsApp

## Descripción General
[Explicación del grafo completo]

## Nodos del Sistema (12 total)

### Nodos Automatizados (5)
[Descripción de cada nodo sin LLM]

### Nodos Inteligentes (7)
[Descripción de cada nodo con LLM]

## Flujos Principales

### 1. Flujo Paciente Externo (Recepcionista)
[Diagrama y explicación]

### 2. Flujo Doctor (Operaciones Médicas)
[Diagrama y explicación]

### 3. Flujo Personal (Calendario)
[Diagrama y explicación]

### 4. Flujo Chat Casual
[Diagrama y explicación]

## Decisiones de Routing

### decidir_flujo_clasificacion()
[Tabla de decisiones]

### decidir_tipo_ejecucion()
[Tabla de decisiones]

### decidir_despues_recepcionista()
[Tabla de decisiones]

## Estado del Sistema (WhatsAppAgentState)
[Lista completa de campos del estado]

## Manejo de Errores
[Estrategias de error handling]
```

### 4. Actualizar `docs/PLAN_ESTRUCTURADO_IMPLEMENTACION.md`
Marcar ETAPA 8 como ✅ COMPLETADA

---

## 🔍 Checklist de Finalización

- [ ] Grafo compila correctamente
- [ ] Los 12 nodos están integrados
- [ ] 3 funciones de decisión implementadas
- [ ] Todas las rutas condicionales funcionan
- [ ] Tests creados (mínimo 64 tests)
- [ ] 100% de tests pasando
- [ ] Cobertura >85%
- [ ] Flujos end-to-end validados
- [ ] Propagación de estado correcta
- [ ] Sin errores de compilación
- [ ] Sin warnings en logs
- [ ] Documentación completa (README + reportes + arquitectura)
- [ ] Diagramas actualizados

---

## 🔄 Validación de Integración

Después de completar esta etapa, ejecutar **TODOS los tests del proyecto**:

```bash
# Ejecutar todos los tests
pytest tests/ -v

# Meta final del proyecto
ETAPA 0: 20/20 (100%)
ETAPA 1: 56+/63 (>89%)
ETAPA 2: 70/70 (100%)
ETAPA 3: 76/80 (95%)
ETAPA 4: 23/23 (100%)
ETAPA 5: 27/27 (100%)
ETAPA 6: 15/15 (100%)
ETAPA 7: X/47+ (>95%)
ETAPA 8: X/64+ (>95%)

TOTAL: >450 tests passing
```

---

## 📞 Comunicación

Al finalizar, reportar:

```
✅ ETAPA 8 COMPLETADA - GRAFO COMPLETO INTEGRADO

Nodos integrados: 12 (5 automatizados + 7 inteligentes)
Rutas condicionales: 3
Tests: X/X pasando (100%)
Duración: X días
Cobertura: X%

🎉 SISTEMA COMPLETO - TODAS LAS ETAPAS FINALIZADAS

Total de tests del proyecto: X/450+ (>95%)

Próximo paso: Correcciones finales y optimización
```

---

**Última actualización:** 29 de Enero de 2026
**Prioridad:** 🔴 CRÍTICA (última etapa del plan)
