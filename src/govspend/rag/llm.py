"""Minimal provider layer: one function, three back ends.

Keys come from the environment: ANTHROPIC_API_KEY, OPENAI_API_KEY.
Ollama runs locally (`ollama serve`) and needs no key.
"""

from __future__ import annotations

import os

DEFAULT_MODELS = {
    "anthropic": os.environ.get("GOVSPEND_ANTHROPIC_MODEL", "claude-sonnet-5-5"),
    "openai": os.environ.get("GOVSPEND_OPENAI_MODEL"),
    "ollama": os.environ.get("GOVSPEND_OLLAMA_MODEL"),
}
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")


def generate(system: str, user: str, *, provider: str = "anthropic", model: str | None = None,
             max_tokens: int = 900, temperature: float = 0.0) -> str:
    model = model or DEFAULT_MODELS.get(provider)
    if not model:
        raise ValueError(f"No default model for {provider!r}; pass --model "
                         f"(or set GOVSPEND_{provider.upper()}_MODEL).")

    if provider == "anthropic":
        import anthropic

        resp = anthropic.Anthropic().messages.create(
            model=model, max_tokens=max_tokens, temperature=temperature, system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(block.text for block in resp.content if getattr(block, "type", "") == "text")

    if provider == "openai":
        from openai import OpenAI

        resp = OpenAI().chat.completions.create(
            model=model, max_tokens=max_tokens, temperature=temperature,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        return resp.choices[0].message.content or ""

    if provider == "ollama":
        import requests

        resp = requests.post(f"{OLLAMA_URL}/api/chat", timeout=300, json={
            "model": model, "stream": False, "options": {"temperature": temperature},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        })
        resp.raise_for_status()
        return resp.json()["message"]["content"]

    raise ValueError(f"Unknown provider {provider!r}; use anthropic, openai, or ollama.")
