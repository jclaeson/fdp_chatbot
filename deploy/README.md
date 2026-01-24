# Azure Deployment Guide

This guide explains how to deploy the FedEx API Chatbot to Azure.

## Architecture

The Azure deployment consists of:

- **Azure Container Apps**: Hosts the FastAPI backend
- **Azure Container Registry (ACR)**: Stores Docker images
- **Azure Storage**: Persists Chroma vector database
- **Azure Static Web Apps**: Hosts the developer portal (optional)
- **Azure Key Vault**: Securely stores API keys (recommended)

## Prerequisites

1. Azure CLI installed and configured
2. Azure subscription with appropriate permissions
3. Docker installed locally
4. Claude API key
5. Scraped and indexed data (Chroma database)

## Cost Estimate

Based on moderate usage (500-1000 queries/day):

| Service | Configuration | Monthly Cost |
|---------|--------------|--------------|
| Container Apps | 1-3 replicas, 1 vCPU, 2 GB | $30-50 |
| Container Registry | Basic tier | $5 |
| Storage Account | Standard LRS, ~1 GB | $0.50 |
| Static Web App | Free tier | $0 |
| **Total** | | **~$35-55** |

Plus Claude API costs (~$10-20/month with intelligent routing)

## Quick Deploy

### 1. Prepare Environment

```bash
# Set your Claude API key
export CLAUDE_API_KEY="your_claude_api_key_here"

# Make deployment script executable
chmod +x deploy/azure-deploy.sh
```

### 2. Run Deployment

```bash
cd deploy
./azure-deploy.sh
```

This script will:
- Create resource group
- Set up Container Registry
- Build and push Docker image
- Create Storage Account for vector database
- Deploy Container App
- Create Static Web App for portal

### 3. Upload Vector Database

After deployment, upload your Chroma database:

```bash
# Get storage account key
STORAGE_KEY=$(az storage account keys list \
    --account-name fedexchatbotstorage \
    --query [0].value -o tsv)

# Upload Chroma database
az storage file upload-batch \
    --account-name fedexchatbotstorage \
    --account-key $STORAGE_KEY \
    --destination chroma-data \
    --source ../rag/chroma_db
```

### 4. Test Deployment

```bash
# Get API URL
API_URL=$(az containerapp show \
    --name fedex-chatbot-api \
    --resource-group fedex-chatbot-rg \
    --query properties.configuration.ingress.fqdn \
    -o tsv)

# Test health endpoint
curl https://$API_URL/health

# View API docs
open https://$API_URL/docs
```

## Manual Deployment Steps

If you prefer manual deployment or need more control:

### 1. Create Resource Group

```bash
az group create \
    --name fedex-chatbot-rg \
    --location eastus
```

### 2. Create Container Registry

```bash
az acr create \
    --resource-group fedex-chatbot-rg \
    --name fedexchatbotacr \
    --sku Basic
```

### 3. Build and Push Image

```bash
# Login to ACR
az acr login --name fedexchatbotacr

# Build and push
az acr build \
    --registry fedexchatbotacr \
    --image fedex-chatbot-api:latest \
    --file Dockerfile \
    .
```

### 4. Create Storage Account

```bash
az storage account create \
    --name fedexchatbotstorage \
    --resource-group fedex-chatbot-rg \
    --location eastus \
    --sku Standard_LRS

# Create file share
az storage share create \
    --name chroma-data \
    --account-name fedexchatbotstorage
```

### 5. Deploy Container App

```bash
az containerapp create \
    --name fedex-chatbot-api \
    --resource-group fedex-chatbot-rg \
    --environment fedex-chatbot-env \
    --image fedexchatbotacr.azurecr.io/fedex-chatbot-api:latest \
    --target-port 8000 \
    --ingress external \
    --secrets claude-api-key=$CLAUDE_API_KEY \
    --env-vars CLAUDE_API_KEY=secretref:claude-api-key
```

## Update Deployment

To update after making changes:

```bash
# Rebuild and push image
az acr build \
    --registry fedexchatbotacr \
    --image fedex-chatbot-api:latest \
    --file Dockerfile \
    .

# Container App will automatically pull new image
# Or force update:
az containerapp update \
    --name fedex-chatbot-api \
    --resource-group fedex-chatbot-rg
```

## Monitoring

### View Logs

```bash
az containerapp logs show \
    --name fedex-chatbot-api \
    --resource-group fedex-chatbot-rg \
    --follow
```

### Monitor Metrics

```bash
# View replica count
az containerapp replica list \
    --name fedex-chatbot-api \
    --resource-group fedex-chatbot-rg

# View revision traffic
az containerapp revision list \
    --name fedex-chatbot-api \
    --resource-group fedex-chatbot-rg
```

## Scaling

### Manual Scaling

```bash
az containerapp update \
    --name fedex-chatbot-api \
    --resource-group fedex-chatbot-rg \
    --min-replicas 2 \
    --max-replicas 5
```

### Auto-scaling Rules

```bash
az containerapp update \
    --name fedex-chatbot-api \
    --resource-group fedex-chatbot-rg \
    --scale-rule-name http-rule \
    --scale-rule-type http \
    --scale-rule-http-concurrency 100
```

## Security Best Practices

1. **Use Azure Key Vault** for storing API keys:
```bash
az keyvault create --name fedex-chatbot-kv --resource-group fedex-chatbot-rg
az keyvault secret set --vault-name fedex-chatbot-kv --name claude-api-key --value $CLAUDE_API_KEY
```

2. **Enable managed identity** for Container App

3. **Restrict ingress** to specific IP ranges if needed

4. **Enable HTTPS** only (default for Container Apps)

## Troubleshooting

### Container won't start

Check logs:
```bash
az containerapp logs show --name fedex-chatbot-api --resource-group fedex-chatbot-rg --follow
```

### Storage mount issues

Verify storage connection:
```bash
az containerapp env storage list --name fedex-chatbot-env --resource-group fedex-chatbot-rg
```

### High costs

- Reduce min replicas to 0 (scale to zero when idle)
- Use smaller container sizes
- Optimize Ollama usage to reduce Claude API calls

## Clean Up

To delete all resources:

```bash
az group delete --name fedex-chatbot-rg --yes --no-wait
```

## Alternative: Azure Functions

For lower traffic, consider using Azure Functions:

- Consumption plan: Pay only for executions
- Lower baseline cost (~$0-5/month)
- Cold start latency trade-off

## Support

For issues with:
- Azure deployment: See [Azure Container Apps docs](https://docs.microsoft.com/en-us/azure/container-apps/)
- Application: Check GitHub issues
