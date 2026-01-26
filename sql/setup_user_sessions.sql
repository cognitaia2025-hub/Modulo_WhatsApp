-- ============================================================================
-- Tabla para Rolling Window: Gestión de Sesiones de Usuario
-- ============================================================================
-- 
-- Permite mantener sesiones activas basadas en INACTIVIDAD (no en fecha)
-- Thread se mantiene mientras last_activity < 24h
-- 
-- Autor: Session Manager
-- Fecha: 2026-01-24
-- ============================================================================

-- Crear tabla de sesiones
CREATE TABLE IF NOT EXISTS user_sessions (
    user_id VARCHAR(50) NOT NULL,
    thread_id VARCHAR(100) NOT NULL,
    phone_number VARCHAR(20),
    last_activity TIMESTAMP NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    messages_count INTEGER DEFAULT 0,
    PRIMARY KEY (user_id, thread_id)
);

-- Índices para optimizar búsquedas
CREATE INDEX IF NOT EXISTS idx_user_last_activity 
ON user_sessions(user_id, last_activity DESC);

CREATE INDEX IF NOT EXISTS idx_thread_lookup 
ON user_sessions(thread_id);

CREATE INDEX IF NOT EXISTS idx_phone_lookup 
ON user_sessions(phone_number);

-- ============================================================================
-- Función: Obtener sesión activa (< 24h inactividad)
-- ============================================================================
CREATE OR REPLACE FUNCTION get_active_session(p_user_id VARCHAR)
RETURNS TABLE(
    thread_id VARCHAR,
    last_activity TIMESTAMP,
    hours_inactive NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        s.thread_id,
        s.last_activity,
        EXTRACT(EPOCH FROM (NOW() - s.last_activity)) / 3600 AS hours_inactive
    FROM user_sessions s
    WHERE s.user_id = p_user_id
        AND s.last_activity > NOW() - INTERVAL '24 hours'
    ORDER BY s.last_activity DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Función: Actualizar timestamp de actividad
-- ============================================================================
CREATE OR REPLACE FUNCTION update_session_activity(
    p_user_id VARCHAR,
    p_thread_id VARCHAR
)
RETURNS BOOLEAN AS $$
BEGIN
    UPDATE user_sessions
    SET 
        last_activity = NOW(),
        messages_count = messages_count + 1
    WHERE user_id = p_user_id 
        AND thread_id = p_thread_id;
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Función: Limpieza automática de sesiones antiguas (>30 días)
-- ============================================================================
CREATE OR REPLACE FUNCTION cleanup_old_sessions()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM user_sessions
    WHERE last_activity < NOW() - INTERVAL '30 days';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    RAISE NOTICE 'Limpiadas % sesiones antiguas (>30 días)', deleted_count;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Vista: Sesiones activas en las últimas 24h
-- ============================================================================
CREATE OR REPLACE VIEW active_sessions_24h AS
SELECT 
    user_id,
    thread_id,
    phone_number,
    last_activity,
    EXTRACT(EPOCH FROM (NOW() - last_activity)) / 3600 AS hours_since_activity,
    messages_count,
    created_at
FROM user_sessions
WHERE last_activity > NOW() - INTERVAL '24 hours'
ORDER BY last_activity DESC;

-- ============================================================================
-- Vista: Estadísticas de sesiones
-- ============================================================================
CREATE OR REPLACE VIEW session_statistics AS
SELECT 
    COUNT(DISTINCT user_id) AS total_users,
    COUNT(DISTINCT thread_id) AS total_threads,
    COUNT(DISTINCT CASE 
        WHEN last_activity > NOW() - INTERVAL '24 hours' 
        THEN user_id 
    END) AS active_users_24h,
    COUNT(DISTINCT CASE 
        WHEN last_activity > NOW() - INTERVAL '1 hour' 
        THEN user_id 
    END) AS active_users_1h,
    SUM(messages_count) AS total_messages,
    AVG(messages_count) AS avg_messages_per_thread,
    MAX(last_activity) AS most_recent_activity
FROM user_sessions;

-- ============================================================================
-- Trigger: Prevenir modificación del user_id
-- ============================================================================
CREATE OR REPLACE FUNCTION prevent_user_id_change()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.user_id IS DISTINCT FROM NEW.user_id THEN
        RAISE EXCEPTION 'user_id no puede ser modificado';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_prevent_user_id_change
BEFORE UPDATE ON user_sessions
FOR EACH ROW
EXECUTE FUNCTION prevent_user_id_change();

-- ============================================================================
-- Job de limpieza automática (ejecutar diariamente)
-- ============================================================================
-- Nota: Requiere pg_cron extension
-- CREATE EXTENSION IF NOT EXISTS pg_cron;
--
-- SELECT cron.schedule(
--     'cleanup-old-sessions',
--     '0 3 * * *',  -- 3:00 AM diariamente
--     $$SELECT cleanup_old_sessions();$$
-- );

-- ============================================================================
-- Datos de ejemplo para testing
-- ============================================================================
-- DESCOMENTAR SOLO PARA TESTING:
-- 
-- INSERT INTO user_sessions (user_id, thread_id, phone_number, last_activity, messages_count)
-- VALUES 
--     ('user_test123', 'thread_user_test123_abc123', '+52123456789', NOW() - INTERVAL '2 hours', 5),
--     ('user_test456', 'thread_user_test456_def456', '+52987654321', NOW() - INTERVAL '30 hours', 12),
--     ('user_test789', 'thread_user_test789_ghi789', '+52555555555', NOW() - INTERVAL '1 hour', 3);

-- ============================================================================
-- Verificación de la tabla
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE '✅ Tabla user_sessions creada correctamente';
    RAISE NOTICE '✅ Índices creados';
    RAISE NOTICE '✅ Funciones de rolling window instaladas';
    RAISE NOTICE '✅ Vistas de estadísticas disponibles';
    RAISE NOTICE '';
    RAISE NOTICE '📋 Para ver sesiones activas: SELECT * FROM active_sessions_24h;';
    RAISE NOTICE '📊 Para ver estadísticas: SELECT * FROM session_statistics;';
    RAISE NOTICE '🧹 Para limpiar sesiones: SELECT cleanup_old_sessions();';
END $$;
