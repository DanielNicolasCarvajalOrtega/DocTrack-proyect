
-- ── ENUMS ────────────────────────────────────────────────────

CREATE TYPE billing_plan AS ENUM ('prueba', 'basico', 'pro', 'empresas');
CREATE TYPE company_role AS ENUM ('admin', 'auditor', 'supervisor', 'tecnicos', 'operadores');
CREATE TYPE machine_status AS ENUM ('operativa', 'mantenimiento', 'fallas', 'descontinuada');
CREATE TYPE document_type AS ENUM ('manuales', 'certificados', 'instrucciones_seguridad', 'mantenimiento', 'hoja_tecnica', 'procedimientos', 'otros');
CREATE TYPE document_status AS ENUM ('activo', 'expirado', 'sustituido', 'borrador');

-- FIX SYNC: Alineado con MaintenanceType del modelo Python (6 valores)
-- El SQL anterior solo tenía 4 valores, el modelo Python tenía 6 → desincronizados
CREATE TYPE maintenance_type AS ENUM (
    'preventivo',
    'reporte_falla',
    'correctivo',
    'predictivo',
    'inspeccion',
    'bloqueo_loto'
);

CREATE TYPE task_status AS ENUM ('pendiente', 'en_progreso', 'completado', 'cancelado', 'vencido');
CREATE TYPE task_priority AS ENUM ('bajo', 'mediano', 'alto', 'critico');


-- ── USERS ────────────────────────────────────────────────────

CREATE TABLE users (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    first_name       VARCHAR(100) NOT NULL,
    last_name        VARCHAR(100) NOT NULL,
    email            VARCHAR(255) UNIQUE NOT NULL,
    password_hash    VARCHAR(255) NOT NULL,
    phone            VARCHAR(20),
    avatar_url       VARCHAR(500),
    is_super_admin   BOOLEAN DEFAULT FALSE NOT NULL,
    email_verified   BOOLEAN DEFAULT FALSE NOT NULL,
    last_login_at    TIMESTAMP,
    is_active        BOOLEAN DEFAULT TRUE NOT NULL,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_users_email          ON users(email);
CREATE INDEX ix_users_is_active      ON users(is_active);
CREATE INDEX ix_users_is_super_admin ON users(is_super_admin);


-- ── COMPANIES ─────────────────────────────────────────────────

CREATE TABLE companies (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                  VARCHAR(200) UNIQUE NOT NULL,
    slug                  VARCHAR(100) UNIQUE NOT NULL,
    billing_plan          billing_plan DEFAULT 'prueba' NOT NULL,
    max_users             INTEGER DEFAULT 10 NOT NULL,
    max_plants            INTEGER DEFAULT 1 NOT NULL,
    max_storage_gb        INTEGER DEFAULT 5 NOT NULL,
    trial_ends_at         TIMESTAMP,
    subscription_ends_at  TIMESTAMP,
    contact_email         VARCHAR(255),
    contact_phone         VARCHAR(50),
    address               TEXT,
    logo_url              VARCHAR(500),
    primary_color         VARCHAR(7) DEFAULT '#3B82F6',
    is_active             BOOLEAN DEFAULT TRUE NOT NULL,
    created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_companies_slug           ON companies(slug);
CREATE INDEX ix_companies_active         ON companies(is_active);
CREATE INDEX ix_companies_billing_active ON companies(billing_plan, is_active);
CREATE INDEX ix_companies_created_at     ON companies(created_at DESC);


-- ── COMPANY USERS ─────────────────────────────────────────────

CREATE TABLE company_users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id    UUID NOT NULL,
    user_id       UUID NOT NULL,
    role          company_role DEFAULT 'operadores' NOT NULL,
    invited_by_id UUID,
    joined_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active     BOOLEAN DEFAULT TRUE NOT NULL,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (company_id)    REFERENCES companies(id) ON DELETE RESTRICT,
    FOREIGN KEY (user_id)       REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (invited_by_id) REFERENCES users(id) ON DELETE SET NULL,

    UNIQUE (company_id, user_id)
);

CREATE INDEX ix_company_users_active  ON company_users(company_id, is_active);
CREATE INDEX ix_user_company_active   ON company_users(user_id, is_active);
CREATE INDEX ix_company_user_lookup   ON company_users(company_id, user_id);
CREATE INDEX ix_company_role_lookup   ON company_users(company_id, role);
CREATE INDEX ix_company_users_role    ON company_users(role);


-- ── PLANTS ───────────────────────────────────────────────────

CREATE TABLE plants (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name           VARCHAR(200) NOT NULL,
    company_id     UUID NOT NULL,
    location       VARCHAR(300),
    description    TEXT,
    logo_url       VARCHAR(500),
    is_active      BOOLEAN DEFAULT TRUE NOT NULL,
    created_by_id  UUID,
    updated_by_id  UUID,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (company_id)    REFERENCES companies(id) ON DELETE RESTRICT,
    FOREIGN KEY (created_by_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (updated_by_id) REFERENCES users(id) ON DELETE SET NULL,

    UNIQUE (company_id, name)
);

CREATE INDEX ix_plants_company_id    ON plants(company_id);
CREATE INDEX ix_plant_company_active ON plants(company_id, is_active);


-- ── USER PLANT ACCESS ─────────────────────────────────────────
-- FIX: Tabla alineada con BaseModel de Python (agrega id, is_active, updated_at)
-- FIX: Reemplaza UNIQUE(user_id, plant_id) por partial index con WHERE is_active = true
--      Permite re-agregar un usuario a una planta después de ser removido (is_active=False)
--      sin conflicto de duplicidad.

CREATE TABLE user_plant_access (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID NOT NULL,
    plant_id   UUID NOT NULL,
    is_active  BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id)  REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (plant_id) REFERENCES plants(id) ON DELETE CASCADE
);

CREATE INDEX ix_user_plant_access_user  ON user_plant_access(user_id);
CREATE INDEX ix_user_plant_access_plant ON user_plant_access(plant_id);

-- Partial unique index: solo un acceso activo por usuario+planta
CREATE UNIQUE INDEX uq_active_user_plant_access
    ON user_plant_access(user_id, plant_id)
    WHERE is_active = true;


-- ── AREAS ────────────────────────────────────────────────────

CREATE TABLE areas (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name           VARCHAR(200) NOT NULL,
    description    TEXT,
    plant_id       UUID NOT NULL,
    is_active      BOOLEAN DEFAULT TRUE NOT NULL,
    created_by_id  UUID,
    updated_by_id  UUID,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (plant_id)      REFERENCES plants(id) ON DELETE RESTRICT,
    FOREIGN KEY (created_by_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (updated_by_id) REFERENCES users(id) ON DELETE SET NULL,

    UNIQUE (plant_id, name)
);

CREATE INDEX ix_areas_plant_id    ON areas(plant_id);
CREATE INDEX ix_area_plant_active ON areas(plant_id, is_active);


-- ── USER AREA ACCESS ──────────────────────────────────────────
-- FIX: Mismo patrón que user_plant_access
-- FIX: Partial index en lugar de UNIQUE para permitir re-acceso tras remoción

CREATE TABLE user_area_access (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID NOT NULL,
    area_id    UUID NOT NULL,
    is_active  BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (area_id) REFERENCES areas(id) ON DELETE CASCADE
);

CREATE INDEX ix_user_area_access_user ON user_area_access(user_id);
CREATE INDEX ix_user_area_access_area ON user_area_access(area_id);

-- Partial unique index: solo un acceso activo por usuario+área
CREATE UNIQUE INDEX uq_active_user_area_access
    ON user_area_access(user_id, area_id)
    WHERE is_active = true;


-- ── MACHINES ─────────────────────────────────────────────────

CREATE TABLE machines (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(200) NOT NULL,
    model           VARCHAR(200),
    brand           VARCHAR(200),
    serial_number   VARCHAR(100) UNIQUE,
    description     TEXT,
    location_detail VARCHAR(300),
    status          machine_status DEFAULT 'operativa' NOT NULL,
    qr_code         VARCHAR(100) UNIQUE NOT NULL,
    image_url       VARCHAR(500),
    area_id         UUID NOT NULL,
    requires_pin    BOOLEAN DEFAULT FALSE NOT NULL,
    -- NOTA: security_pin debe llegar HASHEADO con bcrypt desde el Service, nunca en texto plano
    security_pin    VARCHAR(255),
    is_active       BOOLEAN DEFAULT TRUE NOT NULL,
    created_by_id   UUID,
    updated_by_id   UUID,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (area_id)         REFERENCES areas(id) ON DELETE RESTRICT,
    FOREIGN KEY (created_by_id)   REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (updated_by_id)   REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX ix_machines_area_id    ON machines(area_id);
CREATE INDEX ix_machine_area_active ON machines(area_id, is_active);
CREATE INDEX ix_machine_qr          ON machines(qr_code);
CREATE INDEX ix_machine_status      ON machines(status);


-- ── MACHINE PIN AUDIT LOGS ───────────────────────────────────

CREATE TABLE machine_pin_audit_logs (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    machine_id     UUID NOT NULL,
    changed_by_id  UUID NOT NULL,
    action         VARCHAR(50) NOT NULL,
    changed_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,

    FOREIGN KEY (machine_id)    REFERENCES machines(id) ON DELETE CASCADE,
    FOREIGN KEY (changed_by_id) REFERENCES users(id) ON DELETE RESTRICT
);

CREATE INDEX ix_machine_pin_logs_machine ON machine_pin_audit_logs(machine_id);


-- ── DOCUMENTS ────────────────────────────────────────────────

CREATE TABLE documents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title           VARCHAR(300) NOT NULL,
    description     TEXT,
    doc_type        document_type DEFAULT 'otros' NOT NULL,
    status          document_status DEFAULT 'activo' NOT NULL,
    version         VARCHAR(20) DEFAULT '1.0' NOT NULL,
    version_number  INTEGER DEFAULT 1 NOT NULL,
    file_url        VARCHAR(1000) NOT NULL,
    file_name       VARCHAR(300) NOT NULL,
    file_size       INTEGER,
    file_size_gb    NUMERIC(10, 2) DEFAULT 0,
    file_type       VARCHAR(50),
    valid_from      TIMESTAMP,
    valid_until     TIMESTAMP,

    -- FIX: era NOT NULL con ON DELETE SET NULL → contradicción que causa crash en PostgreSQL
    --      si el usuario es eliminado, PostgreSQL intenta poner NULL pero el campo no lo permite
    uploaded_by_id  UUID,
    updated_by_id   UUID,

    machine_id      UUID NOT NULL,
    company_id      UUID NOT NULL,
    supersedes_id   UUID,
    is_active       BOOLEAN DEFAULT TRUE NOT NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (uploaded_by_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (updated_by_id)  REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (machine_id)     REFERENCES machines(id) ON DELETE RESTRICT,
    FOREIGN KEY (company_id)     REFERENCES companies(id) ON DELETE RESTRICT,
    FOREIGN KEY (supersedes_id)  REFERENCES documents(id) ON DELETE SET NULL
);

CREATE INDEX ix_documents_machine_id      ON documents(machine_id);
CREATE INDEX ix_documents_company_id      ON documents(company_id);
CREATE INDEX ix_documents_uploaded_by_id  ON documents(uploaded_by_id);
CREATE INDEX ix_document_machine_active   ON documents(machine_id, is_active);
CREATE INDEX ix_document_company_active   ON documents(company_id, is_active);
CREATE INDEX ix_document_status           ON documents(status);
CREATE INDEX ix_document_valid_until      ON documents(valid_until);
-- índices para auditoría y reportes por empresa
CREATE INDEX ix_document_company_status   ON documents(company_id, status);
CREATE INDEX ix_document_company_type     ON documents(company_id, doc_type);


-- ── DOCUMENT READ CONFIRMATIONS ───────────────────────────────

CREATE TABLE document_read_confirmations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id     UUID NOT NULL,
    user_id         UUID NOT NULL,
    read_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    confirmed_at    TIMESTAMP,
    risks_accepted  BOOLEAN DEFAULT FALSE NOT NULL,
   
    signature_hash  VARCHAR(255) UNIQUE,
    notes           TEXT,
    is_active       BOOLEAN DEFAULT TRUE NOT NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE RESTRICT,
    FOREIGN KEY (user_id)     REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX ix_doc_confirmation_document          ON document_read_confirmations(document_id);
CREATE INDEX ix_doc_confirmation_user              ON document_read_confirmations(user_id);
CREATE INDEX ix_doc_read_confirmations_document_id ON document_read_confirmations(document_id, is_active);
CREATE INDEX ix_doc_read_confirmations_user_id     ON document_read_confirmations(user_id, is_active);


-- ── MAINTENANCE TASKS ─────────────────────────────────────────

CREATE TABLE maintenance_tasks (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title               VARCHAR(300) NOT NULL,
    description         TEXT,
    maintenance_type    maintenance_type DEFAULT 'preventivo' NOT NULL,
    status              task_status DEFAULT 'pendiente' NOT NULL,
    priority            task_priority DEFAULT 'mediano' NOT NULL,
    scheduled_date      TIMESTAMP,
    started_at          TIMESTAMP,
    completed_at        TIMESTAMP,
    due_date            TIMESTAMP,

    is_loto_required    BOOLEAN DEFAULT FALSE NOT NULL,
    loto_applied_at     TIMESTAMP,
    loto_applied_by_id  UUID,
    evidence_photo_url  VARCHAR(500),
    completion_notes    TEXT,

    machine_id          UUID NOT NULL,
    assigned_to_id      UUID,
    created_by_id       UUID NOT NULL,
    updated_by_id       UUID,
    is_active           BOOLEAN DEFAULT TRUE NOT NULL,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (machine_id)         REFERENCES machines(id) ON DELETE RESTRICT,
    FOREIGN KEY (assigned_to_id)     REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (created_by_id)      REFERENCES users(id) ON DELETE RESTRICT,
    FOREIGN KEY (updated_by_id)      REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (loto_applied_by_id) REFERENCES users(id) ON DELETE RESTRICT
);

CREATE INDEX ix_maintenance_machine    ON maintenance_tasks(machine_id);
CREATE INDEX ix_maintenance_assigned   ON maintenance_tasks(assigned_to_id);
CREATE INDEX ix_maintenance_created_by ON maintenance_tasks(created_by_id);
CREATE INDEX ix_maintenance_status     ON maintenance_tasks(status);
CREATE INDEX ix_maintenance_priority   ON maintenance_tasks(priority);
CREATE INDEX ix_maintenance_due_date   ON maintenance_tasks(due_date);
--  gerencia/auditoría: "tareas críticas pendientes vencidas"
CREATE INDEX ix_maintenance_status_due ON maintenance_tasks(status, due_date);


-- ── MAINTENANCE ACTIVITY LOGS ─────────────────────────────────

CREATE TABLE maintenance_activity_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id         UUID NOT NULL,
    user_id         UUID NOT NULL,
    previous_status task_status,
    new_status      task_status NOT NULL,
    notes           TEXT,
    is_active       BOOLEAN DEFAULT TRUE NOT NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (task_id)  REFERENCES maintenance_tasks(id) ON DELETE RESTRICT,
    FOREIGN KEY (user_id)  REFERENCES users(id) ON DELETE RESTRICT
);

CREATE INDEX ix_maintenance_activity_logs_task_id  ON maintenance_activity_logs(task_id);
CREATE INDEX ix_maintenance_activity_logs_user_id  ON maintenance_activity_logs(user_id);
CREATE INDEX ix_activity_log_created_at            ON maintenance_activity_logs(created_at DESC);

CREATE INDEX ix_activity_log_task_created          ON maintenance_activity_logs(task_id, created_at DESC);