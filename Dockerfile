FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STOCKFISH_FILE=/usr/games/stockfish

RUN apt-get update \
    && apt-get install -y --no-install-recommends stockfish libglib2.0-0 libgl1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements-backend.txt .
RUN pip install --no-cache-dir -r requirements-backend.txt

COPY core.py .
COPY chess_model_best.pth .
COPY pieces ./pieces
COPY web ./web

EXPOSE 8000

CMD ["sh", "-c", "uvicorn web.server:app --host 0.0.0.0 --port ${PORT:-8000}"]
