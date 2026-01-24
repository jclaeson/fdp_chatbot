# FedEx API Chatbot - Developer Assistant

A RAG-powered chatbot that helps developers quickly find answers about FedEx APIs using intelligent routing between local Ollama models and Claude API.

## Architecture

```
┌─────────────────┐
│ Chrome Extension│
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────┐
│      FastAPI Backend Server          │
│  ┌───────────────────────────────┐  │
│  │   Intelligent Query Router     │  │
│  └───────────┬───────────────────┘  │
│              │                       │
│      ┌───────┴────────┐             │
│      ▼                ▼             │
│  ┌────────┐      ┌─────────┐       │
│  │ Ollama │      │ Claude  │       │
│  │ (Local)│      │  API    │       │
│  └───┬────┘      └─────────┘       │
│      │                              │
│      ▼                              │
│  ┌────────────────┐                │
│  │ Chroma Vector  │                │
│  │   Database     │                │
│  └────────────────┘                │
└─────────────────────────────────────┘
         ▲
         │
┌────────┴─────────┐
│  Python Scraper  │
│  (FedEx Dev API) │
└──────────────────┘
```

## Components

### 1. Web Scraper (`/scraper`)
- Scrapes developer.fedex.com documentation
- Chunks content intelligently for embeddings
- Stores raw content and metadata

### 2. RAG System (`/rag`)
- Chroma vector database for document storage
- Sentence transformers for embeddings
- Semantic search with context retrieval

### 3. Backend Server (`/server`)
- FastAPI REST API
- Intelligent routing logic:
  - Simple API queries → Ollama (fast, free)
  - Complex/general questions → Claude (accurate, costs)
- Ollama integration for local LLM
- Claude API integration for enhanced responses

### 4. Developer Portal (`/portal`)
- Modern landing page
- Documentation and guides
- Chrome extension download
- Live demo/playground

### 5. Chrome Extension (`/extension`)
- Sidebar interface
- Quick access to chatbot
- Context-aware suggestions
- Chat history

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, Uvicorn
- **LLM**: Ollama (llama3.1/mistral), Claude API
- **Vector DB**: Chroma
- **Embeddings**: sentence-transformers
- **Scraping**: BeautifulSoup4, Playwright
- **Frontend**: HTML/CSS/JS (vanilla or React)
- **Extension**: Chrome Extension Manifest V3
- **Deployment**: Docker, Azure Container Apps
- **Database**: SQLite (local), PostgreSQL (Azure)

## Local Development Setup

### Prerequisites
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull recommended model
ollama pull llama3.1

# Install Python dependencies
pip install -r requirements.txt
```

### Environment Variables
```bash
cp .env.example .env
# Edit .env with your Claude API key
```

### Run Locally
```bash
# Start all services with Docker Compose
docker-compose up

# Or run individually:

# 1. Start Ollama (if not running as service)
ollama serve

# 2. Run scraper (one-time or scheduled)
python scraper/main.py

# 3. Start backend
cd server && uvicorn main:app --reload

# 4. Serve portal
cd portal && python -m http.server 8000

# 5. Load extension in Chrome
# Go to chrome://extensions/, enable Developer mode, Load unpacked
```

### Access Points
- Backend API: http://localhost:8000
- Developer Portal: http://localhost:8001
- API Docs: http://localhost:8000/docs

## Azure Deployment

### Architecture
- **Azure Container Apps**: Backend server
- **Azure Storage**: Vector DB persistence
- **Azure Functions**: Scheduled scraping
- **Azure Static Web Apps**: Portal hosting
- **Azure Key Vault**: API keys

### Deploy
```bash
# Build and push containers
./deploy/build.sh

# Deploy infrastructure
cd deploy/terraform
terraform init
terraform apply

# Or use Azure CLI
./deploy/azure-deploy.sh
```

## Cost Optimization

### Local Testing (Free)
- Ollama for LLM inference
- Chroma embedded database
- Local development server

### Production (Azure)
- Container Apps: ~$30-50/month
- Storage: ~$5/month
- Claude API: Pay per use (~$0.01-0.05 per query)
- Estimated: **$40-60/month** for moderate usage

### Intelligent Routing Saves Costs
- 70% of queries handled by Ollama (free)
- 30% complex queries use Claude
- Estimated Claude costs: **$10-20/month**

## Project Structure

```
fedex-api-chatbot/
├── scraper/
│   ├── main.py
│   ├── scraper.py
│   ├── chunker.py
│   └── requirements.txt
├── rag/
│   ├── embeddings.py
│   ├── vectorstore.py
│   └── retriever.py
├── server/
│   ├── main.py
│   ├── routers/
│   ├── services/
│   │   ├── ollama_service.py
│   │   ├── claude_service.py
│   │   └── router_service.py
│   ├── models/
│   └── requirements.txt
├── portal/
│   ├── index.html
│   ├── styles.css
│   ├── app.js
│   └── assets/
├── extension/
│   ├── manifest.json
│   ├── popup.html
│   ├── popup.js
│   ├── content.js
│   └── background.js
├── deploy/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── azure-deploy.sh
│   └── terraform/
├── tests/
├── .env.example
├── .gitignore
└── README.md
```

## Usage Examples

### Chat Interface
```
User: How do I authenticate with the FedEx Tracking API?

Bot: [Ollama - Fast Response]
To authenticate with the FedEx Tracking API, you need to:
1. Obtain API credentials from developer.fedex.com
2. Use OAuth 2.0 to get an access token
3. Include the token in your request headers

[Link to relevant docs]
```

### Complex Query
```
User: Compare the authentication methods across all FedEx APIs and recommend the best approach for a Node.js microservices architecture

Bot: [Claude - Enhanced Response]
[Detailed comparison with context from vector store + Claude's analysis]
```

## Development Roadmap

- [x] Architecture design
- [ ] Web scraper implementation
- [ ] RAG system with Chroma
- [ ] Backend API with intelligent routing
- [ ] Developer portal
- [ ] Chrome extension
- [ ] Docker setup
- [ ] Azure deployment configs
- [ ] Testing suite
- [ ] Documentation

## Contributing

This is a personal project. Feel free to fork and adapt.

## License

MIT License
