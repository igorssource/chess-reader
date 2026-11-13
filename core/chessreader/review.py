"""Stage 2: a person fixes one move, the rest of the game is decoded again.

No model call here: the cells read from the photo are kept with the game, the
chosen move is written into its cell as "pinned", and the decoder replays the
remaining cells from the corrected position. Fixing one move often fixes all the
later moves that were wrong only because of it.
"""
from __future__ import annotations

from dataclasses import asdict, fields

import chess

from . import notation
from .decoder import DecodedPly, decode
from .sheet import RawPly

_CELL_FIELDS = {f.name for f in fields(RawPly)}


class ReviewError(ValueError):
    pass


def cell_from_dict(d: dict) -> RawPly:
    return RawPly(**{k: v for k, v in d.items() if k in _CELL_FIELDS})


def cells_from_plies(plies: list[dict]) -> tuple[list[RawPly], list[dict]]:
    """For games saved before the cells were kept: rebuild cells from the moves.
    Every move gets its own cell; plies get matching token numbers."""
    cells, out = [], []
    for k, p in enumerate(plies):
        w = (p.get("written") or "").strip()
        if w:
            cells.append(RawPly(text=w, number=k // 2 + 1, color="wb"[k % 2],
                                confidence=1.0 if p.get("status") == "ok" else 0.5,
                                alternatives=list(p.get("alternatives") or [])))
        else:
            cells.append(RawPly(kind="gap", number=k // 2 + 1, color="wb"[k % 2]))
        out.append(dict(p, token=k))
    return cells, out


def redecode(cells: list[RawPly], plies: list[dict], k: int, san: str, language: str = "de"):
    """Pin move `san` at half-move `k` and decode everything after it again.

    `plies` are the current moves (dicts as sent to the page). Moves before `k` stay as
    they are. Returns (plies, cells, skipped token indices)."""
    lang = notation.LANGUAGES[language]
    if not 0 <= k <= len(plies):
        raise ReviewError("bad move index")
    board = chess.Board()
    for j, p in enumerate(plies[:k]):
        try:
            board.push_san(p["san"])
        except (ValueError, KeyError):
            raise ReviewError(f"illegal move at ply {j + 1}")
    try:
        mv = board.parse_san(san)
    except ValueError:
        raise ReviewError("the chosen move is not legal here")
    local = notation.render(board, mv, lang)

    cells = list(cells)
    # first cell not used by the moves before k
    used = [p["token"] for p in plies[:k] if p.get("token") is not None]
    start = max(used) + 1 if used else 0
    old = plies[k] if k < len(plies) else None
    t = old.get("token") if old else None
    number, color = k // 2 + 1, "wb"[k % 2]
    if t is not None and start <= t < len(cells):
        c = cells[t]
        cells[t] = RawPly(text=local, number=c.number or number, color=c.color or color, confidence=1.0,
                          kind="move", pinned=True, orig=c.orig if c.pinned else c.text)
    else:
        # the move was not on the sheet (inserted by the program, or a new move at the end)
        cells.insert(start, RawPly(text=local, number=number, color=color, confidence=1.0,
                                   kind="move", pinned=True, orig=""))
        t = start

    rest = decode(cells[start:], language, start=board)
    if not rest.plies or rest.plies[0].san != board.san(mv):
        raise ReviewError("could not continue the game after this move")
    out = [dict(p) for p in plies[:k]]
    for p in rest.plies:
        d = _ply_dict(p)
        d["ply"] = p.ply + k
        d["token"] = None if p.token is None else p.token + start
        out.append(d)
    skipped = sorted(i + start for i in rest.skipped_tokens)
    return out, cells, skipped


def _ply_dict(p: DecodedPly) -> dict:
    return dict(p.__dict__)


def cells_to_dicts(cells: list[RawPly]) -> list[dict]:
    return [asdict(c) for c in cells]
