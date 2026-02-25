# Attendance System API

FastAPI backend dengan Clean Architecture, RBAC, dan Face Recognition menggunakan InsightFace.

## Tech Stack

- **FastAPI** 0.109+ — ASGI web framework
- **SQLAlchemy** 2.0 (async) — ORM
- **PostgreSQL** 16 + **pgvector** — database + vector search
- **InsightFace** (buffalo_l) — face recognition
- **Pydantic** v2 — data validation
- **python-jose** — JWT auth
- **APScheduler** — background tasks

## Arsitektur

```
API Endpoint → Service → Repository → Model
```

```
backend/
├── api/v1/endpoints/    # Route handlers
├── services/            # Business logic
├── repositories/        # Database access layer
├── models/             # SQLAlchemy ORM models
├── schemas/            # Pydantic schemas
├── config/             # Settings & DB config
└── utils/              # Logger, security, middleware, etc.
```

## Setup

### 1. Buat database PostgreSQL

```sql
CREATE DATABASE attendance_db;
\c attendance_db
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
```

Kemudian jalankan schema:

```bash
psql -U postgres -d attendance_db -f database/init.sql
```

### 2. Install dependencies

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Konfigurasi environment

```bash
cp .env.example .env
# Edit .env sesuai konfigurasi lokal
```

### 4. Jalankan aplikasi

```bash
python run.py
# atau
uvicorn main:app --reload
```

Dokumentasi API tersedia di: http://localhost:8000/docs

## Roles & Permissions

| Role | Akses |
|------|-------|
| superadmin | Semua akses (bootstrap via env) |
| admin | Semua kecuali delete role/permission |
| kepala_unit | Baca data + update absensi unit |
| pegawai | Absensi sendiri + face verify |

## Endpoints Utama

| Method | Path | Deskripsi |
|--------|------|-----------|
| GET | /api/v1/halo | Health check |
| POST | /api/v1/auth/login | Login |
| GET | /api/v1/auth/me | Info user aktif |
| GET | /api/v1/pegawai | Daftar pegawai |
| POST | /api/v1/absensi/check-in | Absen masuk |
| POST | /api/v1/absensi/check-out | Absen keluar |
| POST | /api/v1/face/enroll/{id} | Daftarkan wajah |
| GET | /api/v1/stats/overview | Statistik kehadiran |

## Test

Pastikan server **tidak** sedang berjalan di port 8000 sebelum menjalankan test.

Test suite tidak mengirim request HTTP sungguhan ke jaringan. Sebagai gantinya,
`httpx.AsyncClient` dipasangkan langsung ke objek aplikasi FastAPI melalui
`ASGITransport` — request diproses di dalam proses Python yang sama tanpa membuka
socket atau port. Artinya: server tidak perlu dinyalakan, test lebih cepat, dan
tidak ada konflik port. Port 8000 tetap perlu bebas hanya jika ada kode yang
secara eksplisit mencoba bind ke sana saat import (yang tidak terjadi di sini).

### Jalankan semua test

```bash
cd backend
source venv/bin/activate
pytest tests/ -v
```

### Jalankan test tertentu

```bash
# Hanya health check
pytest tests/test_health.py -v

# Hanya auth
pytest tests/test_auth.py -v

# Satu test spesifik
pytest tests/test_auth.py::test_login_admin_success -v
```

### Opsi berguna

```bash
# Tampilkan print/log output
pytest tests/ -v -s

# Berhenti di failure pertama
pytest tests/ -v -x

# Tampilkan 10 test terlambat
pytest tests/ -v --durations=10

# Hanya re-run test yang gagal sebelumnya
pytest tests/ -v --lf
```

### Struktur fixture

| Fixture | Digunakan untuk |
|---------|----------------|
| `client` | Test tanpa data (health check, validasi 422) |
| `client_with_db` | Test yang butuh user `tst_admin` / `tst_user` di DB |
| `db_with_data` | Setup otomatis — seed + cleanup test data di PostgreSQL |
| `admin_token` | JWT token untuk `tst_admin` |
| `user_token` | JWT token untuk `tst_user` |

> Test menggunakan PostgreSQL nyata (bukan SQLite). Pastikan DB aktif dan
> konfigurasi `.env` sudah benar sebelum menjalankan test.
