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

```bash
pytest tests/ -v
```
