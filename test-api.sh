#!/usr/bin/env bash

API_URL="https://fedex-chatbot-api.bluewater-bfc57c63.eastus.azurecontainerapps.io"

echo "Testing FedEx API Chatbot"
echo "========================="
echo ""

echo "1. Testing root endpoint..."
curl -s "$API_URL/" | jq .
echo ""

echo "2. Testing health endpoint..."
curl -s "$API_URL/health" | jq .
echo ""

echo "3. Testing chat endpoint (force Claude)..."
curl -s -X POST "$API_URL/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "What is FedEx?", "use_claude": true}' | jq .
echo ""

echo "4. Checking Container App logs for errors..."
az containerapp logs show --name fedex-chatbot-api --resource-group fedex-chatbot-rg --tail 100 --type console | grep -i "error\|exception\|failed\|claude"
