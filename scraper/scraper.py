"""
FedEx Developer Portal Scraper
Extracts API documentation and content from developer.fedex.com
"""
import asyncio
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse
from datetime import datetime

import aiohttp
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from markdownify import markdownify as md

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FedExScraper:
    """Scrapes documentation from FedEx Developer Portal"""

    BASE_URL = "https://developer.fedex.com"

    # Priority sections to scrape
    TARGET_SECTIONS = [
        "/api",
        "/docs",
        "/documentation",
        "/guides",
        "/reference",
        "/tutorials"
    ]

    def __init__(self, output_dir: str = "scraped_data"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.visited_urls = set()
        self.scraped_content = []

    async def scrape(self, max_pages: int = 100, use_playwright: bool = True):
        """
        Main scraping method

        Args:
            max_pages: Maximum number of pages to scrape
            use_playwright: Use Playwright for JS-rendered content
        """
        logger.info(f"Starting scrape of {self.BASE_URL}")

        if use_playwright:
            await self._scrape_with_playwright(max_pages)
        else:
            await self._scrape_with_requests(max_pages)

        self._save_results()
        logger.info(f"Scraping complete. Scraped {len(self.scraped_content)} pages")

    async def _scrape_with_playwright(self, max_pages: int):
        """Scrape using Playwright for JavaScript-rendered content"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            # Start with main API docs page
            await self._scrape_page_playwright(page, f"{self.BASE_URL}/api", max_pages)

            await browser.close()

    async def _scrape_page_playwright(self, page, url: str, max_pages: int):
        """Scrape individual page with Playwright"""
        if len(self.visited_urls) >= max_pages:
            return

        if url in self.visited_urls:
            return

        if not self._is_valid_url(url):
            return

        try:
            logger.info(f"Scraping: {url}")
            self.visited_urls.add(url)

            await page.goto(url, wait_until="networkidle", timeout=30000)
            content = await page.content()

            soup = BeautifulSoup(content, 'lxml')

            # Extract main content
            page_data = self._extract_page_content(soup, url)
            if page_data:
                self.scraped_content.append(page_data)

            # Find and follow relevant links
            links = await self._extract_links(page, soup)

            for link in links[:10]:  # Limit concurrent requests
                if len(self.visited_urls) < max_pages:
                    await self._scrape_page_playwright(page, link, max_pages)

        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")

    async def _scrape_with_requests(self, max_pages: int):
        """Scrape using aiohttp for static content"""
        async with aiohttp.ClientSession() as session:
            await self._scrape_page_requests(session, f"{self.BASE_URL}/api", max_pages)

    async def _scrape_page_requests(self, session, url: str, max_pages: int):
        """Scrape individual page with requests"""
        if len(self.visited_urls) >= max_pages:
            return

        if url in self.visited_urls:
            return

        if not self._is_valid_url(url):
            return

        try:
            logger.info(f"Scraping: {url}")
            self.visited_urls.add(url)

            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status != 200:
                    logger.warning(f"Failed to fetch {url}: {response.status}")
                    return

                html = await response.text()
                soup = BeautifulSoup(html, 'lxml')

                # Extract main content
                page_data = self._extract_page_content(soup, url)
                if page_data:
                    self.scraped_content.append(page_data)

                # Find and follow relevant links
                links = self._extract_links_simple(soup, url)

                tasks = []
                for link in links[:5]:
                    if len(self.visited_urls) < max_pages:
                        tasks.append(self._scrape_page_requests(session, link, max_pages))

                await asyncio.gather(*tasks)

        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")

    def _extract_page_content(self, soup: BeautifulSoup, url: str) -> Optional[Dict]:
        """Extract relevant content from page"""

        # Try to find main content area
        main_content = (
            soup.find('main') or
            soup.find('article') or
            soup.find('div', class_=lambda x: x and any(
                term in str(x).lower() for term in ['content', 'documentation', 'api-doc']
            ))
        )

        if not main_content:
            main_content = soup.find('body')

        if not main_content:
            return None

        # Extract title
        title = None
        if soup.find('h1'):
            title = soup.find('h1').get_text(strip=True)
        elif soup.find('title'):
            title = soup.find('title').get_text(strip=True)
        else:
            title = url.split('/')[-1].replace('-', ' ').title()

        # Remove script, style, nav elements
        for tag in main_content.find_all(['script', 'style', 'nav', 'footer', 'header']):
            tag.decompose()

        # Extract text content
        text_content = main_content.get_text(separator='\n', strip=True)

        # Convert to markdown for better structure preservation
        markdown_content = md(str(main_content))

        # Extract code snippets
        code_snippets = []
        for code_block in main_content.find_all(['code', 'pre']):
            code_text = code_block.get_text(strip=True)
            if len(code_text) > 20:  # Only meaningful code blocks
                code_snippets.append(code_text)

        # Extract metadata
        metadata = {
            'api_name': self._extract_api_name(soup, url),
            'category': self._extract_category(url),
            'endpoint': self._extract_endpoint(soup),
        }

        return {
            'url': url,
            'title': title,
            'content': text_content,
            'markdown': markdown_content,
            'code_snippets': code_snippets,
            'metadata': metadata,
            'scraped_at': datetime.utcnow().isoformat(),
            'word_count': len(text_content.split())
        }

    def _extract_api_name(self, soup: BeautifulSoup, url: str) -> Optional[str]:
        """Extract API name from page"""
        # Look for common patterns
        api_indicators = soup.find_all(string=lambda text: text and 'API' in text)
        if api_indicators:
            return api_indicators[0].strip()
        return None

    def _extract_category(self, url: str) -> str:
        """Extract category from URL"""
        path_parts = urlparse(url).path.split('/')
        if len(path_parts) > 2:
            return path_parts[1]
        return 'general'

    def _extract_endpoint(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract API endpoint if present"""
        # Look for code blocks containing HTTP methods
        for code in soup.find_all(['code', 'pre']):
            text = code.get_text()
            if any(method in text for method in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']):
                return text.strip()
        return None

    async def _extract_links(self, page, soup: BeautifulSoup) -> List[str]:
        """Extract relevant links from page"""
        links = []
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            full_url = urljoin(self.BASE_URL, href)

            if self._is_valid_url(full_url):
                links.append(full_url)

        return list(set(links))

    def _extract_links_simple(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract links without Playwright"""
        links = []
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            full_url = urljoin(base_url, href)

            if self._is_valid_url(full_url):
                links.append(full_url)

        return list(set(links))

    def _is_valid_url(self, url: str) -> bool:
        """Check if URL should be scraped"""
        parsed = urlparse(url)

        # Must be from FedEx developer domain
        if not parsed.netloc.endswith('developer.fedex.com'):
            return False

        # Skip unwanted paths
        skip_patterns = [
            '/login', '/signin', '/signup', '/register',
            '/logout', '/account', '/profile', '/settings',
            '.pdf', '.zip', '.png', '.jpg', '.jpeg', '.gif',
            '/search', '/contact'
        ]

        if any(pattern in url.lower() for pattern in skip_patterns):
            return False

        # Prefer documentation URLs
        priority_patterns = [
            '/api', '/docs', '/documentation', '/guide',
            '/reference', '/tutorial', '/rest'
        ]

        return any(pattern in url.lower() for pattern in priority_patterns)

    def _save_results(self):
        """Save scraped content to files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save as JSON
        json_file = self.output_dir / f"scraped_content_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(self.scraped_content, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved {len(self.scraped_content)} pages to {json_file}")

        # Save metadata
        metadata = {
            'scrape_date': datetime.utcnow().isoformat(),
            'total_pages': len(self.scraped_content),
            'total_words': sum(item['word_count'] for item in self.scraped_content),
            'urls_scraped': [item['url'] for item in self.scraped_content]
        }

        metadata_file = self.output_dir / f"metadata_{timestamp}.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Saved metadata to {metadata_file}")


async def main():
    """Run the scraper"""
    scraper = FedExScraper(output_dir="scraped_data")

    # Scrape with Playwright for JS-rendered content
    await scraper.scrape(max_pages=50, use_playwright=True)


if __name__ == "__main__":
    asyncio.run(main())
