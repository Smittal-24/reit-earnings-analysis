"""LLM client abstraction. The engine depends on this narrow interface,
not the Anthropic SDK directly, so unit tests can substitute a fake client
and never make a real API call."""

from __future__ import annotations

from typing import Protocol


class LLMClient(Protocol):
    def generate_json(self, system_prompt: str, user_prompt: str) -> str:
        """Return a raw JSON string produced by the model."""
        ...


class ClaudeClient:
    """Real implementation backed by the Anthropic API."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-5"):
        import anthropic
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def generate_json(self, system_prompt: str, user_prompt: str) -> str:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return response.content[0].text