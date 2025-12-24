"""
Main Job Scraping Orchestrator
Coordinates scraping, processing, and database storage

Phase 4: Production-grade orchestrator with:
- Playwright async scraper
- Data validation before storage
- Fuzzy matching deduplication
- Redis caching
- Error notifications
- Multi-label classification
"""
import json
import asyncio
import time
from datetime import datetime
from typing import List, Dict, Tuple
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from scrapers.playwright_scraper import PlaywrightJobsScraper
from processors.skills_extractor import SkillsExtractor
from processors.job_classifier import JobClassifier
from processors.deduplication import JobDeduplicator
from models.database import SessionLocal, Job, ScrapingLog, JobStatus
from utils.validation import JobValidator
from utils.cache import RedisCache, CacheKeys
from utils.notifications import NotificationService
from utils.config_loader import ConfigLoader
from loguru import logger

# Configure loguru
logger.add(
    "logs/orchestrator_{time:YYYY-MM-DD}.log",
    rotation="1 day",
    retention="30 days",
    level="INFO"
)


class JobScraperOrchestrator:
    """Production-grade orchestrator for job scraping pipeline"""

    def __init__(self):
        """Initialize the orchestrator with all utilities"""
        # Load configuration
        self.config_loader = ConfigLoader()

        # Initialize scraper (will be created per-session for async)
        self.scraper = None

        # Initialize processors
        self.skills_extractor = SkillsExtractor()
        self.job_classifier = JobClassifier()
        self.deduplicator = JobDeduplicator()

        # Initialize utilities
        self.validator = JobValidator()
        self.cache = RedisCache()
        self.notifier = NotificationService()

        # Database session
        self.db = SessionLocal()

        # Statistics
        self.stats = {
            'total_scraped': 0,
            'total_validated': 0,
            'total_validation_failed': 0,
            'total_duplicates': 0,
            'total_new': 0,
            'total_updated': 0,
            'errors': 0
        }

        logger.info("✅ Job Scraper Orchestrator initialized (Phase 4)")

    def load_config(self):
        """Load configuration files using ConfigLoader"""
        self.categories = self.config_loader.load_config('job_categories')
        self.countries_config = self.config_loader.load_config('countries')
        logger.info("✅ Configuration loaded")

    async def scrape_and_process_jobs_async(
        self,
        job_titles: List[str],
        countries: List[str],
        max_jobs_per_search: int = 50
    ) -> Dict:
        """
        Main method to scrape and process jobs (async version)

        Args:
            job_titles: List of job titles to search
            countries: List of country codes (e.g., ['US', 'CA'])
            max_jobs_per_search: Max jobs to scrape per search

        Returns:
            Dictionary with statistics
        """
        start_time = time.time()

        # Reset stats
        self.stats = {
            'total_scraped': 0,
            'total_validated': 0,
            'total_validation_failed': 0,
            'total_duplicates': 0,
            'total_new': 0,
            'total_updated': 0,
            'errors': 0
        }

        # Get country names from config
        country_map = {c['code']: c['google_jobs_location']
                      for c in self.countries_config['countries']}

        # Create Playwright scraper
        async with PlaywrightJobsScraper() as scraper:
            self.scraper = scraper

            for country_code in countries:
                country_name = country_map.get(country_code, country_code)

                for job_title in job_titles:
                    try:
                        logger.info(f"\n{'='*60}")
                        logger.info(f"🔍 Scraping: {job_title} in {country_name}")
                        logger.info(f"{'='*60}")

                        # Scrape jobs using Playwright
                        raw_jobs = await scraper.search_jobs(
                            job_title=job_title,
                            location=country_name,
                            max_jobs=max_jobs_per_search
                        )

                        self.stats['total_scraped'] += len(raw_jobs)
                        logger.info(f"📦 Found {len(raw_jobs)} jobs")

                        # Process and store each job
                        for raw_job in raw_jobs:
                            try:
                                await self._process_and_store_job(raw_job, country_code)
                            except Exception as e:
                                logger.error(f"❌ Error processing job: {e}")
                                self.stats['errors'] += 1
                                self.notifier.notify_error(
                                    error_type="job_processing_error",
                                    message=f"Failed to process job: {str(e)}",
                                    details={'job': raw_job.get('title', 'Unknown')},
                                    critical=False
                                )
                                continue

                        # Log scraping activity
                        self._log_scraping_activity(
                            search_query=job_title,
                            country=country_name,
                            jobs_found=len(raw_jobs),
                            status="success",
                            duration=time.time() - start_time
                        )

                    except Exception as e:
                        logger.error(f"❌ Error scraping {job_title} in {country_name}: {e}")
                        self.stats['errors'] += 1

                        self._log_scraping_activity(
                            search_query=job_title,
                            country=country_name,
                            jobs_found=0,
                            status="failed",
                            error_message=str(e),
                            duration=time.time() - start_time
                        )

                        self.notifier.notify_error(
                            error_type="scraping_failure",
                            message=f"Failed to scrape {job_title} in {country_name}",
                            details={'error': str(e)},
                            critical=False
                        )
                        continue

        # Calculate duration
        duration = time.time() - start_time
        self.stats['duration_seconds'] = duration
        self.stats['timestamp'] = datetime.utcnow().isoformat()

        # Log summary
        logger.info(f"\n{'='*60}")
        logger.info(f"✅ SCRAPING COMPLETE")
        logger.info(f"   Total scraped: {self.stats['total_scraped']}")
        logger.info(f"   Validated: {self.stats['total_validated']}")
        logger.info(f"   Validation failed: {self.stats['total_validation_failed']}")
        logger.info(f"   Duplicates: {self.stats['total_duplicates']}")
        logger.info(f"   New jobs: {self.stats['total_new']}")
        logger.info(f"   Updated jobs: {self.stats['total_updated']}")
        logger.info(f"   Errors: {self.stats['errors']}")
        logger.info(f"   Duration: {duration:.2f} seconds")
        logger.info(f"{'='*60}\n")

        # Invalidate cache
        self.cache.delete(CacheKeys.stats_key())

        return self.stats

    def scrape_and_process_jobs(
        self,
        job_titles: List[str],
        countries: List[str],
        max_jobs_per_search: int = 50
    ) -> Dict:
        """Synchronous wrapper for scrape_and_process_jobs_async"""
        return asyncio.run(
            self.scrape_and_process_jobs_async(job_titles, countries, max_jobs_per_search)
        )

    async def _process_and_store_job(self, raw_job: Dict, country_code: str):
        """
        Process and store job with validation, deduplication, and classification

        Args:
            raw_job: Raw job data from scraper
            country_code: Country code (e.g., 'US')
        """
        # Step 1: Build initial job data
        processed_job = await self._process_job(raw_job, country_code)

        # Step 2: Validate job data
        is_valid, validation_errors = self.validator.validate(processed_job)

        if not is_valid:
            logger.warning(
                f"⚠️  Validation failed for {processed_job.get('title', 'Unknown')}: "
                f"{', '.join(validation_errors)}"
            )
            self.stats['total_validation_failed'] += 1
            self.notifier.log_validation_failure(processed_job, validation_errors)
            return

        self.stats['total_validated'] += 1

        # Step 3: Sanitize data
        processed_job = self.validator.sanitize(processed_job)

        # Step 4: Check for duplicates in database
        is_duplicate, existing_job = await self._check_duplicate_in_db(processed_job)

        if is_duplicate:
            # Merge with existing job
            logger.info(
                f"🔄 Duplicate found: {processed_job.get('title')} at "
                f"{processed_job.get('company')} (merging)"
            )
            self.stats['total_duplicates'] += 1
            await self._merge_duplicate_job(existing_job, processed_job)
            return

        # Step 5: Store new job
        await self._store_new_job(processed_job)

    async def _process_job(self, raw_job: Dict, country_code: str) -> Dict:
        """Process a raw job with skills extraction and multi-label classification"""
        # Extract skills
        skills_data = self.skills_extractor.extract_skills(
            raw_job.get('description', '')
        )

        # Multi-label classification
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

        # Build processed job with multi-label classification
        processed_job = {
            "job_id": raw_job.get('job_id'),
            "title": raw_job.get('title'),
            "company": raw_job.get('company'),
            "location": location,
            "country": country_code,
            "city": city,
            "remote": raw_job.get('remote', False),
            "description": raw_job.get('description'),
            "url": raw_job.get('source_url'),

            # Multi-label classification
            "industry": classification.get('industry'),
            "primary_category": classification.get('primary_category'),
            "secondary_categories": classification.get('secondary_categories', []),
            "classification_confidence": classification.get('classification_confidence', 0.0),

            # Skills
            "experience_level": experience_level,
            "skills_required": skills_data.get('required', []),
            "skills_preferred": skills_data.get('preferred', []),
            "all_skills": skills_data.get('all_skills', []),

            # Salary
            "salary_min": salary_data.get('min'),
            "salary_max": salary_data.get('max'),
            "salary_currency": salary_data.get('currency', 'USD'),

            # Source
            "source_url": raw_job.get('source_url'),
            "source_platform": raw_job.get('source_platform', 'Google Jobs'),
            "posted_date": raw_job.get('posted_date'),

            # Status
            "status": JobStatus.ACTIVE,
            "is_active": True,
        }

        return processed_job

    async def _check_duplicate_in_db(
        self,
        job_data: Dict
    ) -> Tuple[bool, Job]:
        """
        Check if job is a duplicate using fuzzy matching

        Args:
            job_data: Processed job data

        Returns:
            Tuple of (is_duplicate, existing_job or None)
        """
        # Get recent jobs from same company (within last 90 days)
        from datetime import timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=90)

        # Escape SQL wildcards to prevent injection
        company_name = job_data.get('company', '').replace('%', '\\%').replace('_', '\\_')

        similar_jobs = self.db.query(Job).filter(
            Job.company.ilike(f"%{company_name}%"),
            Job.country == job_data.get('country'),
            Job.created_at >= cutoff_date
        ).limit(100).all()

        # Check each similar job for fuzzy match
        for existing_job in similar_jobs:
            existing_job_dict = {
                'title': existing_job.title,
                'company': existing_job.company,
                'location': existing_job.location
            }

            is_dup, score = self.deduplicator.is_duplicate(job_data, existing_job_dict)

            if is_dup:
                logger.debug(
                    f"Duplicate detected (score: {score:.2f}): "
                    f"{job_data.get('title')} ≈ {existing_job.title}"
                )
                return True, existing_job

        return False, None

    async def _merge_duplicate_job(self, existing_job: Job, new_job_data: Dict):
        """
        Merge duplicate job data into existing job

        Args:
            existing_job: Existing job in database
            new_job_data: New job data to merge
        """
        try:
            # Update last seen timestamp
            existing_job.last_updated = datetime.utcnow()

            # Track source if different
            if hasattr(existing_job, 'dedup_sources'):
                sources = existing_job.dedup_sources or []
                new_source = new_job_data.get('source_platform', 'Google Jobs')
                if new_source not in sources:
                    sources.append(new_source)
                    existing_job.dedup_sources = sources

                # Track source URLs
                source_urls = existing_job.dedup_source_urls or []
                new_url = new_job_data.get('source_url')
                if new_url and new_url not in source_urls:
                    source_urls.append(new_url)
                    existing_job.dedup_source_urls = source_urls

                # Increment dedup count
                existing_job.dedup_count = (existing_job.dedup_count or 1) + 1

            # Merge skills (union of all skills)
            all_skills = list(set(
                (existing_job.all_skills or []) +
                (new_job_data.get('all_skills', []))
            ))
            existing_job.all_skills = all_skills

            # Update description if new one is better (longer, more detailed)
            if new_job_data.get('description'):
                new_desc_len = len(new_job_data['description'])
                existing_desc_len = len(existing_job.description or '')
                if new_desc_len > existing_desc_len:
                    existing_job.description = new_job_data['description']

            # Update salary if not present
            if not existing_job.salary_min and new_job_data.get('salary_min'):
                existing_job.salary_min = new_job_data['salary_min']
                existing_job.salary_max = new_job_data.get('salary_max')
                existing_job.salary_currency = new_job_data.get('salary_currency', 'USD')

            # Keep job active
            existing_job.is_active = True
            existing_job.status = JobStatus.ACTIVE

            self.db.commit()
            self.stats['total_updated'] += 1

        except Exception as e:
            logger.error(f"❌ Error merging duplicate job: {e}")
            self.db.rollback()
            self.stats['errors'] += 1

    async def _store_new_job(self, job_data: Dict):
        """
        Store new job in database

        Args:
            job_data: Processed and validated job data
        """
        try:
            # Create new job
            new_job = Job(**job_data)

            # Calculate expiry date
            new_job.calculate_expiry(days=30)

            # Initialize dedup tracking
            new_job.dedup_sources = [job_data.get('source_platform', 'Google Jobs')]
            new_job.dedup_source_urls = [job_data.get('source_url')] if job_data.get('source_url') else []
            new_job.dedup_count = 1

            self.db.add(new_job)
            self.db.commit()

            logger.info(
                f"✅ New job: {job_data.get('title')} at {job_data.get('company')} "
                f"({job_data.get('primary_category')})"
            )
            self.stats['total_new'] += 1

        except Exception as e:
            logger.error(f"❌ Error storing new job: {e}")
            self.db.rollback()
            self.stats['errors'] += 1
            self.notifier.notify_error(
                error_type="database_error",
                message=f"Failed to store job: {str(e)}",
                details={'job': job_data.get('title', 'Unknown')},
                critical=True
            )

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
        # Playwright scraper uses context managers, no manual cleanup needed
        if self.db:
            self.db.close()
        logger.info("🔒 Orchestrator resources closed")


# Example usage
if __name__ == "__main__":
    orchestrator = JobScraperOrchestrator()

    try:
        # Scrape all configured jobs
        stats = orchestrator.scrape_all_configured_jobs(max_jobs_per_search=20)
        print(f"\n✅ Scraping completed: {json.dumps(stats, indent=2)}")

    finally:
        orchestrator.close()
