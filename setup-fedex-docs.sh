#!/usr/bin/env bash

set -e

echo "Setting up FedEx Documentation for RAG"
echo "======================================"
echo ""

# Activate virtual environment
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
else
    echo "Error: Virtual environment not found. Run ./setup-local.sh first"
    exit 1
fi

# Install additional dependencies for scraping
echo "Installing scraping dependencies..."
pip install playwright beautifulsoup4 lxml markdownify --break-system-packages 2>/dev/null || pip install playwright beautifulsoup4 lxml markdownify

# Install Playwright browsers
echo "Installing Playwright browsers (this may take a few minutes)..."
playwright install chromium

# Run scraper
echo ""
echo "Step 1: Scraping FedEx Developer Portal..."
echo "(This will take 5-10 minutes to scrape 50 pages)"
cd scraper
python scraper.py
cd ..

# Ingest into vector store
echo ""
echo "Step 2: Ingesting documentation into vector store..."
cd rag
python ingest_fedex_docs.py
cd ..

echo ""
echo "✅ Setup complete!"
echo ""
echo "The vector store now contains FedEx REST API documentation."
echo "You can now start the server and get accurate FedEx-specific responses!"
echo ""
echo "To test:"
echo "  ./start-local.sh"
echo "  Then ask questions like 'What is the Ship API?' or 'Show me a Python example for tracking'"
