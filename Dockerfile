# ==========================================
# Stage 1: Build React Frontend
# ==========================================
FROM node:20-slim AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm install

COPY frontend/ ./
RUN npm run build

# ==========================================
# Stage 2: Python Backend Runtime
# ==========================================
FROM python:3.11-slim

# Install system dependencies (Git is required by GitPython)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Hugging Face Spaces runs as user with UID 1000
RUN useradd -m -u 1000 user

ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PORT=7860 \
    HOST=0.0.0.0 \
    HF_HOME=/home/user/.cache/huggingface

WORKDIR /app

# Pre-install CPU-only PyTorch for fast builds and low image size
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Install Python backend requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download SentenceTransformer model weights so first request is instant
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Copy application source code
COPY backend/ ./backend/
COPY tests/ ./tests/
COPY pytest.ini .

# Copy pre-built frontend distribution
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Ensure storage directories exist and have proper permissions for user 1000
RUN mkdir -p /app/backend/cloned_repos /app/backend/sample_repos /home/user/.cache && \
    chown -R 1000:1000 /app /home/user

USER user

EXPOSE 7860

CMD ["python", "backend/run.py"]
