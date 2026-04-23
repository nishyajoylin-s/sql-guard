from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    provider: str = "auto"              # openai | ollama | auto
    model: str = "gpt-4o-mini"
    api_key: str | None = None          # falls back to OPENAI_API_KEY env var
    host: str = "http://localhost:11434"  # ollama only
    timeout: int = 60


class ChecksConfig(BaseModel):
    schema_grounding: bool = True
    self_consistency: bool = True
    self_consistency_n: int = 3
    reverse_translation: bool = True
    weights: dict[str, float] = Field(
        default_factory=lambda: {
            "schema_grounding": 0.35,
            "self_consistency": 0.35,
            "reverse_translation": 0.30,
        }
    )


class BackendConfig(BaseModel):
    """A remotely-hosted text-to-SQL endpoint that sql-guard can proxy or accept pushes from."""
    name: str
    url: str                        # endpoint to forward proxy requests to
    method: str = "POST"
    auth_header: str | None = None  # e.g. "Bearer sk-abc123"
    # Field names used to extract data from request/response bodies
    question_field: str = "question"
    sql_field: str = "sql"
    result_field: str = "result"
    schema_map: dict[str, list[str]] | None = None


class Config(BaseModel):
    event_store: str = "duckdb:///sql_guard.db"
    server_port: int = 8080
    llm: LLMConfig = Field(default_factory=LLMConfig)
    checks: ChecksConfig = Field(default_factory=ChecksConfig)
    backends: list[BackendConfig] = Field(default_factory=list)

    # Keep old field name as alias so existing configs don't break
    @classmethod
    def model_validate(cls, obj, *args, **kwargs):
        if isinstance(obj, dict) and "ollama" in obj and "llm" not in obj:
            ollama = obj.pop("ollama")
            obj["llm"] = {"provider": "ollama", "model": ollama.get("model", "llama3.2"), "host": ollama.get("host", "http://localhost:11434")}
        return super().model_validate(obj, *args, **kwargs)


def _expand_env_vars(value: str) -> str:
    """Replace ${VAR_NAME} with the value of os.environ['VAR_NAME']."""
    return re.sub(
        r"\$\{([^}]+)\}",
        lambda m: os.environ.get(m.group(1), m.group(0)),
        value,
    )


def _expand_dict(data: Any) -> Any:
    if isinstance(data, str):
        return _expand_env_vars(data)
    if isinstance(data, dict):
        return {k: _expand_dict(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_expand_dict(v) for v in data]
    return data


def load_config(path: Path | None = None) -> Config:
    search_paths = [path] if path else [
        Path.cwd() / ".sql-guard.yml",
        Path.cwd() / "sql_guard.yml",
    ]
    for p in search_paths:
        if p and p.exists():
            with open(p) as f:
                data = yaml.safe_load(f) or {}
            data = _expand_dict(data)
            return Config.model_validate(data)
    return Config()


def save_config(config: Config, path: Path | None = None) -> None:
    target = path or Path.cwd() / ".sql-guard.yml"
    with open(target, "w") as f:
        yaml.dump(config.model_dump(exclude_none=True), f, default_flow_style=False)
