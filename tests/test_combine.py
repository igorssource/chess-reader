"""Opponent's sheet, continuation page, zoomed crops."""
import io

import chess

from chessreader import notation
from chessreader.combine import build_tokens, classify, detect_language
from chessreader.config import Settings
from chessreader.decoder import decode
from chessreader.imaging import cell_box, crop_cell, prepare
from chessreader.model.base import Image
from chessreader.model.fake import FakeProvider
from chessreader.pipeline import process_game
from chessreader.sheet import GameReading, Header, RawPly, Sheet

from synth import GAMES

SANS = GAMES[0].split()


def cells(sans, lang="de"):
    L = notation.LANGUAGES[lang]
    b = chess.Board()
    out = []
    for k, san in enumerate(sans):
        mv = b.parse_san(san)
        out.append(RawPly(text=notation.render(b, mv, L), number=k // 2 + 1, color="wb"[k % 2]))
        b.push(mv)
    return out


def test_detect_language():
    assert detect_language(Sheet(plies=cells(SANS, "en")), "de") == "en"
    assert detect_language(Sheet(plies=cells(SANS, "de")), "de") == "de"


def test_classify_continuation_and_opponent():
    a = Sheet(plies=cells(SANS)[:20])
    cont = Sheet(plies=[RawPly(text="x", number=n, color="w") for n in (11, 12)])
    opp = Sheet(plies=cells(SANS))
    assert classify([a, cont])[1].role == "continuation"
    assert classify([a, opp])[1].role == "opponent"


def test_opponent_sheet_fixes_bad_cells():
    mine = cells(SANS)
    mine[4].text, mine[4].confidence = "??", 0.2         # unreadable d4
    mine[9].kind, mine[9].text = "illegible", ""          # 5... dxe5 unreadable
    mine[17].text = "b6"                                  # 9... b5 misread (b6 is legal too)
    opp = cells(SANS, "en")                               # the opponent writes in English
    opp[25].text = "Rxd6"                                 # opponent's own error elsewhere
    reading = GameReading(Header(), [Sheet(plies=mine, image=0), Sheet(plies=opp, role="opponent", image=1)])
    toks = build_tokens(reading, "de")
    r = decode(toks, "de")
    assert [p.san for p in r.plies] == SANS
    assert r.plies[17].san == "b5"


def test_two_photos_pipeline_reads_each_sheet():
    mine = GameReading(Header(white="Max"), [Sheet(plies=cells(SANS)[:30])])
    opp = GameReading(Header(event="Open"), [Sheet(plies=cells(SANS, "en"))])
    prov = FakeProvider(Settings(), reading=[mine, opp])
    s = Settings(); s.model_provider = "fake"
    out = process_game([Image(b"a"), Image(b"b")], prov, s)
    assert prov.reads == 2
    assert [p.san for p in out.result.plies] == SANS       # the rest comes from the opponent's sheet
    assert out.reading.header.white == "Max" and out.reading.header.event == "Open"


def _jpeg(w, h):
    from PIL import Image as P
    buf = io.BytesIO()
    P.new("RGB", (w, h), "white").save(buf, "JPEG")
    return buf.getvalue()


def test_prepare_and_crop():
    big = Image(_jpeg(3000, 4000))
    img = prepare(big)
    from PIL import Image as P
    assert max(P.open(io.BytesIO(img.data)).size) == 1600 and img.hires == big.data
    layout = [{"first_move": 1, "last_move": 30, "left": 100, "top": 300, "right": 500, "bottom": 900},
              {"first_move": 31, "last_move": 60, "left": 550, "top": 300, "right": 950, "bottom": 900}]
    box = cell_box(layout, 31, "b")
    assert box["x0"] == 750 and box["y0"] == 300
    c = crop_cell(img, layout, 12, "w")
    assert c is not None and max(P.open(io.BytesIO(c.data)).size) == 1200
    assert crop_cell(img, layout, 70, "w") is None and crop_cell(img, [], 1, "w") is None


def test_recheck_gets_crop():
    from chessreader.model.fake import demo_reading
    r = demo_reading()
    r.sheets[0].layout = [{"first_move": 1, "last_move": 30, "left": 100, "top": 300, "right": 500, "bottom": 900}]
    r.sheets[0].plies[2].confidence = 0.3
    r.sheets[0].plies[2].text = "Sc3"                      # legal but wrong reading of Sf3 -> doubtful
    prov = FakeProvider(Settings(), reading=r)
    s = Settings(); s.model_provider = "fake"
    img = prepare(Image(_jpeg(2400, 3200)))
    process_game([img], prov, s)
    assert prov.calls >= 2 and prov.last_crop is not None


def test_opponent_sheet_reduces_doubts():
    mine = cells(SANS)
    mine[4].text, mine[4].confidence = "??", 0.2
    mine[9].kind, mine[9].text = "illegible", ""
    alone = decode(build_tokens(GameReading(Header(), [Sheet(plies=[RawPly(**c.__dict__) for c in mine])]), "de"), "de")
    both = decode(build_tokens(GameReading(Header(), [Sheet(plies=mine), Sheet(plies=cells(SANS, "en"), role="opponent", image=1)]), "de"), "de")
    doubts = lambda r: sum(p.status != "ok" for p in r.plies)
    assert doubts(both) == 0 < doubts(alone)


def test_no_recheck_when_time_runs_short():
    import time
    from chessreader.model.fake import demo_reading
    r = demo_reading()
    r.sheets[0].plies[2].confidence = 0.3
    r.sheets[0].plies[2].text = "Sc3"
    prov = FakeProvider(Settings(), reading=r)
    s = Settings(); s.model_provider = "fake"
    out = process_game([Image(b"a")], prov, s, deadline=time.monotonic() + 10)   # less than the reserve
    assert prov.calls == 1 and out.stopped_because == "time"


def test_single_sheet_in_english():
    sheet = Sheet(plies=cells(SANS, "en"), language="de")   # the model may still say "de"
    r = decode(build_tokens(GameReading(Header(), [sheet]), "de"), "de")
    assert [p.san for p in r.plies] == SANS and all(p.status == "ok" for p in r.plies)
    assert r.plies[2].local == "Sf3"


def test_clear_opponent_move_wins_over_unsure_one():
    mine = cells(SANS)
    mine[5].text, mine[5].confidence = "Lf5", 0.3          # 3... Bg4 misread, legal, unsure
    both = decode(build_tokens(GameReading(Header(), [Sheet(plies=mine), Sheet(plies=cells(SANS, "en"), role="opponent", image=1)]), "de"), "de")
    assert both.plies[5].san == "Bg4"
