from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class OllamaConfig(BaseModel):
    model: str = "llama3.2"
    host: str = "http://localhost:11434"
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
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    checks: ChecksConfig = Field(default_factory=ChecksConfig)
    backends: list[BackendConfig] = Field(default_factory=list)


def load_config(path: Path | None = None) -> Config:
    search_paths = [path] if path else [
        Path.cwd() / ".sql-guard.yml",
        Path.cwd() / "sql_guard.yml",
    ]
    for p in search_paths:
        if p and p.exists():
            with open(p) as f:
                data = yaml.safe_load(f) or {}
            return Config.model_validate(data)
    return Config()


def save_config(config: Config, path: Path | None = None) -> None:
    target = path or Path.cwd() / ".sql-guard.yml"
    with open(target, "w") as f:
        yaml.dump(config.model_dump(exclude_none=True), f, default_flow_style=False)
