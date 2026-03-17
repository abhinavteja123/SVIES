# ══════════════════════════════
# SVIES Python Backend
# ══════════════════════════════
FROM python:3.11-slim AS backend

WORKDIR /app

# System deps for OpenCV + Tesseract
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx libglib2.0-0 tesseract-ocr && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Init DB
RUN python data/violations/init_db.py

EXPOSE 8000

CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000"]
