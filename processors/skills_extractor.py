"""
Skills Extraction Processor
Extracts technical skills from job descriptions using:
1. Rule-based matching with skills database
2. NLP with spaCy (optional)
3. Pattern matching for common skill formats
"""
import json
import re
import logging
from typing import List, Dict, Set
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SkillsExtractor:
    """Extract skills from job descriptions"""

    def __init__(self, skills_db_path: str = "config/skills_database.json"):
        """Initialize skills extractor"""
        self.skills_db = self._load_skills_database(skills_db_path)
        self.all_skills = self._flatten_skills()
        logger.info(f"✅ Loaded {len(self.all_skills)} skills from database")

    def _load_skills_database(self, path: str) -> Dict:
        """Load skills database from JSON file"""
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"❌ Error loading skills database: {e}")
            return {}

    def _flatten_skills(self) -> Set[str]:
        """Flatten all skills from database into a single set"""
        skills = set()
        for category, skill_list in self.skills_db.items():
            skills.update([skill.lower() for skill in skill_list])
        return skills

    def extract_skills(self, text: str) -> Dict[str, List[str]]:
        """
        Extract skills from text

        Args:
            text: Job description or any text

        Returns:
            Dictionary with categorized skills
        """
        if not text:
            return {"all_skills": [], "required": [], "preferred": []}

        text_lower = text.lower()
        found_skills = set()

        # Method 1: Direct matching with skills database
        for skill in self.all_skills:
            # Use word boundaries for accurate matching
            pattern = r'\b' + re.escape(skill) + r'\b'
            if re.search(pattern, text_lower, re.IGNORECASE):
                found_skills.add(skill)

        # Method 2: Pattern-based extraction for common formats
        # e.g., "experience with X", "proficient in Y", "knowledge of Z"
        patterns = [
            r'experience (?:with|in)\s+([A-Za-z0-9\.\+\#\-\s]+)',
            r'proficient (?:with|in)\s+([A-Za-z0-9\.\+\#\-\s]+)',
            r'knowledge of\s+([A-Za-z0-9\.\+\#\-\s]+)',
            r'skilled in\s+([A-Za-z0-9\.\+\#\-\s]+)',
            r'expertise in\s+([A-Za-z0-9\.\+\#\-\s]+)',
            r'familiar with\s+([A-Za-z0-9\.\+\#\-\s]+)',
            r'understanding of\s+([A-Za-z0-9\.\+\#\-\s]+)',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                # Check if matched text contains known skills
                for skill in self.all_skills:
                    if skill in match:
                        found_skills.add(skill)

        # Method 3: Extract from bullet points and lists
        # Common in job descriptions: "- Python", "• Java", etc.
        bullet_pattern = r'[•\-\*]\s*([A-Za-z0-9\.\+\#\-\s]+?)(?:\n|,|;|$)'
        bullet_matches = re.findall(bullet_pattern, text)
        for match in bullet_matches:
            match_lower = match.lower().strip()
            for skill in self.all_skills:
                if skill in match_lower:
                    found_skills.add(skill)

        # Categorize skills
        categorized_skills = self._categorize_skills(found_skills)

        # Separate required vs preferred (heuristic-based)
        required, preferred = self._classify_required_preferred(text_lower, found_skills)

        return {
            "all_skills": sorted(list(found_skills)),
            "required": sorted(required),
            "preferred": sorted(preferred),
            "categorized": categorized_skills
        }

    def _categorize_skills(self, skills: Set[str]) -> Dict[str, List[str]]:
        """Categorize skills into their respective categories"""
        categorized = {}

        for category, skill_list in self.skills_db.items():
            category_skills = []
            for skill in skills:
                if skill in [s.lower() for s in skill_list]:
                    category_skills.append(skill)

            if category_skills:
                categorized[category] = sorted(category_skills)

        return categorized

    def _classify_required_preferred(self, text: str, skills: Set[str]) -> tuple:
        """
        Classify skills as required or preferred based on context

        Args:
            text: Job description text (lowercase)
            skills: Set of found skills

        Returns:
            Tuple of (required_skills, preferred_skills)
        """
        required = set()
        preferred = set()

        # Keywords that indicate required skills
        required_keywords = [
            'required', 'must have', 'mandatory', 'essential',
            'minimum qualification', 'necessary', 'needed'
        ]

        # Keywords that indicate preferred skills
        preferred_keywords = [
            'preferred', 'nice to have', 'bonus', 'plus',
            'desirable', 'advantageous', 'beneficial'
        ]

        # Split text into sections
        sections = re.split(r'\n\n+', text)

        for section in sections:
            section_lower = section.lower()

            # Check if section mentions required or preferred
            is_required_section = any(kw in section_lower for kw in required_keywords)
            is_preferred_section = any(kw in section_lower for kw in preferred_keywords)

            # Find skills in this section
            section_skills = set()
            for skill in skills:
                if skill in section_lower:
                    section_skills.add(skill)

            # Classify based on section type
            if is_required_section:
                required.update(section_skills)
            elif is_preferred_section:
                preferred.update(section_skills)

        # If we couldn't determine, put everything in required
        if not required and not preferred:
            required = skills
        # If some skills weren't classified, add to required
        elif required or preferred:
            unclassified = skills - required - preferred
            required.update(unclassified)

        return list(required), list(preferred)

    def extract_experience_level(self, text: str) -> str:
        """
        Extract experience level from job description

        Returns: 'Junior', 'Mid', 'Senior', 'Lead', or 'Unknown'
        """
        text_lower = text.lower()

        # Senior level indicators
        senior_keywords = [
            'senior', 'sr.', 'sr ', 'lead', 'principal',
            'staff', 'architect', '5+ years', '7+ years', '10+ years'
        ]

        # Junior level indicators
        junior_keywords = [
            'junior', 'jr.', 'jr ', 'entry level', 'entry-level',
            'graduate', 'associate', '0-2 years', 'intern'
        ]

        # Mid level indicators
        mid_keywords = [
            'mid level', 'mid-level', 'intermediate',
            '2-5 years', '3-5 years', '3+ years'
        ]

        # Check title first
        title = text.split('\n')[0].lower() if '\n' in text else text[:100].lower()

        if any(kw in title for kw in senior_keywords):
            return 'Senior'
        elif any(kw in title for kw in junior_keywords):
            return 'Junior'
        elif any(kw in title for kw in mid_keywords):
            return 'Mid'

        # Check full description
        if any(kw in text_lower for kw in senior_keywords):
            return 'Senior'
        elif any(kw in text_lower for kw in junior_keywords):
            return 'Junior'
        elif any(kw in text_lower for kw in mid_keywords):
            return 'Mid'

        return 'Unknown'

    def extract_salary(self, text: str) -> Dict:
        """
        Extract salary information from text

        Returns: Dictionary with min, max, and currency
        """
        salary_info = {
            "min": None,
            "max": None,
            "currency": "USD"
        }

        # Patterns for salary
        patterns = [
            r'\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*-\s*\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # $100,000 - $150,000
            r'(\d{1,3}(?:,\d{3})*)\s*-\s*(\d{1,3}(?:,\d{3})*)\s*(?:USD|dollars)',  # 100,000 - 150,000 USD
            r'\$(\d{1,3}(?:,\d{3})*(?:k|K))\s*-\s*\$(\d{1,3}(?:,\d{3})*(?:k|K))',  # $100k - $150k
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    min_sal = match.group(1).replace(',', '').replace('k', '000').replace('K', '000')
                    max_sal = match.group(2).replace(',', '').replace('k', '000').replace('K', '000')

                    salary_info["min"] = float(min_sal)
                    salary_info["max"] = float(max_sal)
                    break
                except:
                    continue

        return salary_info


# Example usage
if __name__ == "__main__":
    extractor = SkillsExtractor()

    sample_text = """
    We are looking for a Senior Python Developer with experience in Django and FastAPI.

    Required skills:
    - Python (5+ years)
    - Django, Flask, or FastAPI
    - PostgreSQL or MySQL
    - Docker and Kubernetes
    - AWS or Azure

    Nice to have:
    - React or Vue.js
    - GraphQL
    - Microservices architecture

    Salary: $120,000 - $180,000
    """

    result = extractor.extract_skills(sample_text)
    print("Skills found:", json.dumps(result, indent=2))

    level = extractor.extract_experience_level(sample_text)
    print(f"\nExperience Level: {level}")

    salary = extractor.extract_salary(sample_text)
    print(f"Salary: {salary}")
