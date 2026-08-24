"""Entrypoint: `python -m sad_mcp` or the `sad-mcp` console script.

stdio transport locally; streamable-http (host/port from env) in deployment.
"""

from __future__ import annotations

from config import get_settings
from tools import svc


def main() -> None:
    s = get_settings()
    if s.transport == "stdio":
        svc.run()
    else:
        svc.run(transport=s.transport, host=s.host, port=s.port)


if __name__ == "__main__":
    main()
