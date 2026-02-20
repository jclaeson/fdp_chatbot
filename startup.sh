#!/bin/bash
# Azure App Service startup script

echo "Starting FedEx API Chatbot..."

# Create directory for Chroma DB if it doesn't exist
mkdir -p /home/site/chromadb
mkdir -p /home/site/appdata

# Download Chroma DB from Azure Blob Storage (if configured)
if [ ! -z "$STORAGE_CONNECTION_STRING" ]; then
    echo "Syncing Chroma DB from Azure Storage..."
    # Install azcopy if needed (App Service should have it)
    # az storage blob download-batch --connection-string "$STORAGE_CONNECTION_STRING" \
    #   --source chromadb --destination /home/site/chromadb
fi

# Set Python path
export PYTHONPATH="${PYTHONPATH}:/home/site/wwwroot"

# Start the FastAPI application
cd /home/site/wwwroot/server
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2
