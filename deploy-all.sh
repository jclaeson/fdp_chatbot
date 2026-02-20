#!/usr/bin/env bash

set -e

echo "======================================"
echo "FedEx API Chatbot - Full Deployment"
echo "======================================"
echo ""

# Configuration
RESOURCE_GROUP="fedex-chatbot-rg"
LOCATION="eastus"
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

# Step 1: Build Docker Image
echo ""
echo_info "Step 1: Building Docker image..."
docker build -t ${ACR_NAME}.azurecr.io/fedex-api-chatbot:${IMAGE_TAG} .
echo_success "Docker image built"

# Step 2: Push to Azure Container Registry
echo ""
echo_info "Step 2: Pushing to Azure Container Registry..."
az acr login --name ${ACR_NAME}
docker push ${ACR_NAME}.azurecr.io/fedex-api-chatbot:${IMAGE_TAG}
echo_success "Image pushed to ACR"

# Step 3: Update Container App
echo ""
echo_info "Step 3: Updating Azure Container App..."
az containerapp update \
    --name ${CONTAINER_APP_NAME} \
    --resource-group ${RESOURCE_GROUP} \
    --image ${ACR_NAME}.azurecr.io/fedex-api-chatbot:${IMAGE_TAG}
echo_success "Container App updated"

# Step 4: Deploy Frontend to Azure Static Web Apps
echo ""
echo_info "Step 4: Deploying frontend to Azure Static Web Apps..."

# Check if Static Web App exists
if az staticwebapp show --name ${STATIC_WEB_APP_NAME} --resource-group ${RESOURCE_GROUP} &> /dev/null; then
    echo_info "Static Web App exists, updating..."
else
    echo_info "Creating new Static Web App..."
    az staticwebapp create \
        --name ${STATIC_WEB_APP_NAME} \
        --resource-group ${RESOURCE_GROUP} \
        --location ${LOCATION} \
        --source portal \
        --app-location "/" \
        --output-location "/" \
        --branch main
fi

# Get deployment token
DEPLOYMENT_TOKEN=$(az staticwebapp secrets list \
    --name ${STATIC_WEB_APP_NAME} \
    --resource-group ${RESOURCE_GROUP} \
    --query properties.apiKey -o tsv)

# Deploy using SWA CLI or manual upload
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

# Step 5: Get URLs
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
echo "  1. Test the frontend at: https://${FRONTEND_URL}"
echo "  2. Login with password: PurplePromise"
echo "  3. Access admin portal at: https://${FRONTEND_URL}/admin-login.html"
echo "  4. Admin credentials: jclaeson / FedExAdmin1234"
echo "  5. Use admin portal to scrape and ingest FedEx docs"
echo ""
