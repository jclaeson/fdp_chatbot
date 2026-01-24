"""
Chroma vector database wrapper
Stores and retrieves document embeddings
"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

from embeddings import get_embedding_model

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VectorStore:
    """Chroma-based vector store for document retrieval"""

    def __init__(
        self,
        persist_directory: str = "./chroma_db",
        collection_name: str = "fedex_docs",
        embedding_model_name: str = None
    ):
        """
        Initialize vector store

        Args:
            persist_directory: Directory to persist Chroma database
            collection_name: Name of the collection
            embedding_model_name: Name of embedding model to use
        """
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)

        self.collection_name = collection_name

        # Initialize Chroma client
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # Get embedding model
        self.embedding_model = get_embedding_model(embedding_model_name)

        # Get or create collection
        self.collection = self._get_or_create_collection()

        logger.info(f"Vector store initialized with {self.count()} documents")

    def _get_or_create_collection(self):
        """Get existing collection or create new one"""
        try:
            collection = self.client.get_collection(
                name=self.collection_name,
            )
            logger.info(f"Loaded existing collection: {self.collection_name}")
        except Exception:
            collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"Created new collection: {self.collection_name}")

        return collection

    def add_documents(
        self,
        chunks: List[Dict],
        batch_size: int = 100
    ):
        """
        Add documents to vector store

        Args:
            chunks: List of chunk dictionaries from chunker
            batch_size: Batch size for adding documents
        """
        logger.info(f"Adding {len(chunks)} documents to vector store")

        # Process in batches
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]

            # Extract data
            ids = [chunk['chunk_id'] for chunk in batch]
            texts = [chunk['content'] for chunk in batch]
            metadatas = [
                {
                    'source_url': chunk['source_url'],
                    'title': chunk['title'],
                    'chunk_index': chunk['chunk_index'],
                    **chunk['metadata']
                }
                for chunk in batch
            ]

            # Generate embeddings
            embeddings = self.embedding_model.embed_texts(texts)

            # Add to collection
            self.collection.add(
                ids=ids,
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas
            )

            logger.info(f"Added batch {i // batch_size + 1}/{(len(chunks) + batch_size - 1) // batch_size}")

        logger.info(f"Successfully added {len(chunks)} documents")

    def search(
        self,
        query: str,
        n_results: int = 5,
        filter_metadata: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Search for relevant documents

        Args:
            query: Search query
            n_results: Number of results to return
            filter_metadata: Optional metadata filters

        Returns:
            List of search results with content and metadata
        """
        # Generate query embedding
        query_embedding = self.embedding_model.embed_query(query)

        # Search
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=filter_metadata,
            include=['documents', 'metadatas', 'distances']
        )

        # Format results
        formatted_results = []
        for i in range(len(results['ids'][0])):
            formatted_results.append({
                'id': results['ids'][0][i],
                'content': results['documents'][0][i],
                'metadata': results['metadatas'][0][i],
                'distance': results['distances'][0][i],
                'score': 1 - results['distances'][0][i]  # Convert distance to similarity
            })

        return formatted_results

    def count(self) -> int:
        """Get number of documents in collection"""
        return self.collection.count()

    def delete_collection(self):
        """Delete the collection"""
        self.client.delete_collection(name=self.collection_name)
        logger.info(f"Deleted collection: {self.collection_name}")

    def reset(self):
        """Reset the collection (delete and recreate)"""
        self.delete_collection()
        self.collection = self._get_or_create_collection()
        logger.info("Collection reset")


def load_and_index_documents(
    chunked_file: str,
    persist_directory: str = "./chroma_db",
    collection_name: str = "fedex_docs"
):
    """
    Load chunked documents and index them in vector store

    Args:
        chunked_file: Path to chunked JSON file
        persist_directory: Directory for Chroma database
        collection_name: Name of collection
    """
    logger.info(f"Loading chunks from {chunked_file}")

    # Load chunks
    with open(chunked_file, 'r', encoding='utf-8') as f:
        chunks = json.load(f)

    logger.info(f"Loaded {len(chunks)} chunks")

    # Initialize vector store
    vector_store = VectorStore(
        persist_directory=persist_directory,
        collection_name=collection_name
    )

    # Check if already indexed
    if vector_store.count() > 0:
        logger.warning(f"Collection already contains {vector_store.count()} documents")
        response = input("Do you want to reset and reindex? (yes/no): ")
        if response.lower() == 'yes':
            vector_store.reset()
        else:
            logger.info("Skipping indexing")
            return

    # Add documents
    vector_store.add_documents(chunks)

    logger.info(f"Indexing complete. Total documents: {vector_store.count()}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python vectorstore.py <chunked_file.json>")
        sys.exit(1)

    load_and_index_documents(sys.argv[1])
