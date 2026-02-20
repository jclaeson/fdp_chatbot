"""
Configuration management
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings"""

    # API Settings
    api_title: str = "FedEx API Chatbot"
    api_version: str = "1.0.0"
    api_description: str = "RAG-powered chatbot for FedEx Developer Portal"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "mistral"  # or llama3.1, codellama

    # Claude API
    claude_api_key: str = ""
    claude_model: str = "claude-sonnet-*"  # Auto-resolves to latest Sonnet version

    # Vector Store
    chroma_persist_dir: str = "../rag/chroma_db"
    chroma_collection_name: str = "fedex_docs"

    # Retrieval
    retrieval_top_k: int = 5
    retrieval_similarity_threshold: float = 0.5

    # Routing Strategy
    use_intelligent_routing: bool = True
    complexity_threshold: float = 0.7  # 0-1, queries above this use Claude
    max_ollama_retries: int = 2

    # CORS
    cors_origins: list = ["*"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
