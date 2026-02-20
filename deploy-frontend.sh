#!/usr/bin/env bash

set -e

echo "Deploying Frontend to Azure Static Web Apps..."
echo ""

RESOURCE_GROUP="fedex-chatbot-rg"
STATIC_WEB_APP_NAME="fedex-chatbot-portal"

# Get deployment token
echo "→ Getting deployment token..."
DEPLOYMENT_TOKEN=$(az staticwebapp secrets list \
    --name ${STATIC_WEB_APP_NAME} \
    --resource-group ${RESOURCE_GROUP} \
    --query properties.apiKey -o tsv)

if [ -z "$DEPLOYMENT_TOKEN" ]; then
    echo "✗ Failed to get deployment token"
    exit 1
fi

echo "✓ Got deployment token"

# Check if SWA CLI is installed
if ! command -v swa &> /dev/null; then
    echo "→ Installing SWA CLI..."
    npm install -g @azure/static-web-apps-cli
fi

echo "→ Deploying frontend files..."

# Deploy from project root with portal as app location
swa deploy ./portal \
    --deployment-token ${DEPLOYMENT_TOKEN} \
    --env production

echo ""
echo "✓ Frontend deployment complete!"
echo ""
echo "Visit your site:"
FRONTEND_URL=$(az staticwebapp show \
    --name ${STATIC_WEB_APP_NAME} \
    --resource-group ${RESOURCE_GROUP} \
    --query defaultHostname -o tsv)
echo "https://${FRONTEND_URL}"
echo ""
echo "Note: It may take 1-2 minutes for the deployment to propagate."
