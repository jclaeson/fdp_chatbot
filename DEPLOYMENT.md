# FedEx API Chatbot - Complete Deployment Guide

## Quick Start (Single Command)

From the project root, run:

```bash
./deploy-all.sh
```

This will:
1. Build the Docker image with all dependencies
2. Push to Azure Container Registry
3. Update the backend Container App
4. Deploy frontend to Static Web Apps
5. Display URLs for access

## What's Deployed

### Backend Features
- ✅ FastAPI server with Ollama + Claude integration
- ✅ RAG system with ChromaDB vector store
- ✅ FedEx documentation scraper (admin-triggered)
- ✅ Automatic ingestion pipeline
- ✅ Chrome extension download endpoint
- ✅ Admin API for scraper controls

### Frontend Features
- ✅ Password-protected chat interface (Password: `PurplePromise`)
- ✅ Admin dashboard with username/password (`jclaeson` / `FedExAdmin1234`)
- ✅ Scraping controls (configure, start, ingest)
- ✅ Chrome extension download page
- ✅ Usage statistics and monitoring

### Admin Portal Capabilities

Access at: `https://your-frontend-url/admin-login.html`

**Scraping Controls:**
- Configure scrape parameters (max pages, depth, URLs)
- Start scraping FedEx Developer Portal
- Trigger ingestion into vector store
- One-click "Scrape & Ingest" workflow
- Real-time status monitoring

**System Monitoring:**
- Server health status
- Ollama/Claude availability
- Vector store document count
- Usage statistics

## Manual Deployment Steps

If you need to deploy components separately:

### 1. Backend Only

```bash
# Build and push
docker build -t fedexapichatbot.azurecr.io/fedex-api-chatbot:latest .
az acr login --name fedexapichatbot
docker push fedexapichatbot.azurecr.io/fedex-api-chatbot:latest

# Update Container App
az containerapp update \
  --name fedex-chatbot-api \
  --resource-group fedex-chatbot-rg \
  --image fedexapichatbot.azurecr.io/fedex-api-chatbot:latest
```

### 2. Frontend Only

```bash
cd portal

# Using SWA CLI
swa deploy --deployment-token YOUR_TOKEN

# OR using Azure CLI
az staticwebapp upload \
  --name fedex-chatbot-portal \
  --resource-group fedex-chatbot-rg \
  --source .
```

### 3. Trigger Documentation Ingestion

After deployment, populate the vector store:

**Option A: Use Admin Portal (Recommended)**
1. Go to `https://your-frontend/admin-login.html`
2. Login (jclaeson / FedExAdmin1234)
3. Scroll to "Documentation Scraper"
4. Click "Scrape & Ingest" button
5. Wait 10-15 minutes for completion

**Option B: Command Line**
```bash
az containerapp exec \
  --name fedex-chatbot-api \
  --resource-group fedex-chatbot-rg \
  --command "python /app/rag/ingest_fedex_docs.py"
```

## Environment Variables

The following environment variables are configured in Azure Container Apps:

```bash
ANTHROPIC_API_KEY=<your-key>
OLLAMA_BASE_URL=http://ollama:11434  # If using Ollama sidecar
CHROMA_PERSIST_DIR=/app/data/chroma_db
CORS_ORIGINS=["https://your-frontend.azurestaticapps.net"]
```

## Architecture

```
┌─────────────────────┐
│  Azure Static Web   │
│     Apps (Portal)   │
└──────────┬──────────┘
           │
           │ HTTPS/REST
           ▼
┌─────────────────────┐
│ Azure Container App │
│   (FastAPI Backend) │
│                     │
│  ┌──────────────┐   │
│  │   Router     │   │
│  │  Service     │   │
│  └─────┬────────┘   │
│        │            │
│   ┌────┴─────┐      │
│   ▼          ▼      │
│ Ollama    Claude    │
│   │                 │
│   │    ┌─────────┐  │
│   └────► ChromaDB │  │
│        │ Vector   │  │
│        │  Store   │  │
│        └─────────┘  │
└─────────────────────┘
```

## Scraping Workflow

1. **Configure** (Admin Portal)
   - Set max pages, depth, delay
   - Add/remove start URLs
   - Save configuration

2. **Scrape** (Automated)
   - Playwright launches headless browser
   - Navigates FedEx Developer Portal
   - Extracts content and metadata
   - Filters out SOAP/deprecated APIs
   - Saves to JSON files

3. **Ingest** (Automated)
   - Loads scraped JSON data
   - Filters SOAP content again
   - Chunks documents semantically
   - Generates embeddings (HuggingFace)
   - Stores in ChromaDB

4. **Query** (User-facing)
   - User asks question
   - Question → embedding vector
   - Search ChromaDB for similar docs
   - Retrieve top 5 relevant chunks
   - Ollama/Claude generates answer with context

## Troubleshooting

### Backend Issues

**Container won't start:**
```bash
# Check logs
az containerapp logs show \
  --name fedex-chatbot-api \
  --resource-group fedex-chatbot-rg \
  --tail 100
```

**Vector store is empty:**
- Use admin portal to trigger scrape & ingest
- OR run ingestion command manually
- Check scraper logs for errors

**Ollama not responding:**
- Verify Ollama is deployed as sidecar
- Check OLLAMA_BASE_URL environment variable

### Frontend Issues

**Can't login:**
- Password for users: `PurplePromise`
- Admin username: `jclaeson`
- Admin password: `FedExAdmin1234`

**API calls failing:**
- Check CORS settings in backend
- Verify API_BASE_URL in frontend JavaScript

### Scraping Issues

**Scraper failing to start:**
- Check Playwright is installed: `playwright install chromium`
- Verify sufficient memory in Container App

**No documents after ingestion:**
- Check scraped data exists: `/app/scraper/scraped_data/`
- Verify embedding model downloaded from HuggingFace
- Check logs for SOAP filtering (shouldn't filter everything)

## Monitoring

### Health Endpoint
```bash
curl https://fedex-chatbot-api.bluewater-xxx.eastus.azurecontainerapps.io/health
```

### Stats Endpoint
```bash
curl https://fedex-chatbot-api.bluewater-xxx.eastus.azurecontainerapps.io/api/stats
```

### Vector Store Status
```bash
curl https://fedex-chatbot-api.bluewater-xxx.eastus.azurecontainerapps.io/api/admin/scraper/status
```

## Cost Optimization

- **Ollama**: Free (runs in container)
- **Claude**: Pay per token (~$3/MTok input, $15/MTok output)
- **Azure Container App**: ~$30-50/month for basic tier
- **Azure Static Web Apps**: Free tier available
- **Azure Container Registry**: ~$5/month for basic

**Tip**: Use Ollama for most queries (free) and only route complex queries to Claude (paid). The router service does this automatically.

## Security Notes

- ✅ Client-side password protection (24-hour sessions)
- ✅ Separate admin authentication
- ✅ CORS restricted to your frontend domain
- ✅ HTTPS enforced on both frontend and backend
- ⚠️ Admin password should be changed in production
- ⚠️ Consider Azure AD authentication for production use

## Next Steps

1. **Deploy**: Run `./deploy-all.sh`
2. **Test**: Visit frontend URL, test chat
3. **Scrape**: Use admin portal to scrape FedEx docs
4. **Verify**: Ask FedEx-specific questions, verify responses
5. **Monitor**: Check admin dashboard for usage stats
6. **Optimize**: Adjust scraping parameters if needed

## Support

For issues:
1. Check logs: `az containerapp logs show`
2. Verify health: `/health` endpoint
3. Test vector store: Admin portal status
4. Review this guide's troubleshooting section
