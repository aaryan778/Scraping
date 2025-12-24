"""
Job Status Checker - Validates if jobs are still active via HTTP requests

This module periodically checks if job listings are still available by:
- Sending HTTP requests to job URLs
- Checking for HTTP 200 (active) vs 404/410 (removed)
- Updating job status in the database
- Integrating with notification system for errors
- Rate limiting to avoid being blocked
"""

import asyncio
import os
import random
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
import aiohttp
from fake_useragent import UserAgent
from tenacity import retry, stop_after_attempt, wait_exponential
from loguru import logger

from models.database import Job, JobStatus, SessionLocal
from utils.notifications import NotificationService
from utils.config_loader import ConfigLoader


class JobStatusChecker:
    """
    Checks if job listings are still active by sending HTTP requests
    """

    def __init__(
        self,
        check_interval_days: int = 7,
        batch_size: int = 50,
        rate_limit_min: float = 1.0,
        rate_limit_max: float = 3.0,
        timeout: int = 10,
        rotate_user_agents: bool = True,
        max_concurrent: int = 5
    ):
        """
        Initialize job status checker

        Args:
            check_interval_days: Days between status checks for each job
            batch_size: Number of jobs to check per batch
            rate_limit_min: Minimum delay between requests (seconds)
            rate_limit_max: Maximum delay between requests (seconds)
            timeout: HTTP request timeout (seconds)
            rotate_user_agents: Whether to rotate user agents
            max_concurrent: Maximum concurrent HTTP requests
        """
        self.check_interval_days = check_interval_days
        self.batch_size = batch_size
        self.rate_limit_min = rate_limit_min
        self.rate_limit_max = rate_limit_max
        self.timeout = timeout
        self.rotate_user_agents = rotate_user_agents
        self.max_concurrent = max_concurrent

        # Initialize services
        self.notifier = NotificationService()
        self.config_loader = ConfigLoader()

        # User agent rotation
        self.ua = None
        if self.rotate_user_agents:
            try:
                self.ua = UserAgent()
            except Exception as e:
                logger.warning(f"Failed to initialize UserAgent: {e}")

        logger.info(
            f"🔍 JobStatusChecker initialized "
            f"(check_interval={check_interval_days}d, batch_size={batch_size})"
        )

    def get_jobs_needing_check(self, db: Session) -> List[Job]:
        """
        Get jobs that need status verification

        Args:
            db: Database session

        Returns:
            List of jobs needing status check
        """
        cutoff_date = datetime.utcnow() - timedelta(days=self.check_interval_days)

        jobs = db.query(Job).filter(
            and_(
                Job.status == JobStatus.ACTIVE,
                Job.url.isnot(None),
                Job.url != "",
                # Either never checked or last check was before cutoff
                (Job.status_last_checked.is_(None)) |
                (Job.status_last_checked < cutoff_date)
            )
        ).limit(self.batch_size).all()

        logger.info(f"Found {len(jobs)} jobs needing status check")
        return jobs

    def _get_user_agent(self) -> str:
        """Get random user agent"""
        if self.rotate_user_agents and self.ua:
            try:
                return self.ua.random
            except Exception:
                pass

        # Fallback user agent
        return (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )

    async def _rate_limit_delay(self):
        """Apply random delay for rate limiting"""
        delay = random.uniform(self.rate_limit_min, self.rate_limit_max)
        await asyncio.sleep(delay)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def _check_url_status(
        self,
        session: aiohttp.ClientSession,
        url: str
    ) -> Tuple[int, Optional[str]]:
        """
        Check if URL is still active

        Args:
            session: aiohttp client session
            url: Job URL to check

        Returns:
            Tuple of (status_code, error_message)
        """
        try:
            # Apply rate limiting
            await self._rate_limit_delay()

            # Send HEAD request (faster than GET)
            async with session.head(
                url,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                allow_redirects=True
            ) as response:
                return response.status, None

        except aiohttp.ClientError as e:
            error_msg = f"HTTP error: {str(e)}"
            logger.warning(f"Failed to check URL {url}: {error_msg}")
            return 0, error_msg

        except asyncio.TimeoutError:
            error_msg = "Request timeout"
            logger.warning(f"Timeout checking URL: {url}")
            return 0, error_msg

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"Error checking URL {url}: {error_msg}")
            return 0, error_msg

    async def _check_job_batch(
        self,
        jobs: List[Job]
    ) -> Dict[int, Tuple[int, Optional[str]]]:
        """
        Check status for a batch of jobs concurrently

        Args:
            jobs: List of Job objects to check

        Returns:
            Dictionary mapping job_id to (status_code, error_message)
        """
        headers = {
            'User-Agent': self._get_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }

        results = {}

        # Create aiohttp session
        async with aiohttp.ClientSession(headers=headers) as session:
            # Process jobs in smaller concurrent batches
            for i in range(0, len(jobs), self.max_concurrent):
                batch = jobs[i:i + self.max_concurrent]

                # Create tasks for concurrent execution
                tasks = [
                    self._check_url_status(session, job.url)
                    for job in batch
                ]

                # Wait for all tasks to complete
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)

                # Map results to job IDs
                for job, result in zip(batch, batch_results):
                    if isinstance(result, Exception):
                        logger.error(f"Exception checking job {job.id}: {result}")
                        results[job.id] = (0, str(result))
                    else:
                        results[job.id] = result

        return results

    def _update_job_status(
        self,
        db: Session,
        job: Job,
        status_code: int,
        error_message: Optional[str]
    ):
        """
        Update job status in database based on HTTP response

        Args:
            db: Database session
            job: Job object to update
            status_code: HTTP status code
            error_message: Error message if any
        """
        job.status_last_checked = datetime.utcnow()
        job.status_check_code = status_code if status_code > 0 else None
        job.status_check_error = error_message

        # Determine if job should be marked as removed
        if status_code == 200:
            # Job is still active
            logger.debug(f"✓ Job {job.id} ({job.title}) is still active")

        elif status_code in [404, 410]:
            # 404 Not Found or 410 Gone - job is removed
            job.mark_as_removed(status_code=status_code)
            logger.info(
                f"🗑️  Job {job.id} ({job.title}) marked as REMOVED "
                f"(HTTP {status_code})"
            )

            # Send notification for removed job
            self.notifier.notify_error(
                error_type="job_removed",
                message=f"Job removed from source: {job.title} at {job.company}",
                details={
                    "job_id": job.id,
                    "url": job.url,
                    "status_code": status_code
                },
                critical=False
            )

        elif status_code in [301, 302, 307, 308]:
            # Redirect - job might be moved, keep as active for now
            logger.info(
                f"↪️  Job {job.id} ({job.title}) redirected "
                f"(HTTP {status_code})"
            )

        elif status_code >= 500:
            # Server error - don't mark as removed, might be temporary
            logger.warning(
                f"⚠️  Server error checking job {job.id} ({job.title}) "
                f"(HTTP {status_code})"
            )

        elif status_code == 0:
            # Network/timeout error - don't mark as removed
            logger.warning(
                f"⚠️  Network error checking job {job.id} ({job.title}): "
                f"{error_message}"
            )

        else:
            # Other status codes (401, 403, etc.) - keep as active
            logger.warning(
                f"⚠️  Unexpected status for job {job.id} ({job.title}) "
                f"(HTTP {status_code})"
            )

        db.commit()

    async def check_jobs_async(self) -> Dict[str, int]:
        """
        Check job statuses asynchronously

        Returns:
            Statistics dictionary with counts
        """
        db = SessionLocal()
        stats = {
            'total_checked': 0,
            'still_active': 0,
            'marked_removed': 0,
            'errors': 0
        }

        try:
            # Get jobs needing check
            jobs = self.get_jobs_needing_check(db)

            if not jobs:
                logger.info("No jobs need status checking at this time")
                return stats

            stats['total_checked'] = len(jobs)

            # Check job statuses in batch
            logger.info(f"Checking status for {len(jobs)} jobs...")
            results = await self._check_job_batch(jobs)

            # Update database with results
            for job in jobs:
                if job.id in results:
                    status_code, error_message = results[job.id]

                    # Update job status
                    self._update_job_status(db, job, status_code, error_message)

                    # Update stats
                    if status_code == 200:
                        stats['still_active'] += 1
                    elif status_code in [404, 410]:
                        stats['marked_removed'] += 1
                    elif status_code == 0 or status_code >= 400:
                        stats['errors'] += 1

            # Log summary
            logger.info(
                f"📊 Status check complete: {stats['total_checked']} checked, "
                f"{stats['still_active']} active, {stats['marked_removed']} removed, "
                f"{stats['errors']} errors"
            )

            return stats

        except Exception as e:
            logger.error(f"Error during status check: {e}")
            self.notifier.notify_error(
                error_type="status_check_failure",
                message=f"Job status check failed: {str(e)}",
                details={'error': str(e)},
                critical=True
            )
            raise

        finally:
            db.close()

    def check_jobs(self) -> Dict[str, int]:
        """
        Synchronous wrapper for check_jobs_async

        Returns:
            Statistics dictionary with counts
        """
        return asyncio.run(self.check_jobs_async())

    async def check_specific_job_async(self, job_id: int) -> bool:
        """
        Check status for a specific job by ID

        Args:
            job_id: Job ID to check

        Returns:
            True if job is still active, False otherwise
        """
        db = SessionLocal()

        try:
            job = db.query(Job).filter(Job.id == job_id).first()

            if not job:
                logger.error(f"Job {job_id} not found")
                return False

            if not job.url:
                logger.warning(f"Job {job_id} has no URL")
                return False

            # Check job status
            results = await self._check_job_batch([job])

            if job.id in results:
                status_code, error_message = results[job.id]
                self._update_job_status(db, job, status_code, error_message)
                return status_code == 200

            return False

        finally:
            db.close()

    def check_specific_job(self, job_id: int) -> bool:
        """
        Synchronous wrapper for check_specific_job_async

        Args:
            job_id: Job ID to check

        Returns:
            True if job is still active, False otherwise
        """
        return asyncio.run(self.check_specific_job_async(job_id))


# Global instance
_checker_instance = None


def get_status_checker() -> JobStatusChecker:
    """
    Get singleton instance of JobStatusChecker

    Returns:
        JobStatusChecker instance
    """
    global _checker_instance

    if _checker_instance is None:
        _checker_instance = JobStatusChecker(
            check_interval_days=int(os.getenv('STATUS_CHECK_INTERVAL_DAYS', 7)),
            batch_size=int(os.getenv('STATUS_CHECK_BATCH_SIZE', 50)),
            rate_limit_min=float(os.getenv('RATE_LIMIT_DELAY_MIN', 1.0)),
            rate_limit_max=float(os.getenv('RATE_LIMIT_DELAY_MAX', 3.0)),
            timeout=int(os.getenv('HTTP_TIMEOUT', 10)),
            rotate_user_agents=os.getenv('ROTATE_USER_AGENTS', 'true').lower() == 'true',
            max_concurrent=int(os.getenv('MAX_CONCURRENT_CHECKS', 5))
        )

    return _checker_instance


if __name__ == "__main__":
    """Run status checker as standalone script"""
    checker = get_status_checker()

    logger.info("Starting job status check...")
    stats = checker.check_jobs()

    logger.info(f"Status check completed: {stats}")
