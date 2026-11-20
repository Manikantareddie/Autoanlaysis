# Multi-stage / optimized production Dockerfile for InsightPilot AI Backend on Render
FROM python:3.11-slim-bookworm

# Prevent Python from writing .pyc files, enable unbuffered logs, and constrain thread memory on Render
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend \
    PORT=8000 \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    VECLIB_MAXIMUM_THREADS=1 \
    NUMEXPR_NUM_THREADS=1 \
    TOKENIZERS_PARALLELISM=false

# Install minimal OS dependencies required by DuckDB, FAISS, and PyTorch OpenMP (libgomp1)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Step 1: Install lightweight CPU-only PyTorch first to stay well within Render memory limits
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Step 2: Install remaining application and RAG dependencies
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Step 3: Copy backend application code and scaffold storage directory
COPY backend /app/backend
RUN mkdir -p /app/storage/datasets /storage/datasets

# Render exposes service on dynamic $PORT
EXPOSE 8000

# Container liveness health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Start Uvicorn bound to 0.0.0.0 and dynamic $PORT with single worker for low-memory environments
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --app-dir /app/backend --workers 1 --timeout-keep-alive 30"]
