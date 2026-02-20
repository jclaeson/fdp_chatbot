"""
Intelligent routing between Ollama and Claude
Routes queries based on complexity and content
"""
import logging
import re
from typing import Tuple, Optional
from dataclasses import dataclass

from server.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class QueryAnalysis:
    """Analysis of query complexity"""
    complexity_score: float  # 0-1
    query_type: str
    recommended_model: str
    reasoning: str


class RouterService:
    """Intelligent router between Ollama and Claude"""

    # Patterns that indicate complex queries
    COMPLEX_PATTERNS = [
        r'\b(compare|versus|vs|difference|which is better)\b',
        r'\b(architecture|design pattern|best practice)\b',
        r'\b(pros and cons|advantages and disadvantages|trade-?offs)\b',
        r'\b(recommend|suggestion|should I|what if)\b',
        r'\b(explain.*why|reasoning|rationale)\b',
        r'\b(multi|multiple|several|various)\b.*\b(apis?|endpoints?|methods?)\b',
    ]

    # Patterns that indicate simple queries
    SIMPLE_PATTERNS = [
        r'\b(what is|how to|how do I)\b.*\b(endpoint|api|authenticate)\b',
        r'\b(example|sample|code snippet)\b',
        r'\bdocumentation\b',
        r'\b(get|post|put|delete|patch)\b.*\brequest\b',
    ]

    # Technical terms that are straightforward lookups
    SIMPLE_TERMS = {
        'endpoint', 'authentication', 'api key', 'token', 'header',
        'request', 'response', 'status code', 'error code', 'parameter'
    }

    def __init__(self, complexity_threshold: float = None):
        """
        Initialize router

        Args:
            complexity_threshold: Threshold for using Claude (0-1)
        """
        self.complexity_threshold = complexity_threshold or settings.complexity_threshold

    def analyze_query(self, query: str) -> QueryAnalysis:
        """
        Analyze query complexity and determine routing

        Args:
            query: User query

        Returns:
            QueryAnalysis with recommendation
        """
        query_lower = query.lower()

        # Calculate complexity score
        complexity_score = self._calculate_complexity(query, query_lower)

        # Determine query type
        query_type = self._determine_query_type(query, query_lower)

        # Recommend model
        if complexity_score >= self.complexity_threshold:
            recommended_model = "claude"
            reasoning = "Complex query requiring nuanced understanding or comparison"
        else:
            recommended_model = "ollama"
            reasoning = "Straightforward query suitable for local model"

        return QueryAnalysis(
            complexity_score=complexity_score,
            query_type=query_type,
            recommended_model=recommended_model,
            reasoning=reasoning
        )

    def _calculate_complexity(self, query: str, query_lower: str) -> float:
        """Calculate complexity score for query"""
        score = 0.5  # Base score

        # Check for complex patterns
        complex_matches = sum(
            1 for pattern in self.COMPLEX_PATTERNS
            if re.search(pattern, query_lower)
        )
        score += complex_matches * 0.15

        # Check for simple patterns
        simple_matches = sum(
            1 for pattern in self.SIMPLE_PATTERNS
            if re.search(pattern, query_lower)
        )
        score -= simple_matches * 0.15

        # Query length factor (longer queries tend to be more complex)
        word_count = len(query.split())
        if word_count > 20:
            score += 0.15
        elif word_count < 8:
            score -= 0.1

        # Multiple questions
        if query.count('?') > 1:
            score += 0.2

        # Specific technical terms (simple lookups)
        simple_term_matches = sum(
            1 for term in self.SIMPLE_TERMS
            if term in query_lower
        )
        if simple_term_matches > 0:
            score -= 0.1

        # Contains code or technical syntax
        if any(char in query for char in ['{', '}', '<', '>', '//']):
            score -= 0.1

        # Clamp between 0 and 1
        return max(0.0, min(1.0, score))

    def _determine_query_type(self, query: str, query_lower: str) -> str:
        """Determine the type of query"""
        if re.search(r'\b(how to|how do i|how can i)\b', query_lower):
            return "how-to"
        elif re.search(r'\b(what is|what are|define)\b', query_lower):
            return "definition"
        elif re.search(r'\b(compare|difference|versus|vs)\b', query_lower):
            return "comparison"
        elif re.search(r'\b(example|sample|code)\b', query_lower):
            return "example"
        elif re.search(r'\b(why|reason|rationale)\b', query_lower):
            return "explanation"
        elif re.search(r'\b(should|recommend|best|which)\b', query_lower):
            return "recommendation"
        elif re.search(r'\b(error|issue|problem|fix|debug)\b', query_lower):
            return "troubleshooting"
        else:
            return "general"

    def should_use_claude(
        self,
        query: str,
        force_claude: Optional[bool] = None,
        ollama_failed: bool = False
    ) -> Tuple[bool, str]:
        """
        Determine whether to use Claude

        Args:
            query: User query
            force_claude: Force use of Claude
            ollama_failed: Whether Ollama failed to respond

        Returns:
            Tuple of (use_claude, reason)
        """
        if force_claude is True:
            return True, "User requested Claude"

        if force_claude is False:
            return False, "User requested Ollama"

        if ollama_failed:
            return True, "Fallback to Claude after Ollama failure"

        analysis = self.analyze_query(query)

        if analysis.recommended_model == "claude":
            return True, analysis.reasoning
        else:
            return False, analysis.reasoning


# Singleton instance
_router_service = None


def get_router_service() -> RouterService:
    """Get router service instance"""
    global _router_service
    if _router_service is None:
        _router_service = RouterService()
    return _router_service


if __name__ == "__main__":
    # Test the router
    router = RouterService(complexity_threshold=0.7)

    test_queries = [
        "How do I authenticate with the FedEx API?",
        "What's the tracking endpoint?",
        "Compare the authentication methods between Tracking and Shipping APIs",
        "Show me an example POST request for creating a shipment",
        "What are the pros and cons of using OAuth vs API keys?",
        "How should I design my microservices architecture for FedEx integration?",
        "What is the rate limit for the API?",
    ]

    for query in test_queries:
        analysis = router.analyze_query(query)
        print(f"\nQuery: {query}")
        print(f"Complexity: {analysis.complexity_score:.2f}")
        print(f"Type: {analysis.query_type}")
        print(f"Recommended: {analysis.recommended_model}")
        print(f"Reasoning: {analysis.reasoning}")
