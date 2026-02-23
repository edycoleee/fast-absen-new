#!/usr/bin/env python3
"""
CLI Script: Manual Session Cleanup
Manually cleanup expired user sessions.

Usage (jalankan dari direktori backend/):
    python -m scripts.cleanup_sessions [OPTIONS]

Options:
    --hours HOURS   Session expiry threshold in hours (default: dari settings)
    --dry-run       Tampilkan apa yang akan dihapus tanpa benar-benar eksekusi
    --force         Skip konfirmasi interaktif
    --help          Tampilkan bantuan ini

Examples:
    python -m scripts.cleanup_sessions
    python -m scripts.cleanup_sessions --hours 48
    python -m scripts.cleanup_sessions --dry-run
    python -m scripts.cleanup_sessions --force
"""
import sys
import os
import asyncio
import argparse
from datetime import datetime, timedelta, timezone

# Pastikan root backend ada di path saat dijalankan langsung
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select, and_
from config.database import AsyncSessionLocal
from config.settings import settings
from models.user_session import UserSession
from repositories.user_session_repository import UserSessionRepository


# ── Helpers ──────────────────────────────────────────────────────────────────

def _fmt_ts(dt: datetime | None) -> str:
    if not dt:
        return "N/A"
    # Normalise ke naive local time untuk tampilan
    if dt.tzinfo:
        dt = dt.astimezone().replace(tzinfo=None)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _fmt_age(dt: datetime | None) -> str:
    if not dt:
        return "N/A"
    now = datetime.now(timezone.utc)
    if not dt.tzinfo:
        dt = dt.replace(tzinfo=timezone.utc)
    secs = (now - dt).total_seconds()
    if secs < 3600:
        return f"{secs / 60:.0f} menit"
    if secs < 86400:
        return f"{secs / 3600:.1f} jam"
    return f"{secs / 86400:.1f} hari"


def _print_session(s: UserSession, index: int | None = None) -> None:
    prefix = f"  [{index}] " if index is not None else "  "
    print(f"{prefix}session_id   : {s.session_id}")
    print(f"       user_id     : {s.user_id}")
    print(f"       device      : {s.device_type} | {s.browser or '-'}")
    print(f"       ip          : {s.ip_address}")
    print(f"       login_at    : {_fmt_ts(s.login_at)}")
    print(f"       last_active : {_fmt_ts(s.last_activity)}  (idle {_fmt_age(s.last_activity)})")
    print()


# ── Async queries ─────────────────────────────────────────────────────────────

async def _fetch_expired(cutoff: datetime) -> list[UserSession]:
    """Sesi yang last_activity < cutoff dan belum logout."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(UserSession).where(
                and_(
                    UserSession.logout_at.is_(None),
                    UserSession.last_activity < cutoff,
                )
            ).order_by(UserSession.last_activity)
        )
        return list(result.scalars().all())


async def _do_invalidate(cutoff: datetime) -> int:
    """Eksekusi invalidasi dan kembalikan jumlah baris yang diupdate."""
    async with AsyncSessionLocal() as db:
        repo = UserSessionRepository(db)
        return await repo.invalidate_expired(cutoff)


# ── Main ──────────────────────────────────────────────────────────────────────

async def run(expiry_hours: int, dry_run: bool, force: bool) -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=expiry_hours)

    print("=" * 65)
    print("  SESSION CLEANUP UTILITY")
    print("=" * 65)
    print(f"  Waktu          : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Threshold idle : > {expiry_hours} jam  (cutoff: {_fmt_ts(cutoff)})")
    print(f"  Mode           : {'DRY RUN — tidak ada perubahan' if dry_run else 'LIVE CLEANUP'}")
    print("=" * 65)
    print()

    # Fetch
    print("[1/2] Mengambil daftar sesi expired...")
    expired = await _fetch_expired(cutoff)
    print(f"      Ditemukan {len(expired)} sesi (idle > {expiry_hours}h):\n")

    if expired:
        for i, s in enumerate(expired, 1):
            _print_session(s, i)
    else:
        print("  Tidak ada sesi expired.\n")

    # Cleanup
    print("[2/2] Eksekusi cleanup...")
    if not expired:
        print("  Tidak ada yang perlu dibersihkan.\n")
    elif dry_run:
        print(f"  DRY RUN: akan menghapus/invalidate {len(expired)} sesi.")
        print("  (Tidak ada perubahan yang dibuat)\n")
    else:
        if not force:
            answer = input(f"  Lanjutkan invalidate {len(expired)} sesi? [y/N]: ")
            if answer.strip().lower() not in ("y", "yes"):
                print("  Dibatalkan.\n")
                return

        count = await _do_invalidate(cutoff)
        print(f"  ✅ {count} sesi berhasil di-invalidate.\n")

    print("=" * 65)
    print("  RINGKASAN")
    print("=" * 65)
    print(f"  Sesi expired ditemukan : {len(expired)}")
    if dry_run:
        print("  Aksi                   : DRY RUN — tidak ada perubahan")
    elif expired:
        print(f"  Aksi                   : {len(expired)} sesi di-invalidate")
    else:
        print("  Aksi                   : Tidak diperlukan")
    print("=" * 65)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Manual cleanup expired user sessions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--hours", type=int, default=None,
        help=f"Threshold idle dalam jam (default: {settings.SESSION_EXPIRY_HOURS} dari settings)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Tampilkan tanpa eksekusi",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Skip konfirmasi",
    )
    args = parser.parse_args()

    expiry_hours = args.hours if args.hours is not None else settings.SESSION_EXPIRY_HOURS

    try:
        asyncio.run(run(expiry_hours, args.dry_run, args.force))
    except KeyboardInterrupt:
        print("\nDibatalkan oleh user.")
        sys.exit(0)
    except Exception as exc:
        print(f"\n❌ Error: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
