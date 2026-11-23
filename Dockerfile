FROM ghcr.io/astral-sh/uv:0.13.4-python3.14-trixie-slim AS build-base
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1 \
    UV_PYTHON_DOWNLOADS=0
WORKDIR /app
COPY . .

FROM build-base AS server-build
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-editable --package server

FROM build-base AS device-build
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-editable --package device

FROM python:3.14-slim-trixie AS runtime-base
ENV PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"
RUN useradd --system --create-home app \
    && mkdir /state \
    && chown app:app /state
USER app
WORKDIR /state
STOPSIGNAL SIGINT

FROM runtime-base AS server
COPY --from=server-build /app/.venv /app/.venv
EXPOSE 8043
CMD ["server"]

FROM runtime-base AS device
COPY --from=device-build /app/.venv /app/.venv
CMD ["device"]
