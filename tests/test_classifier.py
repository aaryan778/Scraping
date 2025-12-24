"""
Tests for Job Classifier
"""
import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from processors.job_classifier import JobClassifier


@pytest.fixture
def classifier():
    """Create a classifier instance"""
    return JobClassifier()


class TestJobClassifier:
    """Test JobClassifier functionality"""

    def test_frontend_classification(self, classifier):
        """Test frontend developer classification"""
        result = classifier.classify_job(
            title="Senior React Developer",
            description="React, TypeScript, Redux, Next.js experience required. Build modern web applications."
        )

        assert result['industry'] == 'IT'
        assert result['primary_category'] == 'Frontend Development'
        assert result['classification_confidence'] > 0.5

    def test_backend_classification(self, classifier):
        """Test backend developer classification"""
        result = classifier.classify_job(
            title="Python Backend Engineer",
            description="Django, PostgreSQL, Redis, Docker, AWS. Build scalable APIs and microservices."
        )

        assert result['industry'] == 'IT'
        assert result['primary_category'] == 'Backend Development'
        assert result['classification_confidence'] > 0.5

    def test_fullstack_classification(self, classifier):
        """Test full stack developer classification"""
        result = classifier.classify_job(
            title="Full Stack Software Engineer",
            description="React frontend, Node.js backend, MongoDB, AWS deployment. Full stack development."
        )

        assert result['industry'] == 'IT'
        assert result['primary_category'] == 'Full Stack Development'
        assert result['classification_confidence'] > 0.3

    def test_devops_classification(self, classifier):
        """Test DevOps engineer classification"""
        result = classifier.classify_job(
            title="DevOps Engineer",
            description="Kubernetes, Terraform, AWS, CI/CD, Jenkins, Docker, monitoring and automation."
        )

        assert result['industry'] == 'IT'
        assert result['primary_category'] == 'Cloud & DevOps'
        assert result['classification_confidence'] > 0.5

    def test_healthcare_ehr_classification(self, classifier):
        """Test healthcare EHR classification"""
        result = classifier.classify_job(
            title="Epic EHR Developer",
            description="Epic implementation, EHR systems, clinical workflows, healthcare IT."
        )

        assert result['industry'] == 'Healthcare'
        assert 'EHR' in result['primary_category']
        assert result['classification_confidence'] > 0.4

    def test_healthcare_interoperability(self, classifier):
        """Test healthcare interoperability classification"""
        result = classifier.classify_job(
            title="FHIR Integration Engineer",
            description="FHIR, HL7 integration, healthcare interoperability, health information exchange."
        )

        assert result['industry'] == 'Healthcare'
        assert 'Interoperability' in result['primary_category']
        assert result['classification_confidence'] > 0.5

    def test_machine_learning_classification(self, classifier):
        """Test ML engineer classification"""
        result = classifier.classify_job(
            title="Machine Learning Engineer",
            description="PyTorch, TensorFlow, NLP, LLM, GenAI, deep learning, model training."
        )

        assert result['industry'] == 'IT'
        assert 'Machine Learning' in result['primary_category'] or 'AI' in result['primary_category']
        assert result['classification_confidence'] > 0.5

    def test_multi_label_classification(self, classifier):
        """Test that secondary categories are returned"""
        result = classifier.classify_job(
            title="Full Stack Developer with DevOps",
            description="React, Node.js, Docker, Kubernetes, AWS, CI/CD, full development lifecycle."
        )

        assert result['industry'] == 'IT'
        assert result['primary_category'] is not None
        assert isinstance(result['secondary_categories'], list)
        # Should have at least one secondary category given mixed skills
        assert len(result['secondary_categories']) >= 1

    def test_get_all_categories(self, classifier):
        """Test getting all categories"""
        it_categories = classifier.get_all_categories('IT')
        healthcare_categories = classifier.get_all_categories('Healthcare')

        assert len(it_categories) > 0
        assert len(healthcare_categories) > 0
        assert 'Frontend Development' in it_categories
        assert 'Backend Development' in it_categories

    def test_get_all_job_titles(self, classifier):
        """Test getting all job titles"""
        it_titles = classifier.get_all_job_titles('IT')
        healthcare_titles = classifier.get_all_job_titles('Healthcare')

        assert len(it_titles) > 0
        assert len(healthcare_titles) > 0
        assert 'Frontend Developer' in it_titles or 'React Developer' in it_titles
        assert 'EHR Developer' in healthcare_titles or 'Epic Developer' in healthcare_titles

    def test_validate_category(self, classifier):
        """Test category validation"""
        assert classifier.validate_category('Frontend Development', 'IT') == True
        assert classifier.validate_category('Invalid Category', 'IT') == False

    def test_confidence_score_range(self, classifier):
        """Test that confidence scores are in valid range"""
        result = classifier.classify_job(
            title="Software Engineer",
            description="Programming and development work."
        )

        assert 0.0 <= result['classification_confidence'] <= 1.0

    def test_empty_description(self, classifier):
        """Test classification with empty description"""
        result = classifier.classify_job(
            title="Software Developer",
            description=""
        )

        # Should still classify based on title
        assert result['industry'] is not None
        assert result['primary_category'] is not None

    def test_security_engineer_classification(self, classifier):
        """Test security engineer classification"""
        result = classifier.classify_job(
            title="Security Engineer",
            description="AWS security, IAM, CloudTrail, compliance, SIEM, penetration testing, cybersecurity."
        )

        assert result['industry'] == 'IT'
        assert 'Security' in result['primary_category']
        assert result['classification_confidence'] > 0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
