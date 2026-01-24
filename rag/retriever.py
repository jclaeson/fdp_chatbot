"""
Advanced retrieval strategies for RAG
Implements hybrid search and result reranking
"""
import logging
from typing import List, Dict, Optional

from vectorstore import VectorStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Retriever:
    """Advanced document retrieval with multiple strategies"""

    def __init__(
        self,
        vector_store: VectorStore,
        top_k: int = 5,
        similarity_threshold: float = 0.5
    ):
        """
        Initialize retriever

        Args:
            vector_store: VectorStore instance
            top_k: Number of documents to retrieve
            similarity_threshold: Minimum similarity score
        """
        self.vector_store = vector_store
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold

    def retrieve(
        self,
        query: str,
        strategy: str = "semantic",
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Retrieve relevant documents

        Args:
            query: Search query
            strategy: Retrieval strategy ('semantic', 'hybrid', 'filtered')
            filters: Optional metadata filters

        Returns:
            List of relevant documents with scores
        """
        if strategy == "semantic":
            return self._semantic_search(query, filters)
        elif strategy == "hybrid":
            return self._hybrid_search(query, filters)
        elif strategy == "filtered":
            return self._filtered_search(query, filters)
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

    def _semantic_search(
        self,
        query: str,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """Pure semantic search using embeddings"""
        results = self.vector_store.search(
            query=query,
            n_results=self.top_k,
            filter_metadata=filters
        )

        # Filter by similarity threshold
        filtered_results = [
            r for r in results
            if r['score'] >= self.similarity_threshold
        ]

        return filtered_results

    def _hybrid_search(
        self,
        query: str,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Hybrid search combining semantic and keyword matching
        Useful for exact API names, endpoints, etc.
        """
        # Get semantic results
        semantic_results = self._semantic_search(query, filters)

        # Boost results that contain exact query terms
        query_terms = set(query.lower().split())

        for result in semantic_results:
            content_terms = set(result['content'].lower().split())

            # Calculate keyword overlap
            overlap = len(query_terms & content_terms) / len(query_terms)

            # Boost score based on keyword overlap
            result['score'] = result['score'] * (1 + overlap * 0.3)

        # Re-sort by boosted score
        semantic_results.sort(key=lambda x: x['score'], reverse=True)

        return semantic_results[:self.top_k]

    def _filtered_search(
        self,
        query: str,
        filters: Dict
    ) -> List[Dict]:
        """Search with strict metadata filtering"""
        return self._semantic_search(query, filters)

    def retrieve_context(
        self,
        query: str,
        max_tokens: int = 2000
    ) -> str:
        """
        Retrieve and format context for LLM

        Args:
            query: Search query
            max_tokens: Maximum tokens for context

        Returns:
            Formatted context string
        """
        results = self.retrieve(query, strategy="hybrid")

        if not results:
            return ""

        context_parts = []
        token_count = 0

        for i, result in enumerate(results):
            # Estimate tokens (rough: 1 token ≈ 4 chars)
            result_tokens = len(result['content']) // 4

            if token_count + result_tokens > max_tokens:
                break

            # Format result
            context_part = f"""
[Source {i + 1}] {result['metadata']['title']}
URL: {result['metadata']['source_url']}
Relevance: {result['score']:.2f}

{result['content']}

---
"""
            context_parts.append(context_part)
            token_count += result_tokens

        return "\n".join(context_parts)

    def get_relevant_sources(
        self,
        query: str,
        max_sources: int = 3
    ) -> List[Dict]:
        """
        Get relevant source URLs for citation

        Args:
            query: Search query
            max_sources: Maximum number of sources

        Returns:
            List of source metadata
        """
        results = self.retrieve(query, strategy="hybrid")

        # Deduplicate by URL
        seen_urls = set()
        unique_sources = []

        for result in results:
            url = result['metadata']['source_url']
            if url not in seen_urls:
                seen_urls.add(url)
                unique_sources.append({
                    'title': result['metadata']['title'],
                    'url': url,
                    'score': result['score']
                })

            if len(unique_sources) >= max_sources:
                break

        return unique_sources


# Singleton instance
_retriever = None


def get_retriever(
    vector_store: VectorStore = None,
    top_k: int = 5
) -> Retriever:
    """
    Get or create retriever instance

    Args:
        vector_store: VectorStore instance
        top_k: Number of results to retrieve

    Returns:
        Retriever instance
    """
    global _retriever

    if _retriever is None:
        if vector_store is None:
            # Create default vector store
            vector_store = VectorStore()

        _retriever = Retriever(vector_store, top_k=top_k)

    return _retriever


if __name__ == "__main__":
    # Test retrieval
    vector_store = VectorStore(persist_directory="./chroma_db")

    if vector_store.count() == 0:
        print("No documents in vector store. Please run vectorstore.py first.")
        exit(1)

    retriever = Retriever(vector_store, top_k=3)

    # Test queries
    test_queries = [
        "How do I authenticate with the FedEx API?",
        "What is the tracking endpoint?",
        "Rate shopping API documentation"
    ]

    for query in test_queries:
        print(f"\nQuery: {query}")
        print("=" * 80)

        results = retriever.retrieve(query, strategy="hybrid")

        for i, result in enumerate(results):
            print(f"\n[Result {i + 1}] Score: {result['score']:.3f}")
            print(f"Title: {result['metadata']['title']}")
            print(f"URL: {result['metadata']['source_url']}")
            print(f"Content preview: {result['content'][:200]}...")

        print("\n" + "=" * 80)
