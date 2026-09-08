# Copyright (C) 2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

# SAD MCP service image. The mcp-service-sdk is baked in at build time so a fresh
# machine never does a slow per-start install. The SDK is installed from a
# shallow clone WITHOUT recursive submodules (the parent repo's submodules are
# irrelevant to this stdlib-only library and are what made `pip install` slow).
FROM python:3.12-slim

ARG SDK_REPO=https://github.com/sachinkaushik/edge-ai-libraries.git
ARG SDK_REF=mcp

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

RUN git clone --depth 1 --branch "$SDK_REF" "$SDK_REPO" /tmp/eal \
    && pip install --no-cache-dir "/tmp/eal/libraries/mcp-service-sdk[mcp]" \
    && rm -rf /tmp/eal

# Install the SAD MCP service itself; deps are already satisfied above.
COPY pyproject.toml ./
COPY src ./src
COPY scripts ./scripts
RUN pip install --no-cache-dir --no-deps .

ENV MCP_TRANSPORT=streamable-http \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=9000 \
    STORE_ID=store_001 \
    SAD_LOG_PATH=/data/sad_log.sqlite \
    SEED_DEMO=true \
    PYTHONUNBUFFERED=1

RUN mkdir -p /data
VOLUME ["/data"]
EXPOSE 9000

# Seed demo data (idempotent) when SEED_DEMO=true, then run the MCP server.
CMD ["sh", "-c", "if [ \"$SEED_DEMO\" = \"true\" ]; then python /app/scripts/seed_demo.py || true; fi; exec sad-mcp"]
