"""
Multi-Label Job Classification Processor
Classifies jobs with primary and secondary categories using weighted keyword scoring
"""
import json
from typing import Dict, List, Tuple
from collections import defaultdict
from loguru import logger


class JobClassifier:
    """Multi-label job classifier with confidence scoring"""

    def __init__(self, categories_path: str = "config/job_categories.json"):
        """Initialize job classifier"""
        self.categories = self._load_categories(categories_path)
        self.category_keywords = self._build_keyword_database()
        logger.info(f"✅ Job classifier initialized with {len(self.category_keywords)} keyword patterns")

    def _load_categories(self, path: str) -> Dict:
        """Load job categories from JSON file"""
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"❌ Error loading categories: {e}")
            return {}

    def _build_keyword_database(self) -> Dict:
        """
        Build comprehensive keyword database with weights

        Returns:
            Dict mapping keywords to their categories and weights
        """
        keyword_db = defaultdict(list)

        for industry, categories in self.categories.items():
            for category, job_titles in categories.items():
                # Extract keywords from job titles
                for title in job_titles:
                    title_lower = title.lower()

                    # Add exact title match (highest weight)
                    keyword_db[title_lower].append({
                        'industry': industry,
                        'category': category,
                        'weight': 10.0,
                        'source': 'exact_title'
                    })

                    # Add individual words (lower weight)
                    words = title_lower.split()
                    for word in words:
                        # Skip common words
                        if word not in ['developer', 'engineer', 'specialist', 'analyst', 'the', 'and', 'or']:
                            keyword_db[word].append({
                                'industry': industry,
                                'category': category,
                                'weight': 1.0,
                                'source': 'word'
                            })

        # Add industry-specific keyword patterns
        self._add_industry_keywords(keyword_db)

        return dict(keyword_db)

    def _add_industry_keywords(self, keyword_db: Dict):
        """Add industry and category-specific keywords with weights"""

        # Healthcare-specific keywords
        healthcare_keywords = {
            'healthcare': 5.0, 'medical': 5.0, 'clinical': 5.0, 'hospital': 4.0,
            'patient': 4.0, 'ehr': 8.0, 'emr': 8.0, 'fhir': 9.0, 'hl7': 9.0,
            'epic': 7.0, 'cerner': 7.0, 'meditech': 7.0, 'telehealth': 7.0,
            'telemedicine': 7.0, 'pacs': 7.0, 'dicom': 7.0, 'hipaa': 6.0
        }

        for keyword, weight in healthcare_keywords.items():
            keyword_db[keyword].append({
                'industry': 'Healthcare',
                'category': None,  # Industry-level keyword
                'weight': weight,
                'source': 'industry_keyword'
            })

        # IT category-specific keywords
        category_keywords = {
            # Frontend
            'Frontend Development': {
                'react': 7.0, 'vue': 7.0, 'angular': 7.0, 'frontend': 9.0,
                'ui': 6.0, 'ux': 6.0, 'javascript': 5.0, 'typescript': 5.0,
                'css': 4.0, 'html': 4.0, 'webpack': 5.0
            },
            # Backend
            'Backend Development': {
                'backend': 9.0, 'api': 6.0, 'database': 5.0, 'sql': 5.0,
                'postgresql': 6.0, 'mongodb': 6.0, 'redis': 5.0, 'kafka': 5.0
            },
            # Cloud & DevOps
            'Cloud & DevOps': {
                'devops': 9.0, 'kubernetes': 8.0, 'docker': 7.0, 'aws': 7.0,
                'azure': 7.0, 'gcp': 7.0, 'terraform': 7.0, 'ansible': 6.0,
                'ci/cd': 6.0, 'jenkins': 5.0, 'sre': 8.0, 'cloud': 6.0
            },
            # Data Engineering
            'Data Engineering': {
                'data': 6.0, 'etl': 8.0, 'pipeline': 6.0, 'spark': 7.0,
                'hadoop': 7.0, 'airflow': 7.0, 'snowflake': 7.0, 'databricks': 7.0,
                'warehouse': 6.0
            },
            # AI & ML
            'AI & Machine Learning': {
                'machine learning': 9.0, 'ai': 7.0, 'ml': 7.0, 'deep learning': 8.0,
                'nlp': 8.0, 'pytorch': 7.0, 'tensorflow': 7.0, 'llm': 8.0,
                'genai': 8.0, 'mlops': 7.0
            },
            # Security
            'Security Engineering': {
                'security': 8.0, 'cybersecurity': 9.0, 'penetration': 7.0,
                'ethical hacker': 8.0, 'soc': 7.0, 'firewall': 6.0
            },
            # Mobile
            'Mobile Development': {
                'mobile': 8.0, 'ios': 9.0, 'android': 9.0, 'swift': 8.0,
                'kotlin': 8.0, 'react native': 8.0, 'flutter': 8.0
            }
        }

        for category, keywords in category_keywords.items():
            for keyword, weight in keywords.items():
                keyword_db[keyword].append({
                    'industry': 'IT',
                    'category': category,
                    'weight': weight,
                    'source': 'category_keyword'
                })

    def classify_job(
        self,
        title: str,
        description: str = "",
        return_all_scores: bool = False
    ) -> Dict:
        """
        Classify job with multi-label support

        Args:
            title: Job title
            description: Job description
            return_all_scores: Return scores for all categories

        Returns:
            Classification result with primary, secondary categories and confidence
        """
        text = (title + " " + description).lower()

        # Calculate scores for each category
        category_scores = self._calculate_category_scores(text)

        if not category_scores:
            return self._default_classification()

        # Determine primary category (highest score)
        sorted_scores = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)
        primary_category, primary_score = sorted_scores[0]

        # Determine industry
        industry = self._determine_industry(primary_category, text)

        # Determine secondary categories (scores > 30% of primary and > threshold)
        secondary_threshold = primary_score * 0.3
        secondary_categories = [
            cat for cat, score in sorted_scores[1:6]  # Top 5 additional
            if score >= secondary_threshold and score >= 5.0
        ]

        # Calculate confidence (0.0 to 1.0)
        max_possible_score = 50.0  # Theoretical max
        confidence = min(primary_score / max_possible_score, 1.0)

        result = {
            "industry": industry,
            "primary_category": primary_category,
            "secondary_categories": secondary_categories,
            "classification_confidence": round(confidence, 3),
            "primary_score": round(primary_score, 2)
        }

        if return_all_scores:
            result["all_scores"] = {cat: round(score, 2) for cat, score in sorted_scores[:10]}

        logger.debug(
            f"📊 Classified '{title}': {primary_category} "
            f"(confidence: {confidence:.2%}, secondary: {len(secondary_categories)})"
        )

        return result

    def _calculate_category_scores(self, text: str) -> Dict[str, float]:
        """
        Calculate weighted scores for all categories

        Args:
            text: Combined title and description (lowercase)

        Returns:
            Dict mapping category names to scores
        """
        scores = defaultdict(float)

        # Check each keyword in our database
        for keyword, matches in self.category_keywords.items():
            if keyword in text:
                for match in matches:
                    category = match['category']
                    if category:  # Skip industry-only keywords
                        weight = match['weight']

                        # Boost weight if keyword is in title vs just description
                        if keyword in text[:200]:  # Rough title area
                            weight *= 1.5

                        scores[category] += weight

        return dict(scores)

    def _determine_industry(self, primary_category: str, text: str) -> str:
        """
        Determine industry based on primary category and keywords

        Args:
            primary_category: Primary category name
            text: Job text

        Returns:
            Industry name
        """
        # Check if primary category belongs to Healthcare
        if any(primary_category in cats for cats in self.categories.get('Healthcare', {}).values()):
            return 'Healthcare'

        # Check for healthcare keywords in text
        healthcare_keywords = [
            'healthcare', 'medical', 'clinical', 'hospital', 'patient',
            'ehr', 'emr', 'fhir', 'hl7', 'epic', 'cerner', 'hipaa'
        ]

        healthcare_count = sum(1 for kw in healthcare_keywords if kw in text)

        # If 3+ healthcare keywords, classify as Healthcare
        if healthcare_count >= 3:
            return 'Healthcare'

        # Default to IT
        return 'IT'

    def _default_classification(self) -> Dict:
        """Return default classification when no matches found"""
        return {
            "industry": "IT",
            "primary_category": "Full Stack Development",
            "secondary_categories": [],
            "classification_confidence": 0.0,
            "primary_score": 0.0
        }

    def get_all_categories(self, industry: str = None) -> List[str]:
        """
        Get all available categories

        Args:
            industry: Filter by industry (IT or Healthcare)

        Returns:
            List of category names
        """
        categories = []

        if industry:
            categories = list(self.categories.get(industry, {}).keys())
        else:
            for ind_categories in self.categories.values():
                categories.extend(ind_categories.keys())

        return categories

    def validate_category(self, category: str, industry: str = None) -> bool:
        """
        Check if a category is valid

        Args:
            category: Category name
            industry: Optional industry filter

        Returns:
            True if valid
        """
        all_categories = self.get_all_categories(industry)
        return category in all_categories


# Example usage
if __name__ == "__main__":
    classifier = JobClassifier()

    test_jobs = [
        ("Senior React Developer", "Looking for React expert with TypeScript and Redux experience"),
        ("Python Backend Engineer", "Django, PostgreSQL, Redis, Docker, AWS"),
        ("Full Stack Software Engineer", "React frontend, Node.js backend, MongoDB"),
        ("DevOps Engineer", "Kubernetes, Terraform, AWS, CI/CD, Jenkins"),
        ("Healthcare Data Analyst", "Epic, Cerner, HL7, FHIR, clinical analytics"),
        ("Machine Learning Engineer", "PyTorch, TensorFlow, NLP, LLM, GenAI"),
        ("Cloud Security Engineer", "AWS security, IAM, CloudTrail, compliance, SIEM")
    ]

    for title, description in test_jobs:
        result = classifier.classify_job(title, description, return_all_scores=True)
        print(f"\n{title}:")
        print(f"  Industry: {result['industry']}")
        print(f"  Primary: {result['primary_category']} (score: {result['primary_score']})")
        print(f"  Secondary: {result['secondary_categories']}")
        print(f"  Confidence: {result['classification_confidence']:.1%}")
        if 'all_scores' in result:
            print(f"  Top scores: {list(result['all_scores'].items())[:3]}")
