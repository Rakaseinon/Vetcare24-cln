# ---- base: dependencias de runtime
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- test: runtime + herramientas de prueba (docker compose run tests)
FROM base AS test
COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY . .
CMD ["pytest", "--cov=src", "--cov-report=term-missing", "--cov-fail-under=80"]

# ---- app: imagen final, usuario sin privilegios
FROM base AS app
COPY src ./src
COPY data ./data
RUN useradd --create-home appuser && chown -R appuser /app
USER appuser
ENV PORT=8000
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request,os;urllib.request.urlopen(f'http://localhost:{os.environ.get(\"PORT\",\"8000\")}/health')"
CMD ["sh", "-c", "uvicorn src.api.main:create_app --factory --host 0.0.0.0 --port ${PORT}"]
