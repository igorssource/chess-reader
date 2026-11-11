"""Synthetic benchmark: write known games in German, add writer/OCR errors, measure recovery.

Usage: python eval/synthetic_benchmark.py [trials]
"""
import random
import sys
import time
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "core"), str(ROOT / "tests")]

from chessreader.decoder import decode            # noqa: E402
from chessreader.similarity import CONFUSABLE      # noqa: E402
from synth import GAMES, random_game, renumber, write_german  # noqa: E402


def corrupt(sheet, rnd):
    errors = []
    for _ in range(rnd.randint(1, 3)):
        k = rnd.randrange(len(sheet))
        t = sheet[k].text
        pos = [i for i, c in enumerate(t) if any(a == c for a, _ in CONFUSABLE)]
        if pos:
            i = rnd.choice(pos)
            repl = rnd.choice([b for a, b in CONFUSABLE if a == t[i]])
            sheet[k].text = t[:i] + repl + t[i + 1:]
            errors.append(f"confuse@{k}")
    if rnd.random() < 0.4:
        k = rnd.randrange(5, len(sheet) - 5)
        del sheet[k]
        renumber(sheet)
        errors.append(f"hidden-skip@{k}")
    return errors


def main(trials=20):
    rnd = random.Random(1)
    total = right = full = silent = 0
    times = []
    for t in range(trials):
        truth = GAMES[t % len(GAMES)].split() if t % 2 == 0 else random_game(100 + t, 60)
        sheet = write_german(truth, long=rnd.random() < 0.3)
        errs = corrupt(sheet, rnd)
        t0 = time.time()
        r = decode(sheet)
        times.append(time.time() - t0)
        got = [p.san for p in r.plies]
        ok = sum(a == b for a, b in zip(truth, got))
        total += len(truth); right += ok; full += got == truth
        # wrong move shown as "ok" (green) = the worst case: a person would not look at it
        first_bad = next((k for k, (a, b) in enumerate(zip(truth, got)) if a != b), None)
        if first_bad is not None and r.plies[first_bad].status == "ok":
            silent += 1
        flag = "" if got == truth else "  <-- differs"
        print(f"{t:2d} {len(truth):3d} plies  {ok:3d} right  {times[-1]:5.1f}s  {errs}{flag}")
    print(f"\nplies right: {right}/{total} = {right/total:.1%}; games fully right: {full}/{trials}; "
          f"first wrong move shown as ok: {silent}; avg time {sum(times)/len(times):.1f}s, max {max(times):.1f}s")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 20)
