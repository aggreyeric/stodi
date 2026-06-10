# Stodi API — Cloud Run container.
# Build context is the stodi/ directory; the app imports itself as the
# `stodi` package, so the code is copied to /app/stodi and PYTHONPATH=/app.
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt /app/stodi/requirements.txt
RUN pip install --no-cache-dir -r /app/stodi/requirements.txt

COPY . /app/stodi

ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1

# Cloud Run injects $PORT.
CMD exec uvicorn stodi.core.api:app --host 0.0.0.0 --port ${PORT:-8080}
