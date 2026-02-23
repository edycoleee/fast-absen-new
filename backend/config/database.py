"""
Database Session & Engine Setup
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import QueuePool
from config.settings import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_recycle=3600,
    pool_pre_ping=True,
    echo=settings.DEBUG,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def check_database_connection() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def get_database_info() -> dict:
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT version(), current_database(), current_user")
            ).fetchone()
        return {
            "connected": True,
            "version": row[0],
            "database": row[1],
            "user": row[2],
            "host": settings.DATABASE_HOST,
            "port": settings.DATABASE_PORT,
        }
    except Exception as exc:
        return {"connected": False, "error": str(exc)}
