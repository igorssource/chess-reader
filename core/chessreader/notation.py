"""Notation languages and parsing of a single written move.

The language is a setting, not hard-coded: add a new entry to LANGUAGES
to support another notation (English, Russian, ...).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import chess

# Internal piece letters are the English ones (K Q R B N), as used by python-chess.
INTERNAL = {"K": chess.KING, "Q": chess.QUEEN, "R": chess.ROOK, "B": chess.BISHOP, "N": chess.KNIGHT}
PIECE_TO_INTERNAL = {v: k for k, v in INTERNAL.items()}


@dataclass(frozen=True)
class Language:
    code: str
    name: str
    # written letter -> internal (English) letter
    pieces: dict

    def letter(self, piece_type: int) -> str:
        internal = PIECE_TO_INTERNAL[piece_type]
        for written, eng in self.pieces.items():
            if eng == internal:
                return written
        return internal


LANGUAGES = {
    "de": Language("de", "Deutsch", {"K": "K", "D": "Q", "T": "R", "L": "B", "S": "N"}),
    "en": Language("en", "English", {"K": "K", "Q": "Q", "R": "R", "B": "B", "N": "N"}),
    "ru": Language("ru", "Русский", {"Кр": "K", "Ф": "Q", "Л": "R", "С": "B", "К": "N"}),
}

FIGURINES = {"♔": "K", "♚": "K", "♕": "Q", "♛": "Q", "♖": "R", "♜": "R",
             "♗": "B", "♝": "B", "♘": "N", "♞": "N"}


@dataclass
class ParsedMove:
    castle: str | None = None          # "K" (short) / "Q" (long)
    piece: int | None = None           # None = pawn (or not written)
    from_file: int | None = None
    from_rank: int | None = None
    to_file: int | None = None
    to_rank: int | None = None
    promotion: int | None = None
    capture: bool = False
    check: bool = False
    mate: bool = False


def clean(text: str) -> str:
    """Unify the many ways people write the same thing (captures, castling, checks)."""
    t = text.strip()
    t = t.replace("×", "x").replace(":", "x").replace("X", "x")
    t = t.replace("–", "-").replace("—", "-")
    t = re.sub(r"e\.?\s?p\.?$", "", t)          # en passant marker
    t = re.sub(r"[!?]+$", "", t)                 # annotations
    t = t.replace(" ", "")
    return t


_CASTLE = re.compile(r"^([0Oo])-?([0Oo])(-?([0Oo]))?([+#†]|\+\+|ch)?$")
_MOVE = re.compile(
    r"^(?P<piece>[KQRBN])?(?P<ff>[a-h])?(?P<fr>[1-8])?(?P<sep>[x-])?"
    r"(?P<tf>[a-h])(?P<tr>[1-8])"
    r"(?:[=/(]?(?P<promo>[QRBN])\)?)?$"
)
_PAWN_FILE_CAPTURE = re.compile(r"^(?P<ff>[a-h])x?(?P<tf>[a-h])$")   # "ed", "exd"


def to_internal(text: str, lang: Language) -> str:
    """Replace the language's piece letters with internal ones."""
    out = []
    i = 0
    # longest written letters first (e.g. Russian "Кр" before "К")
    letters = sorted(lang.pieces, key=len, reverse=True)
    while i < len(text):
        ch = text[i]
        if ch in FIGURINES:
            out.append(FIGURINES[ch]); i += 1; continue
        for w in letters:
            if text.startswith(w, i) and w[0].isupper():
                out.append(lang.pieces[w]); i += len(w); break
        else:
            out.append(ch); i += 1
    return "".join(out)


def parse(text: str, lang: Language) -> ParsedMove | None:
    t = clean(text)
    m = _CASTLE.match(t)
    if m:
        long_castle = bool(m.group(3))
        return ParsedMove(castle="Q" if long_castle else "K", check="+" in (m.group(5) or ""))
    check = mate = False
    if t.endswith("++") or t.endswith("#"):
        mate = True
        t = t.rstrip("+#")
    elif t.endswith("+") or t.endswith("†") or t.endswith("ch"):
        check = True
        t = t[:-2] if t.endswith("ch") else t[:-1]
    t = to_internal(t, lang)
    m = _MOVE.match(t)
    if m:
        return ParsedMove(
            piece=INTERNAL[m["piece"]] if m["piece"] else None,
            from_file=chess.FILE_NAMES.index(m["ff"]) if m["ff"] else None,
            from_rank=int(m["fr"]) - 1 if m["fr"] else None,
            to_file=chess.FILE_NAMES.index(m["tf"]),
            to_rank=int(m["tr"]) - 1,
            promotion=INTERNAL[m["promo"]] if m["promo"] else None,
            capture=m["sep"] == "x",
            check=check, mate=mate,
        )
    m = _PAWN_FILE_CAPTURE.match(t)
    if m:
        return ParsedMove(from_file=chess.FILE_NAMES.index(m["ff"]),
                          to_file=chess.FILE_NAMES.index(m["tf"]), capture=True)
    return None


def matches(board: chess.Board, p: ParsedMove) -> list[chess.Move]:
    """All legal moves in this position that fit the written move."""
    result = []
    for mv in board.legal_moves:
        if p.castle:
            if board.is_castling(mv) and (
                (p.castle == "K") == board.is_kingside_castling(mv)
            ):
                result.append(mv)
            continue
        if board.is_castling(mv) and p.piece == chess.KING and p.to_file is not None:
            # "Kg1" written for short castling is accepted too
            pass
        piece = board.piece_type_at(mv.from_square)
        if p.piece is None:
            # no letter: pawn move, or long notation of a piece move ("g1-f3")
            if piece != chess.PAWN and not (p.from_file is not None and p.from_rank is not None):
                continue
        elif piece != p.piece:
            continue
        if p.to_file is not None and chess.square_file(mv.to_square) != p.to_file:
            continue
        if p.to_rank is not None and chess.square_rank(mv.to_square) != p.to_rank:
            continue
        if p.from_file is not None and chess.square_file(mv.from_square) != p.from_file:
            continue
        if p.from_rank is not None and chess.square_rank(mv.from_square) != p.from_rank:
            continue
        if mv.promotion:
            if p.promotion is not None and mv.promotion != p.promotion:
                continue
            if p.promotion is None and mv.promotion != chess.QUEEN:
                continue
        elif p.promotion is not None:
            continue
        if p.to_rank is None and not board.is_capture(mv):   # "ed" style must be a capture
            continue
        result.append(mv)
    return result


def render(board: chess.Board, mv: chess.Move, lang: Language) -> str:
    """Short algebraic notation in the given language (e.g. German 'Sf3')."""
    san = board.san(mv)
    out = []
    for ch in san:
        if ch in INTERNAL:
            out.append(lang.letter(INTERNAL[ch]))
        else:
            out.append(ch)
    return "".join(out)


def render_long(board: chess.Board, mv: chess.Move, lang: Language) -> str:
    """Long notation as often written in German clubs: 'Sg1-f3', 'e2-e4', 'Lf1xb5'."""
    if board.is_castling(mv):
        return "0-0" if board.is_kingside_castling(mv) else "0-0-0"
    piece = board.piece_type_at(mv.from_square)
    letter = "" if piece == chess.PAWN else lang.letter(piece)
    sep = "x" if board.is_capture(mv) else "-"
    promo = lang.letter(mv.promotion) if mv.promotion else ""
    return f"{letter}{chess.square_name(mv.from_square)}{sep}{chess.square_name(mv.to_square)}{promo}"


def render_plain(board: chess.Board, mv: chess.Move, lang: Language) -> str:
    """Fast short form without disambiguation or check marks (for similarity only)."""
    if board.is_castling(mv):
        return "0-0" if board.is_kingside_castling(mv) else "0-0-0"
    piece = board.piece_type_at(mv.from_square)
    to = chess.square_name(mv.to_square)
    cap = board.is_capture(mv)
    if piece == chess.PAWN:
        s = (chess.FILE_NAMES[chess.square_file(mv.from_square)] + "x" + to) if cap else to
        if mv.promotion:
            s += lang.letter(mv.promotion)
        return s
    return lang.letter(piece) + ("x" if cap else "") + to
