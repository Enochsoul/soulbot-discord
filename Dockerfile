FROM ghcr.io/astral-sh/uv:python3.13-trixie-slim

RUN apt update && apt upgrade -y

RUN apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN groupadd --system --gid 999 nonroot \
    && useradd --system --gid 999 --uid 999 --create-home nonroot

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1

ENV UV_LINK_MODE=copy

ENV UV_NO_DEV=1

ENV UV_TOOL_BIN_DIR=/usr/local/bin

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project


COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

ENV PATH="/app/.venv/bin:$PATH"

ENTRYPOINT []

ARG SOURCE_CONFIG_FILE=soulbot.conf
COPY soulbot/$SOURCE_CONFIG_FILE soulbot/soulbot.conf

WORKDIR /app/soulbot
RUN chown -R nonroot:nonroot .

USER nonroot

CMD ["uv", "run", "soulbot.py"]
