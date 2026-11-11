"""Builds the PGN file. Doubtful moves keep a comment so nothing is hidden."""
from __future__ import annotations

import chess
import chess.pgn

from .decoder import DecodeResult
from .sheet import Header

# Comment texts are settings too (PGN is usually read by German-speaking club members).
MESSAGES = {
    "de": {"doubtful": "unsicher", "written": "Bogen", "alternatives": "Alternativen",
           "missing": "fehlt auf dem Bogen", "fixed": "korrigiert"},
    "ru": {"doubtful": "сомнительно", "written": "на бланке", "alternatives": "варианты",
           "missing": "нет на бланке", "fixed": "исправлено"},
}


def build_pgn(header: Header, result: DecodeResult, comments_language: str = "de") -> str:
    msg = MESSAGES.get(comments_language, MESSAGES["de"])
    game = chess.pgn.Game()
    game.headers["Event"] = header.event or "?"
    game.headers["Site"] = header.site or "?"
    game.headers["Date"] = header.date or "????.??.??"
    game.headers["Round"] = header.round or "?"
    game.headers["White"] = header.white or "?"
    game.headers["Black"] = header.black or "?"
    game.headers["Result"] = header.result if header.result in ("1-0", "0-1", "1/2-1/2", "*") else "*"
    node = game
    for p in result.plies:
        board = node.board()
        node = node.add_variation(board.parse_san(p.san))
        if p.status == "ok":
            continue
        parts = []
        if p.reason == "missing":
            parts.append(msg["missing"])
        elif p.status == "doubtful":
            parts.append(msg["doubtful"])
        else:
            parts.append(msg["fixed"])
        if p.written and p.written != p.local:
            parts.append(f'{msg["written"]}: "{p.written}"')
        if p.alternatives:
            parts.append(f'{msg["alternatives"]}: {", ".join(p.alternatives)}')
        node.comment = "; ".join(parts)
    exporter = chess.pgn.StringExporter(headers=True, variations=False, comments=True)
    return game.accept(exporter)
