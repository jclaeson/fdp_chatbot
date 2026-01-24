## Quick Start Guide

Complete setup instructions for running the FedEx API Chatbot locally.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Data Preparation](#data-preparation)
4. [Running Locally](#running-locally)
5. [Testing](#testing)
6. [Chrome Extension Setup](#chrome-extension-setup)
7. [Troubleshooting](#troubleshooting)

## Prerequisites

### Required

- **Python 3.11+**
- **Ollama** - For local LLM inference
- **Git**

### Optional

- **Docker & Docker Compose** - For containerized deployment
- **Claude API Key** - For enhanced responses (get from https://console.anthropic.com)

## Installation

### 1. Install Ollama

```bash
# macOS/Linux
curl -fsSL https://ollama.com/install.sh | sh

# Windows
# Download from https://ollama.com/download

# Pull the model (choose one)
ollama pull mistral        # Recommended - fast and accurate
# or
ollama pull llama3.1       # Larger, more capable
# or
ollama pull codellama      # Optimized for code/APIs
```

### 2. Clone the Repository

```bash
git clone <your-repo-url>
cd fedex-api-chatbot
```

### 3. Set Up Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Install dependencies for each component
pip install -r scraper/requirements.txt
pip install -r rag/requirements.txt
pip install -r server/requirements.txt
```

### 4. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and add your Claude API key (optional)
# nano .env or use your favorite editor
```

## Data Preparation

### Option 1: Quick Test (Skip Scraping)

For testing, you can use sample data or skip to running the server with an empty database.

### Option 2: Full Setup (Recommended)

#### Step 1: Scrape FedEx Documentation

```bash
cd scraper

# Basic scrape (50 pages, good for testing)
python main.py --mode all --max-pages 50

# Full scrape (more comprehensive)
python main.py --mode all --max-pages 200

# Output: scraped_data/chunked_data.json
```

This will:
1. Scrape developer.fedex.com
2. Extract API documentation
3. Chunk content for optimal retrieval
4. Save to `scraped_data/`

**Note**: Scraping may take 10-30 minutes depending on `max-pages`.

#### Step 2: Create Vector Database

```bash
cd ../rag

# Index the scraped content
python vectorstore.py ../scraper/scraped_data/chunked_data.json

# This creates chroma_db/ with embeddings
```

This will:
1. Load chunked documents
2. Generate embeddings using sentence-transformers
3. Index in Chroma vector database

**Note**: First run downloads ~400MB embedding model.

## Running Locally

### Option 1: Docker Compose (Easiest)

```bash
# From project root
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

Services will be available at:
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Portal: http://localhost:8001
- Ollama: http://localhost:11434

### Option 2: Manual (Better for Development)

#### Terminal 1: Start Ollama

```bash
# If not already running
ollama serve
```

#### Terminal 2: Start Backend Server

```bash
cd server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Server available at: http://localhost:8000

#### Terminal 3: Start Portal (Optional)

```bash
cd portal
python -m http.server 8001
```

Portal available at: http://localhost:8001

## Testing

### 1. Check Health

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "services": {
    "ollama": "available",
    "claude": "configured",
    "vector_store": "available"
  }
}
```

### 2. Test Chat API

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How do I authenticate with the FedEx API?"
  }'
```

### 3. Test Query Analysis

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Compare authentication methods across FedEx APIs"
  }'
```

### 4. View Statistics

```bash
curl http://localhost:8000/stats
```

### 5. Interactive API Docs

Open http://localhost:8000/docs in your browser for Swagger UI.

## Chrome Extension Setup

### 1. Prepare Extension

```bash
cd extension

# The extension is ready to use as-is
# No build step required
```

### 2. Load in Chrome

1. Open Chrome and go to `chrome://extensions/`
2. Enable "Developer mode" (toggle in top right)
3. Click "Load unpacked"
4. Select the `extension/` folder
5. Extension icon should appear in toolbar

### 3. Test Extension

1. Click the extension icon
2. You should see the chat interface
3. Try asking: "How do I authenticate with the FedEx API?"

### 4. Use on FedEx Developer Site

1. Visit https://developer.fedex.com
2. Notice the floating assistant button (bottom right)
3. Click it to open the extension

## Troubleshooting

### Ollama Issues

**Problem**: "Ollama not available"

**Solution**:
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not running:
ollama serve

# Check if model is pulled:
ollama list

# If model missing:
ollama pull mistral
```

### Vector Store Issues

**Problem**: "No documents in vector store"

**Solution**:
```bash
# Re-run indexing
cd rag
python vectorstore.py ../scraper/scraped_data/chunked_data.json
```

**Problem**: "Chroma database errors"

**Solution**:
```bash
# Reset database
cd rag
rm -rf chroma_db
python vectorstore.py ../scraper/scraped_data/chunked_data.json
```

### Server Won't Start

**Problem**: Port 8000 already in use

**Solution**:
```bash
# Find process using port 8000
lsof -ti:8000

# Kill it
kill -9 $(lsof -ti:8000)

# Or use different port
uvicorn main:app --port 8001
```

**Problem**: Import errors

**Solution**:
```bash
# Make sure you're in virtual environment
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Reinstall dependencies
pip install -r server/requirements.txt -r rag/requirements.txt
```

### Claude API Issues

**Problem**: "Claude API not configured"

**Solution**:
1. Get API key from https://console.anthropic.com
2. Add to `.env`: `CLAUDE_API_KEY=your_key_here`
3. Restart server

**Note**: Chatbot works without Claude using only Ollama, but complex queries will be limited.

### Extension Issues

**Problem**: Extension can't connect to server

**Solution**:
1. Verify server is running: `curl http://localhost:8000/health`
2. Check extension console for errors (right-click extension > Inspect)
3. Ensure CORS is enabled in server (it is by default)

**Problem**: Extension popup shows "Offline"

**Solution**:
1. Server must be running on localhost:8000
2. Check network tab in extension dev tools
3. Verify no firewall blocking localhost

### Performance Issues

**Problem**: Slow responses

**Solution**:
- Use smaller Ollama model (mistral vs llama3.1)
- Reduce `retrieval_top_k` in config
- Enable Claude for complex queries only
- Increase `complexity_threshold` to use Ollama more

**Problem**: High memory usage

**Solution**:
- Reduce Ollama context window
- Use smaller embedding model
- Limit number of indexed documents

## Development Tips

### Hot Reloading

Server automatically reloads on code changes with `--reload` flag.

### Debugging

Enable debug logging:
```python
# In server/main.py
logging.basicConfig(level=logging.DEBUG)
```

### Testing Different Models

```bash
# Pull alternative models
ollama pull codellama
ollama pull llama3.1

# Update .env
OLLAMA_MODEL=codellama

# Restart server
```

### Customizing Retrieval

Edit `rag/retriever.py`:
- `top_k`: Number of results (default 5)
- `similarity_threshold`: Minimum score (default 0.5)
- `strategy`: "semantic", "hybrid", "filtered"

## Next Steps

1. **Customize**: Modify prompts in `server/services/`
2. **Extend**: Add new API endpoints in `server/routers/`
3. **Deploy**: See `deploy/README.md` for Azure deployment
4. **Monitor**: Check `/stats` endpoint for usage metrics
5. **Optimize**: Tune routing in `server/services/router_service.py`

## Getting Help

- Check `/docs` endpoint for API documentation
- Review logs: `docker-compose logs -f` or server console
- Test individual components separately
- Use `/health` and `/stats` endpoints for diagnostics

## Quick Reference

```bash
# Start everything (Docker)
docker-compose up -d

# Start manually
ollama serve &
cd server && uvicorn main:app --reload &
cd portal && python -m http.server 8001 &

# Stop everything (Docker)
docker-compose down

# View logs
docker-compose logs -f api

# Rebuild after changes
docker-compose up --build

# Run scraper
cd scraper && python main.py --mode all --max-pages 50

# Reindex documents
cd rag && python vectorstore.py ../scraper/scraped_data/chunked_data.json

# Test API
curl http://localhost:8000/health
curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d '{"message":"test"}'
```

You're all set! 🚀
