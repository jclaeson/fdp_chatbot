"""
Embedding generation using sentence-transformers
Optimized for technical documentation and code
"""
from typing import List
import logging

from sentence_transformers import SentenceTransformer
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmbeddingModel:
    """Wrapper for embedding model with caching and batching"""

    # Best models for technical documentation
    DEFAULT_MODEL = "all-MiniLM-L6-v2"  # Fast, good quality, 384 dimensions
    # Alternative: "all-mpnet-base-v2"  # Higher quality, 768 dimensions, slower

    def __init__(self, model_name: str = None):
        """
        Initialize embedding model

        Args:
            model_name: Name of sentence-transformers model
        """
        self.model_name = model_name or self.DEFAULT_MODEL
        logger.info(f"Loading embedding model: {self.model_name}")

        self.model = SentenceTransformer(self.model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()

        logger.info(f"Model loaded. Embedding dimension: {self.dimension}")

    def embed_texts(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Generate embeddings for a list of texts

        Args:
            texts: List of text strings to embed
            batch_size: Batch size for processing

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        logger.info(f"Generating embeddings for {len(texts)} texts")

        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=True  # Normalize for cosine similarity
        )

        return embeddings.tolist()

    def embed_query(self, query: str) -> List[float]:
        """
        Generate embedding for a single query

        Args:
            query: Query text

        Returns:
            Embedding vector
        """
        embedding = self.model.encode(
            query,
            convert_to_numpy=True,
            normalize_embeddings=True
        )

        return embedding.tolist()

    def get_dimension(self) -> int:
        """Get embedding dimension"""
        return self.dimension


def calculate_similarity(embedding1: List[float], embedding2: List[float]) -> float:
    """
    Calculate cosine similarity between two embeddings

    Args:
        embedding1: First embedding vector
        embedding2: Second embedding vector

    Returns:
        Similarity score (0-1)
    """
    vec1 = np.array(embedding1)
    vec2 = np.array(embedding2)

    # Cosine similarity
    similarity = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

    return float(similarity)


# Singleton instance for reuse
_embedding_model = None


def get_embedding_model(model_name: str = None) -> EmbeddingModel:
    """
    Get or create embedding model instance

    Args:
        model_name: Optional model name

    Returns:
        EmbeddingModel instance
    """
    global _embedding_model

    if _embedding_model is None or (model_name and model_name != _embedding_model.model_name):
        _embedding_model = EmbeddingModel(model_name)

    return _embedding_model


if __name__ == "__main__":
    # Test the embedding model
    model = get_embedding_model()

    test_texts = [
        "How do I authenticate with the FedEx API?",
        "What is the endpoint for tracking packages?",
        "Rate shopping and comparison"
    ]

    embeddings = model.embed_texts(test_texts)
    print(f"Generated {len(embeddings)} embeddings")
    print(f"Embedding dimension: {len(embeddings[0])}")

    # Test similarity
    query = "How to track a shipment"
    query_embedding = model.embed_query(query)

    for i, text in enumerate(test_texts):
        sim = calculate_similarity(query_embedding, embeddings[i])
        print(f"Similarity with '{text}': {sim:.4f}")
