import datetime

from pydantic import BaseModel


class SyncStateOut(BaseModel):
    cursor_value: str | None
    last_success_at: datetime.datetime | None
    last_error: str | None


class SyncSummary(BaseModel):
    created: int
    updated: int
    error: str | None
