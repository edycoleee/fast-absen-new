-- ============================================================
-- INIT DATABASE SCHEMA FOR ATTENDANCE SYSTEM (RBAC)
-- PostgreSQL 16 + pgvector
-- ============================================================

-- ============================================================
-- EXTENSIONS
-- ============================================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";       -- For face embeddings (pgvector)

-- ============================================================
-- UTILITY: auto-update updated_at column
-- ============================================================
CREATE OR REPLACE FUNCTION trigger_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- TABLE: unit  (Master Unit / Instalasi)
-- ============================================================
CREATE TABLE unit (
    id_unit   INTEGER PRIMARY KEY,
    nama_unit VARCHAR(150) UNIQUE NOT NULL,
    status    VARCHAR(20)  NOT NULL DEFAULT 'Aktif'
                CHECK (status IN ('Aktif', 'Tidak Aktif')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TRIGGER set_unit_updated_at
    BEFORE UPDATE ON unit
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- ============================================================
-- TABLE: roles
-- ============================================================
CREATE TABLE roles (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TRIGGER set_roles_updated_at
    BEFORE UPDATE ON roles
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- ============================================================
-- TABLE: permissions
-- ============================================================
CREATE TABLE permissions (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100) UNIQUE NOT NULL,   -- e.g. "absensi:read", "user:write"
    description TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABLE: role_permissions  (RBAC many-to-many)
-- ============================================================
CREATE TABLE role_permissions (
    role_id       INTEGER NOT NULL REFERENCES roles(id)       ON DELETE CASCADE,
    permission_id INTEGER NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

-- ============================================================
-- TABLE: pegawai
-- ============================================================
CREATE TABLE pegawai (
    id_pegawai    VARCHAR(20) PRIMARY KEY,
    nip           VARCHAR(50),
    nama          VARCHAR(255) NOT NULL,
    id_unit       INTEGER REFERENCES unit(id_unit) ON DELETE SET NULL,
    kepala_id_unit INTEGER REFERENCES unit(id_unit) ON DELETE SET NULL,
    jenis_kelamin VARCHAR(10)  CHECK (jenis_kelamin IN ('Laki-Laki', 'Perempuan')),
    tempat_lahir  VARCHAR(100),
    tanggal_lahir DATE,
    alamat        TEXT,
    status        VARCHAR(20)  NOT NULL DEFAULT 'Aktif'
                    CHECK (status IN ('Aktif', 'Non-Aktif')),
    foto          VARCHAR(255),
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_pegawai_unit        ON pegawai(id_unit);
CREATE INDEX idx_pegawai_kepala_unit ON pegawai(kepala_id_unit);
CREATE INDEX idx_pegawai_status      ON pegawai(status);

CREATE TRIGGER set_pegawai_updated_at
    BEFORE UPDATE ON pegawai
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- ============================================================
-- TABLE: users
-- ============================================================
CREATE TABLE users (
    id            SERIAL PRIMARY KEY,
    id_pegawai    VARCHAR(20) UNIQUE REFERENCES pegawai(id_pegawai) ON DELETE SET NULL,
    username      VARCHAR(100) UNIQUE NOT NULL,
    password_hash TEXT        NOT NULL,
    is_active     BOOLEAN     DEFAULT TRUE,
    last_login    TIMESTAMPTZ,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_users_pegawai ON users(id_pegawai);

CREATE TRIGGER set_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- ============================================================
-- TABLE: user_roles  (user <> role many-to-many)
-- ============================================================
CREATE TABLE user_roles (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, role_id)
);

-- ============================================================
-- TABLE: user_sessions
-- ============================================================
CREATE TABLE user_sessions (
    id           SERIAL PRIMARY KEY,
    user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Session Management
    session_id   VARCHAR(255) UNIQUE,
    token        TEXT,                          -- JWT (hashed or raw)

    -- Device & Browser Info
    device_type  VARCHAR(20)  CHECK (device_type IN ('web', 'mobile', 'tablet')),
    user_agent   TEXT,
    browser      VARCHAR(100),
    os           VARCHAR(100),
    device_model VARCHAR(250),

    -- Network Info
    ip_address   INET NOT NULL,
    country      VARCHAR(100),
    city         VARCHAR(100),

    -- Mobile-specific (NULL for web)
    uid          VARCHAR(50),
    player_id    VARCHAR(50),

    -- Session Lifecycle
    login_at      TIMESTAMPTZ DEFAULT NOW(),
    logout_at     TIMESTAMPTZ,                 -- NULL = still active
    last_activity TIMESTAMPTZ DEFAULT NOW(),
    expires_at    TIMESTAMPTZ,

    -- Security
    login_method VARCHAR(20) DEFAULT 'password'
        CHECK (login_method IN ('password', 'face', 'password_face')),
    login_status VARCHAR(20) DEFAULT 'success'
        CHECK (login_status IN ('success', 'failed', 'expired')),
    failed_reason TEXT,

    -- Metadata
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    updated_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_sessions_user_id    ON user_sessions(user_id);
CREATE INDEX idx_sessions_session_id ON user_sessions(session_id);
CREATE INDEX idx_sessions_ip         ON user_sessions(ip_address);
CREATE INDEX idx_sessions_login_at   ON user_sessions(login_at DESC);
CREATE INDEX idx_sessions_active     ON user_sessions(user_id) WHERE logout_at IS NULL;

CREATE TRIGGER set_sessions_updated_at
    BEFORE UPDATE ON user_sessions
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- ============================================================
-- TABLE: absensi
-- ============================================================
CREATE TABLE absensi (
    id            SERIAL PRIMARY KEY,
    id_pegawai    VARCHAR(20) NOT NULL REFERENCES pegawai(id_pegawai) ON DELETE RESTRICT,
    tanggal       DATE        NOT NULL DEFAULT CURRENT_DATE,
    jam_masuk     TIMESTAMPTZ,
    jam_keluar    TIMESTAMPTZ,

    -- Face verification result
    face_verified_masuk  BOOLEAN DEFAULT FALSE,
    face_verified_keluar BOOLEAN DEFAULT FALSE,
    face_similarity_masuk  FLOAT,             -- Cosine similarity saat check-in
    face_similarity_keluar FLOAT,             -- Cosine similarity saat check-out

    status       VARCHAR(20)  NOT NULL DEFAULT 'HADIR'
                    CHECK (status IN ('HADIR', 'IZIN', 'SAKIT', 'ALPHA', 'TERLAMBAT', 'CUTI')),
    keterangan   TEXT,
    dokumen_pendukung VARCHAR(255),

    ip_address   INET,
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    updated_at   TIMESTAMPTZ DEFAULT NOW(),

    -- 1 record per employee per day
    CONSTRAINT uq_absensi_pegawai_tanggal UNIQUE (id_pegawai, tanggal)
);

CREATE INDEX idx_absensi_pegawai ON absensi(id_pegawai);
CREATE INDEX idx_absensi_tanggal ON absensi(tanggal DESC);
CREATE INDEX idx_absensi_status  ON absensi(status);

CREATE TRIGGER set_absensi_updated_at
    BEFORE UPDATE ON absensi
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- ============================================================
-- TABLE: face_embeddings
-- ============================================================
CREATE TABLE face_embeddings (
    id            SERIAL PRIMARY KEY,
    user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    embedding     VECTOR(512) NOT NULL,        -- InsightFace 512-dim ArcFace embedding
    image_path    VARCHAR(500),
    quality_score FLOAT,                       -- Detection confidence (0-1)
    is_active     BOOLEAN DEFAULT TRUE,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_face_embeddings_user_id ON face_embeddings(user_id);
-- Approximate nearest-neighbor cosine search (requires pgvector >= 0.5)
CREATE INDEX idx_face_embeddings_ivfflat
    ON face_embeddings USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE TRIGGER set_face_updated_at
    BEFORE UPDATE ON face_embeddings
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- ============================================================
-- SEED: Default roles
-- ============================================================
INSERT INTO roles (name, description) VALUES
    ('superadmin',  'Full access to all resources'),
    ('admin',       'Manage employees, attendance and reports'),
    ('kepala_unit', 'View and manage their own unit attendance'),
    ('pegawai',     'Self check-in / check-out only');

-- ============================================================
-- SEED: Default permissions
-- ============================================================
INSERT INTO permissions (name, description) VALUES
    -- Authentication
    ('user.login',              'Login ke aplikasi'),
    -- User Management
    ('users.read',              'Melihat data user'),
    ('users.create',            'Membuat user baru'),
    ('users.update',            'Mengubah data user'),
    ('users.delete',            'Menghapus user'),
    -- Role Management
    ('roles.read',              'Melihat data role'),
    ('roles.create',            'Membuat role baru'),
    ('roles.update',            'Mengubah role'),
    ('roles.delete',            'Menghapus role'),
    -- Permission Management
    ('permissions.read',        'Melihat data permission'),
    ('permissions.create',      'Membuat permission baru'),
    ('permissions.update',      'Mengubah permission'),
    ('permissions.delete',      'Menghapus permission'),
    -- Pegawai Management
    ('pegawai.read',            'Melihat data pegawai'),
    ('pegawai.create',          'Membuat data pegawai baru'),
    ('pegawai.update',          'Mengubah data pegawai'),
    ('pegawai.delete',          'Menghapus data pegawai'),
    -- Unit Management
    ('unit.read',               'Melihat data unit'),
    ('unit.create',             'Membuat data unit baru'),
    ('unit.update',             'Mengubah data unit'),
    ('unit.delete',             'Menghapus data unit'),
    -- Absensi
    ('absensi.read',            'Melihat data absensi (history, summary, today)'),
    ('absensi.create',          'Membuat absensi (check-in)'),
    ('absensi.update',          'Mengubah absensi (check-out, admin edit)'),
    ('absensi.delete',          'Menghapus absensi (admin only)'),
    -- User Sessions
    ('user_sessions.read',      'Melihat data sesi pengguna'),
    ('user_sessions.create',    'Membuat sesi pengguna baru'),
    ('user_sessions.update',    'Mengubah status session'),
    ('user_sessions.delete',    'Menghapus session'),
    -- Face Recognition
    ('face.enroll',             'Mendaftarkan data wajah'),
    ('face.verify',             'Verifikasi wajah untuk absensi'),
    ('face.manage',             'Kelola semua data wajah'),
    -- Reports
    ('report.read',             'Melihat dan generate laporan'),
    -- Legacy
    ('login_absensi.read',      'Melihat data sesi absensi (legacy)'),
    ('login_absensi.create',    'Membuat data sesi absensi (legacy)');

-- ============================================================
-- SEED: Map permissions to roles
-- ============================================================
-- superadmin: all permissions
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p WHERE r.name = 'superadmin';

-- admin: semua kecuali roles.delete, permissions.delete
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r
JOIN permissions p ON p.name IN (
    'user.login',
    'users.read','users.create','users.update','users.delete',
    'roles.read','roles.create','roles.update',
    'permissions.read',
    'pegawai.read','pegawai.create','pegawai.update','pegawai.delete',
    'unit.read','unit.create','unit.update','unit.delete',
    'absensi.read','absensi.create','absensi.update','absensi.delete',
    'user_sessions.read','user_sessions.update','user_sessions.delete',
    'face.enroll','face.verify','face.manage',
    'report.read',
    'login_absensi.read','login_absensi.create'
)
WHERE r.name = 'admin';

-- kepala_unit: baca unit sendiri + kelola absensi unit
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r
JOIN permissions p ON p.name IN (
    'user.login',
    'unit.read',
    'pegawai.read',
    'absensi.read','absensi.update',
    'user_sessions.read',
    'face.verify',
    'report.read'
)
WHERE r.name = 'kepala_unit';

-- pegawai: absensi diri sendiri
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r
JOIN permissions p ON p.name IN (
    'user.login',
    'absensi.read','absensi.create','absensi.update',
    'face.verify'
)
WHERE r.name = 'pegawai';

-- Master unit
INSERT INTO unit (id_unit, nama_unit, status) VALUES
(1, 'Struktural', 'Aktif'),
(2, 'Kepala Ruang / Kepala Instalasi', 'Aktif'),
(3, 'Bidang Umum dan Kepegawaian', 'Aktif'),
(4, 'Keuangan', 'Aktif'),
(5, 'Instalasi SIMRS', 'Aktif'),
(6, 'Adenium', 'Aktif'),
(7, 'Poliklinik', 'Aktif'),
(8, 'Tulip', 'Aktif'),
(9, 'Anyelir', 'Aktif'),
(10, 'Lavender', 'Aktif'),
(11, 'Begonia', 'Aktif'),
(12, 'Edelweiss', 'Aktif'),
(13, 'Jasmine', 'Aktif'),
(14, 'Azalea', 'Aktif'),
(15, 'Instalasi Gawat Darurat', 'Aktif'),
(16, 'Instalasi Pemulasaran Jenazah', 'Aktif'),
(17, 'IPSRS', 'Aktif'),
(18, 'Instalasi Gizi', 'Aktif'),
(19, 'Loundry dan CSSD', 'Aktif'),
(20, 'Laboratorium', 'Aktif'),
(21, 'Farmasi', 'Aktif'),
(22, 'Rekam Medis', 'Aktif'),
(23, 'Radiologi', 'Aktif'),
(24, 'Bidang Keperawatan', 'Aktif'),
(25, 'Bidang Pelayanan', 'Aktif'),
(26, 'Bidang Pengembangan RS, Humas, dan Rekam Medis', 'Aktif'),
(27, 'MPP', 'Aktif'),
(28, 'Bagian Program', 'Aktif'),
(29, 'Tata Usaha', 'Aktif'),
(30, 'Komite Keperawatan', 'Aktif'),
(31, 'SIPP dan Informasi', 'Aktif'),
(32, 'Kasir', 'Aktif'),
(33, 'Pendaftaran TPPGD/TPPRI', 'Aktif'),
(34, 'Rehabilitasi Medik', 'Aktif'),
(35, 'Driver Ambulance', 'Aktif'),
(36, 'Instalasi Bedah Sentral', 'Aktif'),
(37, 'ICU', 'Aktif'),
(38, 'Security', 'Aktif'),
(39, 'Komite PPI', 'Aktif'),
(40, 'Dokter Umum', 'Aktif'),
(41, 'Pendaftaran TPPRJ', 'Aktif'),
(42, 'Holding Bed', 'Aktif'),
(43, 'Dokter Spesialis', 'Aktif'),
(99, 'Z-Sudah Tidak Aktif', 'Aktif')
ON CONFLICT (id_unit) DO NOTHING;

