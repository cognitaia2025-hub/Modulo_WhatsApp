# 📚 Documentación del Sistema WhatsApp Agent

> **Sistema Híbrido de Calendario Personal + Gestión Médica**  
> Versión 2.0 - Esquema Consolidado

---

## 📋 Índice de Documentos

### 📖 Documentos Principales

| Documento | Descripción | Para Quién |
|-----------|-------------|------------|
| **[PLAN_ESTRUCTURADO_IMPLEMENTACION.md](PLAN_ESTRUCTURADO_IMPLEMENTACION.md)** | Plan maestro de implementación del sistema completo | Todos |
| **[CONSOLIDACION_ESQUEMA_BD.md](CONSOLIDACION_ESQUEMA_BD.md)** | Resumen de consolidación de esquema de base de datos | DevOps, DBAs |
| **[NODOS_GUIA_NO_TECNICA.md](NODOS_GUIA_NO_TECNICA.md)** | Guía de nodos en lenguaje simple | No técnicos, stakeholders |
| **[NODOS_DOCUMENTACION_TECNICA.md](NODOS_DOCUMENTACION_TECNICA.md)** | Especificaciones técnicas de cada nodo | Desarrolladores |

---

## 🎯 Guía Rápida por Rol

### 👨‍💼 Para Gerentes y Stakeholders

**Leer primero:**
1. [NODOS_GUIA_NO_TECNICA.md](NODOS_GUIA_NO_TECNICA.md) - Entender cómo funciona el sistema
2. [PLAN_ESTRUCTURADO_IMPLEMENTACION.md](PLAN_ESTRUCTURADO_IMPLEMENTACION.md) - Ver roadmap y estado

**¿Qué hace el sistema?**
- Asistente de WhatsApp inteligente
- Gestiona calendario personal y citas médicas
- Atiende tanto a doctores como a pacientes
- Sincroniza automáticamente con Google Calendar

### 👨‍💻 Para Desarrolladores

**Leer primero:**
1. [PLAN_ESTRUCTURADO_IMPLEMENTACION.md](PLAN_ESTRUCTURADO_IMPLEMENTACION.md) - Arquitectura general
2. [NODOS_DOCUMENTACION_TECNICA.md](NODOS_DOCUMENTACION_TECNICA.md) - Detalles de implementación
3. [CONSOLIDACION_ESQUEMA_BD.md](CONSOLIDACION_ESQUEMA_BD.md) - Esquema de base de datos

**Stack Técnico:**
- **Framework:** LangGraph + StateGraph
- **LLM:** DeepSeek-Chat (primario), Claude Sonnet 4.5 (fallback)
- **Base de Datos:** PostgreSQL 14+ con pgvector
- **APIs:** Google Calendar, WhatsApp Business
- **Lenguaje:** Python 3.11+

### 🗄️ Para DBAs y DevOps

**Leer primero:**
1. [CONSOLIDACION_ESQUEMA_BD.md](CONSOLIDACION_ESQUEMA_BD.md) - Esquema consolidado
2. `../sql/README.md` - Guía de inicialización de BD
3. [PLAN_ESTRUCTURADO_IMPLEMENTACION.md](PLAN_ESTRUCTURADO_IMPLEMENTACION.md) - Requisitos de infraestructura

**Scripts SQL:**
- `sql/init_database.sql` - Esquema completo consolidado
- `sql/init_database_consolidated.py` - Inicialización automatizada
- `sql/seed_initial_data.sql` - Datos iniciales

---

## 🗂️ Estructura del Proyecto

```
Modulo_WhatsApp/
├── docs/
│   ├── README.md (este archivo)
│   ├── PLAN_ESTRUCTURADO_IMPLEMENTACION.md
│   ├── CONSOLIDACION_ESQUEMA_BD.md
│   ├── NODOS_GUIA_NO_TECNICA.md
│   ├── NODOS_DOCUMENTACION_TECNICA.md
│   └── archive_old/ (documentación obsoleta)
│
├── sql/
│   ├── README.md
│   ├── init_database.sql (⭐ Principal)
│   ├── init_database_consolidated.py
│   ├── seed_initial_data.sql
│   └── ...
│
├── src/
│   ├── nodes/ (10 nodos del grafo)
│   ├── medical/ (herramientas médicas)
│   ├── state/ (definición del estado)
│   ├── config/ (configuración)
│   └── graph_whatsapp.py (compilación del grafo)
│
├── tests/
│   ├── Etapa_1/ (tests de identificación)
│   ├── Etapa_2/ (tests de turnos)
│   ├── Etapa_3/ (tests de clasificación)
│   └── migrations_deprecated/ (migraciones obsoletas)
│
└── whatsapp-service/ (servidor Node.js)
```

---

## 🚀 Quick Start

### Para Desarrolladores Nuevos

1. **Leer documentación básica** (30 min)
   ```bash
   # Leer en orden:
   1. docs/NODOS_GUIA_NO_TECNICA.md
   2. docs/PLAN_ESTRUCTURADO_IMPLEMENTACION.md (secciones 0-2)
   3. sql/README.md
   ```

2. **Configurar ambiente** (20 min)
   ```bash
   # Clonar repo
   git clone https://github.com/cognitaia2025-hub/Modulo_WhatsApp.git
   cd Modulo_WhatsApp
   
   # Instalar dependencias
   pip install -r requirements.txt
   
   # Configurar .env
   cp .env.example .env
   # Editar .env con tus credenciales
   ```

3. **Inicializar base de datos** (10 min)
   ```bash
   # Opción 1: Script Python automático
   python sql/init_database_consolidated.py
   
   # Opción 2: Manual
   psql -h localhost -p 5434 -U postgres -d agente_whatsapp -f sql/init_database.sql
   # ... ejecutar otros SQL en orden (ver sql/README.md)
   ```

4. **Ejecutar tests** (15 min)
   ```bash
   # Tests de identificación
   pytest tests/Etapa_1/
   
   # Tests de turnos
   pytest tests/Etapa_2/
   ```

5. **Iniciar sistema** (5 min)
   ```bash
   # Backend
   python app.py
   
   # WhatsApp service (otra terminal)
   cd whatsapp-service
   npm start
   ```

---

## 📊 Estado Actual del Proyecto

### ✅ Completado (Etapas 0-7)

- ✅ **Etapa 0:** Seguridad y configuración
- ✅ **Etapa 1:** Identificación de usuarios
- ✅ **Etapa 2:** Sistema de turnos automático
- ✅ **Etapa 3:** Clasificación inteligente con LLM
- ✅ **Etapa 5:** Sincronización Google Calendar
- ✅ **Etapa 6:** Recordatorios automáticos
- ✅ **Etapa 7:** Herramientas médicas avanzadas

### 🔄 En Progreso

- **Etapa 4:** Flujo de recepcionista conversacional (90%)
- **Etapa 8:** Integración completa del grafo (95%)

### 📈 Métricas del Sistema

- **Nodos Implementados:** 10/12 (83%)
- **Herramientas Disponibles:** 18/24 (75%)
- **Tablas de BD:** 15/15 (100%)
- **Tests Pasando:** 45/52 (87%)

---

## 🔑 Conceptos Clave

### 🤖 Nodos

**Definición:** Componentes del grafo que procesan el estado paso a paso.

**Tipos:**
- **Automatizados (7):** Sin LLM, lógica determinística
- **Inteligentes (5):** Con LLM, procesamiento de lenguaje natural

### 📊 Estado (State)

**Definición:** Diccionario que viaja entre nodos con toda la información.

**Componentes Principales:**
- `messages`: Historial de mensajes
- `user_id`: Identificador del usuario
- `tipo_usuario`: doctor/paciente/personal/admin
- `clasificacion`: personal/medica/chat
- `herramientas_seleccionadas`: Acciones a ejecutar
- `resultados_ejecucion`: Resultados de las acciones

### 🛠️ Herramientas (Tools)

**Definición:** Funciones que el sistema puede ejecutar.

**Categorías:**
- **Calendario Personal (6):** list, create, update, delete, search, postpone
- **Médicas Básicas (6):** crear paciente, buscar, slots, agendar, modificar, cancelar
- **Médicas Avanzadas (6):** registrar consulta, historial, disponibilidad, reportes

### 🔄 Flujo del Sistema

```
Mensaje WhatsApp
    ↓
1. Identificación → ¿Quién es?
2. Caché → ¿Conversación previa?
3. Clasificación (LLM) → ¿Qué tipo de solicitud?
4. Recuperación → ¿Qué contexto hay?
5. Selección (LLM) → ¿Qué herramientas usar?
6. Ejecución → Ejecutar acciones
7. Sincronización → Actualizar Google Calendar
8. Respuesta (LLM) → Crear mensaje final
9. Persistencia → Guardar para el futuro
    ↓
Respuesta WhatsApp
```

---

## 🔍 Preguntas Frecuentes

### ¿Por qué consolidar el esquema de BD?

Antes teníamos 12+ migraciones separadas. Ahora todo está en un solo archivo SQL. Beneficios:
- ✅ Más fácil de mantener
- ✅ Más rápido de configurar nuevos ambientes
- ✅ Menos propenso a errores
- ✅ Documentación más clara

### ¿Qué pasó con las migraciones antiguas?

Están archivadas en `tests/migrations_deprecated/`. Ya NO se deben usar. Todo está consolidado en `sql/init_database.sql`.

### ¿Cómo funciona el sistema de turnos?

El sistema alterna automáticamente entre doctores disponibles:
1. Primera cita → Dr. Santiago
2. Segunda cita → Dra. Joana
3. Tercera cita → Dr. Santiago
4. ...y así sucesivamente

Esto asegura distribución equitativa de pacientes.

### ¿Qué pasa si un nodo falla?

- **Nodos con LLM:** Tienen fallback a modelo alternativo (Claude si DeepSeek falla)
- **Nodos de BD:** Reintentan hasta 3 veces con backoff
- **Sincronización Google:** Sistema de reintentos automáticos hasta 5 veces

### ¿Dónde están los tests?

```
tests/
├── Etapa_1/ - Identificación y tipos de usuario
├── Etapa_2/ - Turnos y disponibilidad
├── Etapa_3/ - Clasificación y herramientas
├── Etapa_6/ - Recordatorios
├── Etapa_7/ - Herramientas avanzadas
└── Etapa_8/ - Integración completa
```

---

## 🛠️ Herramientas de Desarrollo

### Inicialización de BD

```bash
# Ver guía completa
cat sql/README.md

# Inicialización rápida
python sql/init_database_consolidated.py

# Con opciones
python sql/init_database_consolidated.py --drop-existing
python sql/init_database_consolidated.py --skip-seed
```

### Tests

```bash
# Todos los tests
pytest tests/

# Tests de una etapa específica
pytest tests/Etapa_2/

# Tests con verbose
pytest tests/Etapa_3/ -v

# Tests con coverage
pytest tests/ --cov=src --cov-report=html
```

### Logs y Debugging

```bash
# Ver logs en tiempo real
tail -f logs/backend.log

# Buscar errores
grep ERROR logs/backend.log

# Ver queries SQL
export DEBUG_SQL=1
python app.py
```

---

## 📞 Contacto y Soporte

### Documentación Adicional

- **Código fuente:** https://github.com/cognitaia2025-hub/Modulo_WhatsApp
- **Base de datos:** Ver `sql/README.md`
- **API Reference:** Ver `docs/NODOS_DOCUMENTACION_TECNICA.md`

### Reportar Issues

1. Verificar que no esté duplicado
2. Incluir logs relevantes
3. Describir pasos para reproducir
4. Especificar versiones (Python, PostgreSQL, etc.)

---

## 📝 Notas de Versión

### v2.0 (30 Enero 2026) - Consolidación

- ✅ Esquema de BD consolidado
- ✅ Documentación reorganizada
- ✅ Tests de migraciones archivados
- ✅ Guías para usuarios no técnicos
- ✅ Especificaciones técnicas detalladas

### v1.0 (27 Enero 2026) - Release Inicial

- ✅ Sistema base funcionando
- ✅ Integración con WhatsApp
- ✅ Calendario personal completo
- ✅ Sistema médico básico

---

## 📚 Recursos de Aprendizaje

### Para Entender el Sistema

1. **Principiantes:** [NODOS_GUIA_NO_TECNICA.md](NODOS_GUIA_NO_TECNICA.md)
2. **Intermedios:** [PLAN_ESTRUCTURADO_IMPLEMENTACION.md](PLAN_ESTRUCTURADO_IMPLEMENTACION.md)
3. **Avanzados:** [NODOS_DOCUMENTACION_TECNICA.md](NODOS_DOCUMENTACION_TECNICA.md)

### Tecnologías Clave

- **LangGraph:** https://langchain-ai.github.io/langgraph/
- **DeepSeek:** https://platform.deepseek.com/docs
- **PostgreSQL + pgvector:** https://github.com/pgvector/pgvector
- **WhatsApp Business API:** https://developers.facebook.com/docs/whatsapp

---

**Última actualización:** 30 de Enero de 2026  
**Mantenido por:** Equipo CognitAI  
**Versión del sistema:** 2.0
