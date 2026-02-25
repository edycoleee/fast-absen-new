from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from config.settings import settings
from models.user import User
from models.role import Role
from models.user_role import UserRole
from models.pegawai import Pegawai
from utils.security import hash_password
from utils.logger import logger


async def bootstrap_superadmin(db: AsyncSession) -> None:
    try:
        result = await db.execute(select(User).where(User.username == settings.ADMIN_USERNAME))
        user = result.scalar_one_or_none()

        if user and not settings.ADMIN_FORCE_UPDATE:
            logger.info(f"Superadmin '{settings.ADMIN_USERNAME}' sudah ada, skip bootstrap")
            return

        # Ensure pegawai record exists
        pegawai = await db.get(Pegawai, settings.ADMIN_ID_PEGAWAI)
        if not pegawai:
            from datetime import date
            tanggal_lahir = (
                date.fromisoformat(settings.ADMIN_TANGGAL_LAHIR)
                if settings.ADMIN_TANGGAL_LAHIR
                else None
            )
            pegawai = Pegawai(
                id_pegawai=settings.ADMIN_ID_PEGAWAI,
                nip=settings.ADMIN_NIP,
                nama=settings.ADMIN_NAMA,
                jenis_kelamin=settings.ADMIN_JENIS_KELAMIN,
                tempat_lahir=settings.ADMIN_TEMPAT_LAHIR,
                tanggal_lahir=tanggal_lahir,
                alamat=settings.ADMIN_ALAMAT,
                is_active=True,
            )
            db.add(pegawai)
            await db.flush()

        role_result = await db.execute(select(Role).where(Role.name == "superadmin"))
        role = role_result.scalar_one_or_none()

        if user and settings.ADMIN_FORCE_UPDATE:
            user.password_hash = hash_password(settings.ADMIN_PASSWORD)
            user.is_active = True
            await db.commit()
            logger.info(f"Superadmin '{settings.ADMIN_USERNAME}' diperbarui")
            return

        new_user = User(
            id_pegawai=settings.ADMIN_ID_PEGAWAI,
            username=settings.ADMIN_USERNAME,
            password_hash=hash_password(settings.ADMIN_PASSWORD),
            is_active=True,
        )
        db.add(new_user)
        await db.flush()

        if role:
            db.add(UserRole(user_id=new_user.id, role_id=role.id))

        await db.commit()
        logger.info(f"Superadmin '{settings.ADMIN_USERNAME}' berhasil dibuat")

    except Exception as e:
        await db.rollback()
        logger.error(f"Bootstrap superadmin gagal: {e}")
        raise
