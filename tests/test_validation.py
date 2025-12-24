"""
Tests for Job Validation
"""
import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.validation import JobValidator


@pytest.fixture
def validator():
    """Create a validator instance"""
    return JobValidator(min_description_length=50)


class TestJobValidator:
    """Test JobValidator functionality"""

    def test_valid_job(self, validator):
        """Test validation of a valid job"""
        job_data = {
            "title": "Software Engineer",
            "company": "Google",
            "location": "San Francisco, CA",
            "country": "US",
            "description": "We are looking for an experienced software engineer to join our team. " * 3,
            "salary_min": 120000,
            "salary_max": 180000,
            "source_url": "https://example.com/job"
        }

        is_valid, errors = validator.validate(job_data)

        assert is_valid == True
        assert len(errors) == 0

    def test_missing_required_fields(self, validator):
        """Test validation with missing required fields"""
        job_data = {
            "title": "",
            "company": "",
            "description": "Some description"
        }

        is_valid, errors = validator.validate(job_data)

        assert is_valid == False
        assert len(errors) > 0
        assert any("title" in error.lower() for error in errors)
        assert any("company" in error.lower() for error in errors)

    def test_description_too_short(self, validator):
        """Test validation with short description"""
        job_data = {
            "title": "Software Engineer",
            "company": "Google",
            "location": "San Francisco",
            "country": "US",
            "description": "Short"  # Less than 50 chars
        }

        is_valid, errors = validator.validate(job_data)

        assert is_valid == False
        assert any("description" in error.lower() for error in errors)

    def test_spam_detection(self, validator):
        """Test spam detection"""
        job_data = {
            "title": "Buy Viagra Now!",
            "company": "Spam Inc",
            "location": "Nowhere",
            "country": "US",
            "description": "Click here for amazing casino deals! Buy now!" * 5
        }

        is_valid, errors = validator.validate(job_data)

        assert is_valid == False
        assert any("spam" in error.lower() for error in errors)

    def test_salary_validation_min_greater_than_max(self, validator):
        """Test salary validation when min > max"""
        job_data = {
            "title": "Software Engineer",
            "company": "Google",
            "location": "San Francisco",
            "country": "US",
            "description": "Great opportunity for experienced engineers to work on challenging projects." * 2,
            "salary_min": 200000,
            "salary_max": 100000  # Invalid: min > max
        }

        is_valid, errors = validator.validate(job_data)

        assert is_valid == False
        assert any("salary" in error.lower() for error in errors)

    def test_salary_out_of_range(self, validator):
        """Test salary validation for unrealistic values"""
        job_data = {
            "title": "Software Engineer",
            "company": "Google",
            "location": "San Francisco",
            "country": "US",
            "description": "Great opportunity for experienced engineers." * 5,
            "salary_min": 100,  # Too low
            "salary_max": 5000000  # Too high
        }

        is_valid, errors = validator.validate(job_data)

        assert is_valid == False
        assert any("salary" in error.lower() or "range" in error.lower() for error in errors)

    def test_sanitize_company_name(self, validator):
        """Test company name sanitization"""
        job_data = {
            "company": "Google Inc.",
            "title": "Engineer",
            "location": "SF",
            "country": "US"
        }

        sanitized = validator.sanitize(job_data)

        assert "Inc." not in sanitized["company"]
        assert "google" in sanitized["company"].lower()

    def test_sanitize_skills_deduplication(self, validator):
        """Test skills deduplication"""
        job_data = {
            "all_skills": ["python", "Python", "PYTHON", "django", "Django"],
            "title": "Engineer",
            "company": "Google",
            "location": "SF",
            "country": "US"
        }

        sanitized = validator.sanitize(job_data)

        # Should remove duplicates (case-insensitive)
        assert len(sanitized["all_skills"]) < len(job_data["all_skills"])
        assert "python" in sanitized["all_skills"]

    def test_sanitize_country_code_normalization(self, validator):
        """Test country code normalization"""
        job_data = {
            "country": "us",  # lowercase
            "title": "Engineer",
            "company": "Google",
            "location": "SF"
        }

        sanitized = validator.sanitize(job_data)

        assert sanitized["country"] == "US"  # Should be uppercase

    def test_invalid_url_format(self, validator):
        """Test URL format validation"""
        job_data = {
            "title": "Software Engineer",
            "company": "Google",
            "location": "San Francisco",
            "country": "US",
            "description": "Great opportunity for software engineers with experience." * 3,
            "source_url": "not-a-valid-url"
        }

        is_valid, errors = validator.validate(job_data)

        assert is_valid == False
        assert any("url" in error.lower() for error in errors)

    def test_valid_https_url(self, validator):
        """Test that HTTPS URLs pass validation"""
        job_data = {
            "title": "Software Engineer",
            "company": "Google",
            "location": "San Francisco",
            "country": "US",
            "description": "Great opportunity for experienced engineers to work on challenging projects." * 2,
            "source_url": "https://example.com/job/123"
        }

        is_valid, errors = validator.validate(job_data)

        assert is_valid == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
