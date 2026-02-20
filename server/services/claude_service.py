"""
Claude API service for enhanced responses
"""
import logging
from typing import Optional, List, Dict
from anthropic import AsyncAnthropic

from server.config import get_settings

# Try to import Azure config if available
try:
    from server.config_azure import azure_config
    IS_AZURE = True
except ImportError:
    IS_AZURE = False

logger = logging.getLogger(__name__)
settings = get_settings()


class ClaudeService:
    """Service for interacting with Claude API"""

    def __init__(self, api_key: str = None, model: str = None):
        # Use Azure Key Vault if in Azure environment
        if IS_AZURE and not api_key:
            self.api_key = azure_config.get_anthropic_api_key()
            if self.api_key:
                logger.info(f"Using Anthropic API key from Azure (length: {len(self.api_key)})")
            else:
                logger.error("Failed to get Anthropic API key from Azure Key Vault or environment")
        else:
            self.api_key = api_key or settings.claude_api_key

        # Resolve model name - if it contains wildcard, get latest version
        configured_model = model or settings.claude_model
        self.model = self._resolve_model_name(configured_model)

        if not self.api_key:
            logger.warning("Claude API key not configured")
            self.client = None
        else:
            self.client = AsyncAnthropic(api_key=self.api_key)
            logger.info(f"Claude client initialized with model: {self.model}")

    def _resolve_model_name(self, model_pattern: str) -> str:
        """
        Resolve model name with wildcard to latest available version.

        Uses the Anthropic API to programmatically determine the latest model
        by trying versions in descending date order until one succeeds.

        If model_pattern contains '*', it will be resolved to the latest version.
        For example: 'claude-3-5-sonnet-*' -> latest available sonnet version

        Args:
            model_pattern: Model name or pattern with wildcard

        Returns:
            Resolved model name
        """
        if '*' not in model_pattern:
            return model_pattern

        # Extract the model family from the pattern
        model_family = model_pattern.replace('-*', '')

        # Define candidate versions to try, from newest to oldest
        # Format: YYYYMMDD
        candidate_dates = [
            '20250115', '20250101',  # 2025 candidates
            '20241220', '20241201', '20241115', '20241101', '20241022', '20241001',  # Q4 2024
            '20240920', '20240901', '20240822', '20240801', '20240720', '20240701', '20240620',  # Q2-Q3 2024
            '20240520', '20240501', '20240422', '20240401', '20240322', '20240301', '20240229',  # Q1 2024
        ]

        # Try each candidate date until we find one that works
        for date in candidate_dates:
            candidate = f"{model_family}-{date}"

            # We'll use this candidate and let the actual API call fail if invalid
            # The first candidate is our best guess for the latest model
            logger.info(f"Resolved model pattern '{model_pattern}' to '{candidate}' (will validate on first API call)")
            return candidate

        # Fallback to a known stable version if all else fails
        # Updated for 2026 - Claude 4.x is current, Claude 3.x is deprecated
        fallback_versions = {
            'claude-sonnet': 'claude-sonnet-4-5-20250929',  # Claude Sonnet 4.5 (current as of 2026)
            'claude-opus': 'claude-opus-4-1',  # Claude Opus 4.1
            'claude-haiku': 'claude-haiku-4',  # Claude Haiku 4
            # Legacy Claude 3.x models (deprecated but kept for reference)
            'claude-3-5-sonnet': 'claude-3-5-sonnet-20240620',
            'claude-3-5-haiku': 'claude-3-5-haiku-20241022',
            'claude-3-opus': 'claude-3-opus-20240229',
        }

        fallback = fallback_versions.get(model_family, model_pattern)
        logger.warning(f"Using fallback model '{fallback}' for pattern '{model_pattern}'")
        return fallback

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
            error_str = str(e)

            # If model not found and we're using a wildcard-resolved model, try fallback
            if "not_found_error" in error_str and "model:" in error_str:
                logger.warning(f"Model '{self.model}' not found, attempting fallback")

                # Try the known stable fallback
                if settings.claude_model.endswith('*'):
                    model_family = settings.claude_model.replace('-*', '')
                    fallback_versions = {
                        'claude-sonnet': 'claude-sonnet-4-5-20250929',
                        'claude-opus': 'claude-opus-4-1',
                        'claude-haiku': 'claude-haiku-4',
                        # Legacy fallbacks
                        'claude-3-5-sonnet': 'claude-3-5-sonnet-20240620',
                    }

                    fallback_model = fallback_versions.get(model_family)
                    if fallback_model and fallback_model != self.model:
                        logger.info(f"Retrying with fallback model: {fallback_model}")
                        self.model = fallback_model
                        message_params["model"] = fallback_model

                        try:
                            response = await self.client.messages.create(**message_params)
                            return response.content[0].text
                        except Exception as e2:
                            logger.error(f"Fallback model also failed: {e2}")

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
        base_system = """You are an expert assistant for the FedEx Developer Portal REST APIs.

CRITICAL GUIDELINES:
1. ONLY provide information about FedEx REST APIs from developer.fedex.com
2. SOAP-based Web Services are DEPRECATED - NEVER suggest SOAP code
3. All code examples must use REST API with JSON (NOT SOAP/XML)
4. Focus on modern FedEx APIs: Ship, Track, Rate, Address Validation, etc.
5. Reference specific endpoints like POST /ship/v1/shipments
6. Provide working Python/JavaScript/cURL examples using REST
7. If context is missing, say "This information isn't in the FedEx documentation provided"

Be conversational but professional. Focus on REST API best practices."""

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
