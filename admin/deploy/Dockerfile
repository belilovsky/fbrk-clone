FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/fbrk-admin

COPY requirements.txt ./
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt

COPY app ./app
COPY deploy ./deploy
COPY scripts ./scripts
COPY static ./static
COPY templates ./templates
COPY enrich.py ingest_fbrk.py import_from_datajs.py ./

RUN chown -R www-data:www-data /opt/fbrk-admin

USER www-data:www-data
EXPOSE 8787

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8787/admin/healthz', timeout=4).read()"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8787", "--workers", "2", "--proxy-headers"]
