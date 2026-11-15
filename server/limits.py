"""Daily money limit and per-game log (to see the average number of model calls)."""
from __future__ import annotations

import datetime as dt
import hashlib
import os
from zoneinfo import ZoneInfo

from chessreader.config import Settings
from chessreader.model.base import ModelCall

TZ = ZoneInfo("Europe/Berlin")
LOG_KEY = "games"

# One-off higher limits for single days (Berlin date -> EUR); the next day the normal
# limit applies again by itself. DAILY_BUDGET_EUR set in Vercel always wins.
DAY_LIMITS = {
    "2026-11-15": 5.0,      # Igor: club members try the site today
}


# Games per IP address per day (Berlin date). One upload = one game, even with two
# photos; fixing a move by hand (no model) is not counted; admin test mode is exempt.
# GAMES_PER_IP_PER_DAY set in Vercel always wins over these values.
GAMES_PER_IP_DEFAULT = 5
GAMES_PER_IP_DAYS = {
    "2026-11-15": 10,       # Igor: first day for the club members
}


def today() -> str:
    return dt.datetime.now(TZ).strftime("%Y-%m-%d")


class Budget:
    def __init__(self, kv, settings: Settings):
        self.kv = kv
        self.settings = settings
        self.key = f"spend:{today()}"
        self.limit = settings.daily_budget_eur
        if "DAILY_BUDGET_EUR" not in os.environ:
            self.limit = DAY_LIMITS.get(today(), self.limit)

    def spent(self) -> float:
        return self.kv.get_float(self.key)

    def remaining(self) -> float:
        return max(0.0, self.limit - self.spent())

    def ok(self) -> bool:
        return self.spent() < self.limit

    def add(self, call: ModelCall):
        self.kv.incr_float(self.key, call.cost_eur, ttl=3 * 24 * 3600)


def client_ip(headers, fallback: str | None = None) -> str:
    """Vercel puts the visitor's real address into x-real-ip / x-forwarded-for
    (it overwrites values the browser sends, so they can't be faked there)."""
    ip = (headers.get("x-real-ip") or "").strip()
    if not ip:
        ip = (headers.get("x-forwarded-for") or "").split(",")[0].strip()
    return ip or fallback or "unknown"


class IpLimit:
    def __init__(self, kv, ip: str):
        self.kv = kv
        # store only a short hash, not the address itself
        self.key = f"ipgames:{today()}:{hashlib.sha256(ip.encode()).hexdigest()[:16]}"
        env = os.environ.get("GAMES_PER_IP_PER_DAY")
        if env:
            self.limit = int(env)
        else:
            self.limit = GAMES_PER_IP_DAYS.get(today(), GAMES_PER_IP_DEFAULT)

    def used(self) -> int:
        return int(self.kv.get_float(self.key))

    def ok(self) -> bool:
        return self.limit <= 0 or self.used() < self.limit

    def count(self):
        self.kv.incr_float(self.key, 1, ttl=2 * 24 * 3600)


def log_game(kv, entry: dict, keep: int = 2000):
    kv.push_log(LOG_KEY, entry, keep)


def _summary(games: list) -> dict:
    if not games:
        return {"games": 0}
    calls = [g.get("calls", 0) for g in games]
    cost = [g.get("cost_eur", 0.0) for g in games]
    return {"games": len(games), "cost_eur": round(sum(cost), 4),
            "avg_cost_eur": round(sum(cost) / len(cost), 4),
            "avg_calls": round(sum(calls) / len(calls), 2),
            "stopped_by_cap": sum(1 for g in games if g.get("stopped") == "call_cap"),
            "escalated_to_strong_model": sum(1 for g in games if g.get("escalated"))}


def _by_model(games: list) -> dict:
    groups: dict = {}
    for g in games:
        groups.setdefault(g.get("model", "?"), []).append(g)
    return {m: _summary(gs) for m, gs in sorted(groups.items())}


def stats(kv, n: int = 500, today_prefix: int | None = None) -> dict:
    games = kv.read_log(LOG_KEY, n)
    if not games:
        return {"games": 0}
    calls = [g["calls"] for g in games]
    cost = [g["cost_eur"] for g in games]
    hist: dict = {}
    for c in calls:
        hist[c] = hist.get(c, 0) + 1
    out = {
        "games": len(games),
        "avg_calls_per_game": round(sum(calls) / len(calls), 2),
        "max_calls_per_game": max(calls),
        "calls_histogram": dict(sorted(hist.items())),
        "avg_cost_eur": round(sum(cost) / len(cost), 4),
        "stopped_by_cap": sum(1 for g in games if g.get("stopped") == "call_cap"),
        "spent_today_eur": None,
        "by_model": _by_model(games),
    }
    if today_prefix is not None:
        today_games = [g for g in games if g.get("ts", 0) >= today_prefix]
        out["today"] = {**_summary(today_games), "by_model": _by_model(today_games)}
    # admin comparison runs: one short line per sheet, newest first
    out["ref_runs"] = [
        {"ref": g["ref"], "model": g.get("model"), "match": f'{g["match_until"]}/{g["ref_plies"]}',
         "match_pct": g.get("match_pct"), "calls": g.get("calls"), "cost_eur": g.get("cost_eur"),
         "doubtful": g.get("doubtful"), "fixed": g.get("fixed"), "seconds": g.get("seconds")}
        for g in games if g.get("ref")]
    out["recent"] = games[:20]
    return out
