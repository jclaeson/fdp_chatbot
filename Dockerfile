FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY server/requirements.txt /app/server/requirements.txt
COPY rag/requirements.txt /app/rag/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/server/requirements.txt
RUN pip install --no-cache-dir -r /app/rag/requirements.txt

# Copy application code
COPY server/ /app/server/
COPY rag/ /app/rag/

# Create directory for Chroma DB
RUN mkdir -p /app/data/chroma_db

# Expose port
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV CHROMA_PERSIST_DIR=/app/data/chroma_db

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]
