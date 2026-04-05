"""
scripts/seed_dev.py
────────────────────
Creates a minimal dataset for local development and login testing.

Run from project root:
    python scripts/seed_dev.py

Creates:
  - 1 tenant  (hadir-dev)
  - 1 company (PT HaDir Teknologi)
  - 1 office  (Jakarta HQ)
  - 1 hr_admin employee with PIN 1234  → code: EMP-00001
  - 1 regular employee with PIN 5678   → code: EMP-00002

After running, test login at http://localhost:8000/docs:
  POST /v1/auth/login
  { "employee_code": "EMP-00001", "pin": "1234" }
"""
import asyncio
import sys
import uuid
from datetime import date

sys.path.insert(0, ".")

from app.core.config import settings
from app.core.security import hash_password
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)


async def seed():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as db:
        async with db.begin():

            # ── Check if already seeded ───────────────────────────
            existing = await db.scalar(
                text("SELECT COUNT(*) FROM tenants WHERE slug = 'hadir-dev'")
            )
            if existing:
                print("✅ Already seeded — skipping")
                return

            tenant_id = uuid.uuid4()
            company_id = uuid.uuid4()
            office_id = uuid.uuid4()
            admin_id = uuid.uuid4()
            employee_id = uuid.uuid4()

            # ── Tenant ────────────────────────────────────────────
            await db.execute(text("""
                INSERT INTO tenants (id, slug, plan, status)
                VALUES (:id, 'hadir-dev', 'pro', 'active')
            """), {"id": tenant_id})

            # ── Company ───────────────────────────────────────────
            await db.execute(text("""
                INSERT INTO companies (id, tenant_id, name, timezone)
                VALUES (:id, :tid, 'PT HaDir Teknologi', 'Asia/Jakarta')
            """), {"id": company_id, "tid": tenant_id})

            # ── Office location (Jakarta) ─────────────────────────
            await db.execute(text("""
                INSERT INTO office_locations
                    (id, company_id, name, latitude, longitude, radius_meters, is_primary)
                VALUES
                    (:id, :cid, 'Jakarta HQ', -6.2088, 106.8456, 150, true)
            """), {"id": office_id, "cid": company_id})

            # ── Attendance policy ─────────────────────────────────
            # ALL columns supplied explicitly — never rely on server_default
            # because the deployed migration may or may not have set them.
            await db.execute(text("""
                INSERT INTO attendance_policies (
                    id, company_id,
                    late_tolerance_minutes,
                    early_leave_tolerance_minutes,
                    overtime_threshold_minutes,
                    max_work_minutes_per_day,
                    checkin_window_before_minutes,
                    require_selfie,
                    require_gps,
                    allow_wfh
                ) VALUES (
                    :id, :cid,
                    15,
                    15,
                    30,
                    600,
                    60,
                    false,
                    false,
                    true
                )
            """), {"id": uuid.uuid4(), "cid": company_id})
            # NOTE: selfie + gps OFF for local dev testing convenience

            # ── HR Admin employee ─────────────────────────────────
            await db.execute(text("""
                INSERT INTO employees
                    (id, company_id, employee_code, full_name, email,
                     employment_type, join_date, role, status, hashed_pin)
                VALUES
                    (:id, :cid, 'EMP-00001', 'Admin HaDir', 'admin@hadir.dev',
                     'permanent', :jd, 'hr_admin', 'active', :pin)
            """), {
                "id": admin_id,
                "cid": company_id,
                "jd": date(2024, 1, 1),
                "pin": hash_password("1234"),
            })

            # ── Regular employee ──────────────────────────────────
            await db.execute(text("""
                INSERT INTO employees
                    (id, company_id, employee_code, full_name, email,
                     employment_type, join_date, role, status,
                     hashed_pin, direct_manager_id)
                VALUES
                    (:id, :cid, 'EMP-00002', 'Budi Santoso', 'budi@hadir.dev',
                     'permanent', :jd, 'employee', 'active', :pin, :mgr)
            """), {
                "id": employee_id,
                "cid": company_id,
                "jd": date(2024, 3, 1),
                "pin": hash_password("5678"),
                "mgr": admin_id,
            })

        print()
        print("✅ Seed complete!")
        print()
        print("  Tenant:  hadir-dev (pro/active)")
        print("  Company: PT HaDir Teknologi")
        print()
        print("  ┌─────────────┬──────────────┬──────────┬───────────┐")
        print("  │ Code        │ Name         │ Role     │ PIN       │")
        print("  ├─────────────┼──────────────┼──────────┼───────────┤")
        print("  │ EMP-00001   │ Admin HaDir  │ hr_admin │ 1234      │")
        print("  │ EMP-00002   │ Budi Santoso │ employee │ 5678      │")
        print("  └─────────────┴──────────────┴──────────┴───────────┘")
        print()
        print("  Test login:")
        print('  curl -X POST http://localhost:8000/v1/auth/login \\')
        print('    -H "Content-Type: application/json" \\')
        print('    -d \'{"employee_code": "EMP-00001", "pin": "1234"}\'')
        print()

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())