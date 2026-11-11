import chess
from chessreader import notation

DE = notation.LANGUAGES["de"]


def m(board, text):
    p = notation.parse(text, DE)
    assert p is not None, text
    return [board.san(x) for x in notation.matches(board, p)]


def test_german_short_and_long():
    b = chess.Board()
    assert m(b, "e4") == ["e4"]
    assert m(b, "e2-e4") == ["e4"]
    assert m(b, "Sf3") == ["Nf3"]
    assert m(b, "Sg1-f3") == ["Nf3"]


def test_captures_castling_promotion():
    b = chess.Board("r3k2r/1P6/8/3p4/4P3/8/8/R3K2R w KQkq - 0 1")
    assert m(b, "e4:d5") == ["exd5"]
    assert m(b, "exd5") == ["exd5"]
    assert m(b, "ed") == ["exd5"]
    assert m(b, "0-0") == ["O-O"]
    assert m(b, "O-O-O") == ["O-O-O"]
    assert m(b, "b8D") == ["b8=Q+"]
    assert m(b, "bxa8=S+") == ["bxa8=N"]
    assert m(b, "b7-b8T") == ["b8=R+"]


def test_render():
    b = chess.Board()
    mv = chess.Move.from_uci("g1f3")
    assert notation.render(b, mv, DE) == "Sf3"
    assert notation.render_long(b, mv, DE) == "Sg1-f3"
