-- ============================================================================
-- MIGRACIÓN: Agregar columna tool_name a herramientas_disponibles
-- ============================================================================
-- Propósito: Agregar identificador de texto para herramientas en lugar de usar
--            solo el id_tool numérico, facilitando la selección en el Nodo 4
-- 
-- Cambios:
--   1. Agregar columna tool_name VARCHAR(100)
--   2. Poblar tool_name con valores predefinidos
--   3. Renombrar id_tool → id
--   4. Hacer tool_name NOT NULL y UNIQUE
--
-- RESPETA: descripciones, campo activa, IDs existentes, otros datos
-- ============================================================================

BEGIN;

-- PASO 1: Agregar nueva columna tool_name (nullable temporalmente)
ALTER TABLE herramientas_disponibles
ADD COLUMN tool_name VARCHAR(100);

-- PASO 2: Poblar la columna con los nombres correctos
UPDATE herramientas_disponibles SET tool_name = 'list_calendar_events' WHERE id_tool = 1;
UPDATE herramientas_disponibles SET tool_name = 'create_calendar_event' WHERE id_tool = 2;
UPDATE herramientas_disponibles SET tool_name = 'update_calendar_event' WHERE id_tool = 3;
UPDATE herramientas_disponibles SET tool_name = 'delete_calendar_event' WHERE id_tool = 4;
UPDATE herramientas_disponibles SET tool_name = 'search_calendar_events' WHERE id_tool = 5;

-- PASO 3: Verificar que todos los registros tienen tool_name
DO $$
DECLARE
    null_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO null_count 
    FROM herramientas_disponibles 
    WHERE tool_name IS NULL;
    
    IF null_count > 0 THEN
        RAISE EXCEPTION 'Hay % registros con tool_name NULL. Abortando migración.', null_count;
    END IF;
END $$;

-- PASO 4: Agregar constraints NOT NULL y UNIQUE
ALTER TABLE herramientas_disponibles
ALTER COLUMN tool_name SET NOT NULL;

ALTER TABLE herramientas_disponibles
ADD CONSTRAINT uk_tool_name UNIQUE (tool_name);

-- PASO 5: Renombrar columna id_tool → id (solo el nombre, valores intactos)
ALTER TABLE herramientas_disponibles
RENAME COLUMN id_tool TO id;

-- PASO 6: Validación final (mostrar resultado)
SELECT 
    id,
    tool_name,
    LEFT(descripcion, 30) || '...' AS descripcion_preview,
    activa
FROM herramientas_disponibles
ORDER BY id;

-- Si todo está correcto, confirmar cambios
COMMIT;

-- Para hacer rollback si algo sale mal, ejecutar: ROLLBACK;
