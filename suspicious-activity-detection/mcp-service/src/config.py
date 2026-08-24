"""Env-driven settings for the SAD MCP service."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    store_id: str
    transport: str  # stdio | sse | streamable-http
    host: str
    port: int


def get_settings() -> Settings:
    return Settings(
        store_id=os.getenv("STORE_ID", "store_001"),
        transport=os.getenv("MCP_TRANSPORT", "stdio"),
        host=os.getenv("MCP_HOST", "0.0.0.0"),
        port=int(os.getenv("MCP_PORT", "9000")),
    )
