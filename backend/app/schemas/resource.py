import datetime

from pydantic import BaseModel, Field


class ResourceCreate(BaseModel):
    type: str = Field(min_length=1, max_length=32)
    title: str = Field(min_length=1, max_length=256)
    category: str | None = None
    url: str | None = None
    description: str | None = None
    process_text: str | None = None


class ResourceUpdate(BaseModel):
    title: str | None = None
    category: str | None = None
    url: str | None = None
    description: str | None = None
    process_text: str | None = None


class ResourceOut(BaseModel):
    id: int
    type: str
    title: str
    category: str | None
    url: str | None
    description: str | None
    process_text: str | None
    updated_at: datetime.datetime
