"""JSON shape the model must return (enforced with structured outputs)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from ..sheet import GameReading, Header, RawPly, Sheet


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HeaderOut(_Strict):
    white: str
    black: str
    event: str
    site: str
    date: str
    round: str
    result: str


class CellOut(_Strict):
    number: int
    color: Literal["w", "b"]
    text: str
    confidence: float
    alternatives: list[str]
    kind: Literal["move", "empty", "illegible"]


class SheetOut(_Strict):
    notation_language: str
    header: HeaderOut
    cells: list[CellOut]
    remarks: str


class RecheckOut(_Strict):
    candidates: list[str]
    note: str


def to_reading(out: SheetOut) -> GameReading:
    h = out.header
    header = Header(
        white=h.white or "?", black=h.black or "?", event=h.event or "?", site=h.site or "?",
        date=_pgn_date(h.date), round=h.round or "?", result=_pgn_result(h.result),
    )
    plies = [RawPly(text=c.text, number=c.number, color=c.color,
                    confidence=max(0.0, min(1.0, c.confidence)),
                    alternatives=list(c.alternatives), kind=c.kind) for c in out.cells]
    return GameReading(header=header, sheets=[Sheet(plies=plies, language=out.notation_language or "de")])


def _pgn_result(r: str) -> str:
    r = (r or "").replace(" ", "").replace("½", "1/2").replace(":", "-")
    return r if r in ("1-0", "0-1", "1/2-1/2") else "*"


def _pgn_date(d: str) -> str:
    """Accepts 'YYYY.MM.DD', 'DD.MM.YYYY', 'YYYY-MM-DD'; anything else -> unknown."""
    import re
    d = (d or "").strip()
    m = re.match(r"^(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})$", d)
    if m:
        return f"{m[1]}.{int(m[2]):02d}.{int(m[3]):02d}"
    m = re.match(r"^(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{2,4})$", d)
    if m:
        y = m[3] if len(m[3]) == 4 else "20" + m[3]
        return f"{y}.{int(m[2]):02d}.{int(m[1]):02d}"
    return "????.??.??"
