from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import date, datetime, timezone
from models.pegawai import Pegawai
from models.absensi import Absensi
from models.user_session import UserSession
from schemas.stats import StatsOverview


class StatsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_overview(self) -> StatsOverview:
        today = date.today()
        total_pegawai = (await self.db.execute(
            select(func.count()).select_from(Pegawai).where(Pegawai.status == "Aktif")
        )).scalar() or 0

        def _count_status(s):
            return select(func.count()).select_from(Absensi).where(
                and_(Absensi.tanggal == today, Absensi.status == s)
            )

        hadir = (await self.db.execute(_count_status("HADIR"))).scalar() or 0
        terlambat = (await self.db.execute(_count_status("TERLAMBAT"))).scalar() or 0
        izin = (await self.db.execute(_count_status("IZIN"))).scalar() or 0
        sakit = (await self.db.execute(_count_status("SAKIT"))).scalar() or 0
        alpha = (await self.db.execute(_count_status("ALPHA"))).scalar() or 0
        total_absen = hadir + terlambat + izin + sakit + alpha
        belum = max(0, total_pegawai - total_absen)

        now = datetime.now(timezone.utc)
        sessions = (await self.db.execute(
            select(func.count()).select_from(UserSession).where(
                and_(UserSession.login_status == "success", UserSession.logout_at == None,
                     UserSession.expires_at > now)
            )
        )).scalar() or 0

        persen = round((hadir + terlambat) / total_pegawai * 100, 2) if total_pegawai > 0 else 0.0

        return StatsOverview(
            total_pegawai=total_pegawai,
            total_hadir_hari_ini=hadir,
            total_terlambat_hari_ini=terlambat,
            total_izin_hari_ini=izin,
            total_sakit_hari_ini=sakit,
            total_alpha_hari_ini=alpha,
            total_belum_absen=belum,
            total_sessions_aktif=sessions,
            persentase_kehadiran=persen,
        )
