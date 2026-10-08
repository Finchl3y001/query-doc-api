# 1. Use the official lightweight Python base image
FROM python:3.11-slim-bookworm

# 2. Install libmagic system dependencies (Takes ~3 seconds)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# 3. Install uv cleanly
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/.

# 4. Set environment variables to optimize Python & uv behavior
ENV WORKDIR=/app \
    PATH="/app/.venv/bin:$PATH" \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# 5. Copy package tracking files to leverage Docker layer caching
COPY pyproject.toml uv.lock ./

# 6. Fast, compatible dependency installation (Cached & Isolated)
# Changing --non-package to --no-install-project to fix exit code: 2
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# 7. Copy the rest of your application code
COPY . .

# 8. Expose your FastAPI port
EXPOSE 8000

# 9. Give execute permissions to your startup script
RUN chmod +x start.sh

# 10. Execute the startup script layout
CMD ["./start.sh"]
