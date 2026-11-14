"""Several photos of one game: a continuation page, or the opponent's scoresheet.

The opponent's sheet is a second, independent record of the same moves. Both sheets
are decoded on their own (free, no model call), the better one becomes the main
record, and the other one's moves are added to it half-move by half-move:
  * both sheets give the same move  -> the move is confirmed (high confidence);
  * they differ                     -> the other sheet's move becomes the first
                                       alternative, the chess check decides;
  * a cell is empty/unreadable here -> the other sheet's move fills it;
  * the main sheet stops earlier    -> the other sheet's remaining moves are added.
Aligning by half-move (not by the printed numbers) keeps working when one player
skipped a move in their notation.
"""
from __future__ import annotations

from dataclasses import replace

import chess

from . import notation
from .decoder import DecodeResult, decode
from .sheet import GameReading, Header, RawPly, Sheet, flatten


def detect_language(sheet: Sheet, default: str) -> str:
    """German or English piece letters? Count the cells each language can parse."""
    texts = [p.text for p in sheet.plies if p.kind == "move" and p.text]
    if not texts:
        return default

    def score(code):
        lang = notation.LANGUAGES[code]
        return sum(1 for t in texts if notation.parse(t, lang)
                   and any(ch in lang.pieces for ch in t if ch.isupper() and ch != "K"))

    scores = {c: score(c) for c in ("de", "en")}
    best = max(scores, key=scores.get)
    return best if scores[best] > scores.get(default, 0) else default


def classify(sheets: list[Sheet]) -> list[Sheet]:
    """Second photo: continuation (its numbers start after the first one ends) or
    the opponent's record of the same game."""
    if len(sheets) < 2:
        return sheets
    first = sheets[0]
    out = [first]
    last = max((p.number or 0 for p in first.plies), default=0)
    for s in sheets[1:]:
        nums = [p.number for p in s.plies if p.number]
        if nums and last and min(nums) > last - 1:
            out.append(replace(s, role="continuation"))
            last = max(nums)
        else:
            out.append(replace(s, role="opponent"))
    return out


def merge_headers(headers: list[Header]) -> Header:
    h = Header(**headers[0].__dict__)
    for other in headers[1:]:
        for k, v in other.__dict__.items():
            if getattr(h, k) in ("?", "", "*", "????.??.??", None) and v not in ("?", "", "*", "????.??.??", None):
                setattr(h, k, v)
    return h


def _problems(r: DecodeResult) -> float:
    n = len(r.plies)
    bad = sum(p.status != "ok" for p in r.plies) + len(r.skipped_tokens)
    return bad / max(n, 1) - 0.001 * n          # ties: the longer record wins


def build_tokens(reading: GameReading, language: str) -> list[RawPly]:
    """Cells to decode, in the main notation language. With an opponent's sheet the
    two records are merged as described above."""
    mains = [s for s in reading.sheets if s.role != "opponent"]
    opps = [s for s in reading.sheets if s.role == "opponent"]
    if not opps:
        # one record (maybe with a continuation page): each sheet may use English or
        # German letters; everything is brought to the main notation language
        toks = flatten(reading)
        langs = {sh.image: detect_language(sh, sh.language if sh.language in notation.LANGUAGES else language)
                 for sh in mains}
        return [_to_language(t, langs.get(t.sheet, language), language) for t in toks]
    records = [GameReading(reading.header, mains)] + [GameReading(reading.header, [replace(s, role="main")]) for s in opps]
    decoded = []
    for rec in records:
        # letters on the paper decide; the model's own guess breaks a tie
        sheet_lang = rec.sheets[0].language if rec.sheets[0].language in notation.LANGUAGES else language
        lang = detect_language(rec.sheets[0], sheet_lang)
        toks = flatten(rec)
        decoded.append((rec, lang, toks, decode(toks, lang)))
    decoded.sort(key=lambda d: _problems(d[3]))
    _, plang, prim, pres = decoded[0]
    prim = [_to_language(t, plang, language) for t in prim]
    target = notation.LANGUAGES[language]
    # A move of the other sheet is only compared with the main sheet's move made from the
    # SAME position (not just the same move number): after a skipped or misread move the
    # two records would otherwise be compared one move apart and give wrong "confirmations".
    main_at = {_pos(pp.fen_before): pp for pp in pres.plies}
    last_main_fen = _pos(pres.final_fen)
    # cells of the main record by printed number, for hints when the positions differ
    by_number = {(t.number, t.color): t for t in prim if t.kind == "move" and t.number and t.color}
    for _, _, sec_toks, sres in decoded[1:]:
        board = chess.Board()
        tail = False
        for k, sp in enumerate(sres.plies):
            mv = board.parse_san(sp.san)
            local = notation.render(board, mv, target)
            here = _pos(board.fen())
            board.push(mv)
            src = sec_toks[sp.token] if sp.token is not None else None
            sure = sp.status == "ok"
            pp = main_at.get(here)
            if pp is None:
                if (tail or here == last_main_fen) and src is not None:
                    # the main record ends here: go on with the other sheet's moves
                    tail = True
                    prim.append(RawPly(text=local, number=k // 2 + 1, color="wb"[k % 2],
                                       confidence=min(src.confidence, 0.55), alternatives=[], kind="move",
                                       sheet=src.sheet))
                elif src is not None:
                    # the records went apart (a misread move on one of them): the other
                    # sheet's move with the same number is still a good hint, but only a hint
                    tok = by_number.get((k // 2 + 1, "wb"[k % 2]))
                    if (tok is not None and tok.confidence < 0.9 and local != tok.text
                            and local not in tok.alternatives and len(tok.alternatives) < 4):
                        tok.alternatives.append(local)
                continue
            if pp.token is None or src is None:
                continue                          # an inserted move on either sheet: nothing to compare
            tok = prim[pp.token]
            if tok.kind in ("empty", "gap", "illegible"):
                tok.text, tok.kind = local, "move"
                tok.confidence = 0.55             # taken from the other sheet: shown as corrected, not as sure
                continue
            if pp.san == sp.san:
                if sure and pp.reason == "exact":
                    tok.confidence = max(tok.confidence, 0.95)   # both sheets say the same
                continue
            # the sheets disagree: never shown as sure
            if sure and pp.reason != "exact":
                # the other sheet is clear, this one did not fit as written: use the clear one
                old = tok.text
                tok.text = local
                tok.alternatives = [x for x in [old] + tok.alternatives if x and x != local]
            else:
                if local not in tok.alternatives:
                    tok.alternatives = [local] + tok.alternatives
                tok.conflict = True               # a person should look at it
            tok.confidence = min(tok.confidence, 0.5)
    return prim


def _to_language(tok: RawPly, src: str, dst: str) -> RawPly:
    if src == dst:
        return tok
    a, b = notation.LANGUAGES[src], notation.LANGUAGES[dst]

    def tr(text):
        internal = notation.to_internal(text, a)
        return "".join(b.letter(notation.INTERNAL[ch]) if ch in notation.INTERNAL else ch for ch in internal)

    tok.text = tr(tok.text)
    tok.alternatives = [tr(x) for x in tok.alternatives]
    return tok


def _pos(fen: str) -> str:
    """Position part of a FEN (pieces, side to move, castling, en passant)."""
    return " ".join(fen.split(" ")[:4])
