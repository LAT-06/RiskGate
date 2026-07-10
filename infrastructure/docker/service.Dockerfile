FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ARG SERVICE
ENV SERVICE=${SERVICE} \
    UV_COMPILE_BYTECODE=1

WORKDIR /app
COPY . .
RUN uv sync --package "${SERVICE}"

EXPOSE 8000
CMD ["sh", "-c", "uv run --package \"$SERVICE\" uvicorn \"$(echo \"$SERVICE\" | tr - _).main:app\" --host 0.0.0.0 --port 8000"]
