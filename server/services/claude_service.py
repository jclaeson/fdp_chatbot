"""
Claude API service for enhanced responses
"""
import logging
from typing import Optional, List, Dict
from anthropic import AsyncAnthropic

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ClaudeService:
    """Service for interacting with Claude API"""

    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or settings.claude_api_key
        self.model = model or settings.claude_model

        if not self.api_key:
            logger.warning("Claude API key not configured")
            self.client = None
        else:
            self.client = AsyncAnthropic(api_key=self.api_key)

    def is_available(self) -> bool:
        """Check if Claude API is configured"""
        return self.client is not None

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> Optional[str]:
        """
        Generate response using Claude

        Args:
            prompt: User prompt
            system_prompt: System prompt
            temperature: Temperature for generation
            max_tokens: Max tokens to generate

        Returns:
            Generated text or None if error
        """
        if not self.is_available():
            logger.error("Claude API not configured")
            return None

        try:
            message_params = {
                "model": self.model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            }

            if system_prompt:
                message_params["system"] = system_prompt

            response = await self.client.messages.create(**message_params)

            return response.content[0].text

        except Exception as e:
            logger.error(f"Error calling Claude API: {e}")
            return None

    async def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> Optional[str]:
        """
        Chat completion using Claude

        Args:
            messages: List of message dicts with 'role' and 'content'
            system_prompt: System prompt
            temperature: Temperature for generation
            max_tokens: Max tokens to generate

        Returns:
            Generated response or None if error
        """
        if not self.is_available():
            logger.error("Claude API not configured")
            return None

        try:
            message_params = {
                "model": self.model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": messages
            }

            if system_prompt:
                message_params["system"] = system_prompt

            response = await self.client.messages.create(**message_params)

            return response.content[0].text

        except Exception as e:
            logger.error(f"Error calling Claude API: {e}")
            return None

    def create_rag_prompt(
        self,
        query: str,
        context: str,
        system_context: Optional[str] = None
    ) -> str:
        """
        Create RAG prompt with context for Claude

        Args:
            query: User query
            context: Retrieved context
            system_context: Optional system context

        Returns:
            Formatted prompt
        """
        base_system = """You are an expert assistant for FedEx API developers. Your role is to:
1. Answer questions accurately based on official FedEx documentation
2. Provide code examples and best practices when relevant
3. Explain API concepts clearly for developers of all skill levels
4. Cite source URLs for documentation references
5. Admit when information is not in the provided context

Be conversational but professional. Focus on practical, actionable guidance."""

        if system_context:
            base_system = system_context

        prompt = f"""Here is context from the FedEx Developer Portal documentation:

<context>
{context}
</context>

User's question: {query}

Please provide a comprehensive answer based on the context. Include:
- Direct answer to the question
- Relevant code examples or API endpoints if applicable
- Best practices or important considerations
- Links to the source documentation

If the context doesn't fully answer the question, acknowledge what's missing."""

        return prompt


# Singleton instance
_claude_service = None


def get_claude_service() -> ClaudeService:
    """Get Claude service instance"""
    global _claude_service
    if _claude_service is None:
        _claude_service = ClaudeService()
    return _claude_service
