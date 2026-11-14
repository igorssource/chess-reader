"""All tunable values in one place. Every value can be overridden by an
environment variable (on Vercel: Project -> Settings -> Environment Variables),
so limits can be changed without touching the code."""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env(name, default, cast=str):
    v = os.environ.get(name)
    return default if v in (None, "") else cast(v)


def _bool(v: str) -> bool:
    return str(v).lower() in ("1", "true", "yes", "on")


# USD per 1M tokens (input, output). Keep in sync with the provider's price list.
MODEL_PRICES_USD = {
    "claude-opus-5-5": (4.00, 20.00),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-haiku-5-5": (0.10, 0.50),
}


@dataclass
class Settings:
    notation_language: str = field(default_factory=lambda: _env("NOTATION_LANGUAGE", "de"))
    model_provider: str = field(default_factory=lambda: _env("MODEL_PROVIDER", "anthropic"))
    model_name: str = field(default_factory=lambda: _env("MODEL_NAME", "claude-sonnet-5-5"))
    model_effort: str = field(default_factory=lambda: _env("MODEL_EFFORT", "medium"))
    max_calls_per_game: int = field(default_factory=lambda: _env("MAX_CALLS_PER_GAME", 10, int))
    daily_budget_eur: float = field(default_factory=lambda: _env("DAILY_BUDGET_EUR", 1.0, float))
    usd_to_eur: float = field(default_factory=lambda: _env("USD_TO_EUR", 0.95, float))
    store_photos: bool = field(default_factory=lambda: _env("STORE_PHOTOS", True, _bool))
    # Cascade: read with the first model; if too many moves are unsure, re-read with the next.
    # Empty CASCADE_MODELS = always use MODEL_NAME only.
    cascade_models: list = field(default_factory=lambda: [m.strip() for m in _env(
        "CASCADE_MODELS", "claude-haiku-5-5,claude-sonnet-5-5").split(",") if m.strip()])
    cascade_max_problem_share: float = field(default_factory=lambda: _env("CASCADE_MAX_PROBLEM_SHARE", 0.10, float))
    cascade_max_doubtful: int = field(default_factory=lambda: _env("CASCADE_MAX_DOUBTFUL", 3, int))
    cascade_min_plies: int = field(default_factory=lambda: _env("CASCADE_MIN_PLIES", 10, int))
    cascade_cheap_max_calls: int = field(default_factory=lambda: _env("CASCADE_CHEAP_MAX_CALLS", 3, int))
    # Time for one game. The host (Vercel) cuts a request off at 300 s; stay well below.
    time_limit_seconds: float = field(default_factory=lambda: _env("TIME_LIMIT_SECONDS", 250, float))
    recheck_reserve_seconds: float = field(default_factory=lambda: _env("RECHECK_RESERVE_SECONDS", 40, float))
    escalate_reserve_seconds: float = field(default_factory=lambda: _env("ESCALATE_RESERVE_SECONDS", 100, float))
    # How many doubtful moves are re-read at the same time (faster; same number of calls).
    recheck_parallel: int = field(default_factory=lambda: _env("RECHECK_PARALLEL", 3, int))
    # Re-read a doubtful move on a zoomed crop of its cell (from the full-size photo).
    recheck_crop: bool = field(default_factory=lambda: _env("RECHECK_CROP", True, _bool))
    pgn_comments_language: str = field(default_factory=lambda: _env("PGN_COMMENTS_LANGUAGE", "de"))

    def price_eur(self, input_tokens: int, output_tokens: int, model: str | None = None) -> float:
        p_in, p_out = MODEL_PRICES_USD.get(model or self.model_name, MODEL_PRICES_USD["claude-opus-5-5"])
        usd = input_tokens / 1e6 * p_in + output_tokens / 1e6 * p_out
        return usd * self.usd_to_eur
