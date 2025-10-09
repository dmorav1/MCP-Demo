FROM python:3.11-slim AS base

ARG SLIM_EMBEDDINGS=1
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UVICORN_WORKERS=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc g++ curl libpq-dev \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./requirements.txt

# Optionally slim down heavy ML deps (torch / transformers / scipy / scikit-learn / sentence-transformers) and replace with fastembed
RUN if [ "$SLIM_EMBEDDINGS" = "1" ]; then \
      grep -v -E '^(torch==|scikit-learn==|scipy==|transformers==|sentence-transformers==)' requirements.txt > requirements.slim && \
      # Drop incompatible pillow pin (fastembed requires pillow <11) if present
      sed -i '/^pillow==11\./d' requirements.slim || true && \
      echo 'pillow<11.0.0,>=10.3.0' >> requirements.slim && \
      echo 'fastembed==0.3.3' >> requirements.slim && \
      mv requirements.slim requirements.txt ; \
    fi

RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

COPY app ./app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
