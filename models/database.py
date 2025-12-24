"""Database models and configuration"""
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Float, Text, JSON, Enum as SQLEnum, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import enum

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://jobscraper:changeme123@localhost:5432/jobs_db")

# PostgreSQL pool settings
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Verify connections before using
    echo=False  # Set to True for SQL query logging
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class JobStatus(enum.Enum):
    """Job status enumeration"""
    ACTIVE = "active"  # Job is currently active
    REMOVED = "removed"  # Job was removed from source
    EXPIRED = "expired"  # Job expired (30+ days old)
    CHECKING = "checking"  # Currently checking if job is still active


class Job(Base):
    """Job posting model with multi-label classification and status tracking"""
    __tablename__ = "jobs"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(255), unique=True, index=True)  # Unique identifier

    # Basic info
    title = Column(String(500), index=True, nullable=False)
    company = Column(String(255), index=True, nullable=False)
    location = Column(String(255), index=True)
    country = Column(String(10), index=True)
    city = Column(String(100))
    remote = Column(Boolean, default=False, index=True)

    # Job details
    description = Column(Text)

    # Multi-label classification
    primary_category = Column(String(100), index=True)  # Main category
    secondary_categories = Column(JSON)  # List of secondary categories
    industry = Column(String(50), index=True)  # IT/Healthcare
    experience_level = Column(String(50))  # Junior/Mid/Senior/Lead

    # Classification metadata
    classification_confidence = Column(Float, default=0.0)  # 0.0 to 1.0
    manual_override = Column(Boolean, default=False)  # User manually set category
    manual_category = Column(String(100), nullable=True)  # User-set category

    # Skills (stored as JSON arrays)
    skills_required = Column(JSON)
    skills_preferred = Column(JSON)
    all_skills = Column(JSON)  # Combined list with GIN index support

    # Salary
    salary_min = Column(Float, nullable=True)
    salary_max = Column(Float, nullable=True)
    salary_currency = Column(String(10), default="USD")

    # Source information
    source_url = Column(Text)  # Can be long
    source_platform = Column(String(100), index=True)  # LinkedIn, Indeed, etc.

    # Deduplication tracking
    dedup_sources = Column(JSON)  # List of all source platforms for this job
    dedup_source_urls = Column(JSON)  # All URLs where this job appears
    dedup_count = Column(Integer, default=1)  # Number of duplicates merged

    # Job status tracking
    status = Column(SQLEnum(JobStatus), default=JobStatus.ACTIVE, index=True, nullable=False)
    status_last_checked = Column(DateTime, nullable=True)  # When we last verified
    status_check_code = Column(Integer, nullable=True)  # HTTP status code from check
    status_check_error = Column(Text, nullable=True)  # Error message if check failed

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True, nullable=False)
    posted_date = Column(DateTime, nullable=True, index=True)
    scraped_date = Column(DateTime, default=datetime.utcnow, index=True)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True, index=True)  # Auto-calculated expiry

    # Legacy field for backwards compatibility
    is_active = Column(Boolean, default=True, index=True)

    # Table indexes for performance
    __table_args__ = (
        Index('idx_job_search', 'country', 'industry', 'primary_category', 'status'),
        Index('idx_job_status_check', 'status', 'status_last_checked'),
        Index('idx_job_expiry', 'expires_at', 'status'),
        Index('idx_job_company_title', 'company', 'title'),
    )

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            "id": self.id,
            "job_id": self.job_id,
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "country": self.country,
            "city": self.city,
            "remote": self.remote,
            "description": self.description,
            # Multi-label classification
            "primary_category": self.primary_category,
            "secondary_categories": self.secondary_categories or [],
            "category": self.manual_category if self.manual_override else self.primary_category,  # Backwards compat
            "industry": self.industry,
            "experience_level": self.experience_level,
            "classification_confidence": self.classification_confidence,
            "manual_override": self.manual_override,
            # Skills
            "skills_required": self.skills_required or [],
            "skills_preferred": self.skills_preferred or [],
            "all_skills": self.all_skills or [],
            # Salary
            "salary_min": self.salary_min,
            "salary_max": self.salary_max,
            "salary_currency": self.salary_currency,
            # Source
            "source_url": self.source_url,
            "source_platform": self.source_platform,
            "dedup_sources": self.dedup_sources or [],
            "dedup_count": self.dedup_count,
            # Status
            "status": self.status.value if self.status else "active",
            "status_last_checked": self.status_last_checked.isoformat() if self.status_last_checked else None,
            "is_active": self.is_active,
            # Timestamps
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "posted_date": self.posted_date.isoformat() if self.posted_date else None,
            "scraped_date": self.scraped_date.isoformat() if self.scraped_date else None,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }

    def calculate_expiry(self, days: int = 30):
        """
        Calculate and set expiry date based on posted date

        Args:
            days: Number of days until expiry (default: 30)
        """
        if self.posted_date:
            self.expires_at = self.posted_date + timedelta(days=days)
        elif self.scraped_date:
            self.expires_at = self.scraped_date + timedelta(days=days)

    def mark_as_removed(self, status_code: int = None, error: str = None):
        """Mark job as removed from source"""
        self.status = JobStatus.REMOVED
        self.is_active = False
        self.status_last_checked = datetime.utcnow()
        if status_code:
            self.status_check_code = status_code
        if error:
            self.status_check_error = error

    def mark_as_expired(self):
        """Mark job as expired"""
        self.status = JobStatus.EXPIRED
        self.is_active = False

    def needs_status_check(self, check_interval_days: int = 7) -> bool:
        """
        Check if job needs status verification

        Args:
            check_interval_days: Days between status checks

        Returns:
            True if check is needed
        """
        if self.status != JobStatus.ACTIVE:
            return False

        if not self.status_last_checked:
            return True

        days_since_check = (datetime.utcnow() - self.status_last_checked).days
        return days_since_check >= check_interval_days


class ScrapingLog(Base):
    """Log of scraping activities"""
    __tablename__ = "scraping_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    search_query = Column(String)
    country = Column(String)
    jobs_found = Column(Integer)
    jobs_new = Column(Integer)
    jobs_updated = Column(Integer)
    status = Column(String)  # success/failed
    error_message = Column(Text, nullable=True)
    duration_seconds = Column(Float)


def init_db():
    """Initialize database tables"""
    from loguru import logger

    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database initialized successfully")
        logger.info(f"   Tables created: {', '.join(Base.metadata.tables.keys())}")
    except Exception as e:
        logger.error(f"❌ Error initializing database: {e}")
        raise


def get_db():
    """Get database session (generator for FastAPI dependency injection)"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_session():
    """Get database session (direct function for non-FastAPI use)"""
    return SessionLocal()


if __name__ == "__main__":
    init_db()
