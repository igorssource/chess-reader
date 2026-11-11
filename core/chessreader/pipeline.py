"""One game from photo(s) to PGN: read -> check -> repair -> (re-ask model) -> PGN.

Protection against endless ping-pong between the model and the chess check:
  * at most `settings.max_calls_per_game` model requests per game (reading included);
  * `budget_ok()` is asked before every request (daily money limit, kept by the server);
  * a cell is re-asked at most once, and only if the answer brings something new.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import chess

from . import notation
from .config import Settings
from .decoder import DecodeResult, decode
from .model.base import Image, ModelCall, ModelProvider
from .pgn_export import build_pgn
from .sheet import GameReading, flatten


@dataclass
class GameOutcome:
    reading: GameReading
    result: DecodeResult
    pgn: str
    calls: list[ModelCall] = field(default_factory=list)
    stopped_because: str = ""          # "", "call_cap", "budget"

    @property
    def cost_eur(self) -> float:
        return sum(c.cost_eur for c in self.calls)


def process_game(images: list[Image], provider: ModelProvider, settings: Settings,
                 budget_ok: Callable[[], bool] = lambda: True,
                 on_call: Callable[[ModelCall], None] = lambda c: None) -> GameOutcome:
    calls: list[ModelCall] = []

    def record(call: ModelCall):
        calls.append(call)
        on_call(call)

    if not budget_ok():
        raise BudgetExhausted()
    reading, call = provider.read_sheet(images)
    record(call)
    lang = settings.notation_language
    tokens = flatten(reading)
    result = decode(tokens, lang)
    stopped = ""

    asked: set[int] = set()
    while True:
        target = _next_doubtful(result, tokens, asked)
        if target is None:
            break
        if len(calls) >= settings.max_calls_per_game:
            stopped = "call_cap"
            break
        if not budget_ok():
            stopped = "budget"
            break
        ply, tok_index = target
        asked.add(tok_index)
        tok = tokens[tok_index]
        board = chess.Board(ply.fen_before)
        legal = sorted(notation.render(board, m, notation.LANGUAGES[lang]) for m in board.legal_moves)
        prev = " ".join(p.local for p in result.plies[:ply.ply])
        answer, call = provider.recheck(images, tok.number or ply.ply // 2 + 1,
                                        tok.color or ("w" if ply.ply % 2 == 0 else "b"),
                                        tok.text, ply.fen_before, legal, prev)
        record(call)
        new = [c for c in answer.candidates if c not in tok.alternatives and c != tok.text]
        if not new:
            continue                    # same answer again: do not insist, a person decides
        tok.alternatives = new + tok.alternatives
        tok.confidence = min(tok.confidence, 0.5)
        result = decode(tokens, lang)

    pgn = build_pgn(reading.header, result, settings.pgn_comments_language)
    return GameOutcome(reading, result, pgn, calls, stopped)


def _next_doubtful(result: DecodeResult, tokens, asked):
    """Earliest doubtful written cell not asked yet (fixing it often fixes later ones)."""
    for p in result.plies:
        if p.status == "doubtful" and p.token is not None and p.token not in asked \
                and tokens[p.token].kind in ("move", "illegible"):
            return p, p.token
    return None


class BudgetExhausted(Exception):
    pass
