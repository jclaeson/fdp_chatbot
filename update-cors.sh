#!/usr/bin/env bash

set -e

echo "Updating CORS settings for Container App..."
echo ""

RESOURCE_GROUP="fedex-chatbot-rg"
CONTAINER_APP_NAME="fedex-chatbot-api"
FRONTEND_URL="https://thankful-beach-0fc7f100f.1.azurestaticapps.net"

echo "→ Adding frontend URL to CORS allowed origins..."

# Update with new CORS origins
az containerapp update \
    --name ${CONTAINER_APP_NAME} \
    --resource-group ${RESOURCE_GROUP} \
    --set-env-vars "CORS_ORIGINS=[\"${FRONTEND_URL}\",\"http://localhost:3000\",\"http://localhost:8080\"]"

echo ""
echo "✓ CORS settings updated!"
echo ""
echo "The frontend can now communicate with the backend."
echo "Try downloading the extension again - it should work now."
echo ""
