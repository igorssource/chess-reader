"""Everything that talks to a multimodal model lives here.

The rest of the code only uses `get_provider(settings)` and the ModelProvider
interface, so another provider (or several, for voting) can be added later
without touching the chess logic or the server.
"""
from .base import ModelCall, ModelProvider, RecheckAnswer  # noqa: F401


def get_provider(settings):
    if settings.model_provider == "anthropic":
        from .anthropic_provider import AnthropicProvider
        return AnthropicProvider(settings)
    if settings.model_provider == "fake":
        from .fake import FakeProvider
        return FakeProvider(settings)
    raise ValueError(f"Unknown model provider: {settings.model_provider}")
