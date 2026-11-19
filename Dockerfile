FROM python:3.13.11-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DERAG_MODEL_DIR=/app/models/embedding \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    HF_HUB_DISABLE_IMPLICIT_TOKEN=1 \
    HF_HUB_DISABLE_TELEMETRY=1

WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl libgomp1 \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN python -m pip install --no-cache-dir --no-deps torch==2.15.0+cpu --index-url https://download.pytorch.org/whl/cpu \
    && python -m pip install --no-cache-dir -r requirements.txt \
    && python -m pip check \
    && python -c "import torch; assert torch.version.cuda is None"
COPY requirements-linux.txt .
RUN python -m pip install --no-cache-dir -r requirements-linux.txt && python -m pip check
COPY app ./app
COPY config ./config
COPY scripts ./scripts
COPY .env.example ./.env.example
COPY data ./data
COPY 项目设计.md ./项目设计.md
RUN mkdir -p /app/data/sqlite /app/data/chroma /app/data/chunks \
    /app/data/indexes /app/data/runs /app/models/embedding

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3).close()"]
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM runtime AS test
COPY requirements-*.txt ./
RUN python -m pip install --no-cache-dir -r requirements-dev.txt && python -m pip check
COPY tests ./tests
COPY docs ./docs
COPY Dockerfile .dockerignore README.md 开发文档.md B开发文档.md B测试.md ./
HEALTHCHECK NONE
CMD ["python", "-m", "pytest", "-p", "no:cacheprovider", "tests", "--basetemp=/tmp/derag-tests", "-q"]

# The default image contains production dependencies only.
FROM runtime AS final
