"""Database models and configuration"""
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Float, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./jobs.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Job(Base):
    """Job posting model"""
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String, unique=True, index=True)  # Unique identifier from source
    title = Column(String, index=True)
    company = Column(String, index=True)
    location = Column(String, index=True)
    country = Column(String, index=True)
    city = Column(String)
    remote = Column(Boolean, default=False)

    # Job details
    description = Column(Text)
    category = Column(String, index=True)  # Frontend/Backend/Full Stack/etc.
    industry = Column(String, index=True)  # IT/Healthcare
    experience_level = Column(String)  # Junior/Mid/Senior

    # Skills (stored as JSON)
    skills_required = Column(JSON)
    skills_preferred = Column(JSON)
    all_skills = Column(JSON)  # Combined list for easy querying

    # Salary
    salary_min = Column(Float, nullable=True)
    salary_max = Column(Float, nullable=True)
    salary_currency = Column(String, default="USD")

    # Source information
    source_url = Column(String)
    source_platform = Column(String)  # Indeed, LinkedIn, Glassdoor, etc.

    # Timestamps
    posted_date = Column(DateTime, nullable=True)
    scraped_date = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Status
    is_active = Column(Boolean, default=True)

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
            "category": self.category,
            "industry": self.industry,
            "experience_level": self.experience_level,
            "skills_required": self.skills_required,
            "skills_preferred": self.skills_preferred,
            "all_skills": self.all_skills,
            "salary_min": self.salary_min,
            "salary_max": self.salary_max,
            "salary_currency": self.salary_currency,
            "source_url": self.source_url,
            "source_platform": self.source_platform,
            "posted_date": self.posted_date.isoformat() if self.posted_date else None,
            "scraped_date": self.scraped_date.isoformat() if self.scraped_date else None,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "is_active": self.is_active
        }


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
    Base.metadata.create_all(bind=engine)
    print("✅ Database initialized successfully")


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
