"""
Ollama LLM service for local inference
"""
import logging
from typing import Optional, List, Dict
import httpx

from server.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class OllamaService:
    """Service for interacting with Ollama API"""

    def __init__(
        self,
        base_url: str = None,
        model: str = None
    ):
        self.base_url = base_url or settings.ollama_base_url
        self.model = model or settings.ollama_model
        self.timeout = 60.0

    async def is_available(self) -> bool:
        """Check if Ollama is running and accessible"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/tags",
                    timeout=5.0
                )
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama not available: {e}")
            return False

    async def is_model_available(self) -> bool:
        """Check if the configured model is available"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/tags",
                    timeout=5.0
                )

                if response.status_code == 200:
                    models = response.json().get('models', [])
                    model_names = [m['name'] for m in models]
                    return any(self.model in name for name in model_names)

                return False
        except Exception as e:
            logger.warning(f"Error checking model availability: {e}")
            return False

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> Optional[str]:
        """
        Generate response using Ollama

        Args:
            prompt: User prompt
            system_prompt: System prompt
            temperature: Temperature for generation
            max_tokens: Max tokens to generate

        Returns:
            Generated text or None if error
        """
        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens,
                    }
                }

                if system_prompt:
                    payload["system"] = system_prompt

                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    timeout=self.timeout
                )

                if response.status_code == 200:
                    result = response.json()
                    return result.get('response', '')
                else:
                    logger.error(f"Ollama API error: {response.status_code}")
                    return None

        except httpx.TimeoutException:
            logger.error("Ollama request timed out")
            return None
        except Exception as e:
            logger.error(f"Error calling Ollama: {e}")
            return None

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> Optional[str]:
        """
        Chat completion using Ollama

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Temperature for generation
            max_tokens: Max tokens to generate

        Returns:
            Generated response or None if error
        """
        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens,
                    }
                }

                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                    timeout=self.timeout
                )

                if response.status_code == 200:
                    result = response.json()
                    return result.get('message', {}).get('content', '')
                else:
                    logger.error(f"Ollama API error: {response.status_code}")
                    return None

        except httpx.TimeoutException:
            logger.error("Ollama request timed out")
            return None
        except Exception as e:
            logger.error(f"Error calling Ollama: {e}")
            return None

    def create_rag_prompt(
        self,
        query: str,
        context: str,
        system_context: Optional[str] = None
    ) -> str:
        """
        Create RAG prompt with context

        Args:
            query: User query
            context: Retrieved context
            system_context: Optional system context

        Returns:
            Formatted prompt
        """
        base_system = """You are a specialized assistant for the FedEx Developer Portal REST APIs.

CRITICAL GUIDELINES:
- ONLY provide information about FedEx REST APIs (NOT SOAP/Web Services)
- SOAP-based Web Services are DEPRECATED - never suggest or show SOAP code
- Focus on modern REST API endpoints from developer.fedex.com
- All code examples must use REST/JSON, not SOAP/XML
- Reference official FedEx REST API documentation only
- If the context doesn't contain the answer, say "I don't have information about that in the FedEx documentation"

Answer based on the provided context from the FedEx Developer Portal."""

        if system_context:
            base_system = system_context

        prompt = f"""{base_system}

Context from FedEx Developer Documentation:
{context}

User Question: {query}

Please provide a clear, accurate answer based on the context above. Include relevant code examples
or API endpoints when applicable. Cite the source URLs at the end of your response."""

        return prompt


# Singleton instance
_ollama_service = None


def get_ollama_service() -> OllamaService:
    """Get Ollama service instance"""
    global _ollama_service
    if _ollama_service is None:
        _ollama_service = OllamaService()
    return _ollama_service
