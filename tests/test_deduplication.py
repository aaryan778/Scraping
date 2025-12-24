"""
Tests for Job Deduplication
"""
import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from processors.deduplication import JobDeduplicator


@pytest.fixture
def deduplicator():
    """Create a deduplicator instance with default 85% threshold"""
    return JobDeduplicator(threshold=85)


class TestJobDeduplicator:
    """Test JobDeduplicator functionality"""

    def test_exact_duplicate(self, deduplicator):
        """Test exact duplicate detection"""
        job1 = {
            "title": "Software Engineer",
            "company": "Google",
            "location": "San Francisco, CA"
        }
        job2 = {
            "title": "Software Engineer",
            "company": "Google",
            "location": "San Francisco, CA"
        }

        is_dup, score = deduplicator.is_duplicate(job1, job2)

        assert is_dup == True
        assert score == 100.0

    def test_not_duplicate(self, deduplicator):
        """Test non-duplicate jobs"""
        job1 = {
            "title": "Frontend Developer",
            "company": "Google",
            "location": "San Francisco, CA"
        }
        job2 = {
            "title": "Backend Engineer",
            "company": "Microsoft",
            "location": "Seattle, WA"
        }

        is_dup, score = deduplicator.is_duplicate(job1, job2)

        assert is_dup == False
        assert score < 85.0

    def test_title_variation(self, deduplicator):
        """Test that title variations are detected as duplicates"""
        job1 = {
            "title": "Senior Software Engineer",
            "company": "Google",
            "location": "San Francisco, CA"
        }
        job2 = {
            "title": "Software Engineer (Senior)",
            "company": "Google",
            "location": "San Francisco, CA"
        }

        is_dup, score = deduplicator.is_duplicate(job1, job2)

        # Should be duplicate due to high similarity in company and location
        assert is_dup == True

    def test_case_insensitive(self, deduplicator):
        """Test case-insensitive matching"""
        job1 = {
            "title": "Software Engineer",
            "company": "GOOGLE",
            "location": "San Francisco"
        }
        job2 = {
            "title": "software engineer",
            "company": "google",
            "location": "san francisco"
        }

        is_dup, score = deduplicator.is_duplicate(job1, job2)

        assert is_dup == True
        assert score == 100.0

    def test_company_suffix_normalization(self, deduplicator):
        """Test company suffix normalization"""
        normalized1 = deduplicator.normalize_company("Google Inc.")
        normalized2 = deduplicator.normalize_company("Google")

        assert normalized1 == normalized2

    def test_location_variation(self, deduplicator):
        """Test location variations"""
        job1 = {
            "title": "Software Engineer",
            "company": "Google",
            "location": "San Francisco, CA"
        }
        job2 = {
            "title": "Software Engineer",
            "company": "Google",
            "location": "San Francisco, California"
        }

        is_dup, score = deduplicator.is_duplicate(job1, job2)

        # Should be duplicate due to fuzzy matching
        assert is_dup == True

    def test_merge_duplicate_jobs(self, deduplicator):
        """Test merging duplicate job data"""
        primary_job = {
            "title": "Software Engineer",
            "company": "Google",
            "location": "San Francisco, CA",
            "description": "Short description",
            "all_skills": ["python", "django"],
            "source_platform": "LinkedIn",
            "source_url": "https://linkedin.com/job1"
        }

        duplicate_jobs = [{
            "title": "Software Engineer",
            "company": "Google",
            "location": "San Francisco, CA",
            "description": "Much longer and more detailed description about the role",
            "all_skills": ["python", "flask", "docker"],
            "source_platform": "Indeed",
            "source_url": "https://indeed.com/job2",
            "salary_min": 120000,
            "salary_max": 180000
        }]

        merged = deduplicator.merge_duplicate_jobs(primary_job, duplicate_jobs)

        # Should prefer longer description
        assert "detailed" in merged["description"]

        # Should merge skills
        assert "python" in merged["all_skills"]
        assert "django" in merged["all_skills"]
        assert "flask" in merged["all_skills"]
        assert "docker" in merged["all_skills"]

        # Should track sources
        assert "LinkedIn" in merged["_dedup_sources"]
        assert "Indeed" in merged["_dedup_sources"]

        # Should have salary info
        assert merged["salary_min"] == 120000

    def test_threshold_sensitivity(self):
        """Test different thresholds"""
        strict_dedup = JobDeduplicator(threshold=95)
        lenient_dedup = JobDeduplicator(threshold=70)

        job1 = {
            "title": "Senior Software Engineer",
            "company": "Google",
            "location": "San Francisco"
        }
        job2 = {
            "title": "Software Engineer",
            "company": "Google",
            "location": "San Francisco"
        }

        strict_dup, strict_score = strict_dedup.is_duplicate(job1, job2)
        lenient_dup, lenient_score = lenient_dedup.is_duplicate(job1, job2)

        # Strict threshold might not match, lenient should
        assert lenient_dup == True
        # Scores should be the same, just different thresholds
        assert strict_score == lenient_score

    def test_empty_fields(self, deduplicator):
        """Test handling of empty fields"""
        job1 = {
            "title": "Software Engineer",
            "company": "",
            "location": "San Francisco"
        }
        job2 = {
            "title": "Software Engineer",
            "company": "",
            "location": "San Francisco"
        }

        is_dup, score = deduplicator.is_duplicate(job1, job2)

        # Should still work with empty fields
        assert isinstance(is_dup, bool)
        assert isinstance(score, float)

    def test_missing_fields(self, deduplicator):
        """Test handling of missing fields"""
        job1 = {
            "title": "Software Engineer"
        }
        job2 = {
            "title": "Software Engineer"
        }

        is_dup, score = deduplicator.is_duplicate(job1, job2)

        # Should handle missing fields gracefully
        assert isinstance(is_dup, bool)
        assert isinstance(score, float)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
