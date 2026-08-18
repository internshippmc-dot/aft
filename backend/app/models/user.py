import datetime
import enum

from sqlalchemy import ForeignKey, Index, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import CITEXT, ENUM, INET, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class UserRole(str, enum.Enum):
    owner = "owner"
    ops = "ops"
    viewer = "viewer"


user_role_enum = ENUM(UserRole, name="user_role", create_type=False)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(CITEXT, unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[UserRole] = mapped_column(user_role_enum, nullable=False, default=UserRole.viewer)
    totp_secret: Mapped[str | None] = mapped_column(Text)
    totp_enrolled_at: Mapped[datetime.datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    failed_attempts: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    locked_until: Mapped[datetime.datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    disabled_at: Mapped[datetime.datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[datetime.datetime] = mapped_column(TIMESTAMP(timezone=True), server_default="now()")

    sessions: Mapped[list["Session"]] = relationship(
        "Session", back_populates="user", cascade="all, delete-orphan"
    )


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # SHA-256 hash of the raw token
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(TIMESTAMP(timezone=True), server_default="now()")
    last_seen_at: Mapped[datetime.datetime] = mapped_column(TIMESTAMP(timezone=True), server_default="now()")
    expires_at: Mapped[datetime.datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    ip: Mapped[str | None] = mapped_column(INET)
    user_agent: Mapped[str | None] = mapped_column(Text)
    revoked_at: Mapped[datetime.datetime | None] = mapped_column(TIMESTAMP(timezone=True))

    user: Mapped["User"] = relationship("User", back_populates="sessions")

    __table_args__ = (Index("ix_sessions_user_id_active", "user_id"),)
