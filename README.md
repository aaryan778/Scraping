# Job Scraping System

An automated job scraping and analysis system that collects job postings, extracts skills, categorizes positions, and provides both a web dashboard and API for accessing the data.

## What This Does

This system automatically:
- Scrapes job postings from Google Jobs (which pulls from Indeed, LinkedIn, Glassdoor, etc.)
- Extracts required and preferred skills from job descriptions
- Categorizes jobs into 14 different specialties (8 IT, 6 Healthcare)
- Removes duplicate postings from different sources
- Checks if jobs are still active
- Stores everything in a PostgreSQL database
- Provides a web dashboard to view and export data
- Offers a REST API for programmatic access

## Features

- **Automated Scraping**: Runs hourly to keep job data fresh
- **Smart Classification**: Automatically categorizes jobs with confidence scores
- **Duplicate Detection**: Finds and merges the same job posted on multiple sites
- **Skills Extraction**: Identifies 500+ technical skills from job descriptions
- **Multi-Country**: Supports US, Canada, India, and Australia
- **Data Validation**: Filters out spam and incomplete postings
- **Dashboard**: Interactive web interface with charts and export options
- **API**: RESTful API with authentication and caching
- **Database Backups**: Automatic daily backups with retention policy

## System Requirements

- Python 3.9 or higher
- PostgreSQL 16 or higher
- Redis 7 or higher (for caching)
- 2GB RAM minimum
- Linux, macOS, or Windows

## Installation

### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone <your-repo-url>
cd Scraping

# Copy environment file
cp .env.example .env

# Edit .env with your settings (see Configuration section)
nano .env

# Start everything with Docker
docker-compose up -d

# Initialize database
docker-compose exec postgres psql -U jobscraper -d jobs_db < init.sql
```

### Option 2: Manual Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd Scraping

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browser
playwright install chromium

# Copy environment file
cp .env.example .env

# Edit .env file with your database credentials
nano .env
```

## Configuration

### Basic Setup

Edit the `.env` file with your settings:

```bash
# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=jobs_db
POSTGRES_USER=jobscraper
POSTGRES_PASSWORD=your_password_here

# Redis Cache
REDIS_HOST=localhost
REDIS_PORT=6379

# Scraping
SCRAPE_INTERVAL_HOURS=2
MAX_JOBS_PER_SEARCH=50
```

### Security Setup (Recommended for Production)

1. **Generate a secure password hash for the dashboard:**
```bash
python utils/auth.py your-secure-password
# Copy the output hash to your .env file
```

2. **Add to `.env`:**
```bash
# Dashboard Authentication
DASHBOARD_AUTH_ENABLED=true
DASHBOARD_USERNAME=admin
DASHBOARD_PASSWORD_HASH=<paste-hash-here>

# API Authentication
API_AUTH_ENABLED=true
API_KEY=<generate-random-key>
```

## Usage

### Initialize the Database

```bash
# Create database tables
python main.py --init-db
```

### Run One-Time Scraping

```bash
# Scrape jobs once
python main.py --scrape
```

### Start Automated Scheduler

```bash
# Run scraper every hour
python main.py --schedule
```

### Start the Dashboard

```bash
# Start web dashboard on port 8501
python main.py --dashboard
```

Then open http://localhost:8501 in your browser.

### Start the API

```bash
# Start API server on port 8000
python main.py --api
```

Then access http://localhost:8000/docs for API documentation.

### Run Everything Together

```bash
# Start scheduler + API + dashboard
python main.py --all
```

## Dashboard Features

The web dashboard provides:

- **Overview**: Charts showing jobs by industry, category, and experience level
- **Geographic**: Jobs by country and city, remote vs on-site distribution
- **Skills**: Most in-demand skills across all jobs
- **Job Listings**: Searchable list with filters
- **Export**: Download filtered data as Excel files

Login with credentials from your `.env` file (default: admin/changeme456).

## API Endpoints

All endpoints require an API key if authentication is enabled. Include it in the header:
```
X-API-Key: your-api-key-here
```

### Get Jobs

```bash
GET /jobs?country=US&industry=IT&limit=100

Response:
{
  "total": 12547,
  "pages": 126,
  "offset": 0,
  "limit": 100,
  "results": [...]
}
```

**Query Parameters:**
- `country` - Filter by country code (US, CA, IN, AU)
- `industry` - Filter by industry (IT, Healthcare)
- `primary_category` - Filter by job category
- `skill` - Filter by required skill
- `min_salary` - Minimum salary
- `remote_only` - Show only remote jobs (true/false)
- `limit` - Results per page (max 1000)
- `offset` - Pagination offset

### Get Statistics

```bash
GET /stats

Response:
{
  "total_jobs": 12547,
  "jobs_by_country": {...},
  "jobs_by_industry": {...},
  "top_skills": [...]
}
```

### Get Top Skills

```bash
GET /skills?limit=50

Response:
{
  "skills": [
    {"name": "Python", "count": 5432},
    {"name": "JavaScript", "count": 4821}
  ]
}
```

### Health Check

```bash
GET /health

Response:
{
  "status": "healthy",
  "checks": {
    "database": {"status": "healthy", "total_jobs": 12547},
    "redis": {"status": "healthy"},
    "scraper": {"status": "healthy", "last_run": "2025-01-15T13:00:00"}
  }
}
```

## Job Categories

The system classifies jobs into 14 categories:

**IT (8 categories):**
1. Frontend Development - React, Vue, Angular developers
2. Backend Development - Python, Java, Node.js engineers
3. Full Stack Development - Full-stack engineers
4. Cloud & DevOps - Kubernetes, AWS, Azure specialists
5. Data Engineering - Data pipelines, ETL developers
6. AI & Machine Learning - ML engineers, data scientists
7. Security Engineering - Cybersecurity professionals
8. Mobile Development - iOS, Android developers

**Healthcare (6 categories):**
9. EHR & EMR Systems - Epic, Cerner developers
10. Healthcare Interoperability - HL7, FHIR specialists
11. Telehealth & Digital Health - Telemedicine platforms
12. Clinical Informatics - Healthcare IT analysts
13. Healthcare Data & Analytics - Clinical data scientists
14. Medical Devices & IoT - Medical device software

## How It Works

### 1. Scraping Process

The system uses Playwright to scrape Google Jobs:
- Searches for configured job titles in specified countries
- Extracts job details (title, company, description, salary, etc.)
- Applies rate limiting to avoid getting blocked (2-5 second delays)
- Rotates user agents to appear as different browsers

### 2. Data Processing

For each job found:
- **Validation**: Checks for required fields, minimum description length, spam indicators
- **Skills Extraction**: Matches 500+ skills from the description using pattern matching
- **Classification**: Assigns primary and secondary categories based on keywords
- **Deduplication**: Compares with existing jobs using fuzzy matching (85% similarity)
- **Storage**: Saves to PostgreSQL with all metadata

### 3. Classification System

Jobs are classified using weighted keyword scoring:
- Exact title matches get highest weight (10.0)
- Industry keywords weighted 4.0-9.0
- Title mentions get 1.5x boost
- Calculates primary category (highest score)
- Finds secondary categories (30%+ of primary score)
- Generates confidence score (0.0 to 1.0)

### 4. Deduplication

The system merges duplicate jobs by:
- Comparing title, company, and location
- Using fuzzy string matching (handles word order variations)
- Merging if 85%+ similar
- Combining skills from all sources
- Tracking all platforms where the job was found

## Database Schema

The main `jobs` table includes:

**Basic Info:**
- `title`, `company`, `location`, `country`, `city`
- `description`, `remote` (boolean)

**Classification:**
- `industry` (IT or Healthcare)
- `primary_category` (one of 14 categories)
- `secondary_categories` (array of related categories)
- `classification_confidence` (0.0 to 1.0)

**Skills:**
- `skills_required` (array)
- `skills_preferred` (array)
- `all_skills` (combined array)

**Salary:**
- `salary_min`, `salary_max`, `salary_currency`

**Status:**
- `status` (active, removed, expired, checking)
- `status_last_checked` (last HTTP check timestamp)
- `is_active` (boolean)

**Metadata:**
- `source_platform` (LinkedIn, Indeed, etc.)
- `source_url` (link to original posting)
- `dedup_sources` (array of all platforms)
- `dedup_count` (number of duplicates found)
- `created_at`, `scraped_date`, `last_updated`

## Maintenance

### Database Backups

Backups are automatically created daily if using Docker:
- Location: `./backups/`
- Retention: 7 days, 4 weeks, 3 months
- Format: Compressed SQL dumps

To restore a backup:
```bash
cat backups/daily/jobs_db-2025-01-15.sql.gz | gunzip | \
  docker-compose exec -T postgres psql -U jobscraper jobs_db
```

### Database Migrations

When the database schema changes, apply migrations:
```bash
# See current version
alembic current

# Apply all pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

### Cache Management

Redis cache is automatically managed, but you can:
```bash
# Clear all cache
docker-compose exec redis redis-cli FLUSHALL

# Clear versioned cache only
docker-compose exec redis redis-cli KEYS "v2:*" | xargs redis-cli DEL
```

### Checking Job Status

The system automatically checks if jobs are still active:
- Runs daily at 2 AM
- Sends HTTP HEAD request to job URL
- Marks as "removed" if 404 or 410 response
- Keeps jobs with 5xx errors (temporary server issues)

To run manually:
```bash
python -c "from utils.job_status_checker import get_status_checker; get_status_checker().check_jobs()"
```

## Testing

Run the test suite:
```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov

# Run specific test file
pytest tests/test_classifier.py

# Run with verbose output
pytest -v
```

Test coverage:
- 51 tests across 4 test files
- 85%+ coverage on critical components

## Troubleshooting

### Scraper Not Finding Jobs

**Problem**: No jobs returned from scraping
**Solution**:
- Google may have changed their HTML structure
- Check `scrapers/playwright_scraper.py` CSS selectors
- Run with `headless=False` to see what's happening
- Check logs in `logs/` directory

### Database Connection Failed

**Problem**: Can't connect to PostgreSQL
**Solution**:
- Check PostgreSQL is running: `docker-compose ps` or `systemctl status postgresql`
- Verify credentials in `.env` file
- Check `DATABASE_URL` environment variable
- Look for errors in logs

### Redis Connection Failed

**Problem**: Cache not working
**Solution**:
- Check Redis is running: `docker-compose ps` or `redis-cli ping`
- System will work without Redis, just slower
- Check `REDIS_URL` in `.env` file

### Dashboard Won't Load

**Problem**: Streamlit dashboard not accessible
**Solution**:
- Check if port 8501 is already in use
- Try a different port: `streamlit run dashboard/app.py --server.port 8502`
- Check firewall settings
- Look for errors when starting: `python main.py --dashboard`

### API Authentication Failing

**Problem**: Getting 401 or 403 errors
**Solution**:
- Check `API_AUTH_ENABLED` in `.env`
- Verify `API_KEY` is set correctly
- Include `X-API-Key` header in requests
- Try with auth disabled first: `API_AUTH_ENABLED=false`

### Out of Memory

**Problem**: System crashes or becomes slow
**Solution**:
- Reduce `MAX_JOBS_PER_SEARCH` in `.env`
- Increase swap space
- Run components separately instead of all together
- Check PostgreSQL and Redis memory limits

## Performance Tips

**For Faster Scraping:**
- Run multiple scrapers in parallel (different job titles)
- Increase scraper concurrency (edit `playwright_scraper.py`)
- Use faster network connection

**For Better API Performance:**
- Keep Redis running for caching
- Add database indexes for your common queries
- Use pagination (limit results)
- Enable API authentication to prevent abuse

**For Lower Resource Usage:**
- Increase `SCRAPE_INTERVAL_HOURS` (scrape less often)
- Reduce `MAX_JOBS_PER_SEARCH`
- Disable features you don't need
- Run scrapers on separate machines

## Project Structure

```
Scraping/
├── api/                    # FastAPI REST API
│   └── main.py            # API endpoints
├── dashboard/             # Streamlit web dashboard
│   └── app.py            # Dashboard UI
├── models/                # Database models
│   └── database.py       # SQLAlchemy models
├── processors/            # Data processing
│   ├── job_classifier.py # Multi-label classification
│   ├── deduplication.py  # Fuzzy matching
│   └── skills_extractor.py # Skill extraction
├── scrapers/              # Web scrapers
│   ├── playwright_scraper.py  # Modern async scraper
│   └── google_jobs_scraper.py # Legacy scraper
├── utils/                 # Utilities
│   ├── auth.py           # Authentication helpers
│   ├── cache.py          # Redis caching
│   ├── validation.py     # Data validation
│   ├── notifications.py  # Error notifications
│   ├── config_loader.py  # Config management
│   └── job_status_checker.py # Job validation
├── tests/                 # Test suite
│   ├── test_classifier.py
│   ├── test_deduplication.py
│   ├── test_validation.py
│   └── test_auth.py
├── config/                # Configuration files
│   ├── job_categories.json  # 14 categories, 232 titles
│   ├── skills_database.json # 500+ skills
│   └── countries.json       # 4 countries
├── alembic/               # Database migrations
├── logs/                  # Application logs
├── backups/               # Database backups
├── main.py               # CLI entry point
├── scheduler.py          # Automated scheduling
├── docker-compose.yml    # Docker setup
└── requirements.txt      # Python dependencies
```

## Configuration Files

### job_categories.json

Defines the 14 job categories and 232 job titles to search for. Edit this file to:
- Add new job titles to search
- Create new categories
- Modify industry classifications

### skills_database.json

Contains 500+ technical skills across 15 categories:
- Programming languages
- Frontend/backend frameworks
- Databases and cloud platforms
- DevOps tools
- Healthcare-specific technologies

### countries.json

Defines supported countries and cities. Currently includes:
- United States (10 major cities)
- Canada (6 major cities)
- India (7 major cities)
- Australia (6 major cities)

## Environment Variables

**Database:**
- `POSTGRES_HOST` - Database server (default: localhost)
- `POSTGRES_PORT` - Database port (default: 5432)
- `POSTGRES_DB` - Database name (default: jobs_db)
- `POSTGRES_USER` - Database username
- `POSTGRES_PASSWORD` - Database password
- `DATABASE_URL` - Full connection string (overrides above)

**Redis:**
- `REDIS_HOST` - Redis server (default: localhost)
- `REDIS_PORT` - Redis port (default: 6379)
- `REDIS_URL` - Full connection string (overrides above)
- `CACHE_TTL_STATS` - Stats cache duration in seconds (default: 300)
- `CACHE_TTL_SKILLS` - Skills cache duration in seconds (default: 3600)

**Scraping:**
- `SCRAPE_INTERVAL_HOURS` - Hours between scraping runs (default: 2)
- `MAX_JOBS_PER_SEARCH` - Max jobs per search query (default: 50)
- `HEADLESS_BROWSER` - Run browser in headless mode (default: true)
- `RATE_LIMIT_DELAY_MIN` - Min delay between requests in seconds (default: 2)
- `RATE_LIMIT_DELAY_MAX` - Max delay between requests in seconds (default: 5)

**Job Status Checking:**
- `CHECK_JOB_STATUS` - Enable job validation (default: true)
- `STATUS_CHECK_INTERVAL_DAYS` - Days between checks (default: 7)
- `STATUS_CHECK_BATCH_SIZE` - Jobs per batch (default: 50)
- `MAX_CONCURRENT_CHECKS` - Parallel HTTP requests (default: 5)

**Validation:**
- `FUZZY_MATCH_THRESHOLD` - Similarity for duplicates 0-100 (default: 85)
- `MIN_DESCRIPTION_LENGTH` - Minimum description chars (default: 50)
- `LOG_VALIDATION_FAILURES` - Log rejected jobs (default: true)

**API:**
- `API_HOST` - API server host (default: 0.0.0.0)
- `API_PORT` - API server port (default: 8000)
- `API_AUTH_ENABLED` - Require API key (default: false)
- `API_KEY` - API authentication key

**Dashboard:**
- `DASHBOARD_PORT` - Dashboard port (default: 8501)
- `DASHBOARD_AUTH_ENABLED` - Require login (default: true)
- `DASHBOARD_USERNAME` - Login username (default: admin)
- `DASHBOARD_PASSWORD` - Plain password (not recommended)
- `DASHBOARD_PASSWORD_HASH` - Hashed password (recommended)

**Logging:**
- `LOG_LEVEL` - Logging level (default: INFO)
- `LOG_TO_FILE` - Enable file logging (default: true)
- `LOG_RETENTION` - Keep logs for duration (default: 30 days)

## Security Considerations

**For Production Deployments:**

1. **Change Default Passwords**: Never use default credentials
2. **Use Password Hashing**: Set `DASHBOARD_PASSWORD_HASH` instead of plaintext
3. **Enable API Authentication**: Set `API_AUTH_ENABLED=true`
4. **Use Strong API Keys**: Generate random 64-character keys
5. **Enable HTTPS**: Use reverse proxy (Nginx) with SSL certificates
6. **Restrict Database Access**: Don't expose PostgreSQL port publicly
7. **Keep Dependencies Updated**: Regularly run `pip install --upgrade`
8. **Monitor Logs**: Check `logs/` directory for suspicious activity
9. **Backup Regularly**: Verify backups are working
10. **Use Firewall**: Only allow necessary ports

## License

This project is provided as-is for educational and commercial use.

## Support

For issues and questions:
- Check the Troubleshooting section above
- Review logs in the `logs/` directory
- Check `IMPROVEMENTS.md` for recent changes
- Review test files in `tests/` for usage examples

## Recent Updates

See `IMPROVEMENTS.md` for a complete list of recent improvements including:
- Security enhancements (password hashing, API authentication)
- Database migrations with Alembic
- Comprehensive test suite (51 tests)
- SQL injection fixes
- Cache versioning system
- API pagination metadata
- Enhanced health checks
- Automated backups

## Contributing

When making changes:
1. Run tests: `pytest`
2. Check code style: `black .` and `flake8`
3. Create database migration if needed: `alembic revision --autogenerate -m "description"`
4. Update relevant documentation
5. Test with both Docker and manual setup
