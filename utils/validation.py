"""
Data validation module
Validates job data before storage to ensure quality
"""
import os
from typing import Dict, Any, List, Tuple
from datetime import datetime
from dotenv import load_dotenv
from loguru import logger

load_dotenv()


class JobValidator:
    """Validator for job data quality"""

    def __init__(self):
        """Initialize validator with configuration"""
        self.min_description_length = int(os.getenv("MIN_DESCRIPTION_LENGTH", "50"))
        self.require_company_name = os.getenv("REQUIRE_COMPANY_NAME", "true").lower() == "true"
        self.require_location = os.getenv("REQUIRE_LOCATION", "true").lower() == "true"
        self.log_failures = os.getenv("LOG_VALIDATION_FAILURES", "true").lower() == "true"

        logger.info(f"✅ Job validator initialized (min_desc_length={self.min_description_length})")

    def validate(self, job_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate job data

        Args:
            job_data: Dictionary containing job information

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Required fields
        if not job_data.get("job_id"):
            errors.append("Missing required field: job_id")

        if not job_data.get("title"):
            errors.append("Missing required field: title")
        elif len(job_data["title"].strip()) < 3:
            errors.append("Job title too short (minimum 3 characters)")

        # Company name validation
        if self.require_company_name:
            if not job_data.get("company"):
                errors.append("Missing required field: company")
            elif len(job_data["company"].strip()) < 2:
                errors.append("Company name too short")
            elif job_data["company"].lower() in ["unknown", "n/a", "na", "none"]:
                errors.append("Invalid company name")

        # Location validation
        if self.require_location:
            if not job_data.get("location"):
                errors.append("Missing required field: location")
            elif len(job_data["location"].strip()) < 2:
                errors.append("Location too short")

        # Description validation
        description = job_data.get("description", "")
        if not description or len(description.strip()) < self.min_description_length:
            errors.append(
                f"Description too short (minimum {self.min_description_length} characters, "
                f"got {len(description.strip())})"
            )

        # Check for spam/invalid patterns
        if description:
            spam_indicators = [
                "viagra", "cialis", "casino", "poker",
                "click here", "limited time offer", "earn $$$"
            ]
            description_lower = description.lower()
            for spam in spam_indicators:
                if spam in description_lower:
                    errors.append(f"Potential spam detected: contains '{spam}'")
                    break

        # Country validation
        valid_countries = ["US", "CA", "IN", "AU"]  # Add more as needed
        if job_data.get("country") and job_data["country"] not in valid_countries:
            errors.append(f"Invalid country code: {job_data['country']}")

        # Salary validation
        salary_min = job_data.get("salary_min")
        salary_max = job_data.get("salary_max")

        if salary_min is not None:
            if not isinstance(salary_min, (int, float)) or salary_min < 0:
                errors.append(f"Invalid salary_min: {salary_min}")
            elif salary_min > 1_000_000:  # Sanity check
                errors.append(f"Salary min too high (>$1M): {salary_min}")

        if salary_max is not None:
            if not isinstance(salary_max, (int, float)) or salary_max < 0:
                errors.append(f"Invalid salary_max: {salary_max}")
            elif salary_max > 2_000_000:  # Sanity check
                errors.append(f"Salary max too high (>$2M): {salary_max}")

        if salary_min and salary_max and salary_min > salary_max:
            errors.append(f"Salary min ({salary_min}) > max ({salary_max})")

        # Skills validation
        skills = job_data.get("all_skills", [])
        if skills and not isinstance(skills, list):
            errors.append("Skills must be a list")
        elif skills and len(skills) > 100:  # Sanity check
            errors.append(f"Too many skills ({len(skills)}), possible extraction error")

        # Source URL validation
        source_url = job_data.get("source_url")
        if source_url:
            if not source_url.startswith(("http://", "https://")):
                errors.append(f"Invalid source URL format: {source_url}")

        # Date validation
        posted_date = job_data.get("posted_date")
        if posted_date:
            if isinstance(posted_date, str):
                try:
                    datetime.fromisoformat(posted_date.replace("Z", "+00:00"))
                except ValueError:
                    errors.append(f"Invalid posted_date format: {posted_date}")
            elif isinstance(posted_date, datetime):
                # Check if date is in the future
                if posted_date > datetime.utcnow():
                    errors.append("Posted date is in the future")

        is_valid = len(errors) == 0

        if not is_valid and self.log_failures:
            logger.warning(f"❌ Validation failed for job '{job_data.get('title', 'Unknown')}': {errors}")

        return is_valid, errors

    def sanitize(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize job data by cleaning and normalizing fields

        Args:
            job_data: Raw job data

        Returns:
            Sanitized job data
        """
        sanitized = job_data.copy()

        # Trim whitespace from string fields
        string_fields = ["title", "company", "location", "description", "category", "industry"]
        for field in string_fields:
            if field in sanitized and isinstance(sanitized[field], str):
                sanitized[field] = sanitized[field].strip()

        # Normalize company name
        if "company" in sanitized:
            company = sanitized["company"]
            # Remove common suffixes
            for suffix in [" Inc.", " LLC", " Ltd.", " Corporation", " Corp."]:
                if company.endswith(suffix):
                    company = company[:-len(suffix)].strip()
            sanitized["company"] = company

        # Ensure skills is a list
        if "all_skills" in sanitized and not isinstance(sanitized["all_skills"], list):
            sanitized["all_skills"] = []

        # Normalize country code to uppercase
        if "country" in sanitized and sanitized["country"]:
            sanitized["country"] = sanitized["country"].upper()

        # Remove duplicate skills
        if "all_skills" in sanitized and isinstance(sanitized["all_skills"], list):
            sanitized["all_skills"] = list(set(sanitized["all_skills"]))
            # Sort for consistency
            sanitized["all_skills"] = sorted(sanitized["all_skills"])

        if "skills_required" in sanitized and isinstance(sanitized["skills_required"], list):
            sanitized["skills_required"] = sorted(list(set(sanitized["skills_required"])))

        if "skills_preferred" in sanitized and isinstance(sanitized["skills_preferred"], list):
            sanitized["skills_preferred"] = sorted(list(set(sanitized["skills_preferred"])))

        # Ensure boolean fields are boolean
        if "remote" in sanitized:
            sanitized["remote"] = bool(sanitized["remote"])

        return sanitized

    def validate_batch(self, jobs: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Validate a batch of jobs

        Args:
            jobs: List of job dictionaries

        Returns:
            Tuple of (valid_jobs, invalid_jobs_with_errors)
        """
        valid_jobs = []
        invalid_jobs = []

        for job in jobs:
            is_valid, errors = self.validate(job)
            if is_valid:
                # Sanitize before adding to valid list
                valid_jobs.append(self.sanitize(job))
            else:
                invalid_jobs.append({
                    "job_data": job,
                    "errors": errors
                })

        logger.info(
            f"📊 Validation complete: {len(valid_jobs)} valid, "
            f"{len(invalid_jobs)} invalid out of {len(jobs)} total"
        )

        return valid_jobs, invalid_jobs


# Global validator instance
_validator: Optional[JobValidator] = None


def get_validator() -> JobValidator:
    """Get or create global validator instance"""
    global _validator
    if _validator is None:
        _validator = JobValidator()
    return _validator


def validate_job_data(job_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Convenience function to validate job data"""
    validator = get_validator()
    return validator.validate(job_data)


def sanitize_job_data(job_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function to sanitize job data"""
    validator = get_validator()
    return validator.sanitize(job_data)


if __name__ == "__main__":
    # Test validation
    validator = JobValidator()

    # Valid job
    valid_job = {
        "job_id": "test123",
        "title": "Senior Python Developer",
        "company": "Tech Corp Inc.",
        "location": "San Francisco, CA",
        "country": "US",
        "description": "We are looking for an experienced Python developer with 5+ years of experience. Must have strong knowledge of Django, Flask, and PostgreSQL.",
        "salary_min": 120000,
        "salary_max": 180000,
        "all_skills": ["Python", "Django", "PostgreSQL"],
        "remote": True,
        "source_url": "https://example.com/job/123"
    }

    is_valid, errors = validator.validate(valid_job)
    print(f"Valid job: {is_valid}, Errors: {errors}")

    # Invalid job
    invalid_job = {
        "job_id": "test456",
        "title": "XY",  # Too short
        "company": "",  # Missing
        "description": "Short",  # Too short
        "salary_min": 200000,
        "salary_max": 100000,  # Min > Max
    }

    is_valid, errors = validator.validate(invalid_job)
    print(f"\nInvalid job: {is_valid}")
    print(f"Errors: {errors}")

    # Test sanitization
    messy_job = {
        "title": "  Software Engineer  ",
        "company": "  Google Inc.  ",
        "all_skills": ["Python", "python", "PYTHON", "Java"],
        "country": "us",
        "remote": "true"
    }

    sanitized = validator.sanitize(messy_job)
    print(f"\nSanitized job: {sanitized}")
