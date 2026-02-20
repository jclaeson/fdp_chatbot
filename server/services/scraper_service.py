"""
Scraper service for admin-triggered documentation scraping
"""
import json
import logging
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ScrapeConfig(BaseModel):
    """Configuration for scraping FedEx Developer Portal"""
    start_urls: List[str] = [
        "https://developer.fedex.com/api/en-us/home.html",
        "https://developer.fedex.com/api/en-us/catalog.html"
    ]
    max_pages: int = 50
    max_depth: int = 3
    include_patterns: List[str] = ["/api/en-us/"]
    exclude_patterns: List[str] = [
        "web-services",
        "wsdl",
        "soap",
        "/es-",
        "/fr-",
        "developer.fedex.com/login"
    ]
    use_playwright: bool = True
    delay_ms: int = 1000


class ScrapeStatus(BaseModel):
    """Status of scraping job"""
    status: str  # idle, running, completed, failed
    progress: int  # 0-100
    pages_scraped: int
    total_pages: int
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None


class ScraperService:
    """Service for managing documentation scraping"""

    def __init__(self, config_file: Path = None, data_dir: Path = None):
        self.config_file = config_file or Path("scraper/config.json")
        self.data_dir = data_dir or Path("scraper/scraped_data")
        self.status_file = Path("scraper/scrape_status.json")
        self.scraper_script = Path("scraper/scraper.py")

        # Ensure directories exist
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Load or create config
        self.config = self._load_config()
        self.status = self._load_status()

        # Track running process
        self.process: Optional[asyncio.subprocess.Process] = None

    def _load_config(self) -> ScrapeConfig:
        """Load scrape configuration"""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                data = json.load(f)
                return ScrapeConfig(**data)
        else:
            # Create default config
            config = ScrapeConfig()
            self._save_config(config)
            return config

    def _save_config(self, config: ScrapeConfig):
        """Save scrape configuration"""
        with open(self.config_file, 'w') as f:
            json.dump(config.dict(), f, indent=2)

    def _load_status(self) -> ScrapeStatus:
        """Load scrape status"""
        if self.status_file.exists():
            with open(self.status_file, 'r') as f:
                data = json.load(f)
                return ScrapeStatus(**data)
        else:
            return ScrapeStatus(
                status="idle",
                progress=0,
                pages_scraped=0,
                total_pages=0
            )

    def _save_status(self, status: ScrapeStatus):
        """Save scrape status"""
        with open(self.status_file, 'w') as f:
            json.dump(status.dict(), f, indent=2)

    def get_config(self) -> Dict:
        """Get current scrape configuration"""
        return self.config.dict()

    def update_config(self, config_data: Dict) -> ScrapeConfig:
        """Update scrape configuration"""
        self.config = ScrapeConfig(**config_data)
        self._save_config(self.config)
        logger.info(f"Scrape config updated: {config_data}")
        return self.config

    def get_status(self) -> Dict:
        """Get current scrape status"""
        return self.status.dict()

    async def start_scrape(self) -> Dict:
        """Start scraping process"""
        if self.status.status == "running":
            return {"error": "Scrape already running"}

        if not self.scraper_script.exists():
            return {"error": f"Scraper script not found: {self.scraper_script}"}

        # Update status
        self.status = ScrapeStatus(
            status="running",
            progress=0,
            pages_scraped=0,
            total_pages=self.config.max_pages,
            started_at=datetime.now().isoformat()
        )
        self._save_status(self.status)

        # Start scraper process in background
        asyncio.create_task(self._run_scraper())

        logger.info("Scraping started")
        return {"status": "started", "message": "Scraping in progress"}

    async def _run_scraper(self):
        """Run the scraper script"""
        try:
            # Build command with config
            cmd = [
                "python",
                str(self.scraper_script),
                "--start-urls", *self.config.start_urls,
                "--max-pages", str(self.config.max_pages),
                "--max-depth", str(self.config.max_depth),
                "--output-dir", str(self.data_dir),
            ]

            if not self.config.use_playwright:
                cmd.append("--no-playwright")

            logger.info(f"Running scraper: {' '.join(cmd)}")

            # Run process
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            self.process = process

            # Wait for completion
            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                # Success
                self.status = ScrapeStatus(
                    status="completed",
                    progress=100,
                    pages_scraped=self.config.max_pages,
                    total_pages=self.config.max_pages,
                    started_at=self.status.started_at,
                    completed_at=datetime.now().isoformat()
                )
                logger.info("Scraping completed successfully")
            else:
                # Failed
                error_msg = stderr.decode() if stderr else "Unknown error"
                self.status = ScrapeStatus(
                    status="failed",
                    progress=0,
                    pages_scraped=0,
                    total_pages=self.config.max_pages,
                    started_at=self.status.started_at,
                    completed_at=datetime.now().isoformat(),
                    error=error_msg
                )
                logger.error(f"Scraping failed: {error_msg}")

            self._save_status(self.status)

        except Exception as e:
            logger.error(f"Scraper error: {e}", exc_info=True)
            self.status = ScrapeStatus(
                status="failed",
                progress=0,
                pages_scraped=0,
                total_pages=self.config.max_pages,
                error=str(e)
            )
            self._save_status(self.status)

    async def trigger_ingestion(self) -> Dict:
        """Trigger ingestion of scraped data"""
        try:
            ingest_script = Path("rag/ingest_fedex_docs.py")

            if not ingest_script.exists():
                return {"error": f"Ingestion script not found: {ingest_script}"}

            # Check for scraped data
            scraped_files = list(self.data_dir.glob("scraped_content_*.json"))
            if not scraped_files:
                return {"error": "No scraped data found. Run scrape first."}

            logger.info("Starting ingestion...")

            # Run ingestion
            process = await asyncio.create_subprocess_exec(
                "python",
                str(ingest_script),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                logger.info("Ingestion completed successfully")
                return {
                    "status": "success",
                    "message": "Documentation ingested into vector store",
                    "output": stdout.decode()
                }
            else:
                error_msg = stderr.decode() if stderr else "Unknown error"
                logger.error(f"Ingestion failed: {error_msg}")
                return {
                    "status": "failed",
                    "error": error_msg
                }

        except Exception as e:
            logger.error(f"Ingestion error: {e}", exc_info=True)
            return {"status": "failed", "error": str(e)}


# Singleton instance
_scraper_service: Optional[ScraperService] = None


def get_scraper_service() -> ScraperService:
    """Get or create scraper service instance"""
    global _scraper_service

    if _scraper_service is None:
        _scraper_service = ScraperService()

    return _scraper_service
