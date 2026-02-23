#!/usr/bin/env python3
"""
CLI Script: Sync Permission Registry → Database

Sinkronisasi isi PERMISSIONS registry ke tabel `permissions` di database,
lalu pastikan setiap role bawaan mendapat set permission yang sesuai.

Usage (jalankan dari direktori backend/):
    python -m scripts.sync_permissions

Role default yang di-handle:
    superadmin  → semua permission
    admin       → operasional penuh (tanpa roles/permissions management)
    kepala_unit → baca + approval absensi unit sendiri
    pegawai     → absensi mandiri
"""
import sys
import os
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from config.database import AsyncSessionLocal
from models.permission import Permission
from models.role import Role
from models.role_permission import RolePermission
from utils.permission_registry import PERMISSIONS

# ── Default permission sets per role ─────────────────────────────────────────

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "superadmin": set(PERMISSIONS.keys()),   # semua permission
    "admin": {
        "user.login",
        "users.read", "users.create", "users.update", "users.delete",
        "roles.read",
        "pegawai.read", "pegawai.create", "pegawai.update", "pegawai.delete",
        "unit.read",
        "absensi.read", "absensi.create", "absensi.update", "absensi.delete",
        "face.enroll", "face.verify", "face.manage",
        "user_sessions.read", "user_sessions.delete",
        "report.read",
    },
    "kepala_unit": {
        "user.login",
        "pegawai.read",
        "unit.read",
        "absensi.read", "absensi.update",
        "report.read",
    },
    "pegawai": {
        "user.login",
        "absensi.read", "absensi.create",
        "face.verify",
    },
}


# ── Core logic ────────────────────────────────────────────────────────────────

async def sync(db: AsyncSession) -> None:
    # ── 1. Sync permission rows ───────────────────────────────────────────
    existing_perms: dict[str, Permission] = {
        p.name: p
        for p in (await db.execute(select(Permission))).scalars().all()
    }

    created = updated = 0
    for name, description in PERMISSIONS.items():
        if name in existing_perms:
            if description and existing_perms[name].description != description:
                existing_perms[name].description = description
                updated += 1
        else:
            new_perm = Permission(name=name, description=description)
            db.add(new_perm)
            existing_perms[name] = new_perm
            created += 1

    await db.flush()   # flush so new perms get IDs before assignment

    if created or updated:
        print(f"✅ Permissions: {created} dibuat, {updated} diperbarui")
    else:
        print("   Permissions: tidak ada perubahan")

    # Reload untuk memastikan semua ID terisi (termasuk yang baru di-flush)
    perm_map: dict[str, Permission] = {
        p.name: p
        for p in (await db.execute(select(Permission))).scalars().all()
    }

    # ── 2. Assign permissions ke setiap role ─────────────────────────────
    roles: list[Role] = list(
        (await db.execute(
            select(Role).where(Role.name.in_(ROLE_PERMISSIONS.keys()))
        )).scalars().all()
    )

    for role in roles:
        target_names = ROLE_PERMISSIONS.get(role.name, set())
        current_names = {p.name for p in role.permissions}
        missing_names = target_names - current_names

        if missing_names:
            for perm_name in missing_names:
                perm = perm_map.get(perm_name)
                if perm:
                    db.add(RolePermission(role_id=role.id, permission_id=perm.id))
            print(f"✅ Role '{role.name}': +{len(missing_names)} permission ditambahkan")
        else:
            print(f"   Role '{role.name}': sudah lengkap")

    await db.commit()

    # ── 3. Cek orphaned permissions ───────────────────────────────────────
    orphans = [name for name in existing_perms if name not in PERMISSIONS]
    if orphans:
        print(f"\n⚠️  Peringatan: {len(orphans)} permission di database tidak ada di registry:")
        for name in sorted(orphans):
            print(f"   - {name}")


async def main() -> None:
    print("=" * 55)
    print("  SYNC PERMISSIONS")
    print("=" * 55)
    async with AsyncSessionLocal() as db:
        await sync(db)
    print("=" * 55)
    print("✅ Selesai.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        print(f"\n❌ Gagal: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
