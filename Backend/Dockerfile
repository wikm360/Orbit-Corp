FROM python:3.12.12-slim-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/tmp

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# tiktoken downloads its BPE file on first use; with a read-only rootfs (tmpfs /tmp) that would happen on every
# container start (and needs outbound internet). Bake it into the image instead.
ENV TIKTOKEN_CACHE_DIR=/opt/tiktoken
RUN mkdir -p /opt/tiktoken && python -c "import tiktoken; tiktoken.get_encoding('cl100k_base')" \
    && chmod -R a+rX /opt/tiktoken

# Non-root runtime user (uid 10001). The upload dir is created and owned here so a fresh
# named volume mounted at /app/data/uploads inherits the right ownership.
RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app \
    && mkdir -p /app/data/uploads \
    && chown -R app:app /app/data

COPY --chown=app:app . .

USER 10001:10001

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
