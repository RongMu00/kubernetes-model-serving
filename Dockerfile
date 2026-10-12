FROM python:3.12-slim AS base

ARG TORCH_VERSION=2.7.0
ARG TARGETARCH

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app \
    HF_HOME=/models/cache

WORKDIR /app

COPY requirements.txt .
RUN if [ "${TARGETARCH}" = "amd64" ]; then \
      pip install --no-cache-dir \
        --index-url https://download.pytorch.org/whl/cpu \
        "torch==${TORCH_VERSION}"; \
    else \
      pip install --no-cache-dir "torch==${TORCH_VERSION}"; \
    fi \
 && pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000

FROM base AS test

COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY tests ./tests

CMD ["pytest", "-q"]

FROM base AS runtime

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
