"""Replays the written moves with python-chess and repairs errors.

Every way of reading the sheet is a path with a cost:
  * written move matches a legal move exactly            -> 0
  * one of the model's alternatives matches               -> small cost
  * a legal move that *looks* similar to what was written -> cost by similarity
  * a move the writer forgot (hidden gap, colours swapped)-> MISSING_PLY
  * a written cell that is not a move of this game        -> SKIP_TOKEN
A beam search keeps the cheapest paths and returns the best one, plus close
alternatives so a person can decide where the sheet is truly ambiguous.
No neural network here, only chess rules.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import chess

from . import notation, similarity
from .sheet import RawPly


@dataclass
class DecoderSettings:
    beam_width: int = 48
    max_similarity: float = 2.0       # ignore legal moves less similar than this
    similar_base: float = 0.5
    alternative_cost: float = 0.6     # per rank of the model's alternative
    missing_ply: float = 2.5
    max_consecutive_missing: int = 2
    skip_token: float = 3.0
    empty_fill: float = 0.3           # an explicitly empty cell is filled with a move
    empty_skip: float = 1.5
    gap_fill: float = 1.0
    gap_skip: float = 1.0
    illegible_fill: float = 1.2
    low_confidence: float = 0.6
    ambiguity_margin: float = 0.35
    lookahead_bonus: float = 0.1      # guessed move that lets the side's next written moves work
    lookahead_moves: int = 3
    move_back_cost: float = 0.1       # ambiguous written move: undoing own last move is less likely
    insert_from_top: int = 8          # only the best paths may assume a forgotten move     # alternatives within this cost are shown to a person


@dataclass
class Step:
    move: chess.Move
    token: int | None                 # index of the written cell, None = inserted move
    cost: float
    kind: str                         # exact | alternative | similar | missing | fill | user
    ambiguous_written: bool = False   # written move fitted several legal moves


@dataclass
class _State:
    board: chess.Board
    token: int
    cost: float
    steps: tuple                      # tuple of Step (persistent)
    skipped: tuple                    # token indices skipped
    missing_run: int = 0


@dataclass
class DecodedPly:
    ply: int
    san: str                          # internal (English) SAN
    written: str                      # what was on the sheet ("" if inserted)
    local: str                        # move in the sheet's language
    status: str                       # ok | fixed | doubtful
    reason: str                       # exact | alternative | similar | missing | fill
    alternatives: list[str] = field(default_factory=list)   # in sheet's language
    token: int | None = None
    fen_before: str = ""


@dataclass
class DecodeResult:
    plies: list[DecodedPly]
    skipped_tokens: list[int]
    cost: float
    final_fen: str


def _candidates(board: chess.Board, tok: RawPly, lang, s: DecoderSettings):
    """Cost of reading this cell as each legal move."""
    costs: dict[chess.Move, tuple[float, str, bool]] = {}

    def put(mv, c, kind, amb=False):
        if mv not in costs or costs[mv][0] > c:
            costs[mv] = (c, kind, amb)

    parsed = notation.parse(tok.text, lang)
    if parsed:
        found = notation.matches(board, parsed)
        for mv in found:
            put(mv, 0.0 if len(found) == 1 else 0.3, "exact", len(found) > 1)
    for rank, alt in enumerate(tok.alternatives, start=1):
        p = notation.parse(alt, lang)
        if p:
            for mv in notation.matches(board, p):
                put(mv, s.alternative_cost * rank, "alternative")
    written = notation.clean(tok.text).rstrip("+#")
    if written:
        legal = list(board.legal_moves)
        targets: dict = {}
        for mv in legal:
            k = (board.piece_type_at(mv.from_square), mv.to_square)
            targets[k] = targets.get(k, 0) + 1
        for mv in legal:
            k = (board.piece_type_at(mv.from_square), mv.to_square)
            short = (notation.render(board, mv, lang).rstrip("+#") if targets[k] > 1
                     else notation.render_plain(board, mv, lang))   # keep "Tad8" vs "Tfd8"
            d = min(similarity.distance(written, short),
                    similarity.distance(written, notation.render_long(board, mv, lang)))
            if 0 < d <= s.max_similarity:
                put(mv, s.similar_base + d, "similar")
    return costs


def _plausibility(board: chess.Board, mv: chess.Move, tokens, first: int, lang, s, cache) -> float:
    """Bonus for a guessed move: do this side's next written moves fit after it?

    The opponent's moves in between are ignored (null moves); this only breaks
    ties between otherwise equally good guesses.
    """
    key = ("plaus", board._transposition_key(), mv, first)
    if key in cache:
        return cache[key]
    b = board.copy(stack=False)
    b.push(mv)
    score = 0
    for j in range(first, min(len(tokens), first + 2 * s.lookahead_moves), 2):
        tok = tokens[j]
        p = notation.parse(tok.text, lang) if tok.kind == "move" else None
        if p is None:
            break
        b.push(chess.Move.null())
        found = notation.matches(b, p)
        if not found:
            break
        b.push(found[0])
        score += 1
    cache[key] = bonus = s.lookahead_bonus * score
    return bonus


def _key(b: chess.Board, token: int):
    return (b._transposition_key(), token)


def decode(tokens: list[RawPly], language: str = "de",
           settings: DecoderSettings | None = None,
           start: chess.Board | None = None) -> DecodeResult:
    s = settings or DecoderSettings()
    lang = notation.LANGUAGES[language]
    n = len(tokens)
    # trailing empty cells are free to skip
    last_real = max((i for i, t in enumerate(tokens) if t.kind not in ("empty", "gap")), default=-1)

    layer = [_State(start.copy() if start else chess.Board(), 0, 0.0, (), ())]
    finished: list[_State] = []
    cache: dict = {}

    for i in range(n + 1):
        if i == n:
            finished = layer
            break
        tok = tokens[i]
        next_layer: dict = {}
        queue = layer
        while queue:
            queue = _prune(queue, s.beam_width)
            same_layer: dict = {}
            for rank, st in enumerate(queue):
                for child in _expand(st, tok, i, i > last_real, lang, s, cache,
                                     allow_insert=rank < s.insert_from_top, tokens=tokens):
                    target = next_layer if child.token == i + 1 else same_layer
                    k = _key(child.board, child.token)
                    if k not in target or target[k].cost > child.cost:
                        target[k] = child
            queue = list(same_layer.values())
        layer = _prune(list(next_layer.values()), s.beam_width)
        if not layer:
            break

    finished.sort(key=lambda x: x.cost)
    if not finished:
        return DecodeResult([], list(range(n)), float("inf"), chess.STARTING_FEN)
    return _build_result(finished, tokens, lang, s, start)


def _prune(states, width):
    states = sorted(states, key=lambda x: x.cost)
    return states[:width]


def _expand(st: _State, tok: RawPly, i: int, trailing: bool, lang, s: DecoderSettings,
            cache: dict, allow_insert: bool = True, tokens=()):
    board = st.board

    def push(mv, cost, kind, consume=True, amb=False):
        b = board.copy(stack=False)
        b.push(mv)
        step = Step(mv, i if consume else None, cost, kind, amb)
        return _State(b, i + 1 if consume else i, st.cost + cost, st.steps + (step,), st.skipped,
                      0 if consume else st.missing_run + 1)

    def skip(cost):
        return _State(board, i + 1, st.cost + cost, st.steps, st.skipped + (i,), 0)

    if trailing and tok.kind in ("empty", "gap"):
        yield skip(0.0)
        return

    if tok.kind in ("empty", "gap", "illegible"):
        fill = {"empty": s.empty_fill, "gap": s.gap_fill, "illegible": s.illegible_fill}[tok.kind]
        sk = {"empty": s.empty_skip, "gap": s.gap_skip, "illegible": s.skip_token}[tok.kind]
        for mv in board.legal_moves:
            yield push(mv, fill - _plausibility(board, mv, tokens, i + 2, lang, s, cache), "fill")
        # an illegible cell may still carry alternatives
        if tok.kind == "illegible" and tok.alternatives:
            for mv, (c, kind, amb) in _candidates(board, tok, lang, s).items():
                yield push(mv, min(c, fill), kind)
        yield skip(sk)
        return

    if tok.pinned:
        # a person chose this move: only that move, no skipping, nothing inserted before it
        parsed = notation.parse(tok.text, lang)
        for mv in (notation.matches(board, parsed) if parsed else [])[:1]:
            yield push(mv, 0.0, "user")
        return

    ck = _key(board, i)
    cands = cache.get(ck)
    if cands is None:
        cands = cache[ck] = _candidates(board, tok, lang, s)
    # Several pieces fit the written move (Td1 with rooks on d2 and h1): a piece rarely
    # goes straight back to where it just came from, so that reading costs a little more.
    own_prev = st.steps[-2].move if len(st.steps) >= 2 else None
    for mv, (c, kind, amb) in cands.items():
        if amb and own_prev is not None and mv.from_square == own_prev.to_square \
                and mv.to_square == own_prev.from_square:
            c += s.move_back_cost
        yield push(mv, c, kind, amb=amb)
    has_exact = any(k == "exact" for _, k, _ in cands.values())
    if not has_exact or tok.confidence < s.low_confidence:
        if allow_insert and st.missing_run < s.max_consecutive_missing:
            for mv in board.legal_moves:
                yield push(mv, s.missing_ply - _plausibility(board, mv, tokens, i + 1, lang, s, cache), "missing", consume=False)
        yield skip(s.skip_token)


def _build_result(finished, tokens, lang, s, start) -> DecodeResult:
    best = finished[0]
    # alternatives: near-best paths, recorded at the ply where they first differ
    alts: dict[int, list[chess.Move]] = {}
    best_moves = [st.move for st in best.steps]
    for other in finished[1:]:
        if other.cost > best.cost + s.ambiguity_margin:
            break
        om = [st.move for st in other.steps]
        for k in range(min(len(om), len(best_moves))):
            if om[k] != best_moves[k]:
                lst = alts.setdefault(k, [])
                if om[k] not in lst:
                    lst.append(om[k])
                break

    board = start.copy() if start else chess.Board()
    plies = []
    for k, step in enumerate(best.steps):
        tok = tokens[step.token] if step.token is not None else None
        alt_moves = [m for m in alts.get(k, []) if m in board.legal_moves]
        if step.kind == "exact" and not step.ambiguous_written and not (
                tok is not None and tok.confidence < s.low_confidence):
            alt_moves = []   # the written move fits the rules: a near miss elsewhere is no doubt here
        low_conf = tok is not None and tok.kind == "move" and tok.confidence < s.low_confidence
        if alt_moves or step.ambiguous_written or (low_conf and step.kind != "exact"):
            status = "doubtful"
        elif step.kind == "exact" and not low_conf:
            status = "ok"
        elif step.kind == "exact" and low_conf:
            status = "fixed"     # model unsure, but the written text fits the rules
        else:
            status = "fixed"
        if step.kind in ("missing", "fill"):
            status = "doubtful"     # a guessed move is always shown to a person
        if step.kind == "user":
            status, alt_moves = "ok", []
        plies.append(DecodedPly(
            ply=k,
            san=board.san(step.move),
            written=(tok.orig or "" if tok.pinned else tok.text) if tok else "",
            local=notation.render(board, step.move, lang),
            status=status,
            reason=step.kind,
            alternatives=[notation.render(board, m, lang) for m in alt_moves],
            token=step.token,
            fen_before=board.fen(),
        ))
        board.push(step.move)
    return DecodeResult(plies, list(best.skipped), best.cost, board.fen())
