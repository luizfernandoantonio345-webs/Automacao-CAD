# ====================================================================
# Dockerfile - Fase 1: Docker + Celery
# Builds imagem completa: Python 3.10 + workers Celery + healthchecks
# Compatible Windows/Linux/Mac (multi-platform)
# ====================================================================

FROM python:3.10-slim

LABEL maintainer="CAD Automation Team"
LABEL description="Celery Workers para Automação CAD com AI"

# ✓ Variáveis ambiente
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

# ✓ Instalar dependências de sistema (slim image)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# ✓ Workdir
WORKDIR /app

# ✓ Copiar requirements
COPY requirements-celery.txt .
COPY requirements.txt .

# ✓ Instalar Python packages
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements-celery.txt

# ✓ Copiar código
COPY . .

# ✓ Health check (Celery worker alive)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "from celery_app import app; app.control.inspect().active() or exit(1)" || exit 1

# ✓ Comando padrão: worker Celery
CMD ["celery", "-A", "celery_app", "worker", \
    "--loglevel=info", \
    "--concurrency=4", \
    "--prefetch-multiplier=4", \
    "--max-tasks-per-child=100"]
