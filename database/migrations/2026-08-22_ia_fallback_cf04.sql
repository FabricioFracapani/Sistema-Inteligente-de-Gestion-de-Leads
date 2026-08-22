-- ============================================================
-- MIGRACION: CF-04 fallback centinela + prioridad 0 para spam (M-15, m06)
-- Fecha: 2026-08-22
-- Ejecutar en Supabase > SQL Editor (requiere rol con permisos DDL,
-- la anon key NO alcanza para esto).
-- ============================================================

-- 1) Nueva columna: marca si la fila quedo con clasificacion de
--    fallback (la IA no devolvio JSON parseable) en vez de una
--    clasificacion real.
ALTER TABLE leads
    ADD COLUMN IF NOT EXISTS ia_fallback BOOLEAN NOT NULL DEFAULT false;

-- 2) La constraint original exigia ia_prioridad BETWEEN 1 AND 100,
--    lo cual bloqueaba guardar prioridad = 0 para spam. Hay que
--    relajarla a BETWEEN 0 AND 100 antes de que el pipeline empiece
--    a forzar 0 en los leads de spam, o el PATCH a Supabase va a
--    fallar con un error de constraint.
--    Si el nombre autogenerado de la constraint no es exactamente
--    este, buscalo con:
--      SELECT conname FROM pg_constraint WHERE conrelid = 'leads'::regclass;
ALTER TABLE leads
    DROP CONSTRAINT IF EXISTS leads_ia_prioridad_check;

ALTER TABLE leads
    ADD CONSTRAINT leads_ia_prioridad_check CHECK (ia_prioridad BETWEEN 0 AND 100);

-- Verificacion rapida
-- SELECT column_name, data_type, column_default
--   FROM information_schema.columns
--  WHERE table_name = 'leads' AND column_name = 'ia_fallback';
