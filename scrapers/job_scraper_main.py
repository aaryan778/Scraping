"""
Main Job Scraping Orchestrator
Coordinates scraping, processing, and database storage
"""
import json
import logging
import time
from datetime import datetime
from typing import List, Dict
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from scrapers.google_jobs_scraper import GoogleJobsScraper
from processors.skills_extractor import SkillsExtractor
from processors.job_classifier import JobClassifier
from models.database import SessionLocal, Job, ScrapingLog

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class JobScraperOrchestrator:
    """Main orchestrator for job scraping pipeline"""

    def __init__(self):
        """Initialize the orchestrator"""
        self.scraper = GoogleJobsScraper(headless=True)
        self.skills_extractor = SkillsExtractor()
        self.job_classifier = JobClassifier()
        self.db = SessionLocal()
        logger.info("✅ Job Scraper Orchestrator initialized")

    def load_config(self):
        """Load configuration files"""
        with open('config/job_categories.json', 'r') as f:
            self.categories = json.load(f)

        with open('config/countries.json', 'r') as f:
            self.countries_config = json.load(f)

        logger.info("✅ Configuration loaded")

    def scrape_and_process_jobs(
        self,
        job_titles: List[str],
        countries: List[str],
        max_jobs_per_search: int = 50
    ) -> Dict:
        """
        Main method to scrape and process jobs

        Args:
            job_titles: List of job titles to search
            countries: List of country codes (e.g., ['US', 'CA'])
            max_jobs_per_search: Max jobs to scrape per search

        Returns:
            Dictionary with statistics
        """
        start_time = time.time()
        total_scraped = 0
        total_new = 0
        total_updated = 0

        # Get country names from config
        country_map = {c['code']: c['google_jobs_location']
                      for c in self.countries_config['countries']}

        for country_code in countries:
            country_name = country_map.get(country_code, country_code)

            for job_title in job_titles:
                try:
                    logger.info(f"\n{'='*60}")
                    logger.info(f"🔍 Scraping: {job_title} in {country_name}")
                    logger.info(f"{'='*60}")

                    # Scrape jobs
                    raw_jobs = self.scraper.search_jobs(
                        job_title=job_title,
                        location=country_name,
                        max_jobs=max_jobs_per_search
                    )

                    total_scraped += len(raw_jobs)

                    # Process and store each job
                    for raw_job in raw_jobs:
                        try:
                            processed_job = self._process_job(raw_job, country_code)
                            is_new = self._store_job(processed_job)

                            if is_new:
                                total_new += 1
                            else:
                                total_updated += 1

                        except Exception as e:
                            logger.error(f"❌ Error processing job: {e}")
                            continue

                    # Log scraping activity
                    self._log_scraping_activity(
                        search_query=job_title,
                        country=country_name,
                        jobs_found=len(raw_jobs),
                        status="success",
                        duration=time.time() - start_time
                    )

                    # Small delay between searches to avoid rate limiting
                    time.sleep(2)

                except Exception as e:
                    logger.error(f"❌ Error scraping {job_title} in {country_name}: {e}")
                    self._log_scraping_activity(
                        search_query=job_title,
                        country=country_name,
                        jobs_found=0,
                        status="failed",
                        error_message=str(e),
                        duration=time.time() - start_time
                    )
                    continue

        # Close scraper
        self.scraper.close_driver()

        duration = time.time() - start_time
        stats = {
            "total_scraped": total_scraped,
            "total_new": total_new,
            "total_updated": total_updated,
            "duration_seconds": duration,
            "timestamp": datetime.utcnow().isoformat()
        }

        logger.info(f"\n{'='*60}")
        logger.info(f"✅ SCRAPING COMPLETE")
        logger.info(f"   Total scraped: {total_scraped}")
        logger.info(f"   New jobs: {total_new}")
        logger.info(f"   Updated jobs: {total_updated}")
        logger.info(f"   Duration: {duration:.2f} seconds")
        logger.info(f"{'='*60}\n")

        return stats

    def _process_job(self, raw_job: Dict, country_code: str) -> Dict:
        """Process a raw job with skills extraction and classification"""
        # Extract skills
        skills_data = self.skills_extractor.extract_skills(
            raw_job.get('description', '')
        )

        # Classify job
        classification = self.job_classifier.classify_job(
            title=raw_job.get('title', ''),
            description=raw_job.get('description', '')
        )

        # Extract experience level
        experience_level = self.skills_extractor.extract_experience_level(
            raw_job.get('title', '') + '\n' + raw_job.get('description', '')
        )

        # Extract salary
        salary_data = self.skills_extractor.extract_salary(
            raw_job.get('description', '') + ' ' + raw_job.get('salary_text', '')
        )

        # Parse location
        location = raw_job.get('location', '')
        city = None
        if ',' in location:
            parts = location.split(',')
            city = parts[0].strip()

        # Build processed job
        processed_job = {
            "job_id": raw_job.get('job_id'),
            "title": raw_job.get('title'),
            "company": raw_job.get('company'),
            "location": location,
            "country": country_code,
            "city": city,
            "remote": raw_job.get('remote', False),
            "description": raw_job.get('description'),
            "category": classification.get('category'),
            "industry": classification.get('industry'),
            "experience_level": experience_level,
            "skills_required": skills_data.get('required', []),
            "skills_preferred": skills_data.get('preferred', []),
            "all_skills": skills_data.get('all_skills', []),
            "salary_min": salary_data.get('min'),
            "salary_max": salary_data.get('max'),
            "salary_currency": salary_data.get('currency', 'USD'),
            "source_url": raw_job.get('source_url'),
            "source_platform": raw_job.get('source_platform'),
            "posted_date": raw_job.get('posted_date'),
        }

        return processed_job

    def _store_job(self, job_data: Dict) -> bool:
        """
        Store job in database

        Returns:
            True if new job, False if updated existing job
        """
        try:
            # Check if job already exists
            existing_job = self.db.query(Job).filter(
                Job.job_id == job_data['job_id']
            ).first()

            if existing_job:
                # Update existing job
                for key, value in job_data.items():
                    setattr(existing_job, key, value)
                existing_job.last_updated = datetime.utcnow()
                self.db.commit()
                logger.info(f"🔄 Updated: {job_data['title']} at {job_data['company']}")
                return False
            else:
                # Create new job
                new_job = Job(**job_data)
                self.db.add(new_job)
                self.db.commit()
                logger.info(f"✅ New job: {job_data['title']} at {job_data['company']}")
                return True

        except Exception as e:
            logger.error(f"❌ Error storing job: {e}")
            self.db.rollback()
            return False

    def _log_scraping_activity(
        self,
        search_query: str,
        country: str,
        jobs_found: int,
        status: str,
        duration: float,
        error_message: str = None
    ):
        """Log scraping activity to database"""
        try:
            log_entry = ScrapingLog(
                search_query=search_query,
                country=country,
                jobs_found=jobs_found,
                jobs_new=0,  # Will be updated later
                jobs_updated=0,  # Will be updated later
                status=status,
                error_message=error_message,
                duration_seconds=duration
            )
            self.db.add(log_entry)
            self.db.commit()
        except Exception as e:
            logger.error(f"❌ Error logging activity: {e}")
            self.db.rollback()

    def scrape_all_configured_jobs(self, max_jobs_per_search: int = 50):
        """Scrape all configured job titles and countries"""
        self.load_config()

        # Get all job titles from IT and Healthcare
        job_titles = []
        for industry in ['IT', 'Healthcare']:
            job_titles.extend(self.job_classifier.get_all_job_titles(industry))

        # Get countries
        countries = ['US', 'CA', 'IN', 'AU']

        # For initial run, let's use a subset of popular titles
        # You can modify this to scrape all titles
        popular_titles = [
            # IT
            "Software Engineer", "Frontend Developer", "Backend Developer",
            "Full Stack Developer", "Python Developer", "React Developer",
            "DevOps Engineer", "Data Engineer", "Machine Learning Engineer",
            # Healthcare IT
            "Healthcare Software Engineer", "EHR Developer", "Medical Informatics Specialist"
        ]

        logger.info(f"🚀 Starting scraping for {len(popular_titles)} job titles across {len(countries)} countries")

        return self.scrape_and_process_jobs(
            job_titles=popular_titles,
            countries=countries,
            max_jobs_per_search=max_jobs_per_search
        )

    def close(self):
        """Clean up resources"""
        if hasattr(self.scraper, 'driver') and self.scraper.driver:
            self.scraper.close_driver()
        if self.db:
            self.db.close()


# Example usage
if __name__ == "__main__":
    orchestrator = JobScraperOrchestrator()

    try:
        # Scrape all configured jobs
        stats = orchestrator.scrape_all_configured_jobs(max_jobs_per_search=20)
        print(f"\n✅ Scraping completed: {json.dumps(stats, indent=2)}")

    finally:
        orchestrator.close()
