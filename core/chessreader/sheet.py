"""What was read from the scoresheet(s).

A game is a list of sheets so that later we can add a continuation sheet
and the opponent's sheet without changing this structure.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# Cells that end the game instead of holding a move ("Remis", "1:0", "aufgegeben", "Matt" ...)
_RESULT = re.compile(r"^(rem\w*|remis|draw|½.*|1/2.*|1\s*[:-]\s*0|0\s*[:-]\s*1|aufg\w*|resign\w*|matt?|checkmate|mate|=)\.?$", re.I)


def result_of(text: str) -> str | None:
    t = (text or "").strip()
    if not _RESULT.match(t):
        return None
    tl = t.lower().replace(" ", "")
    if tl.startswith(("rem", "draw", "½", "1/2", "=")):
        return "1/2-1/2"
    if tl.replace(":", "-") == "1-0":
        return "1-0"
    if tl.replace(":", "-") == "0-1":
        return "0-1"
    return "*"           # "aufgegeben": who resigned is not clear from the cell alone


@dataclass
class RawPly:
    """One cell of the sheet as the model read it."""
    text: str = ""
    number: int | None = None          # move number written on the sheet
    color: str | None = None           # "w" / "b" column
    confidence: float = 1.0            # model's confidence 0..1
    alternatives: list[str] = field(default_factory=list)
    kind: str = "move"                 # move | empty | illegible | gap (synthetic, numbering jump)
    pinned: bool = False               # a person chose this move in the review: the decoder must use it
    orig: str | None = None            # for a pinned cell: what the model had read there
    sheet: int = 0                     # index of the photo this cell is on
    conflict: bool = False             # the opponent's sheet has another legal move here


@dataclass
class Sheet:
    plies: list[RawPly] = field(default_factory=list)
    role: str = "main"                 # main | continuation | opponent
    language: str = "de"
    image: int = 0                     # index of the photo this sheet was read from
    # Where the move cells are on the photo (for zooming in during the review):
    # [{"first_move", "last_move", "left", "top", "right", "bottom"}], coordinates 0..1000.
    layout: list = field(default_factory=list)


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
            p.sheet = sheet.image
            res = result_of(p.text) if p.kind == "move" else None
            if res is not None:
                if res != "*" and reading.header.result in ("*", "", None):
                    reading.header.result = res
                continue           # a result written into a move cell is not a move
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
