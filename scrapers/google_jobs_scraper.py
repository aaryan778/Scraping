"""
Google Jobs Scraper
This scraper uses Google's job search which aggregates jobs from:
- Indeed, LinkedIn, Glassdoor, ZipRecruiter, Monster, and many more
"""
import time
import json
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import hashlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GoogleJobsScraper:
    """Scraper for Google Jobs (aggregates multiple job boards)"""

    def __init__(self, headless: bool = True):
        """Initialize the scraper"""
        self.headless = headless
        self.driver = None
        self.jobs_data = []

    def setup_driver(self):
        """Set up Chrome driver with appropriate options"""
        chrome_options = Options()

        if self.headless:
            chrome_options.add_argument("--headless=new")

        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        logger.info("✅ Chrome driver initialized")

    def close_driver(self):
        """Close the driver"""
        if self.driver:
            self.driver.quit()
            logger.info("✅ Driver closed")

    def search_jobs(
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
        if not self.driver:
            self.setup_driver()

        jobs = []
        search_url = f"https://www.google.com/search?q={job_title.replace(' ', '+')}+jobs+{location.replace(' ', '+')}&ibp=htl;jobs"

        try:
            logger.info(f"🔍 Searching: {job_title} in {location}")
            self.driver.get(search_url)
            time.sleep(3)  # Wait for page load

            # Try to find and click "See more jobs" to load more results
            jobs_collected = 0
            scroll_attempts = 0
            max_scroll_attempts = 10

            while jobs_collected < max_jobs and scroll_attempts < max_scroll_attempts:
                try:
                    # Find all job cards
                    job_cards = self.driver.find_elements(By.CSS_SELECTOR, "li.iFjolb")

                    if not job_cards:
                        # Try alternative selector
                        job_cards = self.driver.find_elements(By.CSS_SELECTOR, "div.PwjeAc")

                    logger.info(f"📋 Found {len(job_cards)} job cards on page")

                    # Extract job details from each card
                    for card in job_cards[jobs_collected:]:
                        try:
                            # Click on the job card to load details
                            self.driver.execute_script("arguments[0].scrollIntoView(true);", card)
                            time.sleep(0.5)
                            card.click()
                            time.sleep(1.5)

                            job_data = self._extract_job_details()
                            if job_data:
                                job_data['search_query'] = job_title
                                job_data['search_location'] = location
                                jobs.append(job_data)
                                jobs_collected += 1
                                logger.info(f"✅ Scraped job {jobs_collected}/{max_jobs}: {job_data.get('title', 'Unknown')}")

                                if jobs_collected >= max_jobs:
                                    break

                        except Exception as e:
                            logger.warning(f"⚠️ Error extracting job card: {str(e)}")
                            continue

                    # Try to scroll or load more jobs
                    try:
                        # Scroll to bottom
                        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(2)

                        # Look for "Show more jobs" button
                        try:
                            more_button = self.driver.find_element(By.XPATH, "//span[contains(text(), 'Show more jobs')]")
                            self.driver.execute_script("arguments[0].click();", more_button)
                            time.sleep(2)
                        except NoSuchElementException:
                            pass

                    except Exception as e:
                        logger.warning(f"⚠️ Error scrolling: {str(e)}")

                    scroll_attempts += 1

                except Exception as e:
                    logger.error(f"❌ Error in scroll loop: {str(e)}")
                    break

            logger.info(f"✅ Total jobs scraped: {len(jobs)}")

        except Exception as e:
            logger.error(f"❌ Error searching jobs: {str(e)}")

        return jobs

    def _extract_job_details(self) -> Optional[Dict]:
        """Extract job details from the currently displayed job"""
        try:
            job_data = {}

            # Wait for job details to load
            wait = WebDriverWait(self.driver, 10)

            # Job Title
            try:
                title_element = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "h2.KLsYvd, div.sMJyQc"))
                )
                job_data['title'] = title_element.text.strip()
            except:
                job_data['title'] = "Unknown"

            # Company
            try:
                company_element = self.driver.find_element(By.CSS_SELECTOR, "div.nJlQNd.sMJyQc")
                job_data['company'] = company_element.text.strip()
            except:
                job_data['company'] = "Unknown"

            # Location
            try:
                location_element = self.driver.find_element(By.CSS_SELECTOR, "div.Qk80Jf")
                job_data['location'] = location_element.text.strip()
            except:
                job_data['location'] = "Unknown"

            # Job Description
            try:
                desc_element = self.driver.find_element(By.CSS_SELECTOR, "div.HBvzbc, div.YgLbBe")
                job_data['description'] = desc_element.text.strip()
            except:
                job_data['description'] = ""

            # Source URL
            try:
                apply_button = self.driver.find_element(By.CSS_SELECTOR, "a.pMhGee")
                job_data['source_url'] = apply_button.get_attribute('href')

                # Determine source platform from URL
                url = job_data['source_url'].lower()
                if 'linkedin' in url:
                    job_data['source_platform'] = 'LinkedIn'
                elif 'indeed' in url:
                    job_data['source_platform'] = 'Indeed'
                elif 'glassdoor' in url:
                    job_data['source_platform'] = 'Glassdoor'
                elif 'ziprecruiter' in url:
                    job_data['source_platform'] = 'ZipRecruiter'
                elif 'monster' in url:
                    job_data['source_platform'] = 'Monster'
                else:
                    job_data['source_platform'] = 'Other'
            except:
                job_data['source_url'] = ""
                job_data['source_platform'] = "Google Jobs"

            # Posted date
            try:
                date_elements = self.driver.find_elements(By.CSS_SELECTOR, "div.LL4CDc span")
                for elem in date_elements:
                    text = elem.text.lower()
                    if 'ago' in text or 'today' in text or 'yesterday' in text:
                        job_data['posted_date_text'] = text
                        job_data['posted_date'] = self._parse_posted_date(text)
                        break
            except:
                job_data['posted_date'] = None

            # Salary (if available)
            try:
                salary_elements = self.driver.find_elements(By.CSS_SELECTOR, "div.I2Cbhb")
                for elem in salary_elements:
                    text = elem.text
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
            job_data['remote'] = any(keyword in location_text or keyword in description_text
                                    for keyword in ['remote', 'work from home', 'wfh'])

            return job_data

        except Exception as e:
            logger.error(f"❌ Error extracting job details: {str(e)}")
            return None

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


# Example usage
if __name__ == "__main__":
    scraper = GoogleJobsScraper(headless=False)

    try:
        jobs = scraper.search_jobs(
            job_title="Python Developer",
            location="United States",
            max_jobs=10
        )

        print(f"\n✅ Scraped {len(jobs)} jobs")
        print(json.dumps(jobs[0], indent=2) if jobs else "No jobs found")

    finally:
        scraper.close_driver()
