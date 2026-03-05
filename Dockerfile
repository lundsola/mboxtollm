FROM python:3.11-slim

WORKDIR /app

# Install system deps for sentence-transformers / torch
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Pre-download the embedding model at build time so startup is fast
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

EXPOSE 8000

# Persistent volumes for data and chroma
VOLUME ["/app/data", "/app/chroma_store"]

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
