"""One game from photo(s) to PGN: read -> check -> repair -> (re-ask model) -> PGN.

Protection against endless ping-pong between the model and the chess check:
  * at most `settings.max_calls_per_game` model requests per game (reading included);
  * `budget_ok()` is asked before every request (daily money limit, kept by the server);
  * a cell is re-asked at most once, and only if the answer brings something new.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Callable

import time

import chess

from . import notation
from .config import Settings
from .decoder import DecodeResult, decode
from .model.base import Image, ModelCall, ModelProvider
from .pgn_export import build_pgn
from .combine import build_tokens, classify, merge_headers
from .imaging import crop_cell
from .sheet import GameReading


@dataclass
class GameOutcome:
    reading: GameReading
    result: DecodeResult
    pgn: str
    calls: list[ModelCall] = field(default_factory=list)
    stopped_because: str = ""          # "", "call_cap", "budget"
    escalated: bool = False            # cascade: the cheap result was unsure, strong model re-read
    tokens: list = field(default_factory=list)   # the cells that were decoded (kept for the review)

    @property
    def cost_eur(self) -> float:
        return sum(c.cost_eur for c in self.calls)


def process_game(images: list[Image], provider: ModelProvider, settings: Settings,
                 budget_ok: Callable[[], bool] = lambda: True,
                 on_call: Callable[[ModelCall], None] = lambda c: None,
                 deadline: float | None = None) -> GameOutcome:
    """`deadline` (time.monotonic()): stop asking the model again when time runs short,
    so the answer arrives before the host cuts the request off."""
    calls: list[ModelCall] = []
    if deadline is None:
        deadline = time.monotonic() + settings.time_limit_seconds

    def record(call: ModelCall):
        calls.append(call)
        on_call(call)

    if not budget_ok():
        raise BudgetExhausted()
    reading = _read(images, provider, record, budget_ok)
    lang = settings.notation_language
    tokens = build_tokens(reading, lang)
    result = decode(tokens, lang)
    layouts = {s.image: s.layout for s in reading.sheets}
    stopped = ""

    asked: set[int] = set()
    while True:
        # up to `recheck_parallel` doubtful cells are re-read at the same time
        targets = _doubtful_targets(result, tokens, asked, settings.recheck_parallel)
        if not targets:
            break
        room = settings.max_calls_per_game - len(calls)
        if room <= 0:
            stopped = "call_cap"
            break
        if not budget_ok():
            stopped = "budget"
            break
        if deadline - time.monotonic() < settings.recheck_reserve_seconds:
            stopped = "time"
            break
        jobs = []
        for ply, tok_index in targets[:room]:
            asked.add(tok_index)
            tok = tokens[tok_index]
            board = chess.Board(ply.fen_before)
            legal = sorted(notation.render(board, m, notation.LANGUAGES[lang]) for m in board.legal_moves)
            prev = " ".join(p.local for p in result.plies[:ply.ply])
            number = tok.number or ply.ply // 2 + 1
            color = tok.color or ("w" if ply.ply % 2 == 0 else "b")
            img = images[tok.sheet] if tok.sheet < len(images) else (images[0] if images else None)
            crop = crop_cell(img, layouts.get(tok.sheet), number, color) if settings.recheck_crop and img else None
            jobs.append((tok, ([img] if img else images, number, color, tok.text, ply.fen_before, legal, prev, crop)))

        def ask(job):
            a = job[1]
            return provider.recheck(a[0], a[1], a[2], a[3], a[4], a[5], a[6], crop=a[7])

        answers = _parallel(provider, ask, jobs)
        changed = False
        for (tok, _), (answer, call) in zip(jobs, answers):
            record(call)
            new = [c for c in answer.candidates if c not in tok.alternatives and c != tok.text]
            if not new:
                continue                # same answer again: do not insist, a person decides
            tok.alternatives = new + tok.alternatives
            tok.confidence = min(tok.confidence, 0.5)
            changed = True
        if changed:
            result = decode(tokens, lang)

    pgn = build_pgn(reading.header, result, settings.pgn_comments_language)
    return GameOutcome(reading, result, pgn, calls, stopped, tokens=tokens)


def _read(images, provider, record, budget_ok) -> GameReading:
    """One photo: one reading. Several photos: each is read on its own (a second page
    or the opponent's sheet would confuse a single reading), then classified."""
    if len(images) <= 1:
        reading, call = provider.read_sheet(images)
        record(call)
        return reading
    # the photos are read at the same time (each reading takes up to a minute)
    results = _parallel(provider, lambda img: provider.read_sheet([img]), images)
    readings = []
    for i, (r, call) in enumerate(results):
        record(call)
        for sh in r.sheets:
            sh.image = i
        readings.append(r)
    sheets = classify([sh for r in readings for sh in r.sheets])
    return GameReading(merge_headers([r.header for r in readings]), sheets)


def _doubtful_targets(result: DecodeResult, tokens, asked, n: int):
    """Earliest doubtful written cells not asked yet (fixing one often fixes later ones)."""
    out = []
    for p in result.plies:
        if p.status == "doubtful" and p.token is not None and p.token not in asked \
                and tokens[p.token].kind in ("move", "illegible"):
            out.append((p, p.token))
            if len(out) >= n:
                break
    return out


def _parallel(provider, fn, items):
    if len(items) > 1 and getattr(provider, "parallel_ok", True):
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=len(items)) as pool:
            return list(pool.map(fn, items))
    return [fn(x) for x in items]


class BudgetExhausted(Exception):
    pass


# ---- Cascade: a cheap model first, the strong model only when the sheet looks hard.

def problem_score(outcome: GameOutcome) -> dict:
    """How unsure the result is: share of moves that were auto-corrected or need a check."""
    plies = outcome.result.plies
    n = len(plies)
    doubtful = sum(p.status == "doubtful" for p in plies)
    fixed = sum(p.status == "fixed" for p in plies)
    skipped = len(outcome.result.skipped_tokens)
    share = (doubtful + fixed + skipped) / max(n, 1)
    return {"plies": n, "doubtful": doubtful, "fixed": fixed, "skipped": skipped, "share": round(share, 3)}


def needs_strong_model(outcome: GameOutcome, settings: Settings) -> bool:
    sc = problem_score(outcome)
    return (outcome.stopped_because == "call_cap"      # cheap model could not settle its doubts
            or sc["plies"] < settings.cascade_min_plies
            or sc["share"] > settings.cascade_max_problem_share
            or sc["doubtful"] >= settings.cascade_max_doubtful)


def process_cascade(images: list[Image], make_provider: Callable[[str], ModelProvider], settings: Settings,
                    budget_ok: Callable[[], bool] = lambda: True,
                    on_call: Callable[[ModelCall], None] = lambda c: None) -> GameOutcome:
    """Read with settings.cascade_models[0]; if the result looks unsure, read again with the
    next model. The per-game call cap counts the calls of all models together."""
    models = settings.cascade_models
    total_cap = settings.max_calls_per_game
    used: list[ModelCall] = []
    best: GameOutcome | None = None
    escalated = False
    deadline = time.monotonic() + settings.time_limit_seconds
    for i, model in enumerate(models):
        last = i == len(models) - 1
        left = total_cap - len(used)
        if left <= 0:
            break
        if i and deadline - time.monotonic() < settings.escalate_reserve_seconds:
            break                       # not enough time left for the strong model to read again
        cap = left if last else min(left, settings.cascade_cheap_max_calls)
        stage = replace(settings, model_name=model, max_calls_per_game=cap)
        try:
            out = process_game(images, make_provider(model), stage, budget_ok, on_call, deadline)
        except BudgetExhausted:
            if best is None:
                raise
            break
        used += out.calls
        if best is None or problem_score(out)["share"] <= problem_score(best)["share"]:
            best = out
        if last or not needs_strong_model(out, settings):
            break
        escalated = True
    best.calls = used
    best.escalated = escalated
    return best
