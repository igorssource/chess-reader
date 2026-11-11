"""Hand transcriptions of real club scoresheets, cell by cell, exactly as written.

Photos are NOT kept in the repository (personal data); only the written text.
"""
from chessreader.decoder import decode
from chessreader.sheet import GameReading, RawPly, Sheet, flatten


def tokens(cells):
    out = []
    for n, c in enumerate(cells.split("|"), 1):
        parts = c.split()
        for color, text in zip("wb", parts):
            out.append(RawPly(text, n, color))
    return out


def test_club_sheet_with_castling_zeros_writing_slip_and_remis():
    # "000"/"00" castling, "ed" pawn capture, "Tad1" written for Tad8, "Remi" in a move cell
    cells = ("e4 e5|Sf3 Sc6|d4 ed|Sxd4 Sxd4|Dxd4 d6|Lf4 h6|Sc3 Sf6|f3 Le7|000 00|Kb1 Le6|g4 Sh7|"
             "De3 Lg5|Ld3 Df6|Lxg5 Dxg5|Dxg5 Sxg5|Le2 Sh3|Td2 a6|Thd1 Sf4|Lf1 Tad1|Se2 Remi")
    reading = GameReading(sheets=[Sheet(plies=tokens(cells))])
    r = decode(flatten(reading))
    assert len(r.plies) == 39 and not r.skipped_tokens
    assert reading.header.result == "1/2-1/2"
    assert r.plies[37].local == "Tad8" and r.plies[37].status != "ok"
    assert all(p.status == "ok" for k, p in enumerate(r.plies) if k != 37)
