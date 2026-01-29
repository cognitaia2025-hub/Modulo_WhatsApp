# Tests de ETAPA 1: Sistema de Identificación de Usuarios

## 📋 Descripción General

Esta carpeta contiene los tests de la **ETAPA 1** del sistema de calendario médico, que implementa el sistema de identificación automática de usuarios por número de teléfono.

## 🎯 Objetivo de la Etapa

Implementar un sistema que identifica automáticamente quién habla por WhatsApp (doctor, paciente, admin o usuario personal) basándose únicamente en el número de teléfono, sin requerir login tradicional.

## 📁 Archivos de Test

### 1. `test_identificacion_node.py` (15 tests)
Pruebas del nodo principal de identificación.

**Validaciones:**
- ✅ Extracción de número de teléfono desde metadata
- ✅ Extracción con código de país faltante
- ✅ Fallback a contenido del mensaje
- ✅ Creación de usuario nuevo como `paciente_externo`
- ✅ Detección de administrador por número configurado
- ✅ Consulta de usuario existente
- ✅ Actualización de `last_seen`
- ✅ Identificación completa con todos los campos
- ✅ Doctor obtiene su `doctor_id`
- ✅ Manejo de errores sin crashear

### 2. `test_user_registration.py` (15 tests)
Pruebas del sistema de auto-registro.

**Validaciones:**
- ✅ Auto-registro crea tipo `paciente_externo`
- ✅ Campos obligatorios se llenan correctamente
- ✅ Display name por defecto: "Usuario Nuevo"
- ✅ Timezone por defecto: "America/Tijuana"
- ✅ Preferencias incluyen flags de primer uso
- ✅ No duplica usuarios existentes
- ✅ Actualiza `last_seen` automáticamente
- ✅ Constraint UNIQUE en `phone_number`
- ✅ Timestamp `created_at` automático
- ✅ `is_active` por defecto TRUE

### 3. `test_user_types.py` (15 tests)
Pruebas de diferenciación de tipos de usuario.

**Validaciones:**
- ✅ Admin se identifica correctamente
- ✅ Doctor tiene `doctor_id` poblado
- ✅ Doctor tiene especialidad
- ✅ Paciente NO tiene `doctor_id`
- ✅ Diferenciación clara entre tipos
- ✅ Usuario `personal` tiene tipo correcto
- ✅ Solo tipos válidos permitidos
- ✅ Estado contiene `tipo_usuario`

### 4. `test_integration_identificacion.py` (18 tests)
Pruebas de integración del nodo en el grafo.

**Validaciones:**
- ✅ Nodo retorna estado actualizado
- ✅ `user_id` se actualiza con phone_number
- ✅ `usuario_info` se llena con datos de BD
- ✅ Flujo continúa después de identificación
- ✅ Nodo NO modifica campos de otros nodos
- ✅ Múltiples llamadas son consistentes
- ✅ Manejo graceful de errores de BD
- ✅ Wrapper maneja excepciones
- ✅ Maneja mensaje sin metadata
- ✅ Todos los campos del estado presentes
- ✅ Tipos de datos correctos

## 🚀 Ejecución de Tests

### Ejecutar todos los tests de ETAPA 1:
```bash
pytest tests/Etapa_1/ -v
```

### Ejecutar test específico:
```bash
pytest tests/Etapa_1/test_identificacion_node.py -v
pytest tests/Etapa_1/test_user_registration.py -v
pytest tests/Etapa_1/test_user_types.py -v
pytest tests/Etapa_1/test_integration_identificacion.py -v
```

### Con coverage:
```bash
pytest tests/Etapa_1/ --cov=src.nodes.identificacion_usuario_node --cov-report=html
```

### Solo tests que fallen:
```bash
pytest tests/Etapa_1/ -x  # Detener al primer fallo
pytest tests/Etapa_1/ --lf  # Solo ejecutar últimos fallidos
```

## 📊 Resultado Esperado

```
========================================
tests/Etapa_1/test_identificacion_node.py ............... (15 passed)
tests/Etapa_1/test_user_registration.py ................ (15 passed)
tests/Etapa_1/test_user_types.py ...................... (15 passed)
tests/Etapa_1/test_integration_identificacion.py ...... (18 passed)
========================================
63 passed in X.XXs
```

## 🔧 Configuración Necesaria

### Variables de Entorno (.env):
```env
DATABASE_URL=postgresql://user:pass@localhost:5434/agente_whatsapp
ADMIN_PHONE_NUMBER=+526641234567
```

### Base de Datos:
Asegurarse de que las siguientes tablas existen:
- ✅ `usuarios` (con columnas: `tipo_usuario`, `email`, `is_active`)
- ✅ `doctores` (con columnas: `nombre_completo`, `especialidad`, `orden_turno`)

Ejecutar migración:
```bash
psql -h localhost -p 5434 -U postgres -d agente_whatsapp -f sql/migrate_etapa_1_identificacion.sql
```

## 🐛 Troubleshooting

### Error: "Base de datos no disponible"
```bash
# Verificar que PostgreSQL está corriendo
docker ps | grep postgres

# O iniciar contenedor
docker-compose up -d postgres
```

### Error: "Tabla usuarios no tiene columna tipo_usuario"
```bash
# Ejecutar migración
psql -h localhost -p 5434 -U postgres -d agente_whatsapp -f sql/migrate_etapa_1_identificacion.sql
```

### Tests fallan por datos previos
```bash
# Limpiar datos de prueba (CUIDADO en producción)
psql -h localhost -p 5434 -U postgres -d agente_whatsapp -c "DELETE FROM usuarios WHERE phone_number LIKE '+52664%' AND phone_number != '+526641234567';"
```

## 📚 Referencia

- Ver: `docs/PROMPT_ETAPA_1.md` - Especificación completa
- Ver: `src/nodes/identificacion_usuario_node.py` - Implementación
- Ver: `src/state/agent_state.py` - Definición del estado
- Ver: `sql/migrate_etapa_1_identificacion.sql` - Migración de BD

## ✅ Criterios de Aceptación

Para considerar ETAPA 1 completa:

1. ✅ Todos los tests pasan (63/63)
2. ✅ Nodo identifica usuarios por `phone_number`
3. ✅ Auto-registro funciona para usuarios nuevos
4. ✅ Tabla `usuarios` tiene columnas nuevas
5. ✅ Estado del grafo tiene campos `tipo_usuario`, `doctor_id`, `paciente_id`
6. ✅ No rompe funcionalidad existente

## 🎓 Reglas de Testing

Según `.claude/CLAUDE.md`:

> Si test falla → reparar código, NO modificar tests

Los tests son la especificación. Si fallan, el código está mal, no los tests.
