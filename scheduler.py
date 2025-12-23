"""
Automated Job Scraping Scheduler
Runs the scraper every hour to keep job data fresh
"""
import logging
import time
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from scrapers.job_scraper_main import JobScraperOrchestrator
from models.database import init_db

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class JobScraperScheduler:
    """Scheduler for automated job scraping"""

    def __init__(self, interval_hours: int = 1):
        """
        Initialize scheduler

        Args:
            interval_hours: Hours between scraping runs (default: 1)
        """
        self.interval_hours = interval_hours
        self.scheduler = BackgroundScheduler()
        self.orchestrator = None
        logger.info(f"✅ Scheduler initialized (interval: {interval_hours} hours)")

    def scrape_jobs_task(self):
        """Task to scrape jobs - runs on schedule"""
        try:
            logger.info(f"\n{'='*80}")
            logger.info(f"🚀 SCHEDULED SCRAPING STARTED - {datetime.now()}")
            logger.info(f"{'='*80}\n")

            # Create new orchestrator for this run
            self.orchestrator = JobScraperOrchestrator()

            # Run the scraping
            stats = self.orchestrator.scrape_all_configured_jobs(
                max_jobs_per_search=50
            )

            logger.info(f"\n{'='*80}")
            logger.info(f"✅ SCHEDULED SCRAPING COMPLETED")
            logger.info(f"   Total scraped: {stats['total_scraped']}")
            logger.info(f"   New jobs: {stats['total_new']}")
            logger.info(f"   Updated jobs: {stats['total_updated']}")
            logger.info(f"   Duration: {stats['duration_seconds']:.2f} seconds")
            logger.info(f"{'='*80}\n")

            # Clean up
            self.orchestrator.close()
            self.orchestrator = None

        except Exception as e:
            logger.error(f"❌ Error in scheduled scraping: {e}", exc_info=True)
            if self.orchestrator:
                self.orchestrator.close()

    def start(self):
        """Start the scheduler"""
        logger.info("🚀 Starting job scraper scheduler...")

        # Initialize database
        init_db()

        # Add the scraping job
        self.scheduler.add_job(
            func=self.scrape_jobs_task,
            trigger=IntervalTrigger(hours=self.interval_hours),
            id='job_scraping',
            name='Scrape jobs from Google Jobs',
            replace_existing=True
        )

        # Start the scheduler
        self.scheduler.start()
        logger.info(f"✅ Scheduler started! Will scrape jobs every {self.interval_hours} hour(s)")

        # Run initial scrape immediately
        logger.info("🔄 Running initial scrape...")
        self.scrape_jobs_task()

    def stop(self):
        """Stop the scheduler"""
        logger.info("⏹️ Stopping scheduler...")
        self.scheduler.shutdown()
        logger.info("✅ Scheduler stopped")

    def run_forever(self):
        """Keep the scheduler running"""
        self.start()

        try:
            # Keep the script running
            while True:
                time.sleep(60)  # Sleep for 1 minute
        except (KeyboardInterrupt, SystemExit):
            logger.info("\n🛑 Received shutdown signal")
            self.stop()


def run_scheduler(interval_hours: int = 1):
    """
    Run the job scraper scheduler

    Args:
        interval_hours: Hours between scraping runs
    """
    scheduler = JobScraperScheduler(interval_hours=interval_hours)

    try:
        scheduler.run_forever()
    except Exception as e:
        logger.error(f"❌ Scheduler error: {e}", exc_info=True)
        scheduler.stop()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Job Scraping Scheduler")
    parser.add_argument(
        '--interval',
        type=int,
        default=1,
        help='Hours between scraping runs (default: 1)'
    )

    args = parser.parse_args()

    print(f"""
    ╔══════════════════════════════════════════════════════╗
    ║     JOB SCRAPING SCHEDULER - AUTOMATED MODE         ║
    ╠══════════════════════════════════════════════════════╣
    ║  Interval: Every {args.interval} hour(s)                           ║
    ║  Press Ctrl+C to stop                                ║
    ╚══════════════════════════════════════════════════════╝
    """)

    run_scheduler(interval_hours=args.interval)
