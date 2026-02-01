-- Migration: Add 24h and 2h reminder columns to citas_medicas
-- Created for N9 Recordatorios node

-- Add columns for 24h and 2h reminders
ALTER TABLE citas_medicas 
ADD COLUMN IF NOT EXISTS recordatorio_24h_enviado BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS recordatorio_24h_fecha TIMESTAMP,
ADD COLUMN IF NOT EXISTS recordatorio_2h_enviado BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS recordatorio_2h_fecha TIMESTAMP;

-- Create index for efficient querying of upcoming appointments needing reminders
CREATE INDEX IF NOT EXISTS idx_citas_recordatorios_24h 
    ON citas_medicas(fecha_hora_inicio, recordatorio_24h_enviado) 
    WHERE recordatorio_24h_enviado = FALSE AND estado = 'confirmada';

CREATE INDEX IF NOT EXISTS idx_citas_recordatorios_2h 
    ON citas_medicas(fecha_hora_inicio, recordatorio_2h_enviado) 
    WHERE recordatorio_2h_enviado = FALSE AND estado = 'confirmada';

-- Add comment
COMMENT ON COLUMN citas_medicas.recordatorio_24h_enviado IS 'Indica si se envió recordatorio 24h antes';
COMMENT ON COLUMN citas_medicas.recordatorio_24h_fecha IS 'Fecha/hora de envío del recordatorio 24h';
COMMENT ON COLUMN citas_medicas.recordatorio_2h_enviado IS 'Indica si se envió recordatorio 2h antes';
COMMENT ON COLUMN citas_medicas.recordatorio_2h_fecha IS 'Fecha/hora de envío del recordatorio 2h';
