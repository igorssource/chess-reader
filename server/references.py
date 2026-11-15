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
    # 11: checked move by move by Igor against the sheet (2026-11-14)
    "11": "d4 c6 Nf3 d5 e3 Bf5 Bd3 Bxd3 Qxd3 Nd7 b3 e6 Bb2 Ngf6 Nbd2 Bd6 O-O Qc7 c4 Qc8 Ne5 Qc7 f4 Bxe5 "
          "fxe5 Ng4 Qe2 h5 cxd5 exd5 Qf3 f6 h3 Nh6 Qxh5+ Nf7 Qg6 Rf8 e6 O-O-O exf7 Kb8 Ba3 Rh8 e4 Qa5 "
          "Bd6+ Ka8 b4 Qa3 e5 Qe3+ Rf2 Qxd4 Re1 fxe5 Nf3 Qb6 Nxe5 Nxe5 Bxe5 Qxb4 Ref1 Qc5 Kh1 Rc8 Bxg7",
    # 12-18: club coach's games, my transcription from the photos (all moves legal), not yet checked by a person
    "12": "e4 c5 Nf3 d6 c3 Nf6 Be2 e6 O-O Nc6 d3 Be7 Re1 O-O Bf1 b6 d4 cxd4 cxd4 Bb7 Nc3 Rc8 Bd3 Nb4 Bb1 d5 e5 "
          "Ne4 Re3 Qd7 a3 Na6 Nxe4 dxe4 Bxe4 Bxe4 Rxe4 Rfd8 Re2 Nc7 Be3 Nd5 Rc1 Rxc1 Qxc1 Rc8 Rc2 Rxc2 Qxc2 Qc7 "
          "Qxc7 Nxc7 Kf1 Kf8 Ke2 Ke8 Kd3 h6 Bd2 Kd7 Ne1 Nd5 g3 f5 exf6 Nxf6 h3 Bd6 Nf3 Kc6 Ne5+ Kd5 Nc4 Bc7 Bc3 "
          "Nd7 Ne3+ Kd6 Bb4+ Kc6 Be7 g6 Ke4 a5 f4 b5 Ng4 h5 Ne5+ Bxe5 dxe5 Nb6 b3 Nd5 Bd8 a4 bxa4 bxa4 Kd4 Kd7 "
          "Bg5 Kc6 g4 hxg4 hxg4 Nb6 Bf6 Nd5 Kc4 Kb6 Bd8+ Kc6 Bg5 Nb6+ Kb4 Kd5 Kb5 Nc4 Kxa4 Ke4 Kb4 Nb6 Kb5 Nd5 "
          "a4 Nc3+ Kb4 Ne2 Kc5 Nd4 a5 Nb3+ Kb4 Nd4 Kc5 Nb3+ Kb6 Kd5 a6",
    "13": "d4 d6 c4 e5 d5 f5 Nc3 Nf6 Nf3 Be7 Qc2 Na6 a3 Nc5 Ng5 a5 g3 h6 Nf3 Nfe4 Bg2 Nxc3 Qxc3 O-O e3 Bf6 Qc2 "
          "e4 Nd4 Nd3+ Kf1 Qe7 Bd2 Bxd4 exd4 f4 gxf4 Qh4 Be3 Bh3 Rg1 Rae8 Bxh3 Qxh3+ Rg2 Rxf4 Kg1 Rg4 Rg3 Rf8 "
          "Qe2 Rf3 b3 h5 c5 h4 Rxg4 Qxg4+ Kh1 Qf5 Rf1 Qxd5 Qc2 Qf5 b4 Rxe3 cxd6 cxd6 Qc7 Qf3+ Kg1 Qg4+ Kh1 "
          "Nxf2+",
    "14": "d4 d6 e4 c6 Nc3 Qc7 a4 e5 Bc4 Nf6 Bb3 Nbd7 Be3 Be7 h3 Nf8 d5 Ng6 g3 h6 a5 O-O Nf3 c5 Nd2 Rb8 Bc4 a6 "
          "Bd3 Bd8 Nc4 Qe7 Be2 b5 axb6 Bxb6 Bg4 Nd7 Bf5 Bc7 b3 Bb7 h4 Rfd8 Qg4 Nf6 Qf3 Nd7 Kd2 Nb6 Na5 c4 bxc4 "
          "Nd7 Nxb7 Rxb7 Rxa6 Rb4 Ra7 Rxc4 Qe2 Rd4+ Bxd4 exd4 Rxc7 dxc3+ Ke1 Ngf8 Qe3 Ra8 Kf1 Qd8 Rxc3 Ne6 Kg2 "
          "g6 Bg4 Qf8 e5 Qe7 exd6",
    "15": "e4 e5 Nf3 Nc6 Bc4 Bc5 c3 Qe7 O-O Nf6 d4 Bb6 Bg5 O-O d5 Nd8 Bd3 d6 a4 a6 Nfd2 h6 Bh4 g5 Bg3 Bg4 Be2 "
          "Qd7 Bxg4 Qxg4 Qxg4 Nxg4 Nc4 Ba7 h3 Nf6 Nbd2 Nd7 Ne3 f6 Nf5 Kh7 b4 Nf7 Rfc1 Rfe8 a5 Kg6 Kf1 Rad8 f3 "
          "c6 c4 Nb8 Bf2 Bxf2 Kxf2 Rd7 Nf1 h5 N1e3 Kh7 Rab1 Rc8 dxc6 bxc6 Rd1 Rcd8 Rb2 Kg6 Rbd2 Kh7 Rb2 Nh8 b5 "
          "Nf7 Rdb1 Rb7 b6 Nd7 Nc2 Nc5 Nb4 Rc8 Rd2 Rd7 Nd3 Nb7 Ra2 Kg6 Rd1 Nfd8 Nb4 Ra8 g3 Kf7 c5 Ke6 cxd6 c5 "
          "Nd5",
    "16": "Nf3 d6 c4 c6 Nc3 e5 e3 Nd7 d4 Ngf6 Be2 Be7 O-O O-O Qc2 Re8 Rd1 Qc7 b3 Nf8 Bb2 Ng6 dxe5 dxe5 h3 Bd6 "
          "Bd3 Qe7 Ne4 Nxe4 Bxe4 Rf8 Bf5 Bxf5 Qxf5 f6 c5 Bxc5 Rd7 Qe8 Rxb7 Qc8 Rd7 Re8 Rad1 Nf8 Ng5 Rd8 Rxd8 "
          "Qxf5 Rxa8 Qxg5 b4 Bxb4 Rxa7 Qg6 Rc1 Qd3 a3 Bd2 Rxc6 Bxe3 Rb7 Qb1+ Kh2 Bxf2 Rc1 Qd3 Rb8 Bg3+ Kh1 Qe4",
    "17": "e4 c5 Nf3 d6 c3 Nf6 Be2 g6 O-O Bg7 Bb5+ Nc6 Re1 O-O h3 a6 Bxc6 bxc6 d4 cxd4 cxd4 a5 Nc3 Ba6 Bg5 Nd7 "
          "Qd2 Rb8 Bh6 Bxh6 Qxh6 f6 b3 e5 Rad1 Qe7 Rd2 Rfd8 Red1 Nf8 Qe3 Rd7 Ne1 Kg7 Nc2 g5 Qg3 Rdd8 Ne3 Bc8 "
          "dxe5 fxe5 Nc4 Ng6 Nxd6 Be6 Nf5+ Bxf5 exf5 Nf4 Qf3 Rxd2 Rxd2 Kh8 Qxc6 Qf7 f6 Qg6 Ne4 Rg8 f3 h5 Qd6 g4 "
          "f7 Nxh3+ gxh3",
    "18": "Nf3 d6 d4 Nf6 c4 Nbd7 Nc3 e5 Bg5 Be7 dxe5 dxe5 e3 c6 Bd3 O-O Bxf6 Bxf6 Qc2 g6 O-O Bg7 Rfd1 Qe7 Rab1 "
          "a5 a3 Nc5 e4 Bg4 Be2 a4 Rd2 Be6 Ne1 Bh6 Rdd1 Nb3 Na2 f6 Nb4 Rfd8 Nf3 Qc5 Rd3 Bf8 Rbd1 Be7 Nd2 Nd4 "
          "Rxd4 Rxd4 Nf3 Rxd1+",
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
