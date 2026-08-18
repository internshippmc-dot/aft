import datetime
import statistics
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.config import get_settings
from app.domain.stages import BOX_LEGS, effective_legs
from app.models.box import Box
from app.models.leg import LegEvent, LegName, LegScope

settings = get_settings()

# Legs whose predicted date skips Sunday (flight ops and customs don't clear then).
SUNDAY_SKIP_LEGS = {LegName.FLIGHT, LegName.DELHI_WAREHOUSE}


@dataclass
class LegStats:
    leg: LegName
    median_days: float
    p80_days: float
    sample_n: int
    confidence: str  # "high" | "low"


@dataclass
class Prediction:
    p50_date: datetime.date
    p80_date: datetime.date
    sample_n: int
    confidence: str


def _durations_for_leg(db: DbSession, leg: LegName, window: int) -> list[int]:
    """Trailing `window` completed consignment-scoped durations, in days,
    from the leg immediately before `leg` to `leg` itself."""
    idx = BOX_LEGS.index(leg)
    if idx == 0:
        return []
    prev_leg = BOX_LEGS[idx - 1]

    prev_events = {
        row.scope_id: row.occurred_on
        for row in db.scalars(
            select(LegEvent).where(
                LegEvent.scope_type == LegScope.consignment,
                LegEvent.leg == prev_leg,
                LegEvent.superseded_at.is_(None),
            )
        )
    }
    this_events = db.scalars(
        select(LegEvent)
        .where(
            LegEvent.scope_type == LegScope.consignment,
            LegEvent.leg == leg,
            LegEvent.superseded_at.is_(None),
        )
        .order_by(LegEvent.occurred_on.desc())
        .limit(window * 3)  # generous — filtered below, then capped to window
    )

    durations: list[int] = []
    for ev in this_events:
        start = prev_events.get(ev.scope_id)
        if start is None:
            continue
        delta = (ev.occurred_on - start).days
        if delta >= 0:
            durations.append(delta)
        if len(durations) >= window:
            break
    return durations


def _drop_outliers(values: list[int]) -> list[int]:
    """Drop samples beyond 3 median absolute deviations — TECH_SPEC.md section 7."""
    if len(values) < 3:
        return values
    med = statistics.median(values)
    mad = statistics.median([abs(v - med) for v in values]) or 1
    return [v for v in values if abs(v - med) <= 3 * mad]


def leg_stats(db: DbSession, leg: LegName, window: int | None = None) -> LegStats:
    window = window or settings.eta_window
    raw = _durations_for_leg(db, leg, window)
    cleaned = _drop_outliers(raw)

    if len(cleaned) < settings.eta_min_samples:
        default = settings.default_leg_days.get(leg.value, 2)
        return LegStats(
            leg=leg,
            median_days=float(default),
            p80_days=float(default) * 1.3,
            sample_n=len(cleaned),
            confidence="low",
        )

    sorted_vals = sorted(cleaned)
    median = statistics.median(sorted_vals)
    p80_idx = min(int(round(0.8 * (len(sorted_vals) - 1))), len(sorted_vals) - 1)
    p80 = sorted_vals[p80_idx]
    return LegStats(leg=leg, median_days=median, p80_days=p80, sample_n=len(cleaned), confidence="high")


def _advance(start: datetime.date, days: float, leg: LegName) -> datetime.date:
    result = start + datetime.timedelta(days=round(days))
    if leg in SUNDAY_SKIP_LEGS and result.weekday() == 6:  # Sunday
        result += datetime.timedelta(days=1)
    return result


def predict(db: DbSession, box: Box) -> Prediction | None:
    """TECH_SPEC.md section 7 — sum remaining leg medians onto the latest actual leg date."""
    legs = effective_legs(db, box)
    today = datetime.date.today()

    last_leg_idx = -1
    last_date = None
    for i, leg in enumerate(BOX_LEGS):
        if leg in legs:
            last_leg_idx = i
            last_date = legs[leg]

    if last_leg_idx == len(BOX_LEGS) - 1:
        return None  # already landed in Delhi — nothing to predict

    base_date = last_date or today
    p50_date, p80_date = base_date, base_date
    sample_ns: list[int] = []
    confidences: list[str] = []

    for leg in BOX_LEGS[last_leg_idx + 1 :]:
        stats = leg_stats(db, leg)
        p50_date = _advance(p50_date, stats.median_days, leg)
        p80_date = _advance(p80_date, stats.p80_days, leg)
        sample_ns.append(stats.sample_n)
        confidences.append(stats.confidence)

    p50_date = max(p50_date, today)
    p80_date = max(p80_date, today, p50_date)

    return Prediction(
        p50_date=p50_date,
        p80_date=p80_date,
        sample_n=min(sample_ns) if sample_ns else 0,
        confidence="low" if "low" in confidences else "high",
    )
