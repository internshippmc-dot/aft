import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.models.leg import LegEvent, LegName, LegScope, LegSource
from app.models.user import User


def write_leg_event(
    db: DbSession,
    scope_type: LegScope,
    scope_id: int,
    leg: LegName,
    occurred_on: datetime.date,
    actor: User,
    source: LegSource = LegSource.manual,
) -> dict | None:
    """PRD F7 — enter a date against a leg. Supersedes any current entry for
    the same (scope, leg) rather than violating the one-current-row index.
    Returns the superseded value (for the audit `before`), or None if new."""
    existing = db.scalar(
        select(LegEvent).where(
            LegEvent.scope_type == scope_type,
            LegEvent.scope_id == scope_id,
            LegEvent.leg == leg,
            LegEvent.superseded_at.is_(None),
        )
    )
    before = {"occurred_on": str(existing.occurred_on)} if existing else None
    if existing is not None:
        existing.superseded_at = datetime.datetime.now(datetime.timezone.utc)
        db.flush()

    db.add(
        LegEvent(
            scope_type=scope_type,
            scope_id=scope_id,
            leg=leg,
            occurred_on=occurred_on,
            source=source,
            entered_by=actor.id,
        )
    )
    db.flush()
    return before
