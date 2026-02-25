from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.settings import settings
from config.database import engine, AsyncSessionLocal
from api.v1.router import router
from utils.exception_handlers import register_exception_handlers
from utils.middleware import RequestMiddleware
from utils.bootstrap_admin import bootstrap_superadmin
from utils.scheduler import start_scheduler, stop_scheduler
from utils.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    # Bootstrap superadmin
    async with AsyncSessionLocal() as db:
        await bootstrap_superadmin(db)
    # Start scheduler
    start_scheduler()
    logger.info("Application ready")
    yield
    stop_scheduler()
    await engine.dispose()
    logger.info("Application shutdown")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Attendance System API with Face Recognition",
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
    lifespan=lifespan,
)

# Single middleware handles both request-ID generation and logging
app.add_middleware(RequestMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

# Exception handlers
register_exception_handlers(app)

# Routes
app.include_router(router)


@app.get("/", tags=["Root"])
async def root():
    return {"app": settings.APP_NAME, "version": settings.APP_VERSION, "status": "running"}
