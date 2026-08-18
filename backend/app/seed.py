"""Account bootstrap — run once after migrations. Idempotent: skips if users
already exist. No demo boxes/orders/consignments — real data comes in via
Shopify sync and manual entry from day one.

Owner credentials come from OWNER_EMAIL/OWNER_PASSWORD env vars (falling
back to a dev-only default locally) so the real password is never
hardcoded/committed here — set those on the Railway backend service the
same way DATABASE_URL etc. are set. ops/viewer are still on the dev
default until real credentials are given for them too.
"""

import os

from sqlalchemy import select

from app.auth.password import hash_password
from app.db import SessionLocal
from app.models.user import User, UserRole

DEV_PASSWORD = "ChangeMe123!"

OWNER_EMAIL = os.environ.get("OWNER_EMAIL", "siddharth@actuallyfair.in")
OWNER_PASSWORD = os.environ.get("OWNER_PASSWORD", DEV_PASSWORD)


def seed() -> None:
    db = SessionLocal()
    try:
        if db.scalar(select(User)):
            print("Seed skipped — users already exist.")
            return

        owner = User(email=OWNER_EMAIL, full_name="Owner", password_hash=hash_password(OWNER_PASSWORD), role=UserRole.owner)
        ops = User(email="ops@actuallyfair.in", full_name="Ops", password_hash=hash_password(DEV_PASSWORD), role=UserRole.ops)
        viewer = User(email="viewer@actuallyfair.in", full_name="Viewer", password_hash=hash_password(DEV_PASSWORD), role=UserRole.viewer)
        db.add_all([owner, ops, viewer])
        db.commit()
        print("Seeded 3 users, no demo data.")
        print(f"Login — owner: {OWNER_EMAIL} (password from OWNER_PASSWORD env var)")
        print(f"        ops:   ops@actuallyfair.in / {DEV_PASSWORD}")
        print(f"        viewer: viewer@actuallyfair.in / {DEV_PASSWORD}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
