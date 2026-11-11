"""What was read from the scoresheet(s).

A game is a list of sheets so that later we can add a continuation sheet
and the opponent's sheet without changing this structure.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RawPly:
    """One cell of the sheet as the model read it."""
    text: str = ""
    number: int | None = None          # move number written on the sheet
    color: str | None = None           # "w" / "b" column
    confidence: float = 1.0            # model's confidence 0..1
    alternatives: list[str] = field(default_factory=list)
    kind: str = "move"                 # move | empty | illegible | gap (synthetic, numbering jump)


@dataclass
class Sheet:
    plies: list[RawPly] = field(default_factory=list)
    role: str = "main"                 # main | continuation | opponent (later stages)
    language: str = "de"


@dataclass
class Header:
    white: str = "?"
    black: str = "?"
    event: str = "?"
    site: str = "?"
    date: str = "????.??.??"
    round: str = "?"
    result: str = "*"


@dataclass
class GameReading:
    header: Header = field(default_factory=Header)
    sheets: list[Sheet] = field(default_factory=list)


def flatten(reading: GameReading) -> list[RawPly]:
    """Sequence of plies to decode. Stage 1: main + continuation sheets in order.

    A jump in move numbers (e.g. 12 then 14) is turned into "gap" placeholders,
    because it usually means a skipped move.
    """
    out: list[RawPly] = []
    last_number = None
    last_color = None
    for sheet in reading.sheets:
        if sheet.role == "opponent":
            continue   # merging the opponent's sheet comes in a later stage
        for p in sheet.plies:
            if p.number is not None and last_number is not None:
                expected = _index(last_number, last_color) + 1
                got = _index(p.number, p.color or "w")
                for _ in range(max(0, min(got - expected, 4))):
                    out.append(RawPly(kind="gap"))
            out.append(p)
            if p.number is not None:
                last_number, last_color = p.number, p.color or "w"
    return out


def _index(number: int, color: str | None) -> int:
    return (number - 1) * 2 + (1 if color == "b" else 0)
