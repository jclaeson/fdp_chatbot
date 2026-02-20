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

echo "3. Testing chat endpoint with simple question..."
curl -s -X POST "$API_URL/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "What is FedEx?"}' | jq .
echo ""

echo "4. Testing chat endpoint with more complex question..."
curl -s -X POST "$API_URL/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "How do I track a package using the FedEx API?"}' | jq .
echo ""

echo "5. Testing chat with conversation history..."
curl -s -X POST "$API_URL/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What about international shipping?",
    "conversation_history": [
      {"role": "user", "content": "Tell me about FedEx shipping options"},
      {"role": "assistant", "content": "FedEx offers various shipping options including overnight, 2-day, and ground shipping."}
    ]
  }' | jq .

