from chessreader.openings import detect


def test_known_openings():
    o = detect("e4 e5 Nf3 Nc6 Bb5 a6".split())
    assert o.eco == "C70" and o.family == "Ruy Lopez"
    o = detect("d4 d5 c4 e6 Nc3 Nf6 Bg5 Be7".split())
    assert o.eco.startswith("D") and o.family == "Queen's Gambit Declined"
    assert detect("e4 c5".split()).family == "Sicilian Defense"


def test_transposition_and_bad_moves():
    # Same position as 1.d4 d5 2.c4, reached by a different move order
    assert detect("c4 d5 d4".split()).family == "Queen's Gambit"
    # an unreadable move stops the walk, the name from before it stays
    assert detect("e4 e5 Zz9 Nc6".split()).family == "King's Pawn Game"
    assert detect([]) is None
