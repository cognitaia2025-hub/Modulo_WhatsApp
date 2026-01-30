# 🤖 Sistema de Agendamiento Médico con WhatsApp y Google Calendar

## 🎯 Descripción General

Sistema inteligente de agendamiento de citas médicas mediante WhatsApp con:
- 🧠 **LangGraph** para orquestación de nodos inteligentes
- 🗄️ **PostgreSQL + pgvector** para memoria semántica (embeddings 384D)
- 🤖 **DeepSeek-Chat + Claude** para procesamiento de lenguaje natural
- 📅 **Google Calendar API** para gestión de citas
- 📱 **WhatsApp Business API** para comunicación con pacientes

**Versión:** 1.0  
**Última actualización:** 30 Enero 2026  
**Estado:** ✅ Producción

---

## ⚡ INICIO RÁPIDO (5 minutos)

### 1️⃣ Inicializar Base de Datos

```bash
cd sql
python init_database_consolidated.py --drop-existing
```

### 2️⃣ Iniciar Servicios

```bash
# PostgreSQL + pgvector
docker-compose up -d postgres

# Backend FastAPI
python app.py
```

### 3️⃣ Verificar Funcionamiento

```bash
curl http://localhost:8000/health
# Debería responder: {"status": "healthy"}
```

---

## 📚 DOCUMENTACIÓN

### 🌟 Para Empezar

| Documento | Audiencia | Tiempo | Descripción |
|-----------|-----------|--------|-------------|
| [docs/README.md](docs/README.md) | Todos | 10 min | **Índice principal** con navegación completa |
| [docs/NODOS_GUIA_NO_TECNICA.md](docs/NODOS_GUIA_NO_TECNICA.md) | No técnicos | 30 min | Explicación simple del sistema |
| [docs/NODOS_DOCUMENTACION_TECNICA.md](docs/NODOS_DOCUMENTACION_TECNICA.md) | Desarrolladores | 1 hora | Especificaciones técnicas completas |

### 📖 Documentación Adicional

- [PLAN_ESTRUCTURADO_IMPLEMENTACION.md](docs/PLAN_ESTRUCTURADO_IMPLEMENTACION.md) - Plan de desarrollo completo (Etapas 0-8)
- [CONSOLIDACION_ESQUEMA_BD.md](docs/CONSOLIDACION_ESQUEMA_BD.md) - Esquema de base de datos consolidado
- [LIMPIEZA_PROYECTO_RESUMEN.md](LIMPIEZA_PROYECTO_RESUMEN.md) - Resumen de reorganización del proyecto
- [sql/README.md](sql/README.md) - Guía completa de base de datos

---

## 🏗️ ARQUITECTURA DEL SISTEMA

### Flujo de Mensajes (10 Nodos LangGraph)

```
WhatsApp → [N0: Identificación] → [N1: Caché] → [N2: Clasificación LLM]
              ↓                      ↓              ↓
         (Registro)            (24h window)    (Personal/Médico)
              ↓                      ↓              ↓
    [N3A/B: Recuperación Context] ← (pgvector 384D)
              ↓
    [N4: Selección Herramientas LLM]
              ↓
    [N5A/B: Ejecución Personal/Médica] → Google Calendar API
              ↓
    [N6R: Recepcionista LLM] (solo médico)
              ↓
    [N6: Generación Respuesta LLM]
              ↓
    [N7: Memoria Largo Plazo] → (pgvector + PostgreSQL)
              ↓
    [N8: Sincronización Google] → Google Calendar
```

### Stack Tecnológico

| Componente | Tecnología | Versión |
|------------|------------|---------|
| **Backend** | FastAPI | 0.104+ |
| **Orquestación** | LangGraph | 0.2.20+ |
| **LLM Principal** | DeepSeek-Chat | Latest |
| **LLM Fallback** | Claude 3.5 Sonnet | Latest |
| **Base de Datos** | PostgreSQL + pgvector | 14+ |
| **Embeddings** | sentence-transformers | 384D |
| **Calendar** | Google Calendar API | v3 |
| **Mensajería** | WhatsApp Business API | Latest |
| **Testing** | pytest | 7.0+ |
| **Containerization** | Docker | 20+ |

---

## 🗄️ ESQUEMA DE BASE DE DATOS

### Tablas Principales (15 tablas)

**Sistema de Usuarios:**
- `usuarios` - Usuarios del sistema (admin, doctores, pacientes)
- `doctores` - Información de médicos (especialidad, licencia)
- `pacientes` - Información de pacientes (edad, sexo, contacto)

**Agendamiento:**
- `disponibilidad_medica` - Horarios disponibles de doctores
- `control_turnos` - Turnos actuales de cada doctor
- `citas_medicas` - Citas agendadas (completa Etapas 2-6)

**Memoria y Contexto:**
- `session_cache` - Caché de sesiones activas (rolling window 24h)
- `memorias_episodicas` - Memoria a largo plazo con embeddings
- `historiales_medicos` - Historiales clínicos de pacientes
- `clasificaciones_llm` - Log de clasificaciones de intenciones

**Sincronización:**
- `sincronizacion_calendar` - Mapeo entre eventos internos y Google Calendar
- `sincronizacion_whatsapp` - Log de mensajes WhatsApp

**Métricas y Reportes:**
- `metricas_consultas` - Métricas de rendimiento del sistema
- `reportes_generados` - Reportes generados por el sistema

**Herramientas:**
- `herramientas` - Definición de herramientas disponibles (24 tools)

### Funciones y Vistas (8 funciones, 5 vistas)

Ver [sql/README.md](sql/README.md) para detalles completos.

---

## 🚀 INSTALACIÓN COMPLETA

### Prerequisitos

```bash
# Python 3.11+
python --version

# Docker y Docker Compose
docker --version
docker-compose --version
```

### 1. Clonar Repositorio

```bash
git clone https://github.com/cognitaia2025-hub/Modulo_WhatsApp.git
cd Modulo_WhatsApp
```

### 2. Configurar Entorno

```bash
# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

### 3. Configurar Variables de Entorno

```bash
cp .env.example .env
nano .env  # Editar con tus credenciales
```

**Variables requeridas:**
```env
# LLMs
DEEPSEEK_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Base de Datos
DATABASE_URL=postgresql://user:pass@localhost:5432/whatsapp_calendar

# Google Calendar
GOOGLE_CALENDAR_CREDENTIALS=path/to/credentials.json
GOOGLE_CALENDAR_TOKEN=path/to/token.json

# WhatsApp (opcional para desarrollo)
WHATSAPP_API_KEY=...
WHATSAPP_PHONE_NUMBER_ID=...
```

### 4. Inicializar Base de Datos

```bash
cd sql
python init_database_consolidated.py --drop-existing
# Opciones:
#   --drop-existing  : Borra BD existente
#   --skip-seed     : No carga datos iniciales
```

### 5. Verificar Instalación

```bash
# Iniciar servicios
docker-compose up -d postgres
python app.py

# En otra terminal: verificar health
curl http://localhost:8000/health
```

---

## 🧪 TESTS

### Ejecutar Tests

```bash
# Todos los tests de integración
python integration_tests/run_all_tests.py

# Tests por etapa
python -m pytest tests/Etapa_1/
python -m pytest tests/Etapa_2/
# ... hasta Etapa_8/

# Test específico
python integration_tests/14_test_memoria_persistente.py
```

### Tests Disponibles

| Carpeta | Tests | Descripción |
|---------|-------|-------------|
| `tests/Etapa_1/` | 63 | Identificación y registro de usuarios |
| `tests/Etapa_2/` | 45 | Agendamiento básico y disponibilidad |
| `tests/Etapa_3/` | 38 | Clasificación y recuperación de contexto |
| `integration_tests/` | 14 | Tests end-to-end críticos |

---

## 📁 ESTRUCTURA DEL PROYECTO

```
Modulo_WhatsApp/
├── 📄 README.md                    ← Este archivo
├── 📄 LIMPIEZA_PROYECTO_RESUMEN.md ← Resumen de reorganización
├── 🐳 docker-compose.yaml
├── 🐳 Dockerfile
├── 📦 requirements.txt
├── ⚙️ app.py                       ← FastAPI backend
│
├── 📚 docs/                        ← Documentación principal
│   ├── README.md                   ← Índice de documentación
│   ├── PLAN_ESTRUCTURADO_...md    ← Arquitectura completa
│   ├── NODOS_GUIA_NO_TECNICA.md   ← Para no técnicos
│   ├── NODOS_DOCUMENTACION_...md  ← Para desarrolladores
│   ├── CONSOLIDACION_ESQUEMA_BD.md
│   └── archive_old/               ← Docs obsoletos (37 archivos)
│
├── 💾 sql/                         ← Scripts de base de datos
│   ├── README.md                   ← Guía de SQL
│   ├── init_database.sql          ← Esquema completo (15 tablas)
│   ├── seed_initial_data.sql      ← Datos iniciales
│   ├── setup_herramientas.sql     ← Definición de tools
│   └── init_database_consolidated.py  ← Script de inicialización
│
├── 💻 src/                         ← Código fuente
│   ├── graph.py                   ← LangGraph principal
│   ├── nodes/                     ← 10 nodos del sistema
│   │   ├── identificacion_node.py    (N0)
│   │   ├── cache_node.py             (N1)
│   │   ├── clasificacion_node.py     (N2)
│   │   ├── recuperacion_node.py      (N3A/B)
│   │   ├── seleccion_node.py         (N4)
│   │   ├── ejecucion_node.py         (N5A/B)
│   │   ├── recepcionista_node.py     (N6R)
│   │   ├── generacion_node.py        (N6)
│   │   ├── memoria_node.py           (N7)
│   │   └── sincronizacion_node.py    (N8)
│   ├── medical/                   ← Sistema médico (6 herramientas)
│   ├── personal/                  ← Sistema personal (6 herramientas)
│   ├── system/                    ← Sistema general (6 herramientas)
│   ├── state/                     ← WhatsAppAgentState
│   └── memory/                    ← Gestión de memoria
│
├── 🧪 tests/                       ← Tests unitarios (por etapa)
│   ├── Etapa_1/                   ← 63 tests
│   ├── Etapa_2/                   ← 45 tests
│   ├── ...
│   ├── Etapa_8/
│   └── migrations_deprecated/     ← Migraciones obsoletas (7 archivos)
│
├── 🧪 integration_tests/           ← Tests de integración (14)
│
├── 📱 whatsapp-service/           ← Servicio WhatsApp
│
└── 📦 archive_root_docs/          ← Docs raíz obsoletos (5 archivos)
```

---

## 🎯 ESTADO DEL PROYECTO

### ✅ Implementado (Etapas 0-8)

- [x] **Etapa 0:** Arquitectura base y setup inicial
- [x] **Etapa 1:** Identificación y registro de usuarios
- [x] **Etapa 2:** Agendamiento básico y disponibilidad
- [x] **Etapa 3:** Clasificación y recuperación de contexto
- [x] **Etapa 4:** Selección inteligente de herramientas
- [x] **Etapa 5:** Integración Google Calendar
- [x] **Etapa 6:** Recepcionista virtual inteligente
- [x] **Etapa 7:** Métricas y reportes
- [x] **Etapa 8:** Sistema de sincronización completo

### 📊 Métricas del Sistema

| Métrica | Valor | Estado |
|---------|-------|--------|
| **Nodos Totales** | 10 | ✅ Implementados |
| **Herramientas** | 24 (6+12+6) | ✅ Funcionando |
| **Tablas BD** | 15 | ✅ Consolidadas |
| **Funciones SQL** | 8 | ✅ Optimizadas |
| **Tests** | 200+ | ✅ Pasando |
| **Cobertura** | 85%+ | ✅ Alto |

### 📈 Rendimiento

| Operación | Tiempo | Optimización |
|-----------|--------|--------------|
| Identificación (N0) | 50-100ms | Redis cache |
| Clasificación (N2) | 800-1200ms | DeepSeek optimizado |
| Recuperación (N3) | 600-1000ms | pgvector índices |
| Ejecución (N5) | 200-2000ms | Async operations |
| Generación (N6) | 700-1100ms | Prompt engineering |

---

## 🔧 CONFIGURACIÓN AVANZADA

### Configurar Doctores

```sql
-- Ver doctors disponibles
SELECT * FROM doctores;

-- Agregar horarios de disponibilidad
INSERT INTO disponibilidad_medica (doctor_id, dia_semana, hora_inicio, hora_fin)
VALUES (1, 'Monday', '09:00', '17:00');
```

Ver [docs/CONFIGURACION_DOCTORES.md](docs/archive_old/CONFIGURACION_DOCTORES.md) para más detalles.

### Configurar Herramientas

```bash
cd sql
psql -d whatsapp_calendar -f setup_herramientas.sql
```

### Logs y Monitoreo

```bash
# Ver logs del backend
tail -f logs/backend.log

# Métricas del sistema
psql -d whatsapp_calendar -c "SELECT * FROM metricas_consultas ORDER BY fecha DESC LIMIT 10;"
```

---

## 🐛 TROUBLESHOOTING

### Error: Base de datos no existe

```bash
cd sql
python init_database_consolidated.py --drop-existing
```

### Error: pgvector no instalado

```bash
docker-compose down
docker-compose up -d postgres
# Esperar 30 segundos para que se instale pgvector
```

### Error: Google Calendar API

1. Verificar que `credentials.json` esté en la raíz
2. Eliminar `token.json` y volver a autorizar
3. Verificar permisos del service account

### Error: LLM no responde

1. Verificar API keys en `.env`
2. Revisar cuotas de API
3. El sistema automáticamente usa Claude como fallback

---

## 📞 SOPORTE Y CONTRIBUCIÓN

### Documentación

- **Problemas técnicos:** Ver [docs/NODOS_DOCUMENTACION_TECNICA.md](docs/NODOS_DOCUMENTACION_TECNICA.md)
- **Preguntas generales:** Ver [docs/README.md](docs/README.md) (FAQ)
- **Arquitectura:** Ver [docs/PLAN_ESTRUCTURADO_IMPLEMENTACION.md](docs/PLAN_ESTRUCTURADO_IMPLEMENTACION.md)

### Contribuir

1. Fork el repositorio
2. Crear rama: `git checkout -b feature/nueva-funcionalidad`
3. Commit: `git commit -m 'Agregar nueva funcionalidad'`
4. Push: `git push origin feature/nueva-funcionalidad`
5. Abrir Pull Request

### Testing

Antes de hacer PR, ejecutar:
```bash
python integration_tests/run_all_tests.py
python -m pytest tests/
```

---

## 📜 LICENCIA

MIT License - Ver [LICENSE](LICENSE) para detalles.

---

## 🏆 CRÉDITOS

**Desarrollado por:** CognitAI 2025  
**Repositorio:** [cognitaia2025-hub/Modulo_WhatsApp](https://github.com/cognitaia2025-hub/Modulo_WhatsApp)  
**Última actualización:** 30 Enero 2026

---

**Para más información, consulta [docs/README.md](docs/README.md)**
