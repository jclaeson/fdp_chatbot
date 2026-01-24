#!/bin/bash

# Azure Deployment Script for FedEx API Chatbot
# Prerequisites: Azure CLI installed and logged in

set -e

# Configuration
RESOURCE_GROUP="fedex-chatbot-rg"
LOCATION="eastus"
ACR_NAME="fedexchatbotacr"
CONTAINER_APP_NAME="fedex-chatbot-api"
CONTAINER_APP_ENV="fedex-chatbot-env"
STORAGE_ACCOUNT="fedexchatbotstorage"
STATIC_WEB_APP="fedex-chatbot-portal"

echo "🚀 Starting Azure deployment for FedEx API Chatbot..."

# Create resource group
echo "📦 Creating resource group..."
az group create \
    --name $RESOURCE_GROUP \
    --location $LOCATION

# Create Azure Container Registry
echo "📦 Creating Azure Container Registry..."
az acr create \
    --resource-group $RESOURCE_GROUP \
    --name $ACR_NAME \
    --sku Basic \
    --admin-enabled true

# Build and push Docker image
echo "🏗️  Building and pushing Docker image..."
az acr build \
    --registry $ACR_NAME \
    --image fedex-chatbot-api:latest \
    --file ../Dockerfile \
    ../

# Get ACR credentials
ACR_USERNAME=$(az acr credential show --name $ACR_NAME --query username -o tsv)
ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query passwords[0].value -o tsv)
ACR_LOGIN_SERVER=$(az acr show --name $ACR_NAME --query loginServer -o tsv)

# Create Storage Account for vector database persistence
echo "💾 Creating Storage Account..."
az storage account create \
    --name $STORAGE_ACCOUNT \
    --resource-group $RESOURCE_GROUP \
    --location $LOCATION \
    --sku Standard_LRS

# Create file share for Chroma DB
STORAGE_KEY=$(az storage account keys list \
    --account-name $STORAGE_ACCOUNT \
    --query [0].value -o tsv)

az storage share create \
    --name chroma-data \
    --account-name $STORAGE_ACCOUNT \
    --account-key $STORAGE_KEY

# Create Container Apps environment
echo "🌐 Creating Container Apps environment..."
az containerapp env create \
    --name $CONTAINER_APP_ENV \
    --resource-group $RESOURCE_GROUP \
    --location $LOCATION

# Create storage mount
az containerapp env storage set \
    --name $CONTAINER_APP_ENV \
    --resource-group $RESOURCE_GROUP \
    --storage-name chroma-storage \
    --azure-file-account-name $STORAGE_ACCOUNT \
    --azure-file-account-key $STORAGE_KEY \
    --azure-file-share-name chroma-data \
    --access-mode ReadWrite

# Deploy Container App
echo "🚢 Deploying Container App..."
az containerapp create \
    --name $CONTAINER_APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --environment $CONTAINER_APP_ENV \
    --image $ACR_LOGIN_SERVER/fedex-chatbot-api:latest \
    --registry-server $ACR_LOGIN_SERVER \
    --registry-username $ACR_USERNAME \
    --registry-password $ACR_PASSWORD \
    --target-port 8000 \
    --ingress external \
    --min-replicas 1 \
    --max-replicas 3 \
    --cpu 1.0 \
    --memory 2.0Gi \
    --secrets \
        claude-api-key=$CLAUDE_API_KEY \
    --env-vars \
        CLAUDE_API_KEY=secretref:claude-api-key \
        OLLAMA_BASE_URL=http://localhost:11434 \
        CHROMA_PERSIST_DIR=/mnt/chroma-data

# Deploy Static Web App for portal
echo "🌍 Creating Static Web App..."
az staticwebapp create \
    --name $STATIC_WEB_APP \
    --resource-group $RESOURCE_GROUP \
    --location $LOCATION \
    --source ../portal

# Get the API URL
API_URL=$(az containerapp show \
    --name $CONTAINER_APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --query properties.configuration.ingress.fqdn \
    -o tsv)

echo "✅ Deployment complete!"
echo ""
echo "📋 Deployment Summary:"
echo "Resource Group: $RESOURCE_GROUP"
echo "API URL: https://$API_URL"
echo "Container Registry: $ACR_LOGIN_SERVER"
echo ""
echo "Next steps:"
echo "1. Upload your Chroma database to Azure Storage"
echo "2. Update environment variables if needed"
echo "3. Test the API at https://$API_URL/docs"
echo ""
echo "💡 To update the deployment:"
echo "   az acr build --registry $ACR_NAME --image fedex-chatbot-api:latest ../Dockerfile ../"
echo "   az containerapp update --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP"
