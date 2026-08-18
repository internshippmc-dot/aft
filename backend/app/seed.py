"""Account bootstrap — run once after migrations. Idempotent: skips if users
already exist. No demo boxes/orders/consignments — real data comes in via
Shopify sync and manual entry from day one."""

from sqlalchemy import select

from app.auth.password import hash_password
from app.db import SessionLocal
from app.models.user import User, UserRole

DEV_PASSWORD = "ChangeMe123!"


def seed() -> None:
    db = SessionLocal()
    try:
        if db.scalar(select(User)):
            print("Seed skipped — users already exist.")
            return

        owner = User(email="siddharth@actuallyfair.in", full_name="Siddharth", password_hash=hash_password(DEV_PASSWORD), role=UserRole.owner)
        ops = User(email="ops@actuallyfair.in", full_name="Ops", password_hash=hash_password(DEV_PASSWORD), role=UserRole.ops)
        viewer = User(email="viewer@actuallyfair.in", full_name="Viewer", password_hash=hash_password(DEV_PASSWORD), role=UserRole.viewer)
        db.add_all([owner, ops, viewer])
        db.commit()
        print("Seeded 3 users, no demo data.")
        print(f"Dev login — owner: siddharth@actuallyfair.in / {DEV_PASSWORD}")
        print(f"           ops:   ops@actuallyfair.in / {DEV_PASSWORD}")
        print(f"           viewer: viewer@actuallyfair.in / {DEV_PASSWORD}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
