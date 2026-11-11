"""Synthetic scoresheets: real-looking games written in German, with typical writer errors."""
import random

import chess

from chessreader import notation
from chessreader.sheet import RawPly

DE = notation.LANGUAGES["de"]

# Some known games (SAN, English) used as ground truth.
GAMES = [
    # Opera game, Morphy 1858
    "e4 e5 Nf3 d6 d4 Bg4 dxe5 Bxf3 Qxf3 dxe5 Bc4 Nf6 Qb3 Qe7 Nc3 c6 Bg5 b5 Nxb5 cxb5 "
    "Bxb5+ Nbd7 O-O-O Rd8 Rxd7 Rxd7 Rd1 Qe6 Bxd7+ Nxd7 Qb8+ Nxb8 Rd8#",
    # Immortal game, Anderssen 1851
    "e4 e5 f4 exf4 Bc4 Qh4+ Kf1 b5 Bxb5 Nf6 Nf3 Qh6 d3 Nh5 Nh4 Qg5 Nf5 c6 g4 Nf6 Rg1 cxb5 "
    "h4 Qg6 h5 Qg5 Qf3 Ng8 Bxf4 Qf6 Nc3 Bc5 Nd5 Qxb2 Bd6 Bxg1 e5 Qxa1+ Ke2 Na6 Nxg7+ Kd8 "
    "Qf6+ Nxf6 Be7#",
]


def random_game(seed, plies=60):
    rnd = random.Random(seed)
    b = chess.Board()
    sans = []
    for _ in range(plies):
        if b.is_game_over():
            break
        mv = rnd.choice(list(b.legal_moves))
        sans.append(b.san(mv))
        b.push(mv)
    return sans


def write_german(sans, long=False):
    b = chess.Board()
    out = []
    for k, san in enumerate(sans):
        mv = b.parse_san(san)
        text = notation.render_long(b, mv, DE) if long else notation.render(b, mv, DE)
        out.append(RawPly(text=text, number=k // 2 + 1, color="w" if k % 2 == 0 else "b"))
        b.push(mv)
    return out


def renumber(plies):
    """Writer keeps writing in the next free cell (hidden skip): numbers follow the cells."""
    for k, p in enumerate(plies):
        p.number = k // 2 + 1
        p.color = "w" if k % 2 == 0 else "b"
    return plies
