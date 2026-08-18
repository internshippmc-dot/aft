import datetime

from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class SheetImport(Base):
    __tablename__ = "sheet_imports"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str] = mapped_column(Text, nullable=False)
    row_count: Mapped[int | None] = mapped_column(Integer)
    committed_at: Mapped[datetime.datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    committed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    diff: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime.datetime] = mapped_column(TIMESTAMP(timezone=True), server_default="now()")


class SyncState(Base):
    __tablename__ = "sync_state"

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    cursor_value: Mapped[str | None] = mapped_column(Text)
    last_success_at: Mapped[datetime.datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
