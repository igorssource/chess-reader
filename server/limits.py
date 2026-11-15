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

    def take(self) -> bool:
        """Count the game before it is read (one step in the store, so uploads sent at the
        same moment cannot all pass). False = the limit is reached, nothing is counted."""
        if self.limit <= 0:
            return True
        if self.kv.incr_float(self.key, 1, ttl=2 * 24 * 3600) > self.limit:
            self.give_back()
            return False
        return True

    def give_back(self):
        if self.limit > 0:
            self.kv.incr_float(self.key, -1, ttl=2 * 24 * 3600)


class IpAttempts(IpLimit):
    """Every upload that reaches the model, also one that fails (unreadable photo, model
    error): such uploads cost money too. Generous, so that a real user with a few failed
    photos never notices it: 3 x the game limit + 5 per day."""

    def __init__(self, kv, ip: str):
        super().__init__(kv, ip)
        self.key = self.key.replace("ipgames:", "iptries:", 1)
        self.limit = self.limit * 3 + 5 if self.limit > 0 else 0


# ---- history per day (only the admin sees it, on docs/stats.html) ----
# day:<date>    games_user, games_admin, cost_user, cost_admin (EUR, every model call,
#               also of games that failed), ip_limit_hits, budget_hits, errors
# dayip:<date>  shortened address hash -> games read (real users only)
DAY_TTL = 400 * 24 * 3600


def ip_tag(ip: str) -> str:
    """Short salted hash: tells visitors apart without keeping the address itself."""
    salt = os.environ.get("STATS_SALT") or os.environ.get("ADMIN_TOKEN") or ""
    return hashlib.sha256(f"{salt}|{ip}".encode()).hexdigest()[:8]


class DayStats:
    """Counters for the admin's statistics. A failure here must never break an upload."""

    def __init__(self, kv, is_admin: bool, ip: str | None = None):
        self.kv, self.who, self.ip = kv, "admin" if is_admin else "user", ip
        self.date = today()

    def _incr(self, key: str, field: str, amount: float = 1):
        try:
            self.kv.hincr(key, field, amount, DAY_TTL)
        except Exception:       # noqa: BLE001  statistics only
            pass

    def cost(self, call: ModelCall):
        self._incr(f"day:{self.date}", f"cost_{self.who}", call.cost_eur)

    def game(self):
        self._incr(f"day:{self.date}", f"games_{self.who}")
        if self.who == "user" and self.ip:
            self._incr(f"dayip:{self.date}", ip_tag(self.ip))

    def event(self, name: str):
        if self.who == "user":
            self._incr(f"day:{self.date}", name)


def _ip_summary(per_ip: dict) -> dict:
    counts = sorted((int(v) for v in per_ip.values() if v >= 1), reverse=True)
    hist: dict = {}
    for c in counts:
        hist[c] = hist.get(c, 0) + 1
    return {"ips": len(counts), "max_per_ip": counts[0] if counts else 0,
            "per_ip": counts[:50], "ip_histogram": dict(sorted(hist.items()))}


def day_history(kv, days: int = 60) -> list:
    """One row per day, newest first. Days before this history existed are filled from
    the game log (successful games only) and the per-IP limit counters (kept 2 days)."""
    now = dt.datetime.now(TZ)
    dates = [(now - dt.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days)]
    try:
        agg = kv.hgetall_many([f"day:{d}" for d in dates])
        ips = kv.hgetall_many([f"dayip:{d}" for d in dates])
    except Exception:           # noqa: BLE001
        agg, ips = [{} for _ in dates], [{} for _ in dates]
    from_log: dict = {}
    for g in kv.read_log(LOG_KEY, 2000):
        d = dt.datetime.fromtimestamp(g.get("ts", 0), TZ).strftime("%Y-%m-%d")
        who = "admin" if g.get("admin") or g.get("ref") else "user"
        row = from_log.setdefault(d, {})
        row[f"games_{who}"] = row.get(f"games_{who}", 0) + 1
        row[f"cost_{who}"] = row.get(f"cost_{who}", 0.0) + g.get("cost_eur", 0.0)
    out = []
    for i, d in enumerate(dates):
        a, lg, per_ip = agg[i], from_log.get(d, {}), ips[i]
        if i < 2:               # the limit counters still exist for today and yesterday
            try:
                old = kv.counters(f"ipgames:{d}:")
                if sum(old.values()) > sum(per_ip.values()):
                    per_ip = old
            except Exception:   # noqa: BLE001
                pass
        row = {"date": d}
        for f in ("games_user", "games_admin"):
            row[f] = int(max(a.get(f, 0), lg.get(f, 0)))
        for f in ("cost_user", "cost_admin"):
            row[f] = round(max(a.get(f, 0.0), lg.get(f, 0.0)), 4)
        for f in ("ip_limit_hits", "budget_hits", "errors"):
            row[f] = int(a.get(f, 0))
        row.update(_ip_summary(per_ip))
        if any(v for k, v in row.items() if k not in ("date", "per_ip", "ip_histogram")):
            out.append(row)
    return out


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
