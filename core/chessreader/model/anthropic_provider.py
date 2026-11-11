"""Anthropic (Claude) implementation of ModelProvider.

The API key is read from the ANTHROPIC_API_KEY environment variable on the
server only; it never reaches the web page.
"""
from __future__ import annotations

import base64
import json

import anthropic

from .base import Image, ModelCall, ModelProvider, RecheckAnswer
from .prompt import read_instructions, recheck_instructions
from .schema import RecheckOut, SheetOut, to_reading


class ModelError(Exception):
    """The model could not deliver a usable answer (refusal, truncation, API error)."""


def _schema(model_cls) -> dict:
    schema = model_cls.model_json_schema()

    def strip(node):
        if isinstance(node, dict):
            node.pop("title", None)
            for v in node.values():
                strip(v)
        elif isinstance(node, list):
            for v in node:
                strip(v)
    strip(schema)
    return schema


def _image_blocks(images: list[Image]) -> list[dict]:
    return [{
        "type": "image",
        "source": {"type": "base64", "media_type": img.media_type,
                   "data": base64.standard_b64encode(img.data).decode("ascii")},
    } for img in images]


class AnthropicProvider(ModelProvider):
    name = "anthropic"

    def __init__(self, settings, client: anthropic.Anthropic | None = None):
        self.settings = settings
        self.client = client or anthropic.Anthropic(timeout=120.0, max_retries=2)

    def _call(self, system: str, content: list[dict], schema: dict, purpose: str, max_tokens: int):
        s = self.settings
        try:
            response = self.client.beta.messages.create(
                model=s.model_name,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": content}],
                output_config={"effort": s.model_effort,
                               "format": {"type": "json_schema", "schema": schema}},
                # if the model declines, the API retries on a suitable fallback model
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
        except anthropic.AuthenticationError as e:
            raise ModelError("model API key is missing or invalid") from e
        except anthropic.RateLimitError as e:
            raise ModelError("model is busy (rate limit), try again in a minute") from e
        except anthropic.APIStatusError as e:
            raise ModelError(f"model API error {e.status_code}") from e
        except anthropic.APIConnectionError as e:
            raise ModelError("cannot reach the model API") from e

        usage = response.usage
        call = ModelCall(
            model=response.model, purpose=purpose,
            input_tokens=(usage.input_tokens or 0) + (getattr(usage, "cache_read_input_tokens", 0) or 0)
            + (getattr(usage, "cache_creation_input_tokens", 0) or 0),
            output_tokens=usage.output_tokens or 0,
            request_id=getattr(response, "_request_id", None),
        )
        call.cost_eur = s.price_eur(call.input_tokens, call.output_tokens, response.model)
        if response.stop_reason == "refusal":
            raise ModelError("the model declined to read this image")
        if response.stop_reason == "max_tokens":
            raise ModelError("the answer was cut off (sheet too long?)")
        text = "".join(b.text for b in response.content if b.type == "text")
        try:
            return json.loads(text), call
        except json.JSONDecodeError as e:
            raise ModelError("the model returned malformed data") from e

    def read_sheet(self, images):
        lang = self.settings.notation_language
        content = _image_blocks(images) + [{"type": "text", "text": "Transcribe this scoresheet."}]
        data, call = self._call(read_instructions(lang), content, _schema(SheetOut), "read", 16000)
        return to_reading(SheetOut.model_validate(data)), call

    def recheck(self, images, move_number, color, written, fen, legal_moves, previous_moves):
        lang = self.settings.notation_language
        side = "White" if color == "w" else "Black"
        text = (f"Cell: move {move_number}, {side} column.\n"
                f"Read before as: \"{written}\" - this is not a legal move here.\n"
                f"Moves so far: {previous_moves or '(none)'}\n"
                f"Position (FEN): {fen}\n"
                f"Legal moves: {', '.join(legal_moves)}")
        content = _image_blocks(images) + [{"type": "text", "text": text}]
        data, call = self._call(recheck_instructions(lang), content, _schema(RecheckOut), "recheck", 4000)
        out = RecheckOut.model_validate(data)
        return RecheckAnswer(candidates=[c for c in out.candidates if c in legal_moves][:3],
                             note=out.note), call
