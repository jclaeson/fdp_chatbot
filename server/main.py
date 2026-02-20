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

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
import zipfile
import io

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent / "rag"))

from server.config import get_settings
from server.models.schemas import (
    ChatRequest, ChatResponse, HealthResponse,
    QueryAnalysis, StatsResponse, Source
)
from server.services.ollama_service import get_ollama_service
from server.services.claude_service import get_claude_service
from server.services.router_service import get_router_service
from server.admin_stats import stats_tracker
from server.services.scraper_service import get_scraper_service
from rag.vectorstore import VectorStore
from rag.retriever import Retriever

# Try to import Azure config if available
try:
    from config_azure import azure_config
    IS_AZURE = True
except ImportError:
    IS_AZURE = False

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
scraper_service = get_scraper_service()

# Simple in-memory stats
stats = {
    "total_queries": 0,
    "ollama_queries": 0,
    "claude_queries": 0,
    "total_response_time": 0.0,
    "total_downloads": 0
}

# Persistent storage file for downloads
if IS_AZURE:
    DOWNLOADS_FILE = azure_config.app_data_dir / "downloads_count.txt"
else:
    DOWNLOADS_FILE = Path("downloads_count.txt")


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global vector_store, retriever

    logger.info("Starting FedEx API Chatbot server...")

    if IS_AZURE:
        logger.info("Running in Azure environment")
        logger.info(f"Chroma persist directory: {azure_config.chroma_persist_dir}")
        logger.info(f"App data directory: {azure_config.app_data_dir}")

    # Load download count from persistent storage
    if DOWNLOADS_FILE.exists():
        try:
            with open(DOWNLOADS_FILE, 'r') as f:
                stats["total_downloads"] = int(f.read().strip())
            logger.info(f"Loaded {stats['total_downloads']} total downloads")
        except Exception as e:
            logger.warning(f"Could not load download count: {e}")

    # Initialize vector store
    try:
        persist_dir = azure_config.chroma_persist_dir if IS_AZURE else settings.chroma_persist_dir
        vector_store = VectorStore(
            persist_directory=str(persist_dir),
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
async def chat(chat_request: ChatRequest, request: Request):
    """
    Main chat endpoint with intelligent routing

    Automatically routes between Ollama (fast, free) and Claude (accurate, costs)
    based on query complexity.
    """
    start_time = time.time()
    user_ip = request.client.host if request.client else "unknown"

    try:
        # Generate or use conversation ID
        conversation_id = chat_request.conversation_id or str(uuid.uuid4())

        # Analyze query for routing
        use_claude, routing_reason = router_service.should_use_claude(
            query=chat_request.message,
            force_claude=chat_request.use_claude
        )

        logger.info(f"Query routing: {routing_reason} -> {'Claude' if use_claude else 'Ollama'}")

        # Retrieve relevant context
        if retriever:
            context = retriever.retrieve_context(
                query=chat_request.message,
                max_tokens=chat_request.max_tokens // 2  # Leave room for response
            )
            sources = retriever.get_relevant_sources(
                query=chat_request.message,
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
                        query=chat_request.message,
                        context=context
                    )
                else:
                    prompt = chat_request.message

                response_text = await ollama_service.generate(
                    prompt=prompt,
                    max_tokens=chat_request.max_tokens
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
                        query=chat_request.message,
                        context=context
                    )
                else:
                    prompt = chat_request.message

                response_text = await claude_service.generate(
                    prompt=prompt,
                    max_tokens=chat_request.max_tokens
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

        # Track request for admin dashboard
        stats_tracker.track_request(
            user_ip=user_ip,
            query=chat_request.message,
            model=model_used,
            response_time=processing_time,
            status="success"
        )

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
async def analyze_query(analyze_request: ChatRequest):
    """
    Analyze query complexity without generating a response

    Useful for understanding routing decisions
    """
    try:
        analysis = router_service.analyze_query(analyze_request.message)

        return QueryAnalysis(
            query=analyze_request.message,
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
        documents_indexed=vector_store.count() if vector_store else 0,
        total_downloads=stats["total_downloads"]
    )


@app.post("/track-download", tags=["General"])
async def track_download():
    """Track extension download"""
    stats["total_downloads"] += 1

    # Persist to file
    try:
        with open(DOWNLOADS_FILE, 'w') as f:
            f.write(str(stats["total_downloads"]))
    except Exception as e:
        logger.error(f"Failed to persist download count: {e}")

    return {"downloads": stats["total_downloads"]}


@app.get("/api/admin/stats", tags=["Admin"])
async def get_admin_stats():
    """Get detailed statistics for admin dashboard"""
    return stats_tracker.get_stats()


@app.get("/api/admin/recent-queries", tags=["Admin"])
async def get_recent_queries(limit: int = 50):
    """Get recent queries with metadata"""
    return stats_tracker.get_recent_queries(limit=limit)


@app.get("/api/download-extension", tags=["Extension"])
async def download_extension():
    """Download Chrome extension as ZIP"""
    try:
        # Use absolute path in container
        extension_dir = Path("/app/extension")

        # Fallback to relative path for local development
        if not extension_dir.exists():
            extension_dir = Path("extension")

        if not extension_dir.exists():
            raise HTTPException(status_code=404, detail="Extension not found")

        # Create ZIP in memory
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for file_path in extension_dir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(extension_dir)
                    zip_file.write(file_path, arcname)

        zip_buffer.seek(0)

        # Track download
        stats["total_downloads"] += 1
        save_downloads_count()

        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=fedex-api-assistant.zip"}
        )

    except Exception as e:
        logger.error(f"Extension download failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create extension package")


@app.post("/api/track-login", tags=["Admin"])
async def track_login():
    """Track a login event"""
    stats_tracker.track_login()
    return {"status": "ok"}


@app.post("/api/track-admin-login", tags=["Admin"])
async def track_admin_login():
    """Track an admin login event"""
    logger.info("Admin login recorded")
    return {"status": "ok"}


@app.get("/api/admin/scraper/config", tags=["Admin"])
async def get_scraper_config():
    """Get current scraper configuration"""
    return scraper_service.get_config()


@app.post("/api/admin/scraper/config", tags=["Admin"])
async def update_scraper_config(config: dict):
    """Update scraper configuration"""
    try:
        updated_config = scraper_service.update_config(config)
        return {"status": "success", "config": updated_config.dict()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/admin/scraper/status", tags=["Admin"])
async def get_scraper_status():
    """Get current scraper status"""
    return scraper_service.get_status()


@app.post("/api/admin/scraper/start", tags=["Admin"])
async def start_scraper():
    """Start scraping FedEx Developer Portal"""
    result = await scraper_service.start_scrape()
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.post("/api/admin/scraper/ingest", tags=["Admin"])
async def trigger_ingestion():
    """Trigger ingestion of scraped data into vector store"""
    result = await scraper_service.trigger_ingestion()
    if result.get("status") == "failed":
        raise HTTPException(status_code=500, detail=result.get("error", "Ingestion failed"))
    return result


@app.post("/api/admin/restart", tags=["Admin"])
async def restart_server():
    """
    Restart the server (note: this requires process manager like systemd or pm2)
    This endpoint only works if the server is run with auto-restart enabled
    """
    import os
    import signal

    logger.info("Server restart requested via admin dashboard")

    # Note: This will kill the current process
    # The process manager should auto-restart it
    os.kill(os.getpid(), signal.SIGTERM)

    return {"status": "restarting"}


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
