import time
from collections import defaultdict
from threading import Lock

from fastapi import HTTPException, status

# In-process sliding-window limiter. SECURITY.md section 8 calls for Postgres-
# or in-process-enforced limits; single instance (PRD.md section 3.5) makes
# in-process sufficient — there is no second worker to desync against.
_hits: dict[str, list[float]] = defaultdict(list)
_lock = Lock()


def check_rate_limit(key: str, max_hits: int, window_seconds: int) -> None:
    now = time.monotonic()
    with _lock:
        bucket = _hits[key]
        cutoff = now - window_seconds
        while bucket and bucket[0] < cutoff:
            bucket.pop(0)
        if len(bucket) >= max_hits:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many attempts. Try again later.",
                headers={"Retry-After": str(window_seconds)},
            )
        bucket.append(now)
