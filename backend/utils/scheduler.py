"""
Background Task Scheduler
Handles periodic tasks like session cleanup.

Menggunakan AsyncIOScheduler (bukan BackgroundScheduler) karena
seluruh aplikasi berbasis async — job dapat await coroutine secara langsung.
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timezone, timedelta
from config.settings import settings
from config.database import AsyncSessionLocal
from repositories.user_session_repository import UserSessionRepository
from utils.logger import logger

# Global scheduler instance
scheduler = AsyncIOScheduler()


async def _cleanup_expired_sessions():
    """
    Job: hapus sesi yang sudah idle melebihi SESSION_EXPIRY_HOURS.
    Dipanggil otomatis oleh scheduler setiap SESSION_CLEANUP_INTERVAL_MINUTES.
    """
    expiry_hours = settings.SESSION_EXPIRY_HOURS
    cutoff = datetime.now(timezone.utc) - timedelta(hours=expiry_hours)
    try:
        async with AsyncSessionLocal() as db:
            repo = UserSessionRepository(db)
            count = await repo.invalidate_expired(cutoff)
            if count:
                logger.info(
                    f"[Scheduler] Session cleanup: {count} sesi expired "
                    f"(idle > {expiry_hours}h) berhasil di-invalidate"
                )
            else:
                logger.debug(
                    f"[Scheduler] Session cleanup: tidak ada sesi expired "
                    f"(threshold: idle > {expiry_hours}h)"
                )
    except Exception as exc:
        logger.error(f"[Scheduler] Session cleanup error: {exc}", exc_info=True)


def start_scheduler():
    """
    Daftarkan semua job dan jalankan scheduler.
    Dipanggil saat aplikasi startup.
    """
    try:
        interval_minutes = settings.SESSION_CLEANUP_INTERVAL_MINUTES
        scheduler.add_job(
            func=_cleanup_expired_sessions,
            trigger=IntervalTrigger(minutes=interval_minutes),
            id="cleanup_expired_sessions",
            name="Cleanup expired user sessions",
            replace_existing=True,
        )
        scheduler.start()
        logger.info(
            f"[Scheduler] Started — session cleanup setiap {interval_minutes} menit, "
            f"threshold idle > {settings.SESSION_EXPIRY_HOURS} jam"
        )
    except Exception as exc:
        logger.error(f"[Scheduler] Gagal start: {exc}", exc_info=True)


def stop_scheduler():
    """
    Hentikan scheduler dengan graceful shutdown.
    Dipanggil saat aplikasi shutdown.
    """
    try:
        if scheduler.running:
            scheduler.shutdown()
            logger.info("[Scheduler] Stopped")
    except Exception as exc:
        logger.error(f"[Scheduler] Error saat shutdown: {exc}", exc_info=True)


async def run_cleanup_now():
    """
    Trigger cleanup secara manual (untuk testing atau intervensi manual).
    """
    logger.info("[Scheduler] Manual cleanup triggered")
    await _cleanup_expired_sessions()
