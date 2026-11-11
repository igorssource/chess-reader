"""Offline stand-in for tests and local development (no API key, no cost)."""
from __future__ import annotations

from .base import ModelCall, ModelProvider, RecheckAnswer


class FakeProvider(ModelProvider):
    name = "fake"

    def __init__(self, settings, reading=None, recheck_answers=None):
        self.settings = settings
        self.reading = reading
        self.recheck_answers = recheck_answers or {}
        self.calls = 0

    def read_sheet(self, images):
        self.calls += 1
        return self.reading, ModelCall(model="fake", cost_eur=0.01, purpose="read")

    def recheck(self, images, move_number, color, written, fen, legal_moves, previous_moves):
        self.calls += 1
        cands = [c for c in self.recheck_answers.get((move_number, color), []) if c in legal_moves]
        return RecheckAnswer(candidates=cands), ModelCall(model="fake", cost_eur=0.01, purpose="recheck")
