"""How similar two handwritten move strings are.

A weighted edit distance: swapping characters that look alike in handwriting
(b/6, e/c, 1/l, S/5 ...) costs less than an arbitrary change.
"""
from __future__ import annotations

from functools import lru_cache

# Pairs of characters that are easy to confuse in handwriting / OCR.
CONFUSABLE_PAIRS = [
    "b6", "bh", "bl", "ec", "ea", "ce", "l1", "17", "71", "g9", "gq", "ad", "ao", "a0",
    "S5", "Ss", "T7", "Tf", "L1", "Ll", "Lc", "D0", "Do", "Dd", "K4", "Kk",
    "56", "38", "35", "49", "4h", "0o", "0O", "Oo", "hk", "hn", "ft", "fl", "dc",
    "2z", "2Z", "1i", "x+", "-x", "uv",
]
CONFUSABLE = set()
for a, b in CONFUSABLE_PAIRS:
    CONFUSABLE.add((a, b))
    CONFUSABLE.add((b, a))

SUB_SIMILAR = 0.4
SUB_OTHER = 1.0
INDEL = 1.0
INDEL_CHEAP = 0.3       # missing/extra 'x', '-', '+', '#' marks: people often omit them
CHEAP_CHARS = set("x-+#")
TRANSPOSE = 0.6


def _sub(a: str, b: str) -> float:
    if a == b:
        return 0.0
    if (a, b) in CONFUSABLE:
        return SUB_SIMILAR
    return SUB_OTHER


def _indel(c: str) -> float:
    return INDEL_CHEAP if c in CHEAP_CHARS else INDEL


@lru_cache(maxsize=200_000)
def distance(s: str, t: str) -> float:
    n, m = len(s), len(t)
    d = [[0.0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        d[i][0] = d[i - 1][0] + _indel(s[i - 1])
    for j in range(1, m + 1):
        d[0][j] = d[0][j - 1] + _indel(t[j - 1])
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            best = min(
                d[i - 1][j] + _indel(s[i - 1]),
                d[i][j - 1] + _indel(t[j - 1]),
                d[i - 1][j - 1] + _sub(s[i - 1], t[j - 1]),
            )
            if i > 1 and j > 1 and s[i - 1] == t[j - 2] and s[i - 2] == t[j - 1]:
                best = min(best, d[i - 2][j - 2] + TRANSPOSE)
            d[i][j] = best
    return d[n][m]
