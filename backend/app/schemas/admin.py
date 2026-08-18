import datetime

from pydantic import BaseModel


class AuditEntryOut(BaseModel):
    id: int
    actor_user_id: int | None
    actor_email: str | None
    action: str
    object_type: str
    object_id: str
    before: dict | None
    after: dict | None
    occurred_at: datetime.datetime
