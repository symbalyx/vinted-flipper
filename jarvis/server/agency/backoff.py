"""
Backoff exponentiel avec jitter borné (v5.7 incrément 2).

next_delay = clamp(base * 2^(attempt-1), base, max) + jitter
Le résultat est persistable (next_run_at) ; aucune boucle de retry immédiate.
Prend en compte un éventuel en-tête Retry-After.
"""
from __future__ import annotations

import os
import random


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def retry_config() -> dict:
    return {
        "base": max(1.0, _env_float("AGENCY_RETRY_BASE_SECONDS", 10.0)),
        "max": max(5.0, _env_float("AGENCY_RETRY_MAX_SECONDS", 3600.0)),
        "jitter_ratio": min(1.0, max(0.0, _env_float("AGENCY_RETRY_JITTER_RATIO", 0.20))),
    }


def next_delay(attempt: int, base: float = None, maximum: float = None,
               jitter_ratio: float = None, retry_after: float = None,
               rng: random.Random = None) -> float:
    """Délai (secondes) avant le prochain essai. `attempt` >= 1.

    `rng` injectable pour des tests déterministes. `retry_after` (ex. en-tête
    HTTP 429/503) impose un plancher.
    """
    cfg = retry_config()
    base = cfg["base"] if base is None else max(0.1, float(base))
    maximum = cfg["max"] if maximum is None else max(base, float(maximum))
    jitter_ratio = cfg["jitter_ratio"] if jitter_ratio is None else min(1.0, max(0.0, float(jitter_ratio)))
    attempt = max(1, int(attempt))

    # Exponentiel borné (on limite l'exposant pour éviter tout overflow).
    raw = base * (2 ** min(attempt - 1, 20))
    delay = min(raw, maximum)

    # Jitter symétrique borné : delay ± (jitter_ratio * delay).
    r = rng or random
    if jitter_ratio > 0:
        span = delay * jitter_ratio
        delay = delay + r.uniform(-span, span)

    delay = max(base * (1 - jitter_ratio), min(delay, maximum))
    if retry_after:
        try:
            delay = max(delay, float(retry_after))
        except (TypeError, ValueError):
            pass
    return round(max(0.1, delay), 3)


def next_run_at(now: float, attempt: int, **kwargs) -> float:
    return now + next_delay(attempt, **kwargs)
