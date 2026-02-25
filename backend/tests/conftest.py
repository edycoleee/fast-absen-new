"""
Pytest Configuration and Fixtures
"""
import sys
from pathlib import Path
from typing import AsyncGenerator

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from main import app
from config.database import AsyncSessionLocal, get_db, engine as _app_engine
from config.settings import settings
from models import Role, Permission, User, Pegawai, UserRole
from utils.security import hash_password
from utils.permission_registry import PERMISSIONS


# ------------------------------------------------------------------ Pool reset
# The asyncpg pool is a module-level singleton. Dispose it after every test so
# the next test starts with fresh connections on its own event loop.

@pytest_asyncio.fixture(autouse=True)
async def _reset_db_pool():
    yield
    await _app_engine.dispose()


# ------------------------------------------------------------------ Basic client
# No DB override — uses the real app session factory.

@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Async test client against the real app (no DB override)."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


# ------------------------------------------------------------------ Seeded-data fixture
# Creates test users in the real DB, cleans them up in finally so no leftover data.

_TEST_PEGAWAI_IDS = ["TST_PGW_A", "TST_PGW_U"]
_TEST_USERNAMES   = ["tst_admin", "tst_user"]


@pytest_asyncio.fixture
async def db_with_data() -> AsyncGenerator[None, None]:
    """
    Inserts minimal test roles/users into the real DB, yields, then hard-deletes
    everything created via try/finally — safe even when a test fails.
    """
    async with AsyncSessionLocal() as session:
        async with session.begin():
            # ---- roles (find or create) ----
            async def _get_or_create_role(name: str, desc: str) -> Role:
                result = await session.execute(select(Role).where(Role.name == name))
                role = result.scalar_one_or_none()
                if not role:
                    role = Role(name=name, description=desc)
                    session.add(role)
                    await session.flush()
                return role

            superadmin_role = await _get_or_create_role("tst_superadmin", "Test superadmin")
            user_role       = await _get_or_create_role("tst_user_role",  "Test user role")

            # ---- permissions for superadmin role ----
            existing_perms_r = await session.execute(select(Permission.id))
            all_perm_ids = [row[0] for row in existing_perms_r.fetchall()]

            # Grant all existing permissions to tst_superadmin role
            from sqlalchemy import text
            for pid in all_perm_ids:
                await session.execute(
                    text(
                        "INSERT INTO role_permissions (role_id, permission_id) "
                        "VALUES (:r, :p) ON CONFLICT DO NOTHING"
                    ),
                    {"r": superadmin_role.id, "p": pid},
                )

            # Grant login permission to tst_user_role
            login_perm_r = await session.execute(
                select(Permission.id).where(Permission.name == "user.login")
            )
            login_pid = login_perm_r.scalar_one_or_none()
            if login_pid:
                await session.execute(
                    text(
                        "INSERT INTO role_permissions (role_id, permission_id) "
                        "VALUES (:r, :p) ON CONFLICT DO NOTHING"
                    ),
                    {"r": user_role.id, "p": login_pid},
                )

            # ---- pegawai ----
            for pid, name in zip(
                _TEST_PEGAWAI_IDS, ["Test Admin Fixture", "Test User Fixture"]
            ):
                exists = await session.get(Pegawai, pid)
                if not exists:
                    session.add(Pegawai(id_pegawai=pid, nip=f"TST{pid}", nama=name))

            await session.flush()

            # ---- users ----
            for uname, pgw_id, role in [
                (_TEST_USERNAMES[0], _TEST_PEGAWAI_IDS[0], superadmin_role),
                (_TEST_USERNAMES[1], _TEST_PEGAWAI_IDS[1], user_role),
            ]:
                res = await session.execute(select(User).where(User.username == uname))
                user = res.scalar_one_or_none()
                if not user:
                    user = User(
                        id_pegawai=pgw_id,
                        username=uname,
                        password_hash=hash_password("Test@1234"),
                        is_active=True,
                    )
                    session.add(user)
                    await session.flush()
                    session.add(UserRole(user_id=user.id, role_id=role.id))

    try:
        yield
    finally:
        # Hard-delete all test artifacts
        async with AsyncSessionLocal() as session:
            async with session.begin():
                from sqlalchemy import text as t
                # remove user_roles, users, pegawai, then roles (in dependency order)
                for uname in _TEST_USERNAMES:
                    row = await session.execute(
                        select(User.id).where(User.username == uname)
                    )
                    uid = row.scalar_one_or_none()
                    if uid:
                        await session.execute(
                            t("DELETE FROM user_roles WHERE user_id = :u"), {"u": uid}
                        )
                        await session.execute(
                            t("DELETE FROM user_sessions WHERE user_id = :u"), {"u": uid}
                        )
                        await session.execute(
                            t("DELETE FROM users WHERE id = :u"), {"u": uid}
                        )
                for pid in _TEST_PEGAWAI_IDS:
                    await session.execute(
                        t("DELETE FROM absensi WHERE id_pegawai = :p"), {"p": pid}
                    )
                for pid in _TEST_PEGAWAI_IDS:
                    await session.execute(
                        t("DELETE FROM pegawai WHERE id_pegawai = :p"), {"p": pid}
                    )
                for rname in ["tst_superadmin", "tst_user_role"]:
                    row = await session.execute(
                        select(Role.id).where(Role.name == rname)
                    )
                    rid = row.scalar_one_or_none()
                    if rid:
                        await session.execute(
                            t("DELETE FROM role_permissions WHERE role_id = :r"),
                            {"r": rid},
                        )
                        await session.execute(
                            t("DELETE FROM roles WHERE id = :r"), {"r": rid}
                        )


# ------------------------------------------------------------------ Legacy aliases
# Keep backward compatibility with the old conftest shape.

@pytest_asyncio.fixture
async def db_session(db_with_data) -> AsyncGenerator[AsyncSession, None]:
    """Alias: yields a plain AsyncSessionLocal session (not isolated)."""
    async with AsyncSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client_with_db(db_with_data) -> AsyncGenerator[AsyncClient, None]:
    """Client that has test data available in the real DB."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


# ------------------------------------------------------------------ Token helpers

@pytest_asyncio.fixture
async def admin_token(client_with_db: AsyncClient) -> str:
    resp = await client_with_db.post(
        "/api/v1/auth/login",
        json={"username": _TEST_USERNAMES[0], "password": "Test@1234"},
    )
    assert resp.status_code == 200
    return resp.json()["data"]["access_token"]


@pytest_asyncio.fixture
async def user_token(client_with_db: AsyncClient) -> str:
    resp = await client_with_db.post(
        "/api/v1/auth/login",
        json={"username": _TEST_USERNAMES[1], "password": "Test@1234"},
    )
    assert resp.status_code == 200
    return resp.json()["data"]["access_token"]


@pytest.fixture
def auth_headers_admin(admin_token: str) -> dict:
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def auth_headers_user(user_token: str) -> dict:
    return {"Authorization": f"Bearer {user_token}"}


