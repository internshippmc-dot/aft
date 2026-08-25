import datetime

from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=256)
    priority: str = "Medium"
    entity_type: str | None = None
    entity_id: str | None = None
    due_on: datetime.date | None = None
    notes: str | None = None


class TaskUpdate(BaseModel):
    """PATCH /tasks/{id}. Every field optional — only provided fields change.
    Use PATCH /tasks/{id}/complete or /reopen for status transitions."""
    title: str | None = Field(default=None, min_length=1, max_length=256)
    priority: str | None = None
    due_on: datetime.date | None = None
    notes: str | None = None


class TaskOut(BaseModel):
    id: int
    title: str
    priority: str
    entity_type: str | None
    entity_id: str | None
    due_on: datetime.date | None
    status: str
    notes: str | None
    created_at: datetime.datetime
    completed_at: datetime.datetime | None
