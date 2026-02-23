"""
Logging configuration dengan rotating file handler dan separate error logs.
Log level otomatis disesuaikan dengan environment (development vs production).
"""
import logging
import sys
import os
from pathlib import Path
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler

# Absolute path ke direktori logs (backend/logs/)
logs_dir = Path(__file__).parent.parent / "logs"
logs_dir.mkdir(exist_ok=True)

# Format log
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Environment
ENV = os.getenv("ENVIRONMENT", "development")
IS_PRODUCTION = ENV == "production"

# ── Logger instance ──────────────────────────────────────────────────────────
logger = logging.getLogger("attendance_system")
logger.setLevel(logging.WARNING if IS_PRODUCTION else logging.DEBUG)

# ── Console handler ──────────────────────────────────────────────────────────
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO if IS_PRODUCTION else logging.DEBUG)
console_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))

# ── app.log — INFO+ (rotating, max 10 MB, 5 backups) ────────────────────────
file_handler = RotatingFileHandler(
    logs_dir / "app.log",
    maxBytes=10 * 1024 * 1024,
    backupCount=5,
    encoding="utf-8",
)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))

# ── error.log — ERROR+ (rotating, max 10 MB, 5 backups) ─────────────────────
error_handler = RotatingFileHandler(
    logs_dir / "error.log",
    maxBytes=10 * 1024 * 1024,
    backupCount=5,
    encoding="utf-8",
)
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))

# ── Attach handlers ──────────────────────────────────────────────────────────
logger.addHandler(console_handler)
logger.addHandler(file_handler)
logger.addHandler(error_handler)

# Prevent duplicate logs saat module di-import berkali-kali
logger.propagate = False

logger.info(f"Logger initialized — environment: {ENV}")

