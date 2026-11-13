"""Reference move lists for the admin accuracy test (Igor's test sheets).

Only the moves are stored here (no names): the key is the game number from the
internal test catalog. Used when an admin uploads a sheet with "ref" set, to
measure how far the recognised game matches the hand-checked one.
"""
from __future__ import annotations

import chess

REFERENCES = {
    "01": "e4 e5 Nf3 Nc6 d4 exd4 Nxd4 Nxd4 Qxd4 d6 Bf4 h6 Nc3 Nf6 f3 Be7 O-O-O O-O Kb1 Be6 g4 Nh7 "
          "Qe3 Bg5 Bd3 Qf6 Bxg5 Qxg5 Qxg5 Nxg5 Be2 Nh3 Rd2 a6 Rhd1 Nf4 Bf1 Rad8 Ne2",
    "02": "d4 Nf6 Nf3 d6 e3 Nbd7 b3 g6 Bb2 Bg7 Nbd2 O-O Bd3 b6 c4 Bb7 Qc2 Re8 d5 Nc5 h4 e5 dxe6 Rxe6 "
          "Bxf6 Qxf6 O-O-O Nxd3+ Qxd3 Qb2#",
    "07": "e4 c6 d4 d5 e5 Bf5 Bd3 Bxd3 Qxd3 e6 Nf3 f6 O-O fxe5 Nxe5 Bd6 Bf4 Qf6 Bg3 Ne7 Nd2 O-O c4 Nf5 "
          "cxd5 exd5 a3 Bxe5 dxe5 Qg6 f4 Nd7 b4 a5 b5 Nc5 Qc2 Ne4 Nxe4 Ne3 Nf6+ gxf6 Qxg6+ hxg6 Rf3 Nc2 "
          "Rd1 fxe5 fxe5 Rxf3 gxf3 Nxa3 bxc6 bxc6 Kf2 a4 Ke3 Nc4+ Kd4 a3 Kc5 a2 Ra1 Ne3 Kxc6 Nc2 Rxa2 Rxa2 "
          "Kxd5 Ne3+ Ke6 Ra6+ Kd7 Nf5 e6 Ra7+ Bc7 Kg7 e7 Nxe7 Kxe7 Rxc7+ Ke6",
    "10": "e4 c6 Nc3 d5 exd5 cxd5 Qf3 Nf6 h3 Nc6 Nge2 g6 d3 Bg7 Bg5 O-O Bxf6 Bxf6 Nxd5 Bxb2 Rb1 Bg7 h4 h5 "
          "Ne3 Qa5+ Kd1 Be6 Rxb7 Rab8 Qxc6 Rxb7 Qxb7 Qxa2 Nc1 Qa4 Be2 Rc8 Nc4 Bh6 Nb3 Qa2 Nbd2 Kg7 Qb1 Qa4 "
          "Qb2+ f6 g4 Qc6 Rg1 Bxg4 Bxg4 hxg4 Rxg4 Qh1+ Ke2 Qh3 Rg3 Qxh4 Nd6 Qh5+ Nf3 Rd8 Qb7 Kf8 Ne4 Bf4 "
          "Rg2 Ke8 Qc6+ Kf8 Nxf6 exf6 Qxf6+ Ke8 Rxg6 Rd6 Rg8+ Kd7 Qxf4 Re6+ Kd2 Qa5+ Kd1 Qa1+ Qc1 Qa5 Rg7+ Kd6",
    "11": "d4 c6 Nf3 d5 e3 Bf5 Bd3 Bxd3 Qxd3 Nd7 b3 e6 Bb2 Ngf6 Nbd2 Bd6 O-O Qc7 c4 Qc8 Ne5 Qc7 f4 Bxe5 "
          "fxe5 Ng4 Qe2 h5 cxd5 exd5 Qf3 f6 h3 Nh6 Qxh5+ Nf7 Qg6 Rf8 e6 O-O-O exf7 Kb8 Ba3 Rh8 e4 Qa5 "
          "Bd6+ Ka8 b4 Qa3 e5 Qe3+ Rf2 Qxd4 Re1 fxe5 Nf3 Qb6 Nxe5 Nxe5 Bxe5 Qxb4 Ref1 Qc5 Kh1 Rc8 Bxg7",
}


def compare(ref: str, sans: list[str]) -> dict:
    """How many plies from the start match the reference (stops at the first difference,
    because after a wrong move the positions no longer agree)."""
    moves = REFERENCES[ref].split()
    same = 0
    for a, b in zip(sans, moves):
        if a != b:
            break
        same += 1
    return {"ref": ref, "ref_plies": len(moves), "match_until": same,
            "match_pct": round(100 * same / len(moves), 1)}


def check_references():
    """All reference lines must be legal games (used by the tests)."""
    for key, line in REFERENCES.items():
        b = chess.Board()
        for san in line.split():
            b.push_san(san)
