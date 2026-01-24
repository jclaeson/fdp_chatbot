"""
FastAPI server for FedEx API Chatbot
Handles chat requests with intelligent routing between Ollama and Claude
"""
import sys
import logging
import time
from pathlib import Path
from datetime import datetime
from typing import Optional
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent / "rag"))

from config import get_settings
from models.schemas import (
    ChatRequest, ChatResponse, HealthResponse,
    QueryAnalysis, StatsResponse, Source
)
from services.ollama_service import get_ollama_service
from services.claude_service import get_claude_service
from services.router_service import get_router_service
from vectorstore import VectorStore
from retriever import Retriever

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Settings
settings = get_settings()

# Initialize FastAPI app
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description=settings.api_description
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global services
vector_store: Optional[VectorStore] = None
retriever: Optional[Retriever] = None
ollama_service = get_ollama_service()
claude_service = get_claude_service()
router_service = get_router_service()

# Simple in-memory stats
stats = {
    "total_queries": 0,
    "ollama_queries": 0,
    "claude_queries": 0,
    "total_response_time": 0.0
}


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global vector_store, retriever

    logger.info("Starting FedEx API Chatbot server...")

    # Initialize vector store
    try:
        vector_store = VectorStore(
            persist_directory=settings.chroma_persist_dir,
            collection_name=settings.chroma_collection_name
        )
        retriever = Retriever(
            vector_store=vector_store,
            top_k=settings.retrieval_top_k,
            similarity_threshold=settings.retrieval_similarity_threshold
        )
        logger.info(f"Vector store loaded with {vector_store.count()} documents")
    except Exception as e:
        logger.error(f"Failed to initialize vector store: {e}")
        logger.warning("Server starting without vector store")

    # Check Ollama availability
    if await ollama_service.is_available():
        if await ollama_service.is_model_available():
            logger.info(f"Ollama model '{settings.ollama_model}' is available")
        else:
            logger.warning(f"Ollama model '{settings.ollama_model}' not found. "
                          f"Pull it with: ollama pull {settings.ollama_model}")
    else:
        logger.warning("Ollama is not available. Start it with: ollama serve")

    # Check Claude availability
    if claude_service.is_available():
        logger.info("Claude API is configured")
    else:
        logger.warning("Claude API key not configured")

    logger.info("Server startup complete")


@app.get("/", tags=["General"])
async def root():
    """Root endpoint"""
    return {
        "message": "FedEx API Chatbot is running",
        "version": settings.api_version,
        "docs": "/docs"
    }


@app.get("/health", response_model=HealthResponse, tags=["General"])
async def health_check():
    """Health check endpoint"""
    services_status = {
        "ollama": "available" if await ollama_service.is_available() else "unavailable",
        "claude": "configured" if claude_service.is_available() else "not_configured",
        "vector_store": "available" if vector_store and vector_store.count() > 0 else "empty"
    }

    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(),
        services=services_status
    )


@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(request: ChatRequest):
    """
    Main chat endpoint with intelligent routing

    Automatically routes between Ollama (fast, free) and Claude (accurate, costs)
    based on query complexity.
    """
    start_time = time.time()

    try:
        # Generate or use conversation ID
        conversation_id = request.conversation_id or str(uuid.uuid4())

        # Analyze query for routing
        use_claude, routing_reason = router_service.should_use_claude(
            query=request.message,
            force_claude=request.use_claude
        )

        logger.info(f"Query routing: {routing_reason} -> {'Claude' if use_claude else 'Ollama'}")

        # Retrieve relevant context
        if retriever:
            context = retriever.retrieve_context(
                query=request.message,
                max_tokens=request.max_tokens // 2  # Leave room for response
            )
            sources = retriever.get_relevant_sources(
                query=request.message,
                max_sources=3
            )
        else:
            context = ""
            sources = []
            logger.warning("No retriever available, generating without context")

        # Try Ollama first (unless Claude is forced)
        response_text = None
        model_used = "none"

        if not use_claude:
            # Use Ollama
            if await ollama_service.is_available():
                if context:
                    prompt = ollama_service.create_rag_prompt(
                        query=request.message,
                        context=context
                    )
                else:
                    prompt = request.message

                response_text = await ollama_service.generate(
                    prompt=prompt,
                    max_tokens=request.max_tokens
                )

                if response_text:
                    model_used = f"ollama/{settings.ollama_model}"
                    stats["ollama_queries"] += 1
                else:
                    logger.warning("Ollama failed, falling back to Claude")
                    use_claude = True
            else:
                logger.warning("Ollama not available, using Claude")
                use_claude = True

        # Use Claude if needed
        if use_claude and not response_text:
            if claude_service.is_available():
                if context:
                    prompt = claude_service.create_rag_prompt(
                        query=request.message,
                        context=context
                    )
                else:
                    prompt = request.message

                response_text = await claude_service.generate(
                    prompt=prompt,
                    max_tokens=request.max_tokens
                )

                if response_text:
                    model_used = f"claude/{settings.claude_model}"
                    stats["claude_queries"] += 1
            else:
                raise HTTPException(
                    status_code=503,
                    detail="Neither Ollama nor Claude is available"
                )

        if not response_text:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate response"
            )

        # Calculate processing time
        processing_time = time.time() - start_time

        # Update stats
        stats["total_queries"] += 1
        stats["total_response_time"] += processing_time

        # Format sources
        source_models = [
            Source(
                title=s['title'],
                url=s['url'],
                relevance_score=s['score']
            )
            for s in sources
        ]

        return ChatResponse(
            message=response_text,
            conversation_id=conversation_id,
            model_used=model_used,
            sources=source_models,
            processing_time=round(processing_time, 2)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing chat request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze", response_model=QueryAnalysis, tags=["Chat"])
async def analyze_query(request: ChatRequest):
    """
    Analyze query complexity without generating a response

    Useful for understanding routing decisions
    """
    try:
        analysis = router_service.analyze_query(request.message)

        return QueryAnalysis(
            query=request.message,
            complexity_score=analysis.complexity_score,
            recommended_model=analysis.recommended_model,
            reasoning=analysis.reasoning,
            query_type=analysis.query_type
        )

    except Exception as e:
        logger.error(f"Error analyzing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats", response_model=StatsResponse, tags=["General"])
async def get_stats():
    """Get usage statistics"""
    avg_response_time = (
        stats["total_response_time"] / stats["total_queries"]
        if stats["total_queries"] > 0
        else 0.0
    )

    return StatsResponse(
        total_queries=stats["total_queries"],
        ollama_queries=stats["ollama_queries"],
        claude_queries=stats["claude_queries"],
        avg_response_time=round(avg_response_time, 2),
        documents_indexed=vector_store.count() if vector_store else 0
    )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload
    )
