"""Daily money limit and per-game log (to see the average number of model calls)."""
from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

from chessreader.config import Settings
from chessreader.model.base import ModelCall

TZ = ZoneInfo("Europe/Berlin")
LOG_KEY = "games"


def today() -> str:
    return dt.datetime.now(TZ).strftime("%Y-%m-%d")


class Budget:
    def __init__(self, kv, settings: Settings):
        self.kv = kv
        self.settings = settings
        self.key = f"spend:{today()}"

    def spent(self) -> float:
        return self.kv.get_float(self.key)

    def remaining(self) -> float:
        return max(0.0, self.settings.daily_budget_eur - self.spent())

    def ok(self) -> bool:
        return self.spent() < self.settings.daily_budget_eur

    def add(self, call: ModelCall):
        self.kv.incr_float(self.key, call.cost_eur, ttl=3 * 24 * 3600)


def log_game(kv, entry: dict, keep: int = 2000):
    kv.push_log(LOG_KEY, entry, keep)


def stats(kv, n: int = 500) -> dict:
    games = kv.read_log(LOG_KEY, n)
    if not games:
        return {"games": 0}
    calls = [g["calls"] for g in games]
    cost = [g["cost_eur"] for g in games]
    hist: dict = {}
    for c in calls:
        hist[c] = hist.get(c, 0) + 1
    return {
        "games": len(games),
        "avg_calls_per_game": round(sum(calls) / len(calls), 2),
        "max_calls_per_game": max(calls),
        "calls_histogram": dict(sorted(hist.items())),
        "avg_cost_eur": round(sum(cost) / len(cost), 4),
        "stopped_by_cap": sum(1 for g in games if g.get("stopped") == "call_cap"),
        "spent_today_eur": None,
        "recent": games[:20],
    }
