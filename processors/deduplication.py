"""
Job deduplication module using fuzzy matching
Detects and merges duplicate job postings from different sources
"""
import os
from typing import List, Dict, Any, Optional, Tuple
from rapidfuzz import fuzz
from loguru import logger
from dotenv import load_dotenv

load_dotenv()


class JobDeduplicator:
    """Deduplicates jobs using fuzzy string matching"""

    def __init__(self):
        """Initialize deduplicator"""
        self.threshold = int(os.getenv("FUZZY_MATCH_THRESHOLD", "85"))
        self.enabled = os.getenv("ENABLE_DEDUPLICATION", "true").lower() == "true"

        logger.info(
            f"✅ Job deduplicator initialized "
            f"(threshold={self.threshold}%, enabled={self.enabled})"
        )

    def is_duplicate(
        self,
        job1: Dict[str, Any],
        job2: Dict[str, Any],
        check_fields: Optional[List[str]] = None
    ) -> Tuple[bool, float]:
        """
        Check if two jobs are duplicates

        Args:
            job1: First job dictionary
            job2: Second job dictionary
            check_fields: Fields to check (default: title, company, location)

        Returns:
            Tuple of (is_duplicate, similarity_score)
        """
        if not self.enabled:
            return False, 0.0

        if check_fields is None:
            check_fields = ["title", "company", "location"]

        scores = []

        for field in check_fields:
            val1 = str(job1.get(field, "")).lower().strip()
            val2 = str(job2.get(field, "")).lower().strip()

            if not val1 or not val2:
                # If either field is empty, skip it
                continue

            # Use token_sort_ratio for better matching
            # (handles word order differences)
            score = fuzz.token_sort_ratio(val1, val2)
            scores.append(score)

        if not scores:
            return False, 0.0

        # Average similarity across all fields
        avg_score = sum(scores) / len(scores)

        is_dup = avg_score >= self.threshold

        if is_dup:
            logger.debug(
                f"🔍 Duplicate detected: '{job1.get('title')}' @ '{job1.get('company')}' "
                f"matches '{job2.get('title')}' @ '{job2.get('company')}' "
                f"(score: {avg_score:.1f}%)"
            )

        return is_dup, avg_score

    def find_duplicates(
        self,
        new_job: Dict[str, Any],
        existing_jobs: List[Dict[str, Any]]
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Find all duplicates of a job in a list of existing jobs

        Args:
            new_job: New job to check
            existing_jobs: List of existing jobs

        Returns:
            List of tuples (duplicate_job, similarity_score)
        """
        if not self.enabled:
            return []

        duplicates = []

        for existing_job in existing_jobs:
            is_dup, score = self.is_duplicate(new_job, existing_job)
            if is_dup:
                duplicates.append((existing_job, score))

        return duplicates

    def deduplicate_batch(
        self,
        jobs: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Deduplicate a batch of jobs

        Args:
            jobs: List of job dictionaries

        Returns:
            Tuple of (unique_jobs, duplicate_jobs)
        """
        if not self.enabled:
            return jobs, []

        unique_jobs = []
        duplicates = []
        seen_signatures = set()

        for job in jobs:
            # Create a signature for quick dedup check
            signature = self._create_job_signature(job)

            if signature in seen_signatures:
                duplicates.append(job)
                continue

            # Check against existing unique jobs using fuzzy matching
            is_duplicate_of_existing = False
            for unique_job in unique_jobs:
                is_dup, score = self.is_duplicate(job, unique_job)
                if is_dup:
                    is_duplicate_of_existing = True
                    duplicates.append(job)
                    logger.debug(
                        f"🔍 Filtered duplicate: {job.get('title')} @ {job.get('company')} "
                        f"(matches existing, score: {score:.1f}%)"
                    )
                    break

            if not is_duplicate_of_existing:
                unique_jobs.append(job)
                seen_signatures.add(signature)

        logger.info(
            f"📊 Deduplication complete: {len(unique_jobs)} unique jobs, "
            f"{len(duplicates)} duplicates removed from {len(jobs)} total"
        )

        return unique_jobs, duplicates

    def _create_job_signature(self, job: Dict[str, Any]) -> str:
        """
        Create a quick signature for a job (for exact dedup)

        Args:
            job: Job dictionary

        Returns:
            Signature string
        """
        # Normalize and create signature
        title = str(job.get("title", "")).lower().strip()
        company = str(job.get("company", "")).lower().strip()
        location = str(job.get("location", "")).lower().strip()

        return f"{title}|{company}|{location}"

    def merge_duplicate_jobs(
        self,
        primary_job: Dict[str, Any],
        duplicate_jobs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Merge duplicate jobs into a single record, keeping best information

        Args:
            primary_job: The primary job record
            duplicate_jobs: List of duplicate jobs to merge

        Returns:
            Merged job dictionary
        """
        merged = primary_job.copy()

        # Track all sources
        all_sources = [primary_job.get("source_platform", "Unknown")]
        all_urls = [primary_job.get("source_url", "")]

        for dup_job in duplicate_jobs:
            # Collect sources
            source = dup_job.get("source_platform", "Unknown")
            url = dup_job.get("source_url", "")

            if source not in all_sources:
                all_sources.append(source)
            if url and url not in all_urls:
                all_urls.append(url)

            # Prefer non-empty descriptions
            if not merged.get("description") and dup_job.get("description"):
                merged["description"] = dup_job["description"]

            # Prefer jobs with salary info
            if not merged.get("salary_min") and dup_job.get("salary_min"):
                merged["salary_min"] = dup_job["salary_min"]
                merged["salary_max"] = dup_job.get("salary_max")
                merged["salary_currency"] = dup_job.get("salary_currency")

            # Merge skills (combine and deduplicate)
            if dup_job.get("all_skills"):
                existing_skills = set(merged.get("all_skills", []))
                new_skills = set(dup_job.get("all_skills", []))
                merged["all_skills"] = sorted(list(existing_skills | new_skills))

        # Add metadata about sources
        merged["_dedup_sources"] = all_sources
        merged["_dedup_source_urls"] = [url for url in all_urls if url]
        merged["_dedup_count"] = len(duplicate_jobs) + 1

        logger.info(
            f"🔗 Merged {len(duplicate_jobs)} duplicates into: "
            f"'{merged.get('title')}' @ '{merged.get('company')}' "
            f"(sources: {', '.join(all_sources)})"
        )

        return merged

    def normalize_company_name(self, company: str) -> str:
        """
        Normalize company name for better matching

        Args:
            company: Company name

        Returns:
            Normalized company name
        """
        if not company:
            return ""

        normalized = company.lower().strip()

        # Remove common suffixes
        suffixes = [
            " inc.", " inc", " llc", " ltd.", " ltd", " corp.",
            " corp", " corporation", " limited", " company",
            " co.", " co", " l.l.c.", " l.p.", " plc"
        ]

        for suffix in suffixes:
            if normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)].strip()

        # Remove extra whitespace
        normalized = " ".join(normalized.split())

        return normalized

    def get_stats(self) -> Dict[str, Any]:
        """Get deduplication statistics"""
        return {
            "enabled": self.enabled,
            "threshold": self.threshold,
            "algorithm": "rapidfuzz token_sort_ratio"
        }


# Global deduplicator instance
_deduplicator: Optional[JobDeduplicator] = None


def get_deduplicator() -> JobDeduplicator:
    """Get or create global deduplicator instance"""
    global _deduplicator
    if _deduplicator is None:
        _deduplicator = JobDeduplicator()
    return _deduplicator


def is_duplicate_job(job1: Dict[str, Any], job2: Dict[str, Any]) -> Tuple[bool, float]:
    """Convenience function to check if jobs are duplicates"""
    deduplicator = get_deduplicator()
    return deduplicator.is_duplicate(job1, job2)


def deduplicate_jobs(jobs: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Convenience function to deduplicate a batch of jobs"""
    deduplicator = get_deduplicator()
    return deduplicator.deduplicate_batch(jobs)


if __name__ == "__main__":
    # Test deduplication
    deduplicator = JobDeduplicator()

    # Test jobs with slight variations
    job1 = {
        "title": "Senior Python Developer",
        "company": "Google Inc.",
        "location": "Mountain View, CA"
    }

    job2 = {
        "title": "Sr. Python Developer",
        "company": "Google",
        "location": "Mountain View, California"
    }

    job3 = {
        "title": "Java Developer",
        "company": "Amazon",
        "location": "Seattle, WA"
    }

    is_dup, score = deduplicator.is_duplicate(job1, job2)
    print(f"Job1 vs Job2: is_duplicate={is_dup}, score={score:.1f}%")

    is_dup, score = deduplicator.is_duplicate(job1, job3)
    print(f"Job1 vs Job3: is_duplicate={is_dup}, score={score:.1f}%")

    # Test batch deduplication
    jobs = [job1, job2, job3]
    unique, duplicates = deduplicator.deduplicate_batch(jobs)
    print(f"\nBatch dedup: {len(unique)} unique, {len(duplicates)} duplicates")

    # Test company normalization
    companies = ["Google Inc.", "Google LLC", "Google Corporation", "Google"]
    for company in companies:
        normalized = deduplicator.normalize_company_name(company)
        print(f"{company} → {normalized}")
