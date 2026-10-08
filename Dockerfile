# 1. Use the official lightweight Python base image
FROM python:3.11-slim-bookworm

# 2. Install uv cleanly
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/.

# 3. Set environment variables to optimize Python & uv behavior
ENV WORKDIR=/app \
    PATH="/app/.venv/bin:$PATH" \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# 4. Copy package tracking files to leverage Docker layer caching
COPY pyproject.toml uv.lock ./

# 5. Fast locked install using uv sync (Cached & Isolated)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev --no-build-isolation

# 6. Copy the rest of your application code
COPY . .

# 7. Final minimal sync step to incorporate your local project code
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-build-isolation

# 8. Expose your FastAPI port
EXPOSE 8000

# 9. Run the application
#CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# 9. Copy and give execute permissions to your startup script
RUN chmod +x start.sh

# 10. Execute the startup script layout
CMD ["./start.sh"]
