"""
Pydantic models for API requests and responses
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class ChatMessage(BaseModel):
    """Chat message"""
    role: str = Field(..., description="Message role: user or assistant")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Chat request"""
    message: str = Field(..., description="User message")
    conversation_id: Optional[str] = Field(None, description="Conversation ID for context")
    use_claude: Optional[bool] = Field(None, description="Force use of Claude API")
    max_tokens: Optional[int] = Field(2000, description="Max tokens for response")


class Source(BaseModel):
    """Source document reference"""
    title: str
    url: str
    relevance_score: float


class ChatResponse(BaseModel):
    """Chat response"""
    message: str = Field(..., description="Assistant response")
    conversation_id: str = Field(..., description="Conversation ID")
    model_used: str = Field(..., description="Model used (ollama or claude)")
    sources: List[Source] = Field(default_factory=list, description="Source documents")
    processing_time: float = Field(..., description="Processing time in seconds")
    confidence_score: Optional[float] = Field(None, description="Response confidence")


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: datetime
    services: Dict[str, str]


class QueryAnalysis(BaseModel):
    """Query complexity analysis"""
    query: str
    complexity_score: float = Field(..., ge=0, le=1, description="Complexity score 0-1")
    recommended_model: str = Field(..., description="Recommended model")
    reasoning: str = Field(..., description="Why this model was chosen")
    query_type: str = Field(..., description="Type of query")


class StatsResponse(BaseModel):
    """Usage statistics"""
    total_queries: int
    ollama_queries: int
    claude_queries: int
    avg_response_time: float
    documents_indexed: int
    total_downloads: int
