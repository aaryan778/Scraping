"""
Job Classification Processor
Classifies jobs into categories (Frontend, Backend, etc.) and industries (IT, Healthcare)
"""
import json
import logging
from typing import Optional, Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class JobClassifier:
    """Classify jobs into categories and industries"""

    def __init__(self, categories_path: str = "config/job_categories.json"):
        """Initialize job classifier"""
        self.categories = self._load_categories(categories_path)
        self.category_keywords = self._build_keyword_map()
        logger.info("✅ Job classifier initialized")

    def _load_categories(self, path: str) -> Dict:
        """Load job categories from JSON file"""
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"❌ Error loading categories: {e}")
            return {}

    def _build_keyword_map(self) -> Dict:
        """Build keyword map for classification"""
        keyword_map = {}

        for industry, categories in self.categories.items():
            for category, titles in categories.items():
                for title in titles:
                    # Extract keywords from job title
                    keywords = title.lower().split()
                    for keyword in keywords:
                        if keyword not in ['developer', 'engineer', 'specialist', 'analyst']:
                            if keyword not in keyword_map:
                                keyword_map[keyword] = []
                            keyword_map[keyword].append({
                                'industry': industry,
                                'category': category,
                                'title': title
                            })

        return keyword_map

    def classify_job(self, title: str, description: str = "") -> Dict:
        """
        Classify a job based on title and description

        Args:
            title: Job title
            description: Job description

        Returns:
            Dictionary with industry and category
        """
        title_lower = title.lower()
        description_lower = description.lower() if description else ""

        # Default classification
        result = {
            "industry": "IT",  # Default to IT
            "category": "Full Stack",  # Default category
            "confidence": 0.0
        }

        # Check for Healthcare keywords
        healthcare_keywords = [
            'healthcare', 'medical', 'health', 'clinical', 'hospital',
            'patient', 'ehr', 'emr', 'fhir', 'hl7', 'epic', 'cerner',
            'telehealth', 'pacs', 'radiology'
        ]

        if any(kw in title_lower or kw in description_lower for kw in healthcare_keywords):
            result["industry"] = "Healthcare"

        # Classify category based on IT roles
        if result["industry"] == "IT":
            # Frontend detection
            frontend_keywords = [
                'frontend', 'front-end', 'front end', 'react', 'vue', 'angular',
                'ui', 'ux', 'javascript', 'typescript', 'web developer', 'mobile'
            ]

            # Backend detection
            backend_keywords = [
                'backend', 'back-end', 'back end', 'python', 'java', 'node',
                'api', 'database', 'sql', 'devops', 'cloud', 'server'
            ]

            # Full stack detection
            fullstack_keywords = [
                'full stack', 'full-stack', 'fullstack', 'software engineer',
                'software developer'
            ]

            # Specialized detection
            specialized_keywords = {
                'data': ['data engineer', 'data scientist', 'machine learning', 'ai', 'ml'],
                'security': ['security', 'cybersecurity', 'infosec'],
                'qa': ['qa', 'quality assurance', 'test', 'sdet'],
                'devops': ['devops', 'sre', 'site reliability']
            }

            # Check for category matches
            if any(kw in title_lower for kw in frontend_keywords):
                result["category"] = "Frontend"
                result["confidence"] = 0.8
            elif any(kw in title_lower for kw in backend_keywords):
                result["category"] = "Backend"
                result["confidence"] = 0.8
            elif any(kw in title_lower for kw in fullstack_keywords):
                result["category"] = "Full Stack"
                result["confidence"] = 0.9
            else:
                # Check specialized categories
                for spec_cat, keywords in specialized_keywords.items():
                    if any(kw in title_lower for kw in keywords):
                        result["category"] = "Specialized"
                        result["confidence"] = 0.7
                        break

        # For Healthcare industry
        elif result["industry"] == "Healthcare":
            if any(kw in title_lower or kw in description_lower
                   for kw in ['data', 'analyst', 'analytics', 'bi']):
                result["category"] = "Healthcare Data"
            else:
                result["category"] = "Healthcare IT"

            result["confidence"] = 0.7

        return result

    def get_all_job_titles(self, industry: Optional[str] = None) -> list:
        """Get all job titles, optionally filtered by industry"""
        titles = []

        if industry:
            if industry in self.categories:
                for category, title_list in self.categories[industry].items():
                    titles.extend(title_list)
        else:
            for ind, categories in self.categories.items():
                for category, title_list in categories.items():
                    titles.extend(title_list)

        return titles


# Example usage
if __name__ == "__main__":
    classifier = JobClassifier()

    test_jobs = [
        "Senior React Developer",
        "Python Backend Engineer",
        "Full Stack Software Engineer",
        "Healthcare Data Analyst",
        "EHR Developer"
    ]

    for job in test_jobs:
        result = classifier.classify_job(job)
        print(f"{job}: {result}")
