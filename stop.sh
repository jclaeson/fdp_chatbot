#!/bin/bash

# Stop all running services

echo "🛑 Stopping FedEx API Chatbot services..."

# Kill processes by port
echo "Stopping API server (port 8000)..."
lsof -ti:8000 | xargs kill -9 2>/dev/null && echo "✅ API server stopped" || echo "⚠️  No API server running"

echo "Stopping portal (port 8001)..."
lsof -ti:8001 | xargs kill -9 2>/dev/null && echo "✅ Portal stopped" || echo "⚠️  No portal running"

# Optionally stop Ollama (uncomment if you want to stop it too)
# echo "Stopping Ollama (port 11434)..."
# lsof -ti:11434 | xargs kill -9 2>/dev/null && echo "✅ Ollama stopped" || echo "⚠️  No Ollama running"

echo ""
echo "✨ All services stopped"
