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
    for _, _, sec_toks, sres in decoded[1:]:
        board = chess.Board()
        for k, sp in enumerate(sres.plies):
            mv = board.parse_san(sp.san)
            local = notation.render(board, mv, target)
            board.push(mv)
            src = sec_toks[sp.token] if sp.token is not None else None
            sure = sp.status == "ok"
            if k < len(pres.plies):
                pp = pres.plies[k]
                if pp.token is None:
                    continue                      # inserted move on the main sheet: nothing to attach to
                tok = prim[pp.token]
                if tok.kind in ("empty", "gap", "illegible"):
                    if src is not None:
                        tok.text, tok.kind = local, "move"
                        tok.confidence = min(src.confidence, 0.8)
                    continue
                if pp.san == sp.san:
                    if sure:
                        tok.confidence = max(tok.confidence, 0.95)
                elif src is not None and sure and pp.status != "ok":
                    # the other sheet is clear here, this one is not: trust the clear one
                    old = tok.text
                    tok.text, tok.confidence = local, max(0.7, min(src.confidence, 0.9))
                    tok.alternatives = [x for x in [old] + tok.alternatives if x != local]
                elif src is not None and local not in tok.alternatives:
                    tok.alternatives = [local] + tok.alternatives
            elif src is not None:
                # the main record ends here: go on with the other sheet's moves
                prim.append(RawPly(text=local, number=k // 2 + 1, color="wb"[k % 2],
                                   confidence=src.confidence, alternatives=[], kind="move", sheet=src.sheet))
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
