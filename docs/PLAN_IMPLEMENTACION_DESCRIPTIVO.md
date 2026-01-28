# 📋 Plan Descriptivo de Implementación - Sistema Híbrido Médico

## 🎯 Resumen Ejecutivo para Agentes

Este documento describe **paso a paso** cómo transformar nuestro calendario personal WhatsApp en un sistema híbrido que también maneje citas médicas. Está escrito para que cualquier agente de IA pueda retomar el trabajo en cualquier punto.

---

## 📊 Estado Actual del Sistema

**✅ LO QUE YA FUNCIONA:**
- 7 nodos LangGraph para calendario personal
- Base de datos PostgreSQL en puerto 5434
- 6 herramientas Google Calendar
- Sistema de embeddings con pgvector
- Identificación por número de teléfono

**🚧 LO QUE VAMOS A AGREGAR:**
- Gestión de pacientes médicos
- Citas con validación de disponibilidad
- Base de datos médica robusta
- 12 herramientas médicas nuevas
- Sincronización híbrida BD ↔ Google Calendar

---

## 🗂️ Fases de Implementación Descriptiva

### **FASE 1: CIMIENTOS MÉDICOS** 
*⏱️ Duración Estimada: 2-3 días*

#### ¿Qué hacemos?
Agregamos las tablas necesarias para manejar doctores, pacientes y citas médicas, sin tocar el sistema actual que ya funciona.

#### ¿Cómo se siente?
Como agregar un ala nueva a una casa que ya funciona. La casa original sigue igual, pero ahora tiene más habitaciones.

#### Deliverables concretos:
- [x] `sql/migrate_medical_system.sql` - Script que agrega tablas médicas
- [x] `src/medical/models.py` - Definiciones de tablas médicas
- [x] `src/medical/crud.py` - Operaciones básicas BD médica
- [ ] **EJECUTAR:** Migración en base de datos
- [ ] **VERIFICAR:** Tablas creadas correctamente

#### Archivos que se crean/modifican:
```
sql/migrate_medical_system.sql          [NUEVO]
src/medical/__init__.py                 [NUEVO]
src/medical/models.py                   [NUEVO]  
src/medical/crud.py                     [NUEVO]
requirements.txt                        [MODIFICAR - agregar bcrypt]
```

#### ¿Cómo saber que terminamos bien?
- [ ] Base de datos tiene 5 tablas nuevas sin errores
- [ ] Sistema original sigue funcionando igual
- [ ] No hay warnings de foreign keys

---

### **FASE 2: HERRAMIENTAS MÉDICAS BÁSICAS**
*⏱️ Duración Estimada: 3-4 días*

#### ¿Qué hacemos?
Creamos 6 herramientas básicas para que los doctores puedan registrar pacientes, buscarlos y agendar citas. Es como darle instrumentos médicos a un doctor.

#### ¿Cómo se siente?
Como equipar un consultorio médico. Ahora el doctor tiene todo lo necesario para atender pacientes, pero de manera digital.

#### Deliverables concretos:
- [ ] `src/medical/tools.py` - 6 herramientas médicas core
- [ ] `src/tool.py` - Registrar herramientas en sistema
- [ ] `tests/medical/test_basic_tools.py` - Tests unitarios
- [ ] **VERIFICAR:** Herramientas disponibles en LangGraph

#### Las 6 herramientas core:
1. **crear_paciente_medico** - Registrar nuevos pacientes
2. **buscar_pacientes_doctor** - Encontrar pacientes por nombre/teléfono
3. **consultar_slots_disponibles** - Ver horarios libres del doctor
4. **agendar_cita_medica_completa** - Programar citas con validaciones
5. **modificar_cita_medica** - Cambiar detalles de citas existentes
6. **cancelar_cita_medica** - Cancelar citas y liberar horarios

#### Archivos que se crean/modifican:
```
src/medical/tools.py                    [NUEVO]
src/tool.py                            [MODIFICAR - importar medical tools]
tests/medical/__init__.py               [NUEVO]
tests/medical/test_basic_tools.py       [NUEVO]
```

#### ¿Cómo saber que terminamos bien?
- [ ] 6 herramientas se ejecutan sin errores
- [ ] Puedes registrar un paciente de prueba
- [ ] Puedes agendar una cita de prueba
- [ ] Tests pasan al 100%

---

### **FASE 3: CEREBRO INTELIGENTE**
*⏱️ Duración Estimada: 2-3 días*

#### ¿Qué hacemos?
Actualizamos el "cerebro" del sistema para que entienda cuándo hablas de cosas personales vs. cuándo hablas de pacientes médicos.

#### ¿Cómo se siente?
Como entrenar a un asistente para que sepa cuándo eres tú hablando de tu vida personal vs. cuándo eres tú como doctor hablando de trabajo.

#### Deliverables concretos:
- [ ] `src/nodes/filtrado_inteligente_node.py` - Actualizar Node 2
- [ ] `src/nodes/recuperacion_medica_node.py` - Crear Node 3B
- [ ] `src/nodes/ejecucion_medica_node.py` - Crear Node 5B
- [ ] **VERIFICAR:** Sistema detecta contexto médico vs. personal

#### Archivos que se crean/modifican:
```
src/nodes/filtrado_inteligente_node.py    [MODIFICAR - agregar clasificación médica]
src/nodes/recuperacion_medica_node.py     [NUEVO]
src/nodes/ejecucion_medica_node.py        [NUEVO] 
src/graph.py                              [MODIFICAR - agregar nodos médicos]
```

#### ¿Cómo saber que terminamos bien?
- [ ] Mensaje "mi cita del viernes" → flujo personal
- [ ] Mensaje "el paciente Juan" → flujo médico  
- [ ] Mensaje "hola" → chat simple
- [ ] Ambos flujos funcionan independientemente

---

### **FASE 4: SINCRONIZACIÓN MÁGICA**
*⏱️ Duración Estimada: 3-4 días*

#### ¿Qué hacemos?
Creamos el "puente" que conecta la base de datos médica con Google Calendar, para que los doctores vean las citas médicas también en su calendario visual.

#### ¿Cómo se siente?
Como tener un espejo mágico: todo lo que haces en la clínica digital se refleja automáticamente en tu calendario de Google, pero la información real vive en la clínica.

#### Deliverables concretos:
- [ ] `src/nodes/sincronizador_hibrido_node.py` - Node 8 sincronización
- [ ] `src/background/calendar_sync.py` - Workers de sincronización
- [ ] `src/medical/sync_manager.py` - Gestor de errores de sync
- [ ] **VERIFICAR:** Citas médicas aparecen en Google Calendar

#### Archivos que se crean/modifican:
```
src/nodes/sincronizador_hibrido_node.py   [NUEVO]
src/background/__init__.py                [NUEVO]
src/background/calendar_sync.py           [NUEVO]
src/medical/sync_manager.py               [NUEVO]
src/graph.py                             [MODIFICAR - agregar Node 8]
```

#### ¿Cómo saber que terminamos bien?
- [ ] Crear cita médica en BD → aparece en Google Calendar
- [ ] Si Google Calendar falla, sistema médico sigue funcionando
- [ ] Eventos médicos tienen etiqueta especial en calendario
- [ ] No hay duplicados ni conflictos

---

### **FASE 5: HERRAMIENTAS AVANZADAS**
*⏱️ Duración Estimada: 4-5 días*

#### ¿Qué hacemos?
Agregamos las 6 herramientas restantes para historiales médicos, reportes y funcionalidades avanzadas que hacen el sistema completo.

#### ¿Cómo se siente?
Como equipar el consultorio con tecnología de punta: rayos X digitales, historiales completos, estadísticas automáticas.

#### Deliverables concretos:
- [ ] `src/medical/advanced_tools.py` - 6 herramientas avanzadas
- [ ] `src/medical/reports.py` - Generador de reportes médicos
- [ ] `src/medical/analytics.py` - Estadísticas de consultas
- [ ] **VERIFICAR:** Sistema médico completo funcionando

#### Las 6 herramientas avanzadas:
7. **registrar_consulta** - Guardar diagnósticos y tratamientos
8. **consultar_historial_paciente** - Ver historial médico completo
9. **actualizar_disponibilidad_doctor** - Configurar horarios de atención
10. **generar_reporte_doctor** - Reportes de actividad médica
11. **obtener_estadisticas_consultas** - Analytics de productividad
12. **buscar_citas_por_periodo** - Filtros avanzados de búsqueda

#### Archivos que se crean/modifican:
```
src/medical/advanced_tools.py           [NUEVO]
src/medical/reports.py                  [NUEVO]
src/medical/analytics.py                [NUEVO]
src/tool.py                            [MODIFICAR - registrar 6 tools más]
```

#### ¿Cómo saber que terminamos bien?
- [ ] 12 herramientas médicas funcionando
- [ ] Puedes registrar una consulta completa
- [ ] Puedes generar reportes de actividad
- [ ] Analytics muestran estadísticas reales

---

### **FASE 6: TESTING Y OPTIMIZACIÓN**
*⏱️ Duración Estimada: 2-3 días*

#### ¿Qué hacemos?
Probamos todo el sistema de punta a punta, corregimos errores y optimizamos rendimiento.

#### ¿Cómo se siente?
Como hacer la inauguración de la clínica: revisar que todo funcione perfecto antes de que lleguen los pacientes reales.

#### Deliverables concretos:
- [ ] `tests/integration/test_hybrid_flow.py` - Tests de flujo completo
- [ ] `tests/medical/test_full_medical_workflow.py` - Tests médicos end-to-end
- [ ] `docs/GUIA_DOCTOR.md` - Manual para doctores
- [ ] **VERIFICAR:** Sistema listo para producción

#### Archivos que se crean/modifican:
```
tests/integration/test_hybrid_flow.py      [NUEVO]
tests/medical/test_full_medical_workflow.py [NUEVO]
docs/GUIA_DOCTOR.md                        [NUEVO]
docs/TROUBLESHOOTING.md                    [NUEVO]
```

#### ¿Cómo saber que terminamos bien?
- [ ] Flujo personal + médico funcionan simultáneamente
- [ ] Tests de integración pasan al 100%
- [ ] Performance es aceptable con múltiples usuarios
- [ ] Documentación está completa

---

## 🔧 Comandos de Emergencia por Fase

### **Si falla Fase 1 (BD):**
```bash
# Rollback completo
psql -h localhost -p 5434 -U postgres -d postgres -c "DROP TABLE IF EXISTS historiales_medicos, citas_medicas, pacientes, doctores, disponibilidad_medica CASCADE;"

# Volver a ejecutar migración
psql -h localhost -p 5434 -U postgres -d postgres -f sql/migrate_medical_system.sql
```

### **Si falla Fase 2 (Herramientas):**
```python
# Verificar imports
from src.medical.tools import crear_paciente_medico
print("✅ Tools importan correctamente")

# Test manual herramientas
python -c "from src.medical.tools import *; print('✅ Medical tools loaded')"
```

### **Si falla Fase 3 (Nodos):**
```python
# Verificar nodos cargan
from src.nodes.filtrado_inteligente_node import clasificar_solicitud
print("✅ Nodes cargan correctamente")

# Test clasificación
test_msg = "el paciente Juan necesita cita"
resultado = clasificar_solicitud(test_msg, {"tipo_usuario": "doctor"})
print(f"Clasificación: {resultado}")  # Debe ser "medica"
```

### **Si falla Fase 4 (Sync):**
```python
# Modo degradado sin Google Calendar
# Sistema médico funciona independiente
# Solo comentar líneas de sincronización
```

### **Si falla Fase 5 (Avanzadas):**
```python
# Sistema básico funciona con primeras 6 herramientas
# Herramientas avanzadas son opcional
```

---

## 📝 Checklist de Completitud por Fase

### **FASE 1: ¿Está completa?**
- [ ] Script SQL ejecuta sin errores
- [ ] 5 tablas médicas existen en BD  
- [ ] Foreign keys están bien configuradas
- [ ] Sistema original sigue funcionando
- [ ] No hay warnings de migración

### **FASE 2: ¿Está completa?**
- [ ] 6 herramientas médicas están registradas
- [ ] Puedo crear un paciente de prueba
- [ ] Puedo agendar una cita de prueba
- [ ] Tests unitarios pasan
- [ ] No hay imports rotos

### **FASE 3: ¿Está completa?**
- [ ] Node 2 clasifica mensajes correctamente
- [ ] Node 3B recupera contexto médico
- [ ] Node 5B ejecuta herramientas médicas
- [ ] Flujo personal sigue igual
- [ ] Flujo médico funciona independiente

### **FASE 4: ¿Está completa?**
- [ ] Node 8 sincroniza BD → Google Calendar
- [ ] Manejo de errores funciona
- [ ] Sistema médico independiente de Google
- [ ] No hay citas duplicadas
- [ ] Logs de sincronización claros

### **FASE 5: ¿Está completa?**
- [ ] 12 herramientas médicas totales
- [ ] Reportes se generan correctamente
- [ ] Historiales médicos funcionan
- [ ] Analytics muestran datos reales
- [ ] Performance es aceptable

### **FASE 6: ¿Está completa?**
- [ ] Tests de integración pasan
- [ ] Documentación está lista
- [ ] Sistema maneja múltiples usuarios
- [ ] Listo para producción
- [ ] Plan de deployment documentado

---

## 🚨 Puntos Críticos de Interrupción

**Si el proceso se interrumpe, otro agente puede retomar desde cualquiera de estos puntos:**

1. **Después de Fase 1**: Sistema tiene BD médica pero sin herramientas
2. **Después de Fase 2**: Herramientas médicas básicas funcionan
3. **Después de Fase 3**: Sistema híbrido inteligente funcional
4. **Después de Fase 4**: Sincronización completa con Google Calendar
5. **Después de Fase 5**: Sistema médico completo
6. **Después de Fase 6**: Listo para producción

**Cada punto de interrupción mantiene el sistema funcional en el estado anterior.**

---

## 📋 Estado del Proyecto - Template para Handoff

**Última actualización:** [FECHA]
**Agente anterior:** [NOMBRE]
**Fase actual:** [NÚMERO Y NOMBRE]
**% Completitud:** [PORCENTAJE]

**Último comando ejecutado:**
```bash
[COMANDO]
```

**Estado de BD:**
- [ ] Migración completada
- [ ] Tablas médicas creadas  
- [ ] Foreign keys funcionando
- [ ] Sistema original intacto

**Archivos modificados en esta sesión:**
- [archivo1] - [descripción]
- [archivo2] - [descripción]

**Próximo paso recomendado:**
[DESCRIPCIÓN DEL SIGUIENTE PASO]

**Problemas conocidos:**
- [problema1] - [estado]
- [problema2] - [estado]

**Tests que fallan:**
- [test1] - [razón]

**Notas para el siguiente agente:**
[INFORMACIÓN CRÍTICA QUE DEBE SABER EL SIGUIENTE AGENTE]