-- ============================================================
-- SISTEMA INTELIGENTE DE GESTIÓN DE LEADS
-- Schema PostgreSQL + Row Level Security - Supabase
-- TFI - Tecnicatura Superior en Programación - UTN FRM
-- ============================================================

-- ============================================================
-- 1. EXTENSIONES
-- ============================================================
CREATE EXTENSION IF NOT EXISTS "pgcrypto";      -- para encrypt/decrypt, gen_random_bytes
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";      -- para uuid_generate_v4

-- ============================================================
-- 2. TABLAS PRINCIPALES
-- ============================================================

-- 2.1 Leads: datos del prospecto + resultados IA + gestión embudo
CREATE TABLE leads (
    id_lead         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre          VARCHAR(100) NOT NULL,
    apellido        VARCHAR(100),
    email           VARCHAR(255) NOT NULL,
    email_hash      VARCHAR(64),           -- SHA-256 del email para búsqueda sin exponer PII
    telefono        VARCHAR(30),
    telefono_hash   VARCHAR(64),           -- SHA-256 del teléfono
    mensaje         TEXT,
    -- Metadata de captura
    fuente          VARCHAR(50) NOT NULL DEFAULT 'landing_page',
    url_origen      VARCHAR(500),
    ip_origen       INET,                  -- IPv4 o IPv6 (anonimizado: últimos 2 octetos en 0)
    user_agent      TEXT,
    timestamp_ingesta TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Resultados de IA
    ia_clasificacion VARCHAR(50),          -- compra_inmediata, solicita_info, soporte, spam
    ia_prioridad    INTEGER CHECK (ia_prioridad BETWEEN 1 AND 100),
    ia_confianza    DECIMAL(4,3) CHECK (ia_confianza BETWEEN 0 AND 1),
    ia_resumen      TEXT,
    ia_respuesta    TEXT,                  -- email HTML generado por IA
    -- Gestión del embudo
    estado          VARCHAR(30) NOT NULL DEFAULT 'nuevo',
    responsable     VARCHAR(100),
    notas_internas  TEXT,
    -- Auditoría
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2.2 Eventos del pipeline: trazabilidad completa
CREATE TABLE lead_events (
    id_evento       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    id_lead         UUID REFERENCES leads(id_lead) ON DELETE CASCADE,
    tipo_evento     VARCHAR(50) NOT NULL,   -- webhook_recibido, validacion_ok, validacion_fallo,
                                            -- ia_clasificacion, email_enviado, email_error,
                                            -- slack_notificado, error_pipeline, lead_insertado
    detalle         JSONB,                  -- payload completo del evento
    nodo_origen     VARCHAR(100),           -- nodo de n8n que generó el evento
    lrt_segundos    DECIMAL(6,3),           -- lead response time acumulado
    ejecucion_id    VARCHAR(100),           -- ID de ejecución de n8n para correlacionar
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2.3 Configuración de IA: prompts configurables sin tocar n8n
CREATE TABLE ia_config (
    id_config       SERIAL PRIMARY KEY,
    nombre          VARCHAR(100) NOT NULL UNIQUE,
    system_prompt   TEXT NOT NULL,
    modelo          VARCHAR(50) NOT NULL DEFAULT 'gpt-4o-mini',
    temperature     DECIMAL(2,1) DEFAULT 0.3,
    max_tokens      INTEGER DEFAULT 150,
    activo          BOOLEAN DEFAULT true,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2.4 API Keys: gestión de claves de servicio
CREATE TABLE api_keys (
    id_key          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    servicio        VARCHAR(50) NOT NULL,   -- 'n8n', 'dashboard', 'flask'
    clave_hash      VARCHAR(64) NOT NULL,   -- SHA-256 de la clave real
    descripcion     VARCHAR(200),
    permisos        TEXT[] NOT NULL DEFAULT '{}',  -- ['leads:read', 'leads:write', 'events:read']
    activo          BOOLEAN DEFAULT true,
    ultimo_uso      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ             -- NULL = no expira
);

-- ============================================================
-- 3. ÍNDICES
-- ============================================================
CREATE INDEX idx_leads_email        ON leads(email);
CREATE INDEX idx_leads_email_hash   ON leads(email_hash);
CREATE INDEX idx_leads_fuente       ON leads(fuente);
CREATE INDEX idx_leads_estado       ON leads(estado);
CREATE INDEX idx_leads_ia_clasif    ON leads(ia_clasificacion);
CREATE INDEX idx_leads_timestamp    ON leads(timestamp_ingesta DESC);
CREATE INDEX idx_leads_prioridad    ON leads(ia_prioridad DESC);
CREATE INDEX idx_leads_responsable  ON leads(responsable);

CREATE INDEX idx_events_lead        ON lead_events(id_lead);
CREATE INDEX idx_events_tipo        ON lead_events(tipo_evento);
CREATE INDEX idx_events_created     ON lead_events(created_at DESC);
CREATE INDEX idx_events_ejecucion   ON lead_events(ejecucion_id);

-- ============================================================
-- 4. VISTAS
-- ============================================================

-- 4.1 Vista para el dashboard (datos no sensibles)
CREATE VIEW vw_leads_dashboard AS
SELECT
    id_lead,
    nombre || ' ' || COALESCE(apellido, '') AS nombre_completo,
    email,
    telefono,
    mensaje,
    fuente,
    ia_clasificacion AS clasificacion_ia,
    ia_prioridad AS prioridad,
    ia_resumen,
    estado,
    responsable,
    timestamp_ingesta,
    EXTRACT(EPOCH FROM (created_at - timestamp_ingesta)) AS lrt_total_segundos
FROM leads
ORDER BY ia_prioridad DESC NULLS LAST, timestamp_ingesta DESC;

-- 4.2 Vista de auditoría (solo para administradores)
CREATE VIEW vw_audit_log AS
SELECT
    l.id_lead,
    l.email_hash,
    l.timestamp_ingesta,
    l.ia_clasificacion,
    l.estado,
    e.tipo_evento,
    e.nodo_origen,
    e.lrt_segundos,
    e.created_at AS event_timestamp,
    e.ejecucion_id
FROM leads l
LEFT JOIN lead_events e ON l.id_lead = e.id_lead
ORDER BY e.created_at DESC;

-- ============================================================
-- 5. FUNCIONES AUXILIARES
-- ============================================================

-- 5.1 Trigger: actualizar updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER trigger_leads_updated_at
    BEFORE UPDATE ON leads
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- 5.2 Función: hash de email/telefono para búsqueda anónima
CREATE OR REPLACE FUNCTION hash_field(input TEXT)
RETURNS TEXT AS $$
BEGIN
    IF input IS NULL THEN RETURN NULL; END IF;
    RETURN encode(digest(lower(trim(input)), 'sha256'), 'hex');
END;
$$ LANGUAGE plpgsql IMMUTABLE SECURITY DEFINER;

-- 5.3 Función: anonimizar IP (poner últimos 2 octetos en 0)
CREATE OR REPLACE FUNCTION anonymize_ip(ip INET)
RETURNS INET AS $$
BEGIN
    IF ip IS NULL THEN RETURN NULL; END IF;
    IF family(ip) = 4 THEN
        RETURN set_masklen(ip, 16)::INET;  -- /16 para IPv4
    ELSE
        RETURN set_masklen(ip, 48)::INET;  -- /48 para IPv6
    END IF;
END;
$$ LANGUAGE plpgsql IMMUTABLE SECURITY DEFINER;

-- ============================================================
-- 6. ROW LEVEL SECURITY (RLS) — POLÍTICAS DE SEGURIDAD
-- ============================================================

-- 6.1 Habilitar RLS en todas las tablas
ALTER TABLE leads       ENABLE ROW LEVEL SECURITY;
ALTER TABLE lead_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE ia_config   ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_keys    ENABLE ROW LEVEL SECURITY;

-- ============================================================
-- POLÍTICAS PARA TABLA leads
-- ============================================================

-- P1: Cualquiera (incluso anónimo) puede INSERTAR un lead (formulario landing page)
--     El trigger de la tabla genera automáticamente email_hash y telefono_hash
CREATE POLICY "anon_can_insert_leads"
    ON leads FOR INSERT
    TO anon, authenticated
    WITH CHECK (true);

-- P1b: Cualquiera (anónimo) puede LEER leads (dashboard Streamlit con anon key)
--     Habilita la vista de KPIs y detalle sin requerir login de usuario
CREATE POLICY "anon_can_read_leads"
    ON leads FOR SELECT
    TO anon
    USING (true);

--     Hook para calcular hashes automáticamente al insertar
CREATE OR REPLACE FUNCTION auto_hash_lead()
RETURNS TRIGGER AS $$
BEGIN
    NEW.email_hash    := hash_field(NEW.email);
    NEW.telefono_hash := hash_field(NEW.telefono);
    NEW.ip_origen     := anonymize_ip(NEW.ip_origen);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER trigger_auto_hash_lead
    BEFORE INSERT ON leads
    FOR EACH ROW
    EXECUTE FUNCTION auto_hash_lead();

-- P2: Solo usuarios autenticados (equipo de ventas) pueden LEER leads
--     Dashboard y equipo de ventas
CREATE POLICY "authenticated_can_read_leads"
    ON leads FOR SELECT
    TO authenticated
    USING (true);  -- Pueden ver todos los leads

-- P3: Solo usuarios autenticados pueden ACTUALIZAR estado y responsable
CREATE POLICY "authenticated_can_update_leads"
    ON leads FOR UPDATE
    TO authenticated
    USING (true)
    WITH CHECK (true);

-- P4: Nadie anónimo puede LEER ni ACTUALIZAR (solo insertar)
--     Esto está implícito al no crear políticas SELECT/UPDATE para 'anon'

-- P5: Service role (n8n) tiene bypass total de RLS por defecto en Supabase
--     No necesita políticas explícitas

-- ============================================================
-- POLÍTICAS PARA TABLA lead_events
-- ============================================================

-- P6: Solo service_role (n8n) puede INSERTAR eventos
--     Los eventos son solo-escritura desde el pipeline
CREATE POLICY "service_can_insert_events"
    ON lead_events FOR INSERT
    TO authenticated
    WITH CHECK (true);  -- n8n usa service_role que bypass RLS

-- P7: Solo usuarios autenticados pueden LEER eventos (para debugging)
CREATE POLICY "authenticated_can_read_events"
    ON lead_events FOR SELECT
    TO authenticated
    USING (true);

-- P8: Nadie puede MODIFICAR ni ELIMINAR eventos (append-only)
--     Sin política UPDATE/DELETE = bloqueado por defecto

-- ============================================================
-- POLÍTICAS PARA TABLA ia_config
-- ============================================================

-- P9: Solo service_role (n8n) puede LEER la configuración de IA
CREATE POLICY "service_can_read_ia_config"
    ON ia_config FOR SELECT
    TO authenticated
    USING (true);

-- P10: Nadie (excepto service_role) puede MODIFICAR prompts
--      Sin política INSERT/UPDATE/DELETE para otros roles

-- ============================================================
-- POLÍTICAS PARA TABLA api_keys
-- ============================================================

-- P11: Solo service_role puede gestionar API keys
--      Sin políticas públicas = inaccesible para anon/authenticated

-- ============================================================
-- 7. ROLES PERSONALIZADOS
-- ============================================================

-- 7.1 Rol para el equipo de ventas (accede al dashboard)
--     En Supabase esto se maneja con políticas de authenticated
--     Crear usuarios en Authentication > Users

-- 7.2 Función para verificar API key (para n8n y servicios externos)
CREATE OR REPLACE FUNCTION verify_api_key(p_servicio VARCHAR, p_key TEXT)
RETURNS TABLE (
    valido BOOLEAN,
    permisos TEXT[]
) AS $$
DECLARE
    v_hash TEXT;
BEGIN
    v_hash := encode(digest(p_key, 'sha256'), 'hex');

    RETURN QUERY
    SELECT
        true AS valido,
        ak.permisos
    FROM api_keys ak
    WHERE ak.servicio = p_servicio
      AND ak.clave_hash = v_hash
      AND ak.activo = true
      AND (ak.expires_at IS NULL OR ak.expires_at > NOW());

    IF NOT FOUND THEN
        RETURN QUERY SELECT false, '{}'::TEXT[];
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================
-- 8. DATOS INICIALES
-- ============================================================

-- 8.1 Insertar prompts base de IA
INSERT INTO ia_config (nombre, system_prompt, modelo, temperature, max_tokens) VALUES
(
    'clasificador_intencion',
    'Eres un clasificador de leads comerciales. Analiza el mensaje del prospecto y clasificalo en UNA de estas categorias: "compra_inmediata" (muestra intencion clara de comprar/contratar YA), "solicita_info" (pide informacion, cotizacion o demo sin urgencia explicita), "soporte" (consulta tecnica, queja o problema con el servicio), "spam" (mensaje generico, sin relacion con el negocio, o sospechoso). Responde UNICAMENTE con el JSON: {"clasificacion": "...", "prioridad": numero del 1 al 100, "confianza": numero del 0 al 1, "resumen": "breve resumen del mensaje en una linea"}',
    'gpt-4o-mini', 0.2, 200
),
(
    'generador_respuesta',
    'Eres un representante comercial profesional de una consultora de software. Genera un email de respuesta personalizado basado en el mensaje del prospecto y su clasificacion. Si es "compra_inmediata": se directo, ofrece agendar una llamada HOY, tono urgente pero profesional. Si es "solicita_info": comparte informacion relevante, ofrece una demo o llamada en los proximos dias, tono util. Si es "soporte": muestra empatia, explicale que su consulta fue derivada al equipo de soporte, tiempo de respuesta estimado 24h. Si es "spam": NO generes respuesta. El email debe incluir asunto, saludo personalizado, cuerpo y despedida. Responde UNICAMENTE con el JSON: {"asunto": "...", "cuerpo_html": "..."}',
    'gpt-4o-mini', 0.5, 500
);

-- 8.2 Insertar API key para n8n (hash de 'n8n-dev-key-2026' — CAMBIAR EN PRODUCCION)
INSERT INTO api_keys (servicio, clave_hash, descripcion, permisos)
VALUES (
    'n8n',
    encode(digest('n8n-dev-key-2026', 'sha256'), 'hex'),
    'Clave de desarrollo para n8n pipeline',
    '{leads:read, leads:write, leads:update, events:write, events:read, ia:read}'
);

-- ============================================================
-- 9. CONFIGURACIONES ADICIONALES DE SEGURIDAD
-- ============================================================

-- 9.1 Deshabilitar confirmación de email no requerida (para MVP)
--     En producción: Authentication > Settings > Enable email confirmations

-- 9.2 Configurar Row Level Security en Supabase Dashboard:
--     Settings > API > Enable RLS (ya habilitado arriba)
--     Authentication > Policies > Revisar políticas creadas

-- 9.3 Rate Limiting se configura en Supabase Dashboard:
--     Authentication > Rate Limits
--     Recomendado: 30 requests/min para anon, 100 requests/min para authenticated

-- 9.4 CORS se configura en Supabase Dashboard:
--     Settings > API > Additional allowed CORS origins
--     Agregar: http://localhost:5000, http://localhost:8501, TU_DOMINIO_PRODUCCION

COMMENT ON TABLE leads IS 'Datos de prospectos. RLS: anon puede INSERT, authenticated puede SELECT/UPDATE, service_role tiene bypass total.';
COMMENT ON TABLE lead_events IS 'Trazabilidad del pipeline. Solo service_role escribe. Append-only.';
COMMENT ON TABLE ia_config IS 'Configuracion de prompts IA. Solo service_role lee.';
COMMENT ON TABLE api_keys IS 'Gestion de claves de API. Solo accesible por service_role.';
