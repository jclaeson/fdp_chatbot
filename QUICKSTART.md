# FedEx API Chatbot - Quick Start

Get up and running in 10 minutes!

## Prerequisites

Install these first:

1. **Python 3.11+** - [Download](https://www.python.org/downloads/)
2. **Ollama** - [Install](https://ollama.com/download)
3. **Git** - [Download](https://git-scm.com/downloads)

## 1. Install Ollama Model (2 minutes)

```bash
# Pull the Mistral model (recommended)
ollama pull mistral

# Keep Ollama running
ollama serve
```

## 2. Clone and Setup (3 minutes)

```bash
# Clone repo
git clone <your-repo-url>
cd fedex-api-chatbot

# Create virtual environment
python -m venv venv

# Activate it
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r scraper/requirements.txt
pip install -r rag/requirements.txt
pip install -r server/requirements.txt
```

## 3. Configure (1 minute)

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your Claude API key (optional)
nano .env
```

**Note**: The app works without Claude API using only Ollama. Claude is only needed for complex queries.

## 4. Scrape & Index Data (5-15 minutes)

```bash
# Scrape FedEx documentation
cd scraper
python main.py --mode all --max-pages 50

# This creates: scraped_data/chunked_data.json
# Takes ~5-10 minutes
```

```bash
# Index the data
cd ../rag
python vectorstore.py ../scraper/scraped_data/chunked_data.json

# This creates: chroma_db/
# Takes ~3-5 minutes (downloads embedding model first time)
```

## 5. Start the Server (30 seconds)

```bash
# From project root
./run.sh
```

This starts:
- API server at http://localhost:8000
- Developer portal at http://localhost:8001

Or start manually:

```bash
cd server
uvicorn main:app --reload
```

## 6. Test It! (30 seconds)

### Web Interface
Open http://localhost:8001 and try asking:
- "How do I authenticate with the FedEx API?"
- "What is the tracking endpoint?"
- "Show me an example shipment request"

### API Test
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "How do I authenticate with the FedEx API?"}'
```

### Health Check
```bash
curl http://localhost:8000/health
```

## 7. Install Chrome Extension (Optional, 2 minutes)

1. Open Chrome: `chrome://extensions/`
2. Enable "Developer mode" (top right)
3. Click "Load unpacked"
4. Select `fedex-api-chatbot/extension/` folder
5. Click the extension icon to use it!

## Stop Services

```bash
./stop.sh
```

## Troubleshooting

### "Ollama not available"
```bash
# Start Ollama
ollama serve

# Check if running
curl http://localhost:11434/api/tags
```

### "No documents in vector store"
```bash
# Run the scraper and indexer (steps 4 above)
cd scraper && python main.py --mode all --max-pages 50
cd ../rag && python vectorstore.py ../scraper/scraped_data/chunked_data.json
```

### "Port 8000 already in use"
```bash
# Kill existing process
lsof -ti:8000 | xargs kill -9

# Or use different port
cd server && uvicorn main:app --port 8080
```

## What's Next?

### For Testing Locally
You're done! Start querying the chatbot through:
- Web interface at http://localhost:8001
- Chrome extension
- Direct API calls

### For Production Deployment
See `deploy/README.md` for Azure deployment instructions.

### Customize It
- **Prompts**: Edit `server/services/ollama_service.py` and `claude_service.py`
- **Routing**: Adjust complexity threshold in `server/services/router_service.py`
- **UI**: Modify `portal/` files
- **Models**: Try different Ollama models (llama3.1, codellama)

## Project Structure

```
fedex-api-chatbot/
├── scraper/          # Web scraper for FedEx docs
├── rag/              # Vector database & retrieval
├── server/           # FastAPI backend
├── portal/           # Developer portal website
├── extension/        # Chrome extension
├── deploy/           # Azure deployment configs
├── run.sh           # Start everything
├── stop.sh          # Stop everything
└── SETUP.md         # Detailed setup guide
```

## Common Commands

```bash
# Start all services
./run.sh

# Stop all services
./stop.sh

# Re-scrape data
cd scraper && python main.py --mode all --max-pages 50

# Re-index data
cd rag && python vectorstore.py ../scraper/scraped_data/chunked_data.json

# View API docs
open http://localhost:8000/docs

# View logs
tail -f logs/server.log

# Test different model
ollama pull llama3.1
# Edit .env: OLLAMA_MODEL=llama3.1
# Restart server
```

## Cost Optimization

### Free Tier (Local Only)
- Use Ollama exclusively (no Claude API key)
- 100% free
- Good for most queries
- Runs entirely on your machine

### Hybrid (Recommended)
- Ollama for simple queries (70% of traffic)
- Claude for complex queries (30% of traffic)
- ~$10-20/month Claude API costs
- Best quality/cost ratio

### Azure Deployment
- Container Apps: ~$30-50/month
- Storage: ~$5/month
- Claude API: ~$10-20/month
- **Total**: ~$45-75/month

## Need Help?

- 📖 Detailed guide: See `SETUP.md`
- 🚀 Deployment: See `deploy/README.md`
- 🐛 Issues: Check GitHub issues
- 📊 API Docs: http://localhost:8000/docs

## Quick Demo Queries

Try these to test different capabilities:

**Simple (uses Ollama)**:
- "What is the FedEx API?"
- "How do I get an API key?"
- "Show me the tracking endpoint"

**Medium (uses Ollama)**:
- "How do I authenticate with the tracking API?"
- "What are the rate limits?"
- "Give me an example POST request"

**Complex (uses Claude if configured)**:
- "Compare authentication methods across all FedEx APIs"
- "What's the best way to implement rate limiting in my app?"
- "Design a microservices architecture for FedEx integration"

---

**That's it! You're ready to go.** 🚀

For any issues, check `SETUP.md` for detailed troubleshooting.
