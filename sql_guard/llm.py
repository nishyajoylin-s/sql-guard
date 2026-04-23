from __future__ import annotations

import json
import re


def call_llm(prompt: str, config) -> dict:
    """Call the configured LLM provider and return parsed JSON response."""
    provider = _resolve_provider(config)
    if provider == "openai":
        return _call_openai(prompt, config)
    return _call_ollama(prompt, config)


def _resolve_provider(config) -> str:
    if config.provider != "auto":
        return config.provider
    import os
    if os.environ.get("OPENAI_API_KEY") or config.api_key:
        return "openai"
    try:
        import httpx
        r = httpx.get(f"{config.host}/api/tags", timeout=2)
        if r.status_code == 200:
            return "ollama"
    except Exception:
        pass
    raise RuntimeError(
        "No LLM available. Set OPENAI_API_KEY or start Ollama (ollama serve)."
    )


def _call_openai(prompt: str, config) -> dict:
    import os
    from openai import OpenAI

    api_key = config.api_key or os.environ.get("OPENAI_API_KEY")
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=config.model if config.model != "llama3.2" else "gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        response_format={"type": "json_object"},
    )
    return _safe_parse(response.choices[0].message.content or "{}")


def _call_ollama(prompt: str, config) -> dict:
    import ollama

    response = ollama.chat(
        model=config.model,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0},
    )
    return _safe_parse(response["message"]["content"])


def _safe_parse(content: str) -> dict:
    content = re.sub(r"^```(?:json)?\s*", "", content.strip(), flags=re.IGNORECASE)
    content = re.sub(r"\s*```$", "", content.strip())
    return json.loads(content)
