# Test Suite for Job Scraping System

This directory contains comprehensive tests for the Job Scraping System.

## Running Tests

### Run all tests:
```bash
pytest
```

### Run specific test file:
```bash
pytest tests/test_classifier.py
```

### Run tests with coverage:
```bash
pytest --cov=processors --cov=utils --cov-report=html
```

### Run tests in verbose mode:
```bash
pytest -v
```

### Run specific test:
```bash
pytest tests/test_classifier.py::TestJobClassifier::test_frontend_classification
```

## Test Files

- `test_classifier.py` - Tests for multi-label job classification
- `test_deduplication.py` - Tests for fuzzy matching deduplication
- `test_validation.py` - Tests for job data validation
- `test_auth.py` - Tests for authentication utilities

## Coverage Reports

After running tests with coverage, view the HTML report:
```bash
open htmlcov/index.html
```

## Writing New Tests

1. Create test file with `test_` prefix
2. Create test class with `Test` prefix
3. Create test methods with `test_` prefix
4. Use fixtures for common setup

Example:
```python
import pytest

@pytest.fixture
def my_fixture():
    return SomeObject()

class TestMyFeature:
    def test_something(self, my_fixture):
        assert my_fixture.method() == expected_value
```

## CI/CD Integration

Add to your CI/CD pipeline:
```yaml
test:
  script:
    - pip install -r requirements.txt
    - pytest --cov --cov-report=xml
```

## Test Coverage Goals

- **Unit Tests**: > 80% code coverage
- **Integration Tests**: Key workflows
- **Edge Cases**: Handle errors gracefully
