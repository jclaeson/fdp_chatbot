#!/usr/bin/env bash

set -e

echo "======================================"
echo "FedEx API Chatbot - Full Deployment"
echo "(Cloud Build - No Docker Required)"
echo "======================================"
echo ""

# Configuration
RESOURCE_GROUP="fedex-chatbot-rg"
LOCATION="eastus"
STATIC_WEB_APP_LOCATION="eastus2"  # Static Web Apps not available in eastus
ACR_NAME="fedexchatbotacr"
CONTAINER_APP_NAME="fedex-chatbot-api"
STATIC_WEB_APP_NAME="fedex-chatbot-portal"
IMAGE_TAG="latest"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

echo_info() {
    echo -e "${YELLOW}→ $1${NC}"
}

echo_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Check if logged in to Azure
echo_info "Checking Azure login status..."
if ! az account show &> /dev/null; then
    echo_error "Not logged in to Azure. Please run 'az login' first."
    exit 1
fi
echo_success "Azure CLI authenticated"

# Get subscription ID
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
echo_info "Using subscription: $SUBSCRIPTION_ID"

# Step 1: Build Docker Image in Azure (ACR Build)
echo ""
echo_info "Step 1: Building Docker image in Azure Container Registry..."
echo_info "This may take 5-10 minutes..."

az acr build \
    --registry ${ACR_NAME} \
    --image fedex-api-chatbot:${IMAGE_TAG} \
    --file Dockerfile \
    .

echo_success "Docker image built in ACR"

# Step 2: Update Container App
echo ""
echo_info "Step 2: Updating Azure Container App..."
az containerapp update \
    --name ${CONTAINER_APP_NAME} \
    --resource-group ${RESOURCE_GROUP} \
    --image ${ACR_NAME}.azurecr.io/fedex-api-chatbot:${IMAGE_TAG}
echo_success "Container App updated"

# Step 3: Deploy Frontend to Azure Static Web Apps
echo ""
echo_info "Step 3: Deploying frontend to Azure Static Web Apps..."

# Check if Static Web App exists
if az staticwebapp show --name ${STATIC_WEB_APP_NAME} --resource-group ${RESOURCE_GROUP} &> /dev/null; then
    echo_info "Static Web App exists, getting deployment token..."
    
    # Get deployment token
    DEPLOYMENT_TOKEN=$(az staticwebapp secrets list \
        --name ${STATIC_WEB_APP_NAME} \
        --resource-group ${RESOURCE_GROUP} \
        --query properties.apiKey -o tsv)
    
    # Deploy using SWA CLI
    if command -v swa &> /dev/null; then
        echo_info "Using SWA CLI to deploy..."
        cd portal
        swa deploy --deployment-token ${DEPLOYMENT_TOKEN}
        cd ..
    else
        echo_info "Installing SWA CLI..."
        npm install -g @azure/static-web-apps-cli
        cd portal
        swa deploy --deployment-token ${DEPLOYMENT_TOKEN}
        cd ..
    fi
    
    echo_success "Frontend deployed to Static Web Apps"
else
    echo_error "Static Web App not found. Creating one..."
    echo_info "Creating Static Web App..."
    
    az staticwebapp create \
        --name ${STATIC_WEB_APP_NAME} \
        --resource-group ${RESOURCE_GROUP} \
        --location ${STATIC_WEB_APP_LOCATION}
    
    echo_success "Static Web App created"
    echo_info "Manual step: Deploy frontend files to the Static Web App using Azure Portal or GitHub Actions"
fi

# Step 4: Get URLs
echo ""
BACKEND_URL=$(az containerapp show \
    --name ${CONTAINER_APP_NAME} \
    --resource-group ${RESOURCE_GROUP} \
    --query properties.configuration.ingress.fqdn -o tsv)

FRONTEND_URL=$(az staticwebapp show \
    --name ${STATIC_WEB_APP_NAME} \
    --resource-group ${RESOURCE_GROUP} \
    --query defaultHostname -o tsv)

echo ""
echo "======================================"
echo "Deployment Complete!"
echo "======================================"
echo ""
echo_success "Backend API: https://${BACKEND_URL}"
echo_success "Frontend: https://${FRONTEND_URL}"
echo ""
echo_info "Next steps:"
echo "  1. Test the backend health: curl https://${BACKEND_URL}/health"
echo "  2. Visit the frontend at: https://${FRONTEND_URL}"
echo "  3. Login with password: PurplePromise"
echo "  4. Access admin portal: https://${FRONTEND_URL}/admin-login.html"
echo "  5. Admin credentials: jclaeson / FedExAdmin1234"
echo "  6. Use admin portal to scrape and ingest FedEx docs"
echo ""
echo_info "To trigger documentation ingestion manually:"
echo "  az containerapp exec \\"
echo "    --name ${CONTAINER_APP_NAME} \\"
echo "    --resource-group ${RESOURCE_GROUP} \\"
echo "    --command 'python /app/rag/ingest_fedex_docs.py'"
echo ""
