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
