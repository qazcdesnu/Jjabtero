# 배포용 이미지. docs/design/Deployment.md 5절 참조.

FROM node:24-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never
# 의존성 층을 코드보다 먼저 만들어, 코드만 바뀐 배포에서는 의존성을 다시 받지 않는다.
COPY pyproject.toml uv.lock .python-version README.md ./
RUN uv sync --locked --no-dev --no-install-project
COPY src ./src
COPY alembic.ini ./
RUN uv sync --locked --no-dev
COPY --from=frontend /app/frontend/dist ./frontend/dist
ENV PATH="/app/.venv/bin:$PATH"
CMD ["sh", "-c", "exec jjabtero --host 0.0.0.0 --port ${PORT:-10000}"]
