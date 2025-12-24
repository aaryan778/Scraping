"""Pydantic schemas for API validation"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class JobBase(BaseModel):
    """Base job schema"""
    title: str
    company: str
    location: str
    country: str
    city: Optional[str] = None
    remote: bool = False
    description: Optional[str] = None
    category: Optional[str] = None
    industry: Optional[str] = None
    experience_level: Optional[str] = None


class JobCreate(JobBase):
    """Schema for creating a job"""
    job_id: str
    skills_required: Optional[List[str]] = []
    skills_preferred: Optional[List[str]] = []
    all_skills: Optional[List[str]] = []
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: str = "USD"
    source_url: Optional[str] = None
    source_platform: Optional[str] = None
    posted_date: Optional[datetime] = None


class JobResponse(JobBase):
    """Schema for job response"""
    id: int
    job_id: str
    skills_required: Optional[List[str]] = []
    skills_preferred: Optional[List[str]] = []
    all_skills: Optional[List[str]] = []
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: str
    source_url: Optional[str] = None
    source_platform: Optional[str] = None
    posted_date: Optional[datetime] = None
    scraped_date: datetime
    last_updated: datetime
    is_active: bool

    class Config:
        from_attributes = True


class JobFilter(BaseModel):
    """Schema for filtering jobs"""
    country: Optional[str] = None
    industry: Optional[str] = None
    category: Optional[str] = None
    skills: Optional[List[str]] = None
    min_salary: Optional[float] = None
    remote_only: bool = False
    limit: int = Field(default=100, le=1000)
    offset: int = 0


class StatsResponse(BaseModel):
    """Schema for statistics response"""
    total_jobs: int
    jobs_by_country: dict
    jobs_by_industry: dict
    jobs_by_category: dict
    top_skills: List[dict]
    avg_salary_by_category: dict
