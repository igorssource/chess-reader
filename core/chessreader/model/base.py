from __future__ import annotations

from dataclasses import dataclass, field

from ..sheet import GameReading


@dataclass
class Image:
    data: bytes                        # what the model gets for reading the whole sheet
    media_type: str = "image/jpeg"
    hires: bytes | None = None         # the uploaded photo in full size (for zoomed crops)


@dataclass
class ModelCall:
    """Bookkeeping for one request to the model (for limits and the log)."""
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_eur: float = 0.0
    purpose: str = "read"          # read | recheck
    request_id: str | None = None


@dataclass
class RecheckAnswer:
    candidates: list[str] = field(default_factory=list)   # most likely first
    note: str = ""


class ModelProvider:
    name = "base"

    def read_sheet(self, images: list[Image]) -> tuple[GameReading, ModelCall]:
        raise NotImplementedError

    def recheck(self, images: list[Image], move_number: int, color: str, written: str,
                fen: str, legal_moves: list[str], previous_moves: str,
                crop: Image | None = None) -> tuple[RecheckAnswer, ModelCall]:
        raise NotImplementedError
