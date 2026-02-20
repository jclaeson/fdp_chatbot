FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies including Playwright dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    wget \
    gnupg \
    libnss3 \
    libnspr4 \
    libdbus-1-3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements-azure.txt /app/requirements-azure.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/requirements-azure.txt

# Install Playwright browsers
RUN playwright install chromium

# Copy application code
COPY server/ /app/server/
COPY rag/ /app/rag/
COPY scraper/ /app/scraper/
COPY extension/ /app/extension/

# Create directories
RUN mkdir -p /app/data/chroma_db /app/scraper/scraped_data /app/appdata

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
