import datetime

from pydantic import BaseModel, Field, field_validator

ALLOWED_URL_SCHEMES = ("http://", "https://", "mailto:")


def _reject_unsafe_scheme(value: str | None) -> str | None:
    # The frontend renders this straight into an <a href="..."> — a
    # javascript:/data: URL here would be stored XSS against whoever next
    # clicks the link. Only allow schemes a link is actually meant to carry.
    if value is None or value == "":
        return value
    if not value.lower().startswith(ALLOWED_URL_SCHEMES):
        raise ValueError(f"URL must start with one of {ALLOWED_URL_SCHEMES}.")
    return value


class ResourceCreate(BaseModel):
    type: str = Field(min_length=1, max_length=32)
    title: str = Field(min_length=1, max_length=256)
    category: str | None = None
    url: str | None = None
    description: str | None = None
    process_text: str | None = None

    _validate_url = field_validator("url")(_reject_unsafe_scheme)


class ResourceUpdate(BaseModel):
    title: str | None = None
    category: str | None = None
    url: str | None = None
    description: str | None = None
    process_text: str | None = None

    _validate_url = field_validator("url")(_reject_unsafe_scheme)


class ResourceOut(BaseModel):
    id: int
    type: str
    title: str
    category: str | None
    url: str | None
    description: str | None
    process_text: str | None
    updated_at: datetime.datetime
