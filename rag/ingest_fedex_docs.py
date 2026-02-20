"""
Ingest FedEx documentation from scraped JSON files into the vector store
"""
import json
import logging
import sys
from pathlib import Path
from typing import List, Dict

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from rag.vectorstore import VectorStore
from rag.embeddings import get_embedding_model

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FedExDocIngester:
    """Ingests scraped FedEx documentation into vector store"""

    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store

    def ingest_from_json(self, json_file: Path) -> int:
        """
        Ingest documents from a scraped JSON file

        Args:
            json_file: Path to JSON file with scraped content

        Returns:
            Number of documents added
        """
        logger.info(f"Loading scraped data from {json_file}")

        with open(json_file, 'r', encoding='utf-8') as f:
            scraped_data = json.load(f)

        documents = []
        metadatas = []

        for item in scraped_data:
            # Filter out SOAP/deprecated content
            if self._is_deprecated_content(item):
                logger.info(f"Skipping deprecated content: {item['url']}")
                continue

            # Create document chunks from content
            chunks = self._chunk_content(item)

            for chunk in chunks:
                documents.append(chunk['text'])
                metadatas.append({
                    'url': item['url'],
                    'title': item['title'],
                    'api_name': item['metadata'].get('api_name', 'Unknown'),
                    'category': item['metadata'].get('category', 'general'),
                    'chunk_index': chunk['index'],
                    'has_code': chunk['has_code']
                })

        if documents:
            logger.info(f"Adding {len(documents)} document chunks to vector store")
            self.vector_store.add_documents(
                documents=documents,
                metadatas=metadatas
            )

        return len(documents)

    def _is_deprecated_content(self, item: Dict) -> bool:
        """Check if content is deprecated (SOAP/old APIs)"""
        content_lower = item['content'].lower()
        url_lower = item['url'].lower()

        # Skip SOAP-related content
        soap_indicators = [
            'soap', 'wsdl', 'web service', 'webservice',
            'fedexsoap', 'wsbeta', 'soap envelope'
        ]

        if any(indicator in content_lower or indicator in url_lower for indicator in soap_indicators):
            return True

        # Skip if explicitly marked as deprecated
        if 'deprecated' in content_lower or 'legacy' in content_lower:
            return True

        return False

    def _chunk_content(self, item: Dict, chunk_size: int = 1000, overlap: int = 200) -> List[Dict]:
        """
        Split content into chunks for better retrieval

        Args:
            item: Scraped page data
            chunk_size: Target size of each chunk in characters
            overlap: Overlap between chunks

        Returns:
            List of chunk dictionaries
        """
        content = item['content']
        code_snippets = item.get('code_snippets', [])

        chunks = []
        start = 0
        index = 0

        while start < len(content):
            end = start + chunk_size
            chunk_text = content[start:end]

            # Try to break at sentence boundary
            if end < len(content):
                last_period = chunk_text.rfind('. ')
                if last_period > chunk_size // 2:
                    end = start + last_period + 1
                    chunk_text = content[start:end]

            # Add relevant code snippets to chunk
            has_code = False
            if code_snippets:
                # Add first code snippet to first chunk, etc.
                if index < len(code_snippets):
                    chunk_text += f"\n\nCode Example:\n{code_snippets[index]}"
                    has_code = True

            chunks.append({
                'text': f"Title: {item['title']}\nURL: {item['url']}\n\n{chunk_text}",
                'index': index,
                'has_code': has_code
            })

            start = end - overlap
            index += 1

        return chunks


def main():
    """Main ingestion function"""
    # Initialize vector store
    embedding_model = get_embedding_model()
    vector_store = VectorStore(
        collection_name="fedex_docs",
        persist_directory="chroma_db",
        embedding_function=embedding_model
    )

    # Find latest scraped file
    scraper_dir = Path(__file__).parent.parent / "scraper" / "scraped_data"

    if not scraper_dir.exists():
        logger.error(f"Scraper data directory not found: {scraper_dir}")
        return

    json_files = list(scraper_dir.glob("scraped_content_*.json"))

    if not json_files:
        logger.error("No scraped content files found")
        return

    # Use the latest file
    latest_file = max(json_files, key=lambda p: p.stat().st_mtime)
    logger.info(f"Using latest scrape file: {latest_file}")

    # Ingest documents
    ingester = FedExDocIngester(vector_store)
    num_docs = ingester.ingest_from_json(latest_file)

    logger.info(f"✅ Ingestion complete! Added {num_docs} document chunks")
    logger.info(f"Vector store now contains {vector_store.count()} total documents")


if __name__ == "__main__":
    main()
