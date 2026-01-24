"""
Main entry point for the scraper
Orchestrates scraping and chunking process
"""
import asyncio
import argparse
import logging
from pathlib import Path

from scraper import FedExScraper
from chunker import process_scraped_data

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def run_scraper(
    output_dir: str,
    max_pages: int,
    use_playwright: bool
):
    """Run the scraping process"""
    logger.info("Starting FedEx Developer Portal scraper...")

    scraper = FedExScraper(output_dir=output_dir)
    await scraper.scrape(max_pages=max_pages, use_playwright=use_playwright)

    logger.info("Scraping completed")


def run_chunker(scraped_file: str, output_file: str):
    """Run the chunking process"""
    logger.info(f"Chunking scraped data from {scraped_file}...")
    process_scraped_data(scraped_file, output_file)
    logger.info("Chunking completed")


def main():
    parser = argparse.ArgumentParser(
        description="Scrape and chunk FedEx Developer Portal documentation"
    )
    parser.add_argument(
        '--mode',
        choices=['scrape', 'chunk', 'all'],
        default='all',
        help='Operation mode: scrape only, chunk only, or both'
    )
    parser.add_argument(
        '--output-dir',
        default='scraped_data',
        help='Directory to save scraped data'
    )
    parser.add_argument(
        '--max-pages',
        type=int,
        default=50,
        help='Maximum number of pages to scrape'
    )
    parser.add_argument(
        '--no-playwright',
        action='store_true',
        help='Use requests instead of Playwright (faster but misses JS content)'
    )
    parser.add_argument(
        '--scraped-file',
        help='Input file for chunking (required if mode is chunk)'
    )
    parser.add_argument(
        '--chunked-file',
        default='chunked_data.json',
        help='Output file for chunked data'
    )

    args = parser.parse_args()

    # Create output directory
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)

    try:
        if args.mode in ['scrape', 'all']:
            # Run scraper
            asyncio.run(run_scraper(
                output_dir=args.output_dir,
                max_pages=args.max_pages,
                use_playwright=not args.no_playwright
            ))

            if args.mode == 'all':
                # Find the most recent scraped file
                scraped_files = list(Path(args.output_dir).glob('scraped_content_*.json'))
                if scraped_files:
                    latest_file = max(scraped_files, key=lambda p: p.stat().st_mtime)
                    args.scraped_file = str(latest_file)
                else:
                    logger.error("No scraped files found")
                    return

        if args.mode in ['chunk', 'all']:
            if not args.scraped_file:
                logger.error("--scraped-file required for chunk mode")
                return

            # Run chunker
            chunked_output = Path(args.output_dir) / args.chunked_file
            run_chunker(args.scraped_file, str(chunked_output))

        logger.info("All operations completed successfully!")

    except Exception as e:
        logger.error(f"Error during execution: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
