#!/bin/bash

# Simple startup script for local development
# Starts all components without Docker

set -e

echo "🚀 Starting FedEx API Chatbot..."

# Check if Ollama is running
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "⚠️  Ollama is not running. Starting Ollama..."
    ollama serve > /dev/null 2>&1 &
    OLLAMA_PID=$!
    sleep 3
    echo "✅ Ollama started (PID: $OLLAMA_PID)"
else
    echo "✅ Ollama is already running"
fi

# Check if required model is pulled
if ! ollama list | grep -q "mistral"; then
    echo "📥 Pulling Mistral model..."
    ollama pull mistral
fi

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "🐍 Activating virtual environment..."
    source venv/bin/activate
fi

# Check if vector database exists
if [ ! -d "rag/chroma_db" ] || [ -z "$(ls -A rag/chroma_db 2>/dev/null)" ]; then
    echo "⚠️  No vector database found. You'll need to run the scraper and indexer first:"
    echo "   cd scraper && python main.py --mode all --max-pages 50"
    echo "   cd ../rag && python vectorstore.py ../scraper/scraped_data/chunked_data.json"
    echo ""
    echo "   For now, the server will start but won't have documentation to query."
    echo ""
fi

# Start the FastAPI server in the background
echo "🌐 Starting API server on http://localhost:8000..."
cd server
uvicorn main:app --host 0.0.0.0 --port 8000 > ../logs/server.log 2>&1 &
SERVER_PID=$!
cd ..

sleep 2

# Check if server started successfully
if ps -p $SERVER_PID > /dev/null; then
    echo "✅ API server started (PID: $SERVER_PID)"
else
    echo "❌ Failed to start API server. Check logs/server.log"
    exit 1
fi

# Start the portal
echo "🎨 Starting developer portal on http://localhost:8001..."
cd portal
python3 -m http.server 8001 > ../logs/portal.log 2>&1 &
PORTAL_PID=$!
cd ..

sleep 1

if ps -p $PORTAL_PID > /dev/null; then
    echo "✅ Portal started (PID: $PORTAL_PID)"
else
    echo "❌ Failed to start portal. Check logs/portal.log"
fi

echo ""
echo "════════════════════════════════════════════════════════════"
echo "✨ FedEx API Chatbot is running!"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "📍 Access points:"
echo "   • API Server:    http://localhost:8000"
echo "   • API Docs:      http://localhost:8000/docs"
echo "   • Health Check:  http://localhost:8000/health"
echo "   • Dev Portal:    http://localhost:8001"
echo ""
echo "📊 Process IDs:"
echo "   • Server: $SERVER_PID"
echo "   • Portal: $PORTAL_PID"
if [ ! -z "$OLLAMA_PID" ]; then
    echo "   • Ollama: $OLLAMA_PID"
fi
echo ""
echo "📝 Logs:"
echo "   • Server: logs/server.log"
echo "   • Portal: logs/portal.log"
echo ""
echo "🛑 To stop all services:"
echo "   ./stop.sh"
echo ""
echo "💡 Quick test:"
echo "   curl http://localhost:8000/health"
echo ""
echo "Press Ctrl+C to view logs (services will keep running)..."

# Trap Ctrl+C to show message
trap 'echo ""; echo "Services are still running. Use ./stop.sh to stop them."; exit 0' INT

# Follow server logs
tail -f logs/server.log
