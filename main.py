"""
Main entry point for Job Scraping System
Provides CLI interface to run various components
"""
import argparse
import sys
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from models.database import init_db


def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(
        description="Job Scraping System - Automated job scraping with skills extraction",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Initialize database
  python main.py --init-db

  # Run one-time scraping
  python main.py --scrape

  # Start scheduler (scrapes every hour)
  python main.py --schedule

  # Start API server
  python main.py --api

  # Start dashboard
  python main.py --dashboard

  # Run everything (scheduler + API + dashboard)
  python main.py --all
        """
    )

    parser.add_argument('--init-db', action='store_true', help='Initialize the database')
    parser.add_argument('--scrape', action='store_true', help='Run scraper once')
    parser.add_argument('--schedule', action='store_true', help='Start scheduler (runs every hour)')
    parser.add_argument('--api', action='store_true', help='Start API server')
    parser.add_argument('--dashboard', action='store_true', help='Start dashboard')
    parser.add_argument('--all', action='store_true', help='Run scheduler + API + dashboard')
    parser.add_argument('--interval', type=int, default=1, help='Scraping interval in hours (default: 1)')
    parser.add_argument('--max-jobs', type=int, default=50, help='Max jobs per search (default: 50)')

    args = parser.parse_args()

    # If no arguments, show help
    if len(sys.argv) == 1:
        parser.print_help()
        return

    # Initialize database
    if args.init_db or args.all:
        print("📦 Initializing database...")
        init_db()
        print("✅ Database initialized!\n")

    # Run scraper once
    if args.scrape:
        print("🚀 Starting one-time scraping...")
        from scrapers.job_scraper_main import JobScraperOrchestrator

        orchestrator = JobScraperOrchestrator()
        try:
            stats = orchestrator.scrape_all_configured_jobs(max_jobs_per_search=args.max_jobs)
            print(f"\n✅ Scraping completed!")
            print(f"   Total scraped: {stats['total_scraped']}")
            print(f"   New jobs: {stats['total_new']}")
            print(f"   Updated jobs: {stats['total_updated']}")
        finally:
            orchestrator.close()

    # Start scheduler
    if args.schedule or args.all:
        print(f"⏰ Starting scheduler (interval: {args.interval} hour(s))...")
        from scheduler import run_scheduler
        run_scheduler(interval_hours=args.interval)

    # Start API
    if args.api:
        print("🚀 Starting API server...")
        import uvicorn
        from api.main import app
        uvicorn.run(app, host="0.0.0.0", port=8000)

    # Start dashboard
    if args.dashboard:
        print("📊 Starting dashboard...")
        import os
        os.system("streamlit run dashboard/app.py --server.port 8501")


if __name__ == "__main__":
    main()
