#!/usr/bin/env bash

set -e

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Error: Virtual environment not found."
    echo "Please run ./setup-local.sh first"
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "Error: .env file not found."
    echo "Please copy .env.example to .env and add your API keys"
    exit 1
fi

# Load environment variables (handle both Unix and Windows line endings)
echo "Loading environment variables..."
while IFS= read -r line || [ -n "$line" ]; do
    # Remove carriage return if present
    line=$(echo "$line" | tr -d '\r')
    # Skip comments and empty lines
    if [[ ! "$line" =~ ^# && -n "$line" ]]; then
        export "$line"
    fi
done < .env

# Start the server using uvicorn (proper way for FastAPI)
echo ""
echo "Starting FedEx API Chatbot server..."
echo "Server will be available at: http://localhost:8000"
echo "API docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Use uvicorn to start the app (handles module paths correctly)
uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload
