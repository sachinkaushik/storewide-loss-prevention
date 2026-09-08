"""Env-driven settings for the SAD MCP service."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# Persistent by default so a separate seed/pipeline process and the running MCP
# server share the same durable log (an in-memory log would isolate them).
_DEFAULT_LOG_PATH = str(Path(__file__).resolve().parents[1] / "data" / "sad_log.sqlite")


@dataclass(frozen=True)
class Settings:
    store_id: str
    transport: str  # stdio | sse | streamable-http
    host: str
    port: int
    log_backend: str  # sqlite | jsonl | memory
    log_path: str


def get_settings() -> Settings:
    log_backend = os.getenv("SAD_LOG_BACKEND", "sqlite")
    log_path = os.getenv("SAD_LOG_PATH", _DEFAULT_LOG_PATH)
    if log_backend != "memory":
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
    return Settings(
        store_id=os.getenv("STORE_ID", "store_001"),
        transport=os.getenv("MCP_TRANSPORT", "stdio"),
        host=os.getenv("MCP_HOST", "0.0.0.0"),
        port=int(os.getenv("MCP_PORT", "9000")),
        log_backend=log_backend,
        log_path=log_path,
    )
