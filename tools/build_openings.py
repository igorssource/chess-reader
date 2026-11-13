"""Builds core/chessreader/data/openings.tsv from the lichess-org/chess-openings tables
(https://github.com/lichess-org/chess-openings, public domain / CC0).

Usage:  python tools/build_openings.py a.tsv b.tsv c.tsv d.tsv e.tsv
Each output line: ECO <tab> English name <tab> position (EPD, without move counters).
Storing the position (not the moves) lets the lookup also find openings reached by
a different move order (transpositions).
"""
import pathlib
import sys

import chess

OUT = pathlib.Path(__file__).resolve().parents[1] / "core/chessreader/data/openings.tsv"


def main(paths):
    rows = {}
    for path in paths:
        for line in pathlib.Path(path).read_text(encoding="utf-8").splitlines()[1:]:
            eco, name, pgn = line.split("\t")
            board = chess.Board()
            for tok in pgn.split():
                if tok.endswith("."):
                    continue
                board.push_san(tok)
            epd = board.epd()
            # Several lines can lead to one position: keep the first (tables are sorted by ECO).
            rows.setdefault(epd, (eco, name))
    lines = [f"{eco}\t{name}\t{epd}" for epd, (eco, name) in rows.items()]
    OUT.write_text("# Source: lichess-org/chess-openings (CC0). Built by tools/build_openings.py\n"
                   + "\n".join(lines) + "\n", encoding="utf-8")
    print(len(lines), "positions ->", OUT)


if __name__ == "__main__":
    main(sys.argv[1:])
