-- ============================================================================
-- ESQUEMA DE MEMORIA PROCEDIMENTAL: Herramientas Disponibles
-- ============================================================================
-- Propósito: Almacenar las herramientas de Google Calendar disponibles
--            para el agente, con descripción y estado de activación.
-- Usado en: Nodo 4 (Selección de Herramientas)
-- ============================================================================

-- Crear extensión pgvector (para memoria episódica en Nodo 7)
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================================
-- TABLA: herramientas_disponibles
-- ============================================================================

CREATE TABLE IF NOT EXISTS herramientas_disponibles (
    id SERIAL PRIMARY KEY,
    id_tool VARCHAR(100) UNIQUE NOT NULL,         -- Identificador único de la herramienta
    description TEXT NOT NULL,                     -- Descripción para el LLM
    activa BOOLEAN DEFAULT true,                   -- Estado de activación
    categoria VARCHAR(50),                         -- 'calendar', 'notification', etc.
    prioridad INTEGER DEFAULT 0,                   -- Para ordenar en caso de empate
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índice para búsquedas rápidas por estado activo
CREATE INDEX IF NOT EXISTS idx_herramientas_activas 
ON herramientas_disponibles(activa) 
WHERE activa = true;

-- ============================================================================
-- DATOS INICIALES: Herramientas de Google Calendar
-- ============================================================================

-- Limpiar datos existentes (opcional, comentar si quieres preservar)
TRUNCATE TABLE herramientas_disponibles RESTART IDENTITY CASCADE;

-- Insertar herramientas exactas según especificación
INSERT INTO herramientas_disponibles (id_tool, description, activa, categoria, prioridad) VALUES
    (
        'create_calendar_event',
        'Crear nuevos eventos con título, fecha y hora.',
        true,
        'calendar',
        1
    ),
    (
        'list_calendar_events',
        'Listar eventos para ver la agenda en un rango de fechas.',
        true,
        'calendar',
        2
    ),
    (
        'update_calendar_event',
        'Modificar la hora, título o detalles de un evento existente.',
        true,
        'calendar',
        3
    ),
    (
        'delete_calendar_event',
        'Eliminar un evento específico del calendario.',
        true,
        'calendar',
        4
    ),
    (
        'search_calendar_events',
        'Buscar eventos por palabras clave en el título o descripción.',
        true,
        'calendar',
        5
    );

-- ============================================================================
-- FUNCIÓN: Actualizar timestamp automático
-- ============================================================================

CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger para actualizar updated_at automáticamente
CREATE TRIGGER update_herramientas_modtime
BEFORE UPDATE ON herramientas_disponibles
FOR EACH ROW
EXECUTE FUNCTION update_modified_column();

-- ============================================================================
-- VERIFICACIÓN: Mostrar herramientas cargadas
-- ============================================================================

SELECT 
    id_tool,
    description,
    activa,
    categoria,
    prioridad
FROM herramientas_disponibles
ORDER BY prioridad;

-- ============================================================================
-- CONSULTAS DE UTILIDAD
-- ============================================================================

-- Ver solo herramientas activas (usado por el Nodo 4)
-- SELECT id_tool, description FROM herramientas_disponibles WHERE activa = true;

-- Desactivar una herramienta específica
-- UPDATE herramientas_disponibles SET activa = false WHERE id_tool = 'delete_calendar_event';

-- Activar todas las herramientas
-- UPDATE herramientas_disponibles SET activa = true;

-- Agregar nueva herramienta
-- INSERT INTO herramientas_disponibles (id_tool, description, categoria) 
-- VALUES ('send_notification', 'Enviar notificaciones al usuario.', 'notification');

-- ============================================================================
-- NOTAS DE IMPLEMENTACIÓN
-- ============================================================================

/*
1. CACHÉ DE 5 MINUTOS:
   - Implementar en Python con functools.lru_cache o time-based cache
   - Evita consultar la BD en cada mensaje

2. CONEXIÓN SEGURA:
   - Usar psycopg2 o asyncpg
   - Variables de entorno para credenciales (DATABASE_URL)

3. MANEJO DE ERRORES:
   - Si la BD no responde, usar herramientas por defecto: ['list_calendar_events']
   - Log de errores sin detener el flujo del agente

4. EXTENSIBILIDAD:
   - Para agregar nuevas herramientas, solo INSERT en la tabla
   - El LLM las verá automáticamente en la próxima consulta
*/
