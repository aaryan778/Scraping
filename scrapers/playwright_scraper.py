"""
Playwright-based Google Jobs Scraper
Faster and more reliable than Selenium with built-in rate limiting and user agent rotation
"""
import asyncio
import random
import time
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import hashlib
import os

from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeout
from fake_useragent import UserAgent
from loguru import logger
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

load_dotenv()


class PlaywrightJobsScraper:
    """Playwright-based scraper with rate limiting and user agent rotation"""

    def __init__(self):
        """Initialize scraper"""
        self.headless = os.getenv("HEADLESS_BROWSER", "true").lower() == "true"
        self.rate_limit_min = float(os.getenv("RATE_LIMIT_DELAY_MIN", "2"))
        self.rate_limit_max = float(os.getenv("RATE_LIMIT_DELAY_MAX", "5"))
        self.request_timeout = int(os.getenv("REQUEST_TIMEOUT", "30")) * 1000  # Convert to ms
        self.max_retries = int(os.getenv("MAX_RETRIES", "3"))
        self.rotate_user_agents = os.getenv("ROTATE_USER_AGENTS", "true").lower() == "true"

        # User agent rotation
        self.ua = UserAgent() if self.rotate_user_agents else None
        self.browser: Optional[Browser] = None
        self.playwright = None

        logger.info(
            f"✅ Playwright scraper initialized "
            f"(headless={self.headless}, rate_limit={self.rate_limit_min}-{self.rate_limit_max}s)"
        )

    async def __aenter__(self):
        """Async context manager entry"""
        await self.setup()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    async def setup(self):
        """Setup Playwright browser"""
        try:
            self.playwright = await async_playwright().start()

            # Launch browser
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled'
                ]
            )

            logger.info("✅ Playwright browser launched")

        except Exception as e:
            logger.error(f"❌ Error setting up Playwright: {e}")
            raise

    async def close(self):
        """Close browser and playwright"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("✅ Playwright browser closed")

    def _get_user_agent(self) -> str:
        """Get random user agent"""
        if self.rotate_user_agents and self.ua:
            return self.ua.random
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    async def _rate_limit_delay(self):
        """Apply random rate limiting delay"""
        delay = random.uniform(self.rate_limit_min, self.rate_limit_max)
        logger.debug(f"⏱️ Rate limiting: {delay:.2f}s delay")
        await asyncio.sleep(delay)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def search_jobs(
        self,
        job_title: str,
        location: str = "United States",
        max_jobs: int = 50
    ) -> List[Dict]:
        """
        Search for jobs on Google Jobs

        Args:
            job_title: Job title to search for
            location: Location to search in
            max_jobs: Maximum number of jobs to scrape

        Returns:
            List of job dictionaries
        """
        if not self.browser:
            await self.setup()

        jobs = []
        search_url = self._build_search_url(job_title, location)

        try:
            # Create new context with random user agent
            context = await self.browser.new_context(
                user_agent=self._get_user_agent(),
                viewport={'width': 1920, 'height': 1080}
            )

            # Create new page
            page = await context.new_page()

            # Block unnecessary resources for speed
            await page.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "stylesheet", "font", "media"] else route.continue_())

            logger.info(f"🔍 Searching: {job_title} in {location}")

            # Navigate to search results
            await page.goto(search_url, timeout=self.request_timeout, wait_until="domcontentloaded")
            await self._rate_limit_delay()

            # Wait for job listings to load
            try:
                await page.wait_for_selector("li.iFjolb, div.PwjeAc", timeout=10000)
            except PlaywrightTimeout:
                logger.warning("⚠️ Job listings not found, page may have changed structure")
                await context.close()
                return []

            # Scroll and collect jobs
            jobs_collected = 0
            scroll_attempts = 0
            max_scroll_attempts = 10

            while jobs_collected < max_jobs and scroll_attempts < max_scroll_attempts:
                # Get job cards
                job_cards = await page.query_selector_all("li.iFjolb")

                if not job_cards:
                    job_cards = await page.query_selector_all("div.PwjeAc")

                logger.debug(f"📋 Found {len(job_cards)} job cards on page")

                # Process each job card
                for i, card in enumerate(job_cards[jobs_collected:]):
                    if jobs_collected >= max_jobs:
                        break

                    try:
                        # Scroll card into view and click
                        await card.scroll_into_view_if_needed()
                        await asyncio.sleep(0.5)
                        await card.click()
                        await asyncio.sleep(1.5)  # Wait for details to load

                        # Extract job details
                        job_data = await self._extract_job_details(page)

                        if job_data:
                            job_data['search_query'] = job_title
                            job_data['search_location'] = location
                            jobs.append(job_data)
                            jobs_collected += 1

                            logger.info(
                                f"✅ Scraped job {jobs_collected}/{max_jobs}: "
                                f"{job_data.get('title', 'Unknown')} @ {job_data.get('company', 'Unknown')}"
                            )

                            # Rate limit between jobs
                            await self._rate_limit_delay()

                    except Exception as e:
                        logger.warning(f"⚠️ Error processing job card {i}: {e}")
                        continue

                # Try to load more jobs
                try:
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(2)

                    # Look for "Show more jobs" button
                    try:
                        more_button = await page.query_selector("text='Show more jobs'")
                        if more_button:
                            await more_button.click()
                            await asyncio.sleep(2)
                    except:
                        pass

                except Exception as e:
                    logger.debug(f"Scroll error: {e}")

                scroll_attempts += 1

            await context.close()
            logger.info(f"✅ Total jobs scraped: {len(jobs)}")

        except Exception as e:
            logger.error(f"❌ Error searching jobs: {e}")
            raise

        return jobs

    async def _extract_job_details(self, page: Page) -> Optional[Dict]:
        """
        Extract job details from currently displayed job

        Args:
            page: Playwright page object

        Returns:
            Job data dictionary or None
        """
        try:
            job_data = {}

            # Job Title
            try:
                title_elem = await page.query_selector("h2.KLsYvd, div.sMJyQc")
                if title_elem:
                    job_data['title'] = (await title_elem.text_content()).strip()
                else:
                    job_data['title'] = "Unknown"
            except:
                job_data['title'] = "Unknown"

            # Company
            try:
                company_elem = await page.query_selector("div.nJlQNd.sMJyQc")
                if company_elem:
                    job_data['company'] = (await company_elem.text_content()).strip()
                else:
                    job_data['company'] = "Unknown"
            except:
                job_data['company'] = "Unknown"

            # Location
            try:
                location_elem = await page.query_selector("div.Qk80Jf")
                if location_elem:
                    job_data['location'] = (await location_elem.text_content()).strip()
                else:
                    job_data['location'] = "Unknown"
            except:
                job_data['location'] = "Unknown"

            # Job Description
            try:
                desc_elem = await page.query_selector("div.HBvzbc, div.YgLbBe")
                if desc_elem:
                    job_data['description'] = (await desc_elem.text_content()).strip()
                else:
                    job_data['description'] = ""
            except:
                job_data['description'] = ""

            # Source URL and Platform
            try:
                apply_button = await page.query_selector("a.pMhGee")
                if apply_button:
                    source_url = await apply_button.get_attribute('href')
                    job_data['source_url'] = source_url

                    # Determine platform from URL
                    url_lower = source_url.lower()
                    if 'linkedin' in url_lower:
                        job_data['source_platform'] = 'LinkedIn'
                    elif 'indeed' in url_lower:
                        job_data['source_platform'] = 'Indeed'
                    elif 'glassdoor' in url_lower:
                        job_data['source_platform'] = 'Glassdoor'
                    elif 'ziprecruiter' in url_lower:
                        job_data['source_platform'] = 'ZipRecruiter'
                    elif 'monster' in url_lower:
                        job_data['source_platform'] = 'Monster'
                    else:
                        job_data['source_platform'] = 'Other'
                else:
                    job_data['source_url'] = ""
                    job_data['source_platform'] = "Google Jobs"
            except:
                job_data['source_url'] = ""
                job_data['source_platform'] = "Google Jobs"

            # Posted date
            try:
                date_elements = await page.query_selector_all("div.LL4CDc span")
                for elem in date_elements:
                    text = (await elem.text_content()).lower()
                    if 'ago' in text or 'today' in text or 'yesterday' in text:
                        job_data['posted_date_text'] = text
                        job_data['posted_date'] = self._parse_posted_date(text)
                        break
            except:
                job_data['posted_date'] = None

            # Salary (if available)
            try:
                salary_elements = await page.query_selector_all("div.I2Cbhb")
                for elem in salary_elements:
                    text = await elem.text_content()
                    if '$' in text or 'USD' in text:
                        job_data['salary_text'] = text
                        break
            except:
                pass

            # Generate unique job ID
            job_data['job_id'] = self._generate_job_id(job_data)
            job_data['scraped_date'] = datetime.utcnow().isoformat()

            # Check if remote
            location_text = job_data.get('location', '').lower()
            description_text = job_data.get('description', '').lower()
            job_data['remote'] = any(
                keyword in location_text or keyword in description_text
                for keyword in ['remote', 'work from home', 'wfh', 'telecommute']
            )

            return job_data

        except Exception as e:
            logger.error(f"❌ Error extracting job details: {e}")
            return None

    def _build_search_url(self, job_title: str, location: str) -> str:
        """Build Google Jobs search URL"""
        job_query = job_title.replace(' ', '+')
        location_query = location.replace(' ', '+')
        return f"https://www.google.com/search?q={job_query}+jobs+{location_query}&ibp=htl;jobs"

    def _generate_job_id(self, job_data: Dict) -> str:
        """Generate unique job ID from job data"""
        unique_string = f"{job_data.get('title', '')}-{job_data.get('company', '')}-{job_data.get('location', '')}"
        return hashlib.md5(unique_string.encode()).hexdigest()

    def _parse_posted_date(self, date_text: str) -> datetime:
        """Parse posted date from text like '2 days ago', 'today', etc."""
        date_text = date_text.lower()
        now = datetime.utcnow()

        if 'today' in date_text or 'just now' in date_text:
            return now
        elif 'yesterday' in date_text:
            return now - timedelta(days=1)
        elif 'hour' in date_text:
            hours = int(''.join(filter(str.isdigit, date_text)) or 1)
            return now - timedelta(hours=hours)
        elif 'day' in date_text:
            days = int(''.join(filter(str.isdigit, date_text)) or 1)
            return now - timedelta(days=days)
        elif 'week' in date_text:
            weeks = int(''.join(filter(str.isdigit, date_text)) or 1)
            return now - timedelta(weeks=weeks)
        elif 'month' in date_text:
            months = int(''.join(filter(str.isdigit, date_text)) or 1)
            return now - timedelta(days=months * 30)

        return now


# Synchronous wrapper for backwards compatibility
async def scrape_jobs_async(job_title: str, location: str, max_jobs: int = 50) -> List[Dict]:
    """
    Async function to scrape jobs

    Args:
        job_title: Job title to search
        location: Location to search
        max_jobs: Maximum jobs to scrape

    Returns:
        List of job dictionaries
    """
    async with PlaywrightJobsScraper() as scraper:
        return await scraper.search_jobs(job_title, location, max_jobs)


def scrape_jobs(job_title: str, location: str, max_jobs: int = 50) -> List[Dict]:
    """
    Synchronous wrapper for scraping jobs

    Args:
        job_title: Job title to search
        location: Location to search
        max_jobs: Maximum jobs to scrape

    Returns:
        List of job dictionaries
    """
    return asyncio.run(scrape_jobs_async(job_title, location, max_jobs))


# Example usage
if __name__ == "__main__":
    import json

    # Test scraping
    jobs = scrape_jobs("Python Developer", "United States", max_jobs=5)

    print(f"\n✅ Scraped {len(jobs)} jobs")
    if jobs:
        print(json.dumps(jobs[0], indent=2))
