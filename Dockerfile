# ══════════════════════════════
# SVIES Python Backend
# ══════════════════════════════
FROM python:3.11-slim

WORKDIR /app

# System deps for OpenCV + Tesseract + tini (proper signal handling)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 tesseract-ocr tini && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# tini as PID 1 ensures SIGTERM is forwarded properly to python
ENTRYPOINT ["tini", "--"]
CMD ["python", "-m", "api.server"]
