from fastapi import APIRouter
from api.v1.endpoints import (
    halo, auth, users, roles, permissions, unit, pegawai, absensi, face, user_sessions, stats
)

router = APIRouter(prefix="/api/v1")

router.include_router(halo.router)
router.include_router(auth.router)
router.include_router(users.router)
router.include_router(roles.router)
router.include_router(permissions.router)
router.include_router(unit.router)
router.include_router(pegawai.router)
router.include_router(absensi.router)
router.include_router(face.router)
router.include_router(user_sessions.router)
router.include_router(stats.router)
