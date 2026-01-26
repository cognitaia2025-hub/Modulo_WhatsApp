-- Script SQL: Configuración de Base de Datos para Memoria Procedimental
-- Tabla: herramientas_disponibles
-- Propósito: Registro de herramientas de Google Calendar con descripciones

-- Crear tabla si no existe
CREATE TABLE IF NOT EXISTS herramientas_disponibles (
    id SERIAL PRIMARY KEY,
    id_tool VARCHAR(100) UNIQUE NOT NULL,
    description TEXT NOT NULL,
    activa BOOLEAN DEFAULT TRUE,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Crear índice para búsqueda rápida
CREATE INDEX IF NOT EXISTS idx_herramientas_activas 
ON herramientas_disponibles(activa) 
WHERE activa = TRUE;

-- Insertar herramientas de Google Calendar
-- (Si ya existen, actualizarlas)
INSERT INTO herramientas_disponibles (id_tool, description, activa, metadata)
VALUES
    ('create_calendar_event', 
     'Crear nuevos eventos con título, fecha y hora.', 
     TRUE,
     '{"category": "creation", "requires_params": ["title", "start_time"]}'::jsonb
    ),
    ('list_calendar_events', 
     'Listar eventos para ver la agenda en un rango de fechas.', 
     TRUE,
     '{"category": "query", "requires_params": ["date_range"]}'::jsonb
    ),
    ('update_calendar_event', 
     'Modificar la hora, título o detalles de un evento existente.', 
     TRUE,
     '{"category": "modification", "requires_params": ["event_id", "changes"]}'::jsonb
    ),
    ('delete_calendar_event', 
     'Eliminar un evento específico del calendario.', 
     TRUE,
     '{"category": "deletion", "requires_params": ["event_id"]}'::jsonb
    ),
    ('search_calendar_events', 
     'Buscar eventos por palabras clave en el título o descripción.', 
     TRUE,
     '{"category": "query", "requires_params": ["keyword"]}'::jsonb
    )
ON CONFLICT (id_tool) 
DO UPDATE SET
    description = EXCLUDED.description,
    activa = EXCLUDED.activa,
    metadata = EXCLUDED.metadata,
    updated_at = NOW();

-- Verificar inserción
SELECT id_tool, description, activa 
FROM herramientas_disponibles 
ORDER BY id_tool;

-- Comentarios:
-- 1. La tabla usa JSONB para metadata flexible
-- 2. El campo 'activa' permite deshabilitar herramientas sin borrarlas
-- 3. El índice optimiza consultas de herramientas activas
-- 4. ON CONFLICT permite ejecutar el script múltiples veces sin errores
