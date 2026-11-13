from chessreader.config import Settings
from chessreader.model.fake import FakeProvider
from chessreader.pipeline import process_game
from chessreader.sheet import GameReading, Header, Sheet
from synth import GAMES, write_german


def test_recheck_resolves_doubt_and_respects_cap():
    truth = GAMES[0].split()[:11]
    sheet = write_german(truth)
    sheet[10].text = "Lc6"                      # ambiguous: Lc4 / La6 / Lh6
    reading = GameReading(header=Header(white="A", black="B"), sheets=[Sheet(plies=sheet)])
    prov = FakeProvider(Settings(), reading, recheck_answers={(6, "w"): ["Lc4"]})
    out = process_game([], prov, Settings(max_calls_per_game=10))
    assert [p.san for p in out.result.plies] == truth
    assert len(out.calls) == 2
    assert '[White "A"]' in out.pgn


def test_call_cap():
    truth = GAMES[0].split()[:11]
    sheet = write_german(truth)
    sheet[10].text = "Lc6"
    reading = GameReading(sheets=[Sheet(plies=sheet)])
    prov = FakeProvider(Settings(), reading)
    out = process_game([], prov, Settings(max_calls_per_game=1))
    assert len(out.calls) == 1 and out.stopped_because == "call_cap"


def test_same_answer_is_not_repeated():
    truth = GAMES[0].split()[:11]
    sheet = write_german(truth)
    sheet[10].text = "Lc6"
    reading = GameReading(sheets=[Sheet(plies=sheet)])
    prov = FakeProvider(Settings(), reading, recheck_answers={})   # model has nothing new
    out = process_game([], prov, Settings(max_calls_per_game=10))
    assert len(out.calls) == 2                                    # one re-ask, then stop


def _cascade(cheap_reading, strong_reading):
    from dataclasses import replace
    from chessreader.pipeline import process_cascade
    s = Settings(max_calls_per_game=10)
    s.cascade_models = ["cheap", "strong"]
    readings = {"cheap": cheap_reading, "strong": strong_reading}
    return process_cascade([], lambda m: FakeProvider(replace(s, model_name=m), readings[m]), s)


def test_cascade_keeps_clean_cheap_result():
    truth = GAMES[0].split()[:20]
    good = GameReading(sheets=[Sheet(plies=write_german(truth))])
    out = _cascade(good, good)
    assert not out.escalated and {c.model for c in out.calls} == {"cheap"}
    assert [p.san for p in out.result.plies] == truth


def test_cascade_escalates_unsure_cheap_result():
    truth = GAMES[0].split()[:20]
    bad = write_german(truth)
    for k in (4, 7, 10, 13):
        bad[k].text = "Xz9"                    # unreadable cells
    out = _cascade(GameReading(sheets=[Sheet(plies=bad)]),
                   GameReading(sheets=[Sheet(plies=write_german(truth))]))
    assert out.escalated and [c.model for c in out.calls][-1] == "strong"
    assert len(out.calls) <= 10
    assert [p.san for p in out.result.plies] == truth
