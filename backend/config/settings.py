"""
Application Settings — loaded from .env via pydantic-settings
"""
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Optional


class Settings(BaseSettings):
    # ------------------------------------------------------------------ App
    APP_NAME: str = "Attendance System API"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "RBAC Attendance System with Face Recognition"
    ENVIRONMENT: str = "development"   # development | staging | production
    DEBUG: bool = True

    SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION_USE_LONG_RANDOM_STRING"

    # ------------------------------------------------------------------ Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ------------------------------------------------------------------ API
    API_V1_PREFIX: str = "/api/v1"

    # ------------------------------------------------------------------ Database
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 5432
    DATABASE_NAME: str = "attendance_db"
    DATABASE_USER: str = "postgres"
    DATABASE_PASSWORD: str = "postgres"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )

    @property
    def DATABASE_URL_SAFE(self) -> str:
        return (
            f"postgresql://{self.DATABASE_USER}:***"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )

    # ------------------------------------------------------------------ JWT
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8   # 8 hours
    JWT_ISSUER: str = "fast-absen"
    JWT_AUDIENCE: str = "fast-absen-client"

    # ------------------------------------------------------------------ CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    # ------------------------------------------------------------------ Logging
    LOG_LEVEL: str = "DEBUG"
    LOG_DIR: str = "logs"

    # ------------------------------------------------------------------ Bootstrap super-admin
    ADMIN_USERNAME: Optional[str] = None
    ADMIN_PASSWORD: Optional[str] = None
    ADMIN_ID_PEGAWAI: Optional[str] = None
    ADMIN_NIP: Optional[str] = None
    ADMIN_NAMA: Optional[str] = None
    ADMIN_JENIS_KELAMIN: Optional[str] = None
    ADMIN_TEMPAT_LAHIR: Optional[str] = None
    ADMIN_TANGGAL_LAHIR: Optional[str] = None
    ADMIN_ALAMAT: Optional[str] = None
    ADMIN_STATUS: Optional[str] = "Aktif"
    ADMIN_FORCE_UPDATE: bool = False

    # ------------------------------------------------------------------ Face Recognition
    FACE_SIMILARITY_THRESHOLD: float = 0.5
    FACE_MAX_EMBEDDINGS_PER_USER: int = 5
    FACE_MODEL_NAME: str = "buffalo_l"

    # ------------------------------------------------------------------ Upload
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = 5

    # ------------------------------------------------------------------ Scheduler
    SESSION_CLEANUP_INTERVAL_HOURS: int = 6   # seberapa sering job cleanup berjalan
    SESSION_EXPIRY_HOURS: int = 8             # sesi idle > N jam dianggap expired

    # ------------------------------------------------------------------ Helpers
    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def is_staging(self) -> bool:
        return self.ENVIRONMENT == "staging"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()
