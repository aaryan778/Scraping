"""
FastAPI REST API for Job Scraping System
Provides endpoints to query and export job data
"""
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from models import Job, ScrapingLog, get_db, JobResponse, JobFilter, StatsResponse
from models.schemas import JobBase

app = FastAPI(
    title="Job Scraping API",
    description="API for accessing scraped job postings with skills data",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Job Scraping API",
        "version": "1.0.0",
        "endpoints": {
            "jobs": "/jobs",
            "stats": "/stats",
            "health": "/health"
        }
    }


@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint"""
    try:
        # Check database connection
        total_jobs = db.query(func.count(Job.id)).scalar()
        return {
            "status": "healthy",
            "database": "connected",
            "total_jobs": total_jobs,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@app.get("/jobs", response_model=List[JobResponse])
async def get_jobs(
    country: Optional[str] = Query(None, description="Filter by country code (e.g., US, CA)"),
    industry: Optional[str] = Query(None, description="Filter by industry (IT, Healthcare)"),
    category: Optional[str] = Query(None, description="Filter by category (Frontend, Backend, etc.)"),
    skill: Optional[str] = Query(None, description="Filter by skill"),
    min_salary: Optional[float] = Query(None, description="Minimum salary"),
    remote_only: bool = Query(False, description="Show only remote jobs"),
    limit: int = Query(100, le=1000, description="Maximum number of results"),
    offset: int = Query(0, description="Offset for pagination"),
    db: Session = Depends(get_db)
):
    """Get jobs with optional filtering"""
    query = db.query(Job).filter(Job.is_active == True)

    # Apply filters
    if country:
        query = query.filter(Job.country == country.upper())

    if industry:
        query = query.filter(Job.industry == industry)

    if category:
        query = query.filter(Job.category == category)

    if skill:
        # Search in all_skills JSON field
        query = query.filter(Job.all_skills.contains([skill.lower()]))

    if min_salary:
        query = query.filter(Job.salary_min >= min_salary)

    if remote_only:
        query = query.filter(Job.remote == True)

    # Order by most recent
    query = query.order_by(Job.scraped_date.desc())

    # Apply pagination
    jobs = query.offset(offset).limit(limit).all()

    return jobs


@app.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str, db: Session = Depends(get_db)):
    """Get a specific job by ID"""
    job = db.query(Job).filter(Job.job_id == job_id).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return job


@app.get("/stats")
async def get_stats(db: Session = Depends(get_db)):
    """Get statistics about scraped jobs"""
    # Total jobs
    total_jobs = db.query(func.count(Job.id)).filter(Job.is_active == True).scalar()

    # Jobs by country
    jobs_by_country = db.query(
        Job.country,
        func.count(Job.id).label('count')
    ).filter(Job.is_active == True).group_by(Job.country).all()

    # Jobs by industry
    jobs_by_industry = db.query(
        Job.industry,
        func.count(Job.id).label('count')
    ).filter(Job.is_active == True).group_by(Job.industry).all()

    # Jobs by category
    jobs_by_category = db.query(
        Job.category,
        func.count(Job.id).label('count')
    ).filter(Job.is_active == True).group_by(Job.category).all()

    # Top skills (this is complex with JSON field, simplified version)
    # In production, you might want to use a separate skills table
    all_jobs = db.query(Job.all_skills).filter(
        Job.is_active == True,
        Job.all_skills != None
    ).limit(1000).all()

    skills_count = {}
    for job in all_jobs:
        if job.all_skills:
            for skill in job.all_skills:
                skills_count[skill] = skills_count.get(skill, 0) + 1

    top_skills = sorted(skills_count.items(), key=lambda x: x[1], reverse=True)[:20]

    # Average salary by category
    avg_salary = db.query(
        Job.category,
        func.avg(Job.salary_min).label('avg_min'),
        func.avg(Job.salary_max).label('avg_max')
    ).filter(
        Job.is_active == True,
        Job.salary_min != None
    ).group_by(Job.category).all()

    return {
        "total_jobs": total_jobs,
        "jobs_by_country": {country: count for country, count in jobs_by_country},
        "jobs_by_industry": {industry: count for industry, count in jobs_by_industry},
        "jobs_by_category": {category: count for category, count in jobs_by_category},
        "top_skills": [{"skill": skill, "count": count} for skill, count in top_skills],
        "avg_salary_by_category": {
            cat: {"min": float(avg_min) if avg_min else 0, "max": float(avg_max) if avg_max else 0}
            for cat, avg_min, avg_max in avg_salary
        },
        "last_updated": datetime.utcnow().isoformat()
    }


@app.get("/skills")
async def get_skills(
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db)
):
    """Get most common skills from job postings"""
    all_jobs = db.query(Job.all_skills).filter(
        Job.is_active == True,
        Job.all_skills != None
    ).all()

    skills_count = {}
    for job in all_jobs:
        if job.all_skills:
            for skill in job.all_skills:
                skills_count[skill] = skills_count.get(skill, 0) + 1

    top_skills = sorted(skills_count.items(), key=lambda x: x[1], reverse=True)[:limit]

    return {
        "skills": [{"name": skill, "count": count} for skill, count in top_skills],
        "total_unique_skills": len(skills_count)
    }


@app.get("/companies")
async def get_companies(
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db)
):
    """Get companies with most job postings"""
    companies = db.query(
        Job.company,
        func.count(Job.id).label('job_count')
    ).filter(
        Job.is_active == True
    ).group_by(Job.company).order_by(func.count(Job.id).desc()).limit(limit).all()

    return {
        "companies": [{"name": company, "job_count": count} for company, count in companies]
    }


@app.get("/scraping-logs")
async def get_scraping_logs(
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db)
):
    """Get recent scraping activity logs"""
    logs = db.query(ScrapingLog).order_by(
        ScrapingLog.timestamp.desc()
    ).limit(limit).all()

    return {
        "logs": [
            {
                "timestamp": log.timestamp.isoformat(),
                "search_query": log.search_query,
                "country": log.country,
                "jobs_found": log.jobs_found,
                "status": log.status,
                "duration": log.duration_seconds
            }
            for log in logs
        ]
    }


@app.get("/recent-jobs")
async def get_recent_jobs(
    hours: int = Query(24, description="Jobs posted in last N hours"),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db)
):
    """Get recently posted jobs"""
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)

    jobs = db.query(Job).filter(
        Job.is_active == True,
        Job.scraped_date >= cutoff_time
    ).order_by(Job.scraped_date.desc()).limit(limit).all()

    return {
        "count": len(jobs),
        "jobs": [job.to_dict() for job in jobs]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
