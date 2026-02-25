"""
Application Settings — loaded from .env via pydantic-settings
"""
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file"""

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
    WORKERS: int = 4

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
    def ASYNC_DATABASE_URL(self) -> str:
        """Async database URL using asyncpg driver"""
        return (
            f"postgresql+asyncpg://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )

    @property
    def DATABASE_URL_SAFE(self) -> str:
        """Database URL with password redacted (safe for logging)"""
        return (
            f"postgresql://{self.DATABASE_USER}:***"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )

    @property
    def DB_CONFIG(self) -> dict:
        """Database configuration dict for direct psycopg2 usage"""
        return {
            "dbname": self.DATABASE_NAME,
            "user": self.DATABASE_USER,
            "password": self.DATABASE_PASSWORD,
            "host": self.DATABASE_HOST,
            "port": self.DATABASE_PORT,
        }

    # ------------------------------------------------------------------ JWT
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8   # 8 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14          # 14 days
    JWT_ISSUER: str = "fast-absen"
    JWT_AUDIENCE: str = "fast-absen-client"

    # ------------------------------------------------------------------ CORS
    # Union[str, List[str]] prevents pydantic-settings v2 from trying
    # json.loads() on comma-separated env var values before validators run.
    CORS_ORIGINS: str | List[str] = ["http://localhost:3000", "http://localhost:5173"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: str | List[str] = ["*"]
    CORS_ALLOW_HEADERS: str | List[str] = ["*"]

    @field_validator("CORS_ORIGINS", "CORS_ALLOW_METHODS", "CORS_ALLOW_HEADERS", mode="before")
    @classmethod
    def parse_string_list(cls, v):
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    # ------------------------------------------------------------------ Logging
    LOG_LEVEL: str = "DEBUG"
    LOG_DIR: str = "logs"

    # ------------------------------------------------------------------ Bootstrap super-admin
    ADMIN_USERNAME: str | None = None
    ADMIN_PASSWORD: str | None = None
    ADMIN_ID_PEGAWAI: str | None = None
    ADMIN_NIP: str | None = None
    ADMIN_NAMA: str | None = None
    ADMIN_JENIS_KELAMIN: str | None = None
    ADMIN_TEMPAT_LAHIR: str | None = None
    ADMIN_TANGGAL_LAHIR: str | None = None
    ADMIN_ALAMAT: str | None = None
    ADMIN_STATUS: str | None = "Aktif"
    ADMIN_ID_UNIT: int | None = None
    ADMIN_KEPALA_ID_UNIT: int | None = None
    ADMIN_FORCE_UPDATE: bool = False

    # ------------------------------------------------------------------ Face Recognition
    FACE_SIMILARITY_THRESHOLD: float = 0.5
    FACE_MAX_EMBEDDINGS_PER_USER: int = 5
    FACE_MODEL_NAME: str = "buffalo_l"

    # ------------------------------------------------------------------ Upload
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = 5

    # ------------------------------------------------------------------ Session & Scheduler
    SESSION_ACTIVE_MINUTES: int = 30              # heartbeat threshold → "active"
    SESSION_EXPIRY_HOURS: int = 8                 # idle > N hours → expired
    SESSION_CLEANUP_INTERVAL_MINUTES: int = 60    # cleanup job interval (minutes)

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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
