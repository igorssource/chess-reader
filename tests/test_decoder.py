import time

import chess
import pytest

from chessreader.decoder import decode
from chessreader.pgn_export import build_pgn
from chessreader.sheet import Header, RawPly
from synth import GAMES, random_game, renumber, write_german


def sans(result):
    return [p.san for p in result.plies]


@pytest.mark.parametrize("game", GAMES)
@pytest.mark.parametrize("long", [False, True])
def test_clean_sheet(game, long):
    truth = game.split()
    r = decode(write_german(truth, long=long))
    assert sans(r) == truth
    assert all(p.status == "ok" for p in r.plies)


def test_similar_symbols():
    truth = GAMES[0].split()
    sheet = write_german(truth)
    sheet[2].text = "5f3"        # S looks like 5
    sheet[13].text = "Dc7"       # De7 written with c
    r = decode(sheet)
    assert sans(r) == truth
    assert r.plies[2].status != "ok"
    assert r.plies[13].status != "ok"


def test_truly_ambiguous_goes_to_human():
    truth = GAMES[0].split()[:11]  # sheet ends here: nothing later can decide
    sheet = write_german(truth)
    sheet[10].text = "Lc6"       # Lc4 and La6 are equally close and both legal
    r = decode(sheet)
    p = r.plies[10]
    assert p.status == "doubtful"
    assert {"Lc4", "La6"} <= {p.local, *p.alternatives}


def test_hidden_missing_ply_and_swapped_colours():
    truth = GAMES[1].split()
    sheet = write_german(truth)
    del sheet[20]                # black's 11th move forgotten, everything shifts
    r = decode(renumber(sheet))
    assert sans(r) == truth
    assert r.plies[20].reason == "missing"


def test_explicit_empty_cell():
    truth = GAMES[0].split()
    sheet = write_german(truth)
    sheet[8] = RawPly(kind="empty", number=5, color="w")
    r = decode(sheet)
    assert sans(r) == truth


def test_numbering_jump_becomes_gap():
    from chessreader.sheet import GameReading, Sheet, flatten
    truth = GAMES[1].split()
    sheet = write_german(truth)
    del sheet[10:12]             # whole move 6 missing, numbers jump 5 -> 7
    tokens = flatten(GameReading(sheets=[Sheet(plies=sheet)]))
    assert [t.kind for t in tokens[10:12]] == ["gap", "gap"]
    r = decode(tokens)
    # the rest of the game is recovered; the two missing moves are not unique -> a person decides
    assert sans(r)[12:] == truth[12:]
    assert len(sans(r)) == len(truth)
    assert r.plies[10].status == "doubtful" or r.plies[11].status == "doubtful"


def test_alternatives_from_model():
    truth = GAMES[0].split()
    sheet = write_german(truth)
    sheet[4] = RawPly(text="?", kind="illegible", alternatives=["d4", "d3"], number=3, color="w")
    r = decode(sheet)
    assert sans(r) == truth


def test_random_games_with_noise_speed():
    for seed in range(5):
        truth = random_game(seed, 70)
        sheet = write_german(truth)
        sheet[15].text = sheet[15].text.replace("e", "c", 1) if "e" in sheet[15].text else sheet[15].text
        t = time.time()
        r = decode(sheet)
        assert time.time() - t < 10
        assert len(r.plies) == len(truth)


def test_pgn_export():
    truth = GAMES[0].split()
    sheet = write_german(truth)
    sheet[2].text = "5f3"
    r = decode(sheet)
    pgn = build_pgn(Header(white="Morphy", black="Duke/Count", result="1-0"), r)
    assert '[White "Morphy"]' in pgn and "Rd8#" in pgn and "korrigiert" in pgn


def test_ambiguous_rook_prefers_not_moving_back():
    # rook went d2->d1->d2 before; now "Td1" with rooks on d2 and h1: the h1 rook is likelier
    from chessreader.sheet import RawPly as R
    sans = "d4 d5 Nf3 Nf6 Bf4 Bf5 Na3 Na6 e3 e6 Be2 Be7 c3 c6 Qc2 Qc7 O-O-O O-O-O Rd2 Rd7".split()
    import chess
    from chessreader import notation
    b = chess.Board(); toks = []
    for k, san in enumerate(sans):
        mv = b.parse_san(san)
        toks.append(R(text=notation.render(b, mv, notation.LANGUAGES["de"]), number=k // 2 + 1, color="wb"[k % 2]))
        b.push(mv)
    toks.append(R(text="Td1", number=11, color="w"))
    r = decode(toks, "de")
    assert r.plies[-1].san == "Rhd1" and r.plies[-1].status == "doubtful"
    assert "Tdd1" in r.plies[-1].alternatives
