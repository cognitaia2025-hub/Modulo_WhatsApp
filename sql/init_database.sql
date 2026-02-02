-- =====================================================================
-- Script Maestro de Inicialización de Base de Datos
-- Agente WhatsApp con Memoria Infinita
-- =====================================================================
-- Base de datos: agente_whatsapp
-- Puerto: 5434 (externo) → 5432 (interno)
-- Usuario: admin / password123
-- =====================================================================

-- 1. EXTENSIÓN PGVECTOR (Búsqueda semántica de vectores)
-- =====================================================================
CREATE EXTENSION IF NOT EXISTS vector;

COMMENT ON EXTENSION vector IS 
'Extensión para almacenar y buscar embeddings (vectores de 384 dimensiones)';


-- =====================================================================
-- 2. MEMORIA PROCEDIMENTAL: Herramientas Disponibles
-- =====================================================================
-- Almacena las herramientas de Google Calendar que el agente puede usar
-- Esta tabla define las capacidades del agente

CREATE TABLE IF NOT EXISTS herramientas_disponibles (
    id_tool SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE,
    descripcion TEXT NOT NULL,
    parametros JSONB DEFAULT '{}'::jsonb,
    activa BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_herramientas_activas 
ON herramientas_disponibles(activa) 
WHERE activa = true;

COMMENT ON TABLE herramientas_disponibles IS 
'Memoria Procedimental: Catálogo de herramientas que el agente puede ejecutar';

-- Insertar las 5 herramientas de Google Calendar
INSERT INTO herramientas_disponibles (nombre, descripcion, parametros) VALUES
(
    'list_calendar_events',
    'Lista eventos del calendario de Google Calendar en un rango de fechas específico',
    '{"start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD"}'::jsonb
),
(
    'create_calendar_event',
    'Crea un nuevo evento en Google Calendar con título, fecha, hora de inicio y duración',
    '{"title": "string", "date": "YYYY-MM-DD", "time": "HH:MM", "duration_minutes": 60}'::jsonb
),
(
    'update_calendar_event',
    'Actualiza un evento existente en Google Calendar (título, fecha u hora)',
    '{"event_id": "string", "title": "string", "date": "YYYY-MM-DD", "time": "HH:MM"}'::jsonb
),
(
    'delete_calendar_event',
    'Elimina un evento del calendario de Google Calendar por su ID',
    '{"event_id": "string"}'::jsonb
),
(
    'get_event_details',
    'Obtiene los detalles completos de un evento específico de Google Calendar',
    '{"event_id": "string"}'::jsonb
)
ON CONFLICT (nombre) DO NOTHING;


-- =====================================================================
-- 3. MEMORIA EPISÓDICA: Recuerdos a Largo Plazo
-- =====================================================================
-- Almacena resúmenes de conversaciones con embeddings para búsqueda semántica
-- El agente puede recordar interacciones pasadas y aprender patrones del usuario

CREATE TABLE IF NOT EXISTS memoria_episodica (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    resumen TEXT NOT NULL,
    embedding vector(384) NOT NULL,  -- Embeddings de 384 dimensiones
    metadata JSONB DEFAULT '{}'::jsonb,  -- {fecha, session_id, tipo, timezone}
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT user_id_not_empty CHECK (user_id != ''),
    CONSTRAINT resumen_not_empty CHECK (resumen != '')
);

-- Índice para búsqueda por usuario
CREATE INDEX IF NOT EXISTS idx_memoria_user_id 
ON memoria_episodica(user_id);

-- Índice para búsqueda temporal (ordenar por fecha)
CREATE INDEX IF NOT EXISTS idx_memoria_timestamp 
ON memoria_episodica(timestamp DESC);

-- Índice HNSW para búsqueda semántica ultra-rápida con pgvector
-- Usa distancia coseno (óptima para embeddings normalizados)
CREATE INDEX IF NOT EXISTS idx_memoria_embedding_hnsw 
ON memoria_episodica 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Índice GIN para búsqueda en metadata JSON
CREATE INDEX IF NOT EXISTS idx_memoria_metadata 
ON memoria_episodica USING gin(metadata);

COMMENT ON TABLE memoria_episodica IS 
'Memoria Episódica: Resúmenes de conversaciones con embeddings para búsqueda semántica';

COMMENT ON COLUMN memoria_episodica.embedding IS 
'Vector de 384 dimensiones generado con paraphrase-multilingual-MiniLM-L12-v2';

COMMENT ON COLUMN memoria_episodica.metadata IS 
'JSON con: fecha (Pendulum), session_id, tipo (normal/cierre_expiracion), timezone';


-- =====================================================================
-- Función Helper: Buscar Memorias Similares (Búsqueda Semántica)
-- =====================================================================
CREATE OR REPLACE FUNCTION buscar_memorias_similares(
    p_user_id VARCHAR(100),
    p_embedding vector(384),
    p_limit INT DEFAULT 5
)
RETURNS TABLE(
    id INT,
    resumen TEXT,
    similarity FLOAT,
    metadata JSONB,
    created_timestamp TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        m.id,
        m.resumen,
        1 - (m.embedding <=> p_embedding) AS similarity,  -- Cosine similarity
        m.metadata,
        m.timestamp AS created_timestamp
    FROM memoria_episodica m
    WHERE m.user_id = p_user_id
    ORDER BY m.embedding <=> p_embedding  -- Ordena por distancia (menor = más similar)
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION buscar_memorias_similares IS 
'Busca las N memorias más similares semánticamente para un usuario dado';


-- =====================================================================
-- 4. AUDITORÍA PLANA: Logs de Conversaciones (Retención 6 meses)
-- =====================================================================
-- Almacena TODOS los mensajes de usuario y asistente para auditoría
-- Sin TTL automático, pero con índice temporal para limpieza manual

CREATE TABLE IF NOT EXISTS auditoria_conversaciones (
    id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    session_id VARCHAR(200) NOT NULL,
    rol VARCHAR(20) NOT NULL,  -- 'user', 'assistant', 'system'
    contenido TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT rol_valido CHECK (rol IN ('user', 'assistant', 'system'))
);

-- Índice compuesto para consultas por usuario + fecha
CREATE INDEX IF NOT EXISTS idx_auditoria_user_timestamp 
ON auditoria_conversaciones(user_id, timestamp DESC);

-- Índice para consultas por sesión
CREATE INDEX IF NOT EXISTS idx_auditoria_session 
ON auditoria_conversaciones(session_id);

COMMENT ON TABLE auditoria_conversaciones IS 
'Auditoría: Logs planos de todas las conversaciones (retención 6 meses)';

-- Vista para limpieza de registros antiguos (>6 meses)
CREATE OR REPLACE VIEW auditoria_para_limpiar AS
SELECT id, user_id, timestamp
FROM auditoria_conversaciones
WHERE timestamp < NOW() - INTERVAL '6 months';

COMMENT ON VIEW auditoria_para_limpiar IS 
'Registros de auditoría con más de 6 meses para limpieza manual';


-- =====================================================================
-- 5. SISTEMA DE USUARIOS Y DOCTORES (ETAPA 1)
-- =====================================================================
-- Tabla principal de usuarios con soporte multi-rol

CREATE TABLE IF NOT EXISTS usuarios (
    id SERIAL PRIMARY KEY,
    phone_number VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(200),
    es_admin BOOLEAN DEFAULT FALSE,
    timezone VARCHAR(50) DEFAULT 'America/Tijuana',
    preferencias JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    email VARCHAR UNIQUE,
    is_active BOOLEAN DEFAULT TRUE,
    tipo_usuario VARCHAR DEFAULT 'paciente_externo' 
        CHECK (tipo_usuario IN ('personal', 'doctor', 'paciente_externo', 'admin'))
);

-- Índices para búsquedas rápidas
CREATE INDEX IF NOT EXISTS idx_usuarios_tipo ON usuarios(tipo_usuario);
CREATE INDEX IF NOT EXISTS idx_usuarios_phone ON usuarios(phone_number);
CREATE INDEX IF NOT EXISTS idx_usuarios_email ON usuarios(email) WHERE email IS NOT NULL;

COMMENT ON TABLE usuarios IS 
'Tabla principal de usuarios multi-rol con soporte para personal, doctores, pacientes y admin';

-- Tabla de doctores (perfil especializado)
CREATE TABLE IF NOT EXISTS doctores (
    id SERIAL PRIMARY KEY,
    phone_number VARCHAR(50) REFERENCES usuarios(phone_number),
    nombre_completo VARCHAR(200) NOT NULL,
    especialidad VARCHAR(100) NOT NULL,
    num_licencia VARCHAR(50) UNIQUE,
    horario_atencion JSONB DEFAULT '{}'::jsonb,
    direccion_consultorio VARCHAR(300),
    tarifa_consulta DECIMAL(10,2),
    años_experiencia INTEGER DEFAULT 0,
    orden_turno INTEGER DEFAULT 1,
    total_citas_asignadas INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_doctores_phone ON doctores(phone_number);

COMMENT ON TABLE doctores IS 
'Perfiles especializados de médicos con información profesional';

-- Tabla de pacientes (perfil especializado)
CREATE TABLE IF NOT EXISTS pacientes (
    id SERIAL PRIMARY KEY,
    doctor_id INTEGER REFERENCES doctores(id),
    nombre_completo VARCHAR(200) NOT NULL,
    telefono VARCHAR(50) UNIQUE,
    email VARCHAR(100),
    fecha_nacimiento DATE,
    genero VARCHAR(20) CHECK (genero IN ('masculino', 'femenino', 'otro')),
    direccion TEXT,
    contacto_emergencia JSONB DEFAULT '{}'::jsonb,
    seguro_medico VARCHAR(100),
    numero_seguro VARCHAR(50),
    alergias TEXT,
    medicamentos_actuales TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ultima_cita TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_pacientes_doctor ON pacientes(doctor_id);
CREATE INDEX IF NOT EXISTS idx_pacientes_telefono ON pacientes(telefono);

COMMENT ON TABLE pacientes IS 
'Perfiles de pacientes con historial médico básico';


-- =====================================================================
-- 6. SISTEMA DE TURNOS Y DISPONIBILIDAD (ETAPA 2)
-- =====================================================================
-- Tabla de control de turnos entre doctores
CREATE TABLE IF NOT EXISTS control_turnos (
    id SERIAL PRIMARY KEY,
    ultimo_doctor_id INTEGER REFERENCES doctores(id),
    citas_santiago INTEGER DEFAULT 0,
    citas_joana INTEGER DEFAULT 0,
    total_turnos_asignados INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insertar registro inicial si no existe
INSERT INTO control_turnos (ultimo_doctor_id, citas_santiago, citas_joana, total_turnos_asignados)
SELECT NULL, 0, 0, 0
WHERE NOT EXISTS (SELECT 1 FROM control_turnos);

COMMENT ON TABLE control_turnos IS 
'Control de alternancia de turnos entre doctores para distribución equitativa';

-- Tabla de disponibilidad médica por doctor
CREATE TABLE IF NOT EXISTS disponibilidad_medica (
    id SERIAL PRIMARY KEY,
    doctor_id INTEGER REFERENCES doctores(id) NOT NULL,
    dia_semana INTEGER NOT NULL CHECK (dia_semana BETWEEN 0 AND 6),
    hora_inicio TIME NOT NULL,
    hora_fin TIME NOT NULL,
    disponible BOOLEAN DEFAULT TRUE,
    duracion_cita INTEGER DEFAULT 30,
    max_pacientes_dia INTEGER DEFAULT 16,
    notas VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_disponibilidad_doctor ON disponibilidad_medica(doctor_id);
CREATE INDEX IF NOT EXISTS idx_disponibilidad_dia ON disponibilidad_medica(dia_semana);

COMMENT ON TABLE disponibilidad_medica IS 
'Horarios de atención configurables por doctor y día de la semana';


-- =====================================================================
-- 7. SISTEMA DE CITAS MÉDICAS (ETAPA 2-6)
-- =====================================================================
-- Tabla principal de citas médicas
CREATE TABLE IF NOT EXISTS citas_medicas (
    id SERIAL PRIMARY KEY,
    doctor_id INTEGER REFERENCES doctores(id) NOT NULL,
    paciente_id INTEGER REFERENCES pacientes(id) NOT NULL,
    fecha_hora_inicio TIMESTAMP NOT NULL,
    fecha_hora_fin TIMESTAMP NOT NULL,
    tipo_consulta VARCHAR(20) DEFAULT 'seguimiento' 
        CHECK (tipo_consulta IN ('primera_vez', 'seguimiento', 'urgencia', 'revision')),
    estado VARCHAR(20) DEFAULT 'programada'
        CHECK (estado IN ('programada', 'confirmada', 'en_curso', 'completada', 'cancelada', 'no_asistio')),
    motivo_consulta TEXT,
    sintomas_principales TEXT,
    diagnostico TEXT,
    tratamiento_prescrito JSONB DEFAULT '{}'::jsonb,
    medicamentos JSONB DEFAULT '[]'::jsonb,
    proxima_cita DATE,
    notas_privadas TEXT,
    google_event_id VARCHAR(200),
    sincronizada_google BOOLEAN DEFAULT FALSE,
    costo_consulta DECIMAL(10,2),
    metodo_pago VARCHAR(20) DEFAULT 'efectivo'
        CHECK (metodo_pago IN ('efectivo', 'tarjeta', 'transferencia', 'seguro')),
    recordatorio_enviado BOOLEAN DEFAULT FALSE,
    recordatorio_fecha_envio TIMESTAMP,
    recordatorio_intentos INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para citas
CREATE INDEX IF NOT EXISTS idx_citas_doctor ON citas_medicas(doctor_id);
CREATE INDEX IF NOT EXISTS idx_citas_paciente ON citas_medicas(paciente_id);
CREATE INDEX IF NOT EXISTS idx_citas_fecha ON citas_medicas(fecha_hora_inicio);
CREATE INDEX IF NOT EXISTS idx_citas_estado ON citas_medicas(estado);
CREATE INDEX IF NOT EXISTS idx_citas_google_event ON citas_medicas(google_event_id) WHERE google_event_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_citas_recordatorios_pendientes 
    ON citas_medicas(fecha_hora_inicio, recordatorio_enviado) 
    WHERE recordatorio_enviado = FALSE AND estado IN ('programada', 'confirmada');

COMMENT ON TABLE citas_medicas IS 
'Registro completo de citas médicas con sincronización Google Calendar y recordatorios';


-- =====================================================================
-- 8. SISTEMA DE HISTORIALES MÉDICOS (ETAPA 3)
-- =====================================================================
-- Tabla de historiales médicos con búsqueda semántica
CREATE TABLE IF NOT EXISTS historiales_medicos (
    id SERIAL PRIMARY KEY,
    paciente_id INTEGER REFERENCES pacientes(id) NOT NULL,
    cita_id INTEGER REFERENCES citas_medicas(id),
    fecha_consulta DATE NOT NULL,
    peso DECIMAL(5,2),
    altura DECIMAL(5,2),
    presion_arterial VARCHAR(20),
    frecuencia_cardiaca INTEGER,
    temperatura DECIMAL(4,2),
    diagnostico_principal TEXT NOT NULL,
    diagnosticos_secundarios JSONB DEFAULT '[]'::jsonb,
    sintomas TEXT,
    exploracion_fisica TEXT,
    estudios_laboratorio JSONB DEFAULT '{}'::jsonb,
    tratamiento_prescrito TEXT,
    medicamentos JSONB DEFAULT '[]'::jsonb,
    indicaciones_generales TEXT,
    fecha_proxima_revision DATE,
    archivos_adjuntos JSONB DEFAULT '[]'::jsonb,
    embedding vector(384),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para historiales
CREATE INDEX IF NOT EXISTS idx_historiales_paciente ON historiales_medicos(paciente_id);
CREATE INDEX IF NOT EXISTS idx_historiales_fecha ON historiales_medicos(fecha_consulta DESC);
CREATE INDEX IF NOT EXISTS idx_historiales_embedding_hnsw 
    ON historiales_medicos 
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64)
    WHERE embedding IS NOT NULL;

COMMENT ON TABLE historiales_medicos IS 
'Historiales clínicos completos con soporte para búsqueda semántica';

-- Tabla de clasificaciones de LLM (registro de decisiones)
CREATE TABLE IF NOT EXISTS clasificaciones_llm (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(200) NOT NULL,
    user_id VARCHAR(100) NOT NULL,
    modelo VARCHAR(50) NOT NULL,
    clasificacion VARCHAR(50) NOT NULL,
    herramientas_seleccionadas JSONB DEFAULT '[]'::jsonb,
    mensaje_usuario TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    tiempo_respuesta_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_clasificaciones_session ON clasificaciones_llm(session_id);
CREATE INDEX IF NOT EXISTS idx_clasificaciones_user ON clasificaciones_llm(user_id);
CREATE INDEX IF NOT EXISTS idx_clasificaciones_tipo ON clasificaciones_llm(clasificacion);

COMMENT ON TABLE clasificaciones_llm IS 
'Registro de clasificaciones y decisiones tomadas por el LLM para análisis';

-- Vista de resumen de clasificaciones
CREATE OR REPLACE VIEW resumen_clasificaciones AS
SELECT 
    clasificacion,
    COUNT(*) as total,
    AVG(tiempo_respuesta_ms) as tiempo_promedio_ms,
    COUNT(DISTINCT session_id) as sesiones_unicas,
    COUNT(DISTINCT user_id) as usuarios_unicos
FROM clasificaciones_llm
GROUP BY clasificacion
ORDER BY total DESC;

-- Vista de métricas por modelo
CREATE OR REPLACE VIEW metricas_llm_por_modelo AS
SELECT 
    modelo,
    COUNT(*) as total_clasificaciones,
    AVG(tiempo_respuesta_ms) as tiempo_promedio_ms,
    MIN(tiempo_respuesta_ms) as tiempo_min_ms,
    MAX(tiempo_respuesta_ms) as tiempo_max_ms
FROM clasificaciones_llm
GROUP BY modelo
ORDER BY total_clasificaciones DESC;

-- Función de búsqueda semántica en historiales
CREATE OR REPLACE FUNCTION buscar_historiales_semantica(
    p_paciente_id INTEGER,
    p_embedding vector(384),
    p_limit INTEGER DEFAULT 5
)
RETURNS TABLE(
    id INTEGER,
    diagnostico_principal TEXT,
    sintomas TEXT,
    similarity FLOAT,
    fecha_consulta DATE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        h.id,
        h.diagnostico_principal,
        h.sintomas,
        1 - (h.embedding <=> p_embedding) AS similarity,
        h.fecha_consulta
    FROM historiales_medicos h
    WHERE h.paciente_id = p_paciente_id 
        AND h.embedding IS NOT NULL
    ORDER BY h.embedding <=> p_embedding
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;


-- =====================================================================
-- 9. SISTEMA DE SINCRONIZACIÓN GOOGLE CALENDAR (ETAPA 5)
-- =====================================================================
-- Tabla de sincronización con Google Calendar
CREATE TABLE IF NOT EXISTS sincronizacion_calendar (
    id SERIAL PRIMARY KEY,
    cita_id INTEGER REFERENCES citas_medicas(id) NOT NULL,
    google_event_id VARCHAR(200),
    estado VARCHAR(20) DEFAULT 'pendiente'
        CHECK (estado IN ('sincronizada', 'pendiente', 'error', 'reintentando', 'error_permanente')),
    ultimo_intento TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    siguiente_reintento TIMESTAMP,
    intentos INTEGER DEFAULT 0,
    max_intentos INTEGER DEFAULT 5,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para sincronización
CREATE INDEX IF NOT EXISTS idx_sync_cita_id ON sincronizacion_calendar(cita_id);
CREATE INDEX IF NOT EXISTS idx_sync_pendientes 
    ON sincronizacion_calendar(estado, siguiente_reintento)
    WHERE estado IN ('error', 'pendiente', 'reintentando');

COMMENT ON TABLE sincronizacion_calendar IS 
'Control de sincronización bidireccional con Google Calendar con reintento automático';


-- =====================================================================
-- 10. SISTEMA DE MÉTRICAS Y REPORTES (ETAPA 7)
-- =====================================================================
-- Tabla de métricas agregadas por doctor
CREATE TABLE IF NOT EXISTS metricas_consultas (
    id SERIAL PRIMARY KEY,
    doctor_id INTEGER REFERENCES doctores(id) NOT NULL,
    fecha DATE NOT NULL,
    total_citas INTEGER DEFAULT 0,
    citas_completadas INTEGER DEFAULT 0,
    citas_canceladas INTEGER DEFAULT 0,
    citas_no_asistio INTEGER DEFAULT 0,
    ingresos_totales DECIMAL(10,2) DEFAULT 0,
    duracion_promedio_minutos INTEGER DEFAULT 0,
    pacientes_nuevos INTEGER DEFAULT 0,
    pacientes_recurrentes INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(doctor_id, fecha)
);

CREATE INDEX IF NOT EXISTS idx_metricas_doctor_fecha ON metricas_consultas(doctor_id, fecha DESC);

COMMENT ON TABLE metricas_consultas IS 
'Métricas diarias agregadas por doctor para reportes y análisis';

-- Tabla de reportes generados
CREATE TABLE IF NOT EXISTS reportes_generados (
    id SERIAL PRIMARY KEY,
    doctor_id INTEGER REFERENCES doctores(id) NOT NULL,
    tipo_reporte VARCHAR(50) NOT NULL 
        CHECK (tipo_reporte IN ('disponibilidad', 'estadisticas', 'busqueda', 'personalizado')),
    fecha_inicio DATE NOT NULL,
    fecha_fin DATE NOT NULL,
    parametros JSONB DEFAULT '{}'::jsonb,
    resultado JSONB DEFAULT '{}'::jsonb,
    formato VARCHAR(20) DEFAULT 'json' 
        CHECK (formato IN ('json', 'pdf', 'csv', 'xlsx')),
    generado_por VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_reportes_doctor ON reportes_generados(doctor_id);
CREATE INDEX IF NOT EXISTS idx_reportes_tipo ON reportes_generados(tipo_reporte);
CREATE INDEX IF NOT EXISTS idx_reportes_fecha ON reportes_generados(created_at DESC);

COMMENT ON TABLE reportes_generados IS 
'Histórico de reportes generados para auditoría y cache de consultas complejas';

-- Vista de estadísticas por doctor
CREATE OR REPLACE VIEW vista_estadisticas_doctores AS
SELECT 
    d.id as doctor_id,
    d.nombre_completo,
    d.especialidad,
    COUNT(DISTINCT c.id) as total_citas,
    COUNT(DISTINCT CASE WHEN c.estado = 'completada' THEN c.id END) as citas_completadas,
    COUNT(DISTINCT c.paciente_id) as total_pacientes,
    COALESCE(SUM(c.costo_consulta), 0) as ingresos_totales,
    AVG(EXTRACT(EPOCH FROM (c.fecha_hora_fin - c.fecha_hora_inicio))/60) as duracion_promedio_minutos,
    MAX(c.fecha_hora_inicio) as ultima_cita,
    d.total_citas_asignadas as turnos_asignados
FROM doctores d
LEFT JOIN citas_medicas c ON d.id = c.doctor_id
GROUP BY d.id, d.nombre_completo, d.especialidad, d.total_citas_asignadas;

-- Función para actualizar métricas de doctor
CREATE OR REPLACE FUNCTION actualizar_metricas_doctor(
    p_doctor_id INTEGER,
    p_fecha DATE DEFAULT CURRENT_DATE
)
RETURNS VOID AS $$
BEGIN
    INSERT INTO metricas_consultas (
        doctor_id, fecha, total_citas, citas_completadas, citas_canceladas, 
        citas_no_asistio, ingresos_totales, duracion_promedio_minutos
    )
    SELECT 
        p_doctor_id,
        p_fecha,
        COUNT(*),
        COUNT(*) FILTER (WHERE estado = 'completada'),
        COUNT(*) FILTER (WHERE estado = 'cancelada'),
        COUNT(*) FILTER (WHERE estado = 'no_asistio'),
        COALESCE(SUM(costo_consulta) FILTER (WHERE estado = 'completada'), 0),
        AVG(EXTRACT(EPOCH FROM (fecha_hora_fin - fecha_hora_inicio))/60)::INTEGER
    FROM citas_medicas
    WHERE doctor_id = p_doctor_id 
        AND DATE(fecha_hora_inicio) = p_fecha
    ON CONFLICT (doctor_id, fecha) DO UPDATE
    SET 
        total_citas = EXCLUDED.total_citas,
        citas_completadas = EXCLUDED.citas_completadas,
        citas_canceladas = EXCLUDED.citas_canceladas,
        citas_no_asistio = EXCLUDED.citas_no_asistio,
        ingresos_totales = EXCLUDED.ingresos_totales,
        duracion_promedio_minutos = EXCLUDED.duracion_promedio_minutos,
        updated_at = CURRENT_TIMESTAMP;
END;
$$ LANGUAGE plpgsql;

-- Trigger para actualizar métricas automáticamente
CREATE OR REPLACE FUNCTION trigger_actualizar_metricas()
RETURNS TRIGGER AS $$
BEGIN
    PERFORM actualizar_metricas_doctor(NEW.doctor_id, DATE(NEW.fecha_hora_inicio));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_actualizar_metricas ON citas_medicas;
CREATE TRIGGER trigger_actualizar_metricas
AFTER INSERT OR UPDATE ON citas_medicas
FOR EACH ROW
EXECUTE FUNCTION trigger_actualizar_metricas();

-- Función para buscar citas por periodo
CREATE OR REPLACE FUNCTION buscar_citas_por_periodo(
    p_doctor_id INTEGER,
    p_fecha_inicio DATE,
    p_fecha_fin DATE
)
RETURNS TABLE(
    id INTEGER,
    paciente_nombre VARCHAR,
    fecha_hora TIMESTAMP,
    estado VARCHAR,
    tipo_consulta VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        c.id,
        p.nombre_completo,
        c.fecha_hora_inicio,
        c.estado::VARCHAR,
        c.tipo_consulta::VARCHAR
    FROM citas_medicas c
    JOIN pacientes p ON c.paciente_id = p.id
    WHERE c.doctor_id = p_doctor_id
        AND DATE(c.fecha_hora_inicio) BETWEEN p_fecha_inicio AND p_fecha_fin
    ORDER BY c.fecha_hora_inicio;
END;
$$ LANGUAGE plpgsql;


-- =====================================================================
-- 11. TABLAS INTERNAS DE LANGGRAPH (Checkpoint Automático)
-- =====================================================================
-- LangGraph creará automáticamente estas tablas al ejecutar setup():
-- - checkpoints: Estado de cada sesión (TTL 24h)
-- - checkpoint_writes: Escrituras pendientes
-- - checkpoint_blobs: Datos grandes serializados

-- Estas tablas se crean automáticamente con PostgresSaver.setup()
-- Ver: langgraph-checkpoint-postgres


-- =====================================================================
-- 12. FUNCIÓN DE MANTENIMIENTO: Limpieza Automática de Auditoría
-- =====================================================================
CREATE OR REPLACE FUNCTION limpiar_auditoria_antigua()
RETURNS INTEGER AS $$
DECLARE
    registros_eliminados INTEGER;
BEGIN
    DELETE FROM auditoria_conversaciones
    WHERE timestamp < NOW() - INTERVAL '6 months';
    
    GET DIAGNOSTICS registros_eliminados = ROW_COUNT;
    
    RAISE NOTICE 'Eliminados % registros de auditoría antiguos', registros_eliminados;
    RETURN registros_eliminados;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION limpiar_auditoria_antigua IS 
'Elimina registros de auditoría con más de 6 meses de antigüedad';

-- Job programado (ejecutar manualmente o con pg_cron)
-- SELECT cron.schedule('limpiar-auditoria', '0 2 1 * *', 'SELECT limpiar_auditoria_antigua();');


-- =====================================================================
-- 13. VERIFICACIÓN FINAL
-- =====================================================================
DO $$
BEGIN
    RAISE NOTICE '✅ Base de datos inicializada correctamente';
    RAISE NOTICE '📊 Extensión pgvector: Instalada';
    RAISE NOTICE '🛠️  Herramientas disponibles: % registros', (SELECT COUNT(*) FROM herramientas_disponibles);
    RAISE NOTICE '🧠 Memoria episódica: Lista para embeddings de 384 dims';
    RAISE NOTICE '📝 Auditoría de conversaciones: Retención 6 meses';
    RAISE NOTICE '� Sistema de usuarios: % usuarios registrados', (SELECT COUNT(*) FROM usuarios);
    RAISE NOTICE '⚕️  Doctores: % registrados', (SELECT COUNT(*) FROM doctores);
    RAISE NOTICE '🏥 Pacientes: % registrados', (SELECT COUNT(*) FROM pacientes);
    RAISE NOTICE '📅 Citas médicas: % programadas', (SELECT COUNT(*) FROM citas_medicas);
    RAISE NOTICE '📋 Historiales médicos: % registros', (SELECT COUNT(*) FROM historiales_medicos);
    RAISE NOTICE '🔄 Sistema de sincronización: Configurado';
    RAISE NOTICE '📊 Sistema de métricas: Configurado';
    RAISE NOTICE '💾 Tablas de LangGraph: Se crearán al ejecutar checkpointer.setup()';
    RAISE NOTICE '🎯 Puerto: 5434 (externo) → 5432 (interno)';
    RAISE NOTICE '';
    RAISE NOTICE '🎉 ¡TODAS LAS ETAPAS CONSOLIDADAS!';
    RAISE NOTICE '   Ya no es necesario ejecutar migraciones por separado';
END $$;

-- Consultar estado de las tablas creadas
SELECT 
    'herramientas_disponibles' AS tabla,
    COUNT(*) AS registros,
    pg_size_pretty(pg_total_relation_size('herramientas_disponibles')) AS tamaño
FROM herramientas_disponibles
UNION ALL
SELECT 
    'memoria_episodica' AS tabla,
    COUNT(*) AS registros,
    pg_size_pretty(pg_total_relation_size('memoria_episodica')) AS tamaño
FROM memoria_episodica
UNION ALL
SELECT 
    'auditoria_conversaciones' AS tabla,
    COUNT(*) AS registros,
    pg_size_pretty(pg_total_relation_size('auditoria_conversaciones')) AS tamaño
FROM auditoria_conversaciones;


-- =====================================================================
-- MIGRACIÓN: Columnas de recordatorios 24h y 2h para citas_medicas
-- =====================================================================
-- Añade columnas para rastrear el envío de recordatorios

ALTER TABLE citas_medicas 
ADD COLUMN IF NOT EXISTS recordatorio_24h_enviado BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS recordatorio_24h_fecha TIMESTAMP,
ADD COLUMN IF NOT EXISTS recordatorio_2h_enviado BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS recordatorio_2h_fecha TIMESTAMP;

-- Índices para consultas eficientes de recordatorios pendientes
CREATE INDEX IF NOT EXISTS idx_citas_recordatorios_24h 
    ON citas_medicas(fecha_hora_inicio, recordatorio_24h_enviado) 
    WHERE recordatorio_24h_enviado = FALSE AND estado = 'confirmada';

CREATE INDEX IF NOT EXISTS idx_citas_recordatorios_2h 
    ON citas_medicas(fecha_hora_inicio, recordatorio_2h_enviado) 
    WHERE recordatorio_2h_enviado = FALSE AND estado = 'confirmada';

-- Comentarios de documentación
COMMENT ON COLUMN citas_medicas.recordatorio_24h_enviado IS 'Indica si se envió recordatorio 24h antes';
COMMENT ON COLUMN citas_medicas.recordatorio_24h_fecha IS 'Fecha/hora de envío del recordatorio 24h';
COMMENT ON COLUMN citas_medicas.recordatorio_2h_enviado IS 'Indica si se envió recordatorio 2h antes';
COMMENT ON COLUMN citas_medicas.recordatorio_2h_fecha IS 'Fecha/hora de envío del recordatorio 2h';
