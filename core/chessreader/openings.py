"""Opening name + ECO code from the moves, using a bundled table (no model call, free).

The table (data/openings.tsv) comes from lichess-org/chess-openings (CC0) and maps a
board position to an opening. We walk through the game and keep the last position
that is in the table, so a later, more precise name wins, and transpositions work.
"""
from __future__ import annotations

import functools
import pathlib
from dataclasses import asdict, dataclass

import chess

DATA = pathlib.Path(__file__).with_name("data") / "openings.tsv"
MAX_PLIES = 40          # openings in the table are never longer than this


@dataclass
class Opening:
    eco: str            # e.g. "D30"
    name: str           # English, e.g. "Queen's Gambit Declined: Orthodox Defense"
    family: str         # the part before ":", e.g. "Queen's Gambit Declined"
    ply: int            # how many half-moves of the game the name is based on

    def to_dict(self) -> dict:
        return asdict(self)


@functools.lru_cache(maxsize=1)
def _table() -> dict[str, tuple[str, str]]:
    table = {}
    for line in DATA.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        eco, name, epd = line.split("\t")
        table[epd] = (eco, name)
    return table


def detect(sans: list[str]) -> Opening | None:
    """sans: the game's moves in English SAN. Stops quietly at the first unreadable move."""
    table = _table()
    board = chess.Board()
    found = None
    for k, san in enumerate(sans[:MAX_PLIES]):
        try:
            board.push_san(san)
        except ValueError:
            break
        hit = table.get(board.epd())
        if hit:
            found = (hit, k + 1)
    if not found:
        return None
    (eco, name), ply = found
    return Opening(eco=eco, name=name, family=name.split(":")[0], ply=ply)
