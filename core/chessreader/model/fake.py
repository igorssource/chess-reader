"""Offline stand-in for tests and local development (no API key, no cost)."""
from __future__ import annotations

from .base import ModelCall, ModelProvider, RecheckAnswer


class FakeProvider(ModelProvider):
    name = "fake"

    def __init__(self, settings, reading=None, recheck_answers=None):
        self.settings = settings
        self.reading = reading
        self.recheck_answers = recheck_answers or {}
        self.calls = 0

    def read_sheet(self, images):
        self.calls += 1
        return self.reading or demo_reading(), ModelCall(model="fake", cost_eur=0.01, purpose="read")

    def recheck(self, images, move_number, color, written, fen, legal_moves, previous_moves):
        self.calls += 1
        cands = [c for c in self.recheck_answers.get((move_number, color), []) if c in legal_moves]
        return RecheckAnswer(candidates=cands), ModelCall(model="fake", cost_eur=0.01, purpose="recheck")


def demo_reading():
    """Morphy's Opera game in German notation with two typical errors (for local testing)."""
    import chess
    from .. import notation
    from ..sheet import GameReading, Header, RawPly, Sheet
    sans = ("e4 e5 Nf3 d6 d4 Bg4 dxe5 Bxf3 Qxf3 dxe5 Bc4 Nf6 Qb3 Qe7 Nc3 c6 Bg5 b5 Nxb5 cxb5 "
            "Bxb5+ Nbd7 O-O-O Rd8 Rxd7 Rxd7 Rd1 Qe6 Bxd7+ Nxd7 Qb8+ Nxb8 Rd8#").split()
    b = chess.Board()
    plies = []
    for k, san in enumerate(sans):
        mv = b.parse_san(san)
        plies.append(RawPly(text=notation.render(b, mv, notation.LANGUAGES["de"]),
                            number=k // 2 + 1, color="wb"[k % 2]))
        b.push(mv)
    plies[2].text = "5f3"
    del plies[20]                       # forgotten move, writer continues in the next cell
    for k, p in enumerate(plies):
        p.number, p.color = k // 2 + 1, "wb"[k % 2]
    return GameReading(Header(white="Morphy", black="Herzog/Graf", event="Paris", result="1-0"),
                       [Sheet(plies=plies)])
