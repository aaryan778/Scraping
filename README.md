# Job Scraping System

A tool that automatically collects job postings from the internet, organizes them, and lets you search and analyze them through a web interface or API.

## What Does This Do?

This system:
- Automatically collects job postings from Google Jobs (which includes Indeed, LinkedIn, Glassdoor, and others)
- Figures out what skills each job needs (like Python, JavaScript, nursing, etc.)
- Sorts jobs into categories (like Frontend Developer, Data Scientist, Healthcare IT, etc.)
- Removes duplicate postings
- Checks if jobs are still available
- Stores everything in a database
- Gives you a website to browse and export the data
- Provides an API if you want to access the data programmatically

## Features

- Runs automatically every few hours to keep data current
- Categorizes jobs into 14 different specialties
- Recognizes over 500 technical skills in job descriptions
- Works with jobs from US, Canada, India, and Australia
- Filters out spam and low-quality postings
- Web dashboard with charts and Excel export
- REST API for custom integrations
- Automatic daily backups of your data

## Requirements

You'll need:
- Python 3.9 or newer
- PostgreSQL 16 or newer (database to store jobs)
- Redis 7 or newer (makes searches faster)
- At least 2GB of RAM
- Works on Linux, macOS, or Windows

## Quick Start with Docker

Docker runs everything in containers so you don't have to install PostgreSQL and Redis manually.

```bash
# 1. Download the code
git clone <your-repo-url>
cd Scraping

# 2. Copy the example settings file
cp .env.example .env

# 3. Edit the settings file (change passwords, etc.)
nano .env

# 4. Start everything
docker-compose up -d

# 5. Set up the database
docker-compose exec postgres psql -U jobscraper -d jobs_db < init.sql
```

That's it! The system is now running.

## Manual Installation

If you prefer to install without Docker:

```bash
# 1. Download the code
git clone <your-repo-url>
cd Scraping

# 2. Create a Python virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install Python packages
pip install -r requirements.txt

# 4. Install the browser automation tool
playwright install chromium

# 5. Copy the settings file
cp .env.example .env

# 6. Edit settings with your database info
nano .env
```

You'll also need to install PostgreSQL and Redis separately on your system.

## Configuration

Open the `.env` file and update these settings:

### Basic Settings

```bash
# Database connection
POSTGRES_HOST=localhost          # Where PostgreSQL is running
POSTGRES_PORT=5432              # PostgreSQL port
POSTGRES_DB=jobs_db             # Database name
POSTGRES_USER=jobscraper        # Database username
POSTGRES_PASSWORD=your_password # Change this!

# Cache connection (makes things faster)
REDIS_HOST=localhost
REDIS_PORT=6379

# How often to scrape for new jobs
SCRAPE_INTERVAL_HOURS=2         # Check for new jobs every 2 hours
MAX_JOBS_PER_SEARCH=50          # Limit per search to avoid overload
```

### Security Settings (Important for Production)

If you're running this on a server that others can access, set these up:

```bash
# Dashboard login
DASHBOARD_AUTH_ENABLED=true
DASHBOARD_USERNAME=admin
DASHBOARD_PASSWORD=your-secure-password

# API access control
API_AUTH_ENABLED=true
API_KEY=make-this-a-long-random-string
```

For better security, use hashed passwords instead of plain text. Run this command to generate one:

```bash
python -c "from utils.auth import hash_password; h,s = hash_password('your-password'); print(f'DASHBOARD_PASSWORD_HASH={h}\nDASHBOARD_PASSWORD_SALT={s}')"
```

Copy the output into your `.env` file.

## How to Use

### First Time Setup

Before scraping any jobs, initialize the database:

```bash
python main.py --init-db
```

This creates all the necessary tables.

### Scrape Jobs Once

To collect jobs one time:

```bash
python main.py --scrape
```

This will take a few minutes depending on how many job titles you're searching for.

### Run Automatically

To have the system check for new jobs every few hours:

```bash
python main.py --schedule
```

Leave this running in the background.

### Open the Dashboard

To view jobs in your browser:

```bash
python main.py --dashboard
```

Then open your browser and go to: http://localhost:8501

Default login is username: `admin`, password: `changeme456` (change this in your `.env` file).

### Start the API

If you want to access data programmatically:

```bash
python main.py --api
```

The API will run at: http://localhost:8000

View the API documentation at: http://localhost:8000/docs

### Run Everything Together

To start the scheduler, dashboard, and API all at once:

```bash
python main.py --all
```

## Using the Dashboard

When you open the dashboard in your browser, you'll see:

**Overview Tab:**
- Charts showing job distribution by industry and category
- Experience level breakdown (Junior, Mid-level, Senior)
- Salary statistics

**Geographic Tab:**
- Jobs by country and city
- Remote vs on-site distribution
- Map visualizations

**Skills Tab:**
- Most demanded skills across all jobs
- Skills by category
- Trending skills

**Jobs Tab:**
- Searchable list of all jobs
- Filters by country, industry, category, skills
- Click any job to see full details
- Export filtered results to Excel

## Using the API

The API lets you access job data from your own code.

### Get Jobs

```bash
curl "http://localhost:8000/jobs?country=US&industry=IT&limit=10"
```

This returns:
```json
{
  "total": 12547,
  "pages": 1255,
  "offset": 0,
  "limit": 10,
  "results": [
    {
      "title": "Senior Python Developer",
      "company": "Tech Corp",
      "location": "San Francisco, CA",
      "salary_min": 120000,
      "salary_max": 180000,
      "remote": true,
      "skills_required": ["Python", "Django", "PostgreSQL"],
      ...
    }
  ]
}
```

### Filter Options

Add these to the URL to filter results:

- `?country=US` - Only US jobs (US, CA, IN, AU)
- `?industry=IT` - Only IT jobs (IT or Healthcare)
- `?primary_category=Frontend Development` - Specific job type
- `?skill=Python` - Jobs requiring Python
- `?remote_only=true` - Only remote jobs
- `?min_salary=100000` - Minimum salary
- `?limit=100` - How many results to return
- `?offset=100` - Skip first 100 (for pagination)

Combine multiple filters:
```bash
curl "http://localhost:8000/jobs?country=US&skill=Python&remote_only=true&min_salary=100000"
```

### Get Statistics

```bash
curl "http://localhost:8000/stats"
```

Returns overall statistics like total jobs, breakdown by country, top skills, etc.

### Get Top Skills

```bash
curl "http://localhost:8000/skills?limit=50"
```

Returns the 50 most in-demand skills across all jobs.

### Check System Health

```bash
curl "http://localhost:8000/health"
```

Shows if the database, cache, and scraper are working properly.

### Using API with Authentication

If you enabled API authentication, include your API key:

```bash
curl -H "X-API-Key: your-api-key-here" "http://localhost:8000/jobs"
```

## Job Categories

The system automatically sorts jobs into these categories:

### IT Jobs (8 categories)

1. **Frontend Development** - React, Vue, Angular developers
2. **Backend Development** - Python, Java, Node.js engineers
3. **Full Stack Development** - Full-stack engineers
4. **Cloud & DevOps** - AWS, Azure, Kubernetes specialists
5. **Data Engineering** - ETL, data pipeline developers
6. **AI & Machine Learning** - ML engineers, data scientists
7. **Security Engineering** - Cybersecurity, penetration testers
8. **Mobile Development** - iOS, Android developers

### Healthcare Jobs (6 categories)

9. **EHR & EMR Systems** - Epic, Cerner, electronic health records
10. **Healthcare Interoperability** - HL7, FHIR integration specialists
11. **Telehealth & Digital Health** - Telemedicine platforms
12. **Clinical Informatics** - Healthcare IT analysts
13. **Healthcare Data & Analytics** - Clinical data analysis
14. **Medical Devices & IoT** - Medical device software

## How Classification Works

When a job is collected, the system:

1. **Extracts Skills** - Scans the job description for 500+ known skills
2. **Calculates Category Scores** - Matches keywords to job categories
3. **Assigns Primary Category** - The best matching category
4. **Finds Secondary Categories** - Other relevant categories
5. **Generates Confidence Score** - How sure the system is (0% to 100%)

For example, a "Full Stack React Developer" job might be:
- Primary: Frontend Development (90% confidence)
- Secondary: Full Stack Development (75% confidence)
- Skills: React, JavaScript, Node.js, PostgreSQL

## How Deduplication Works

The same job often appears on multiple sites (LinkedIn, Indeed, Glassdoor). The system:

1. Compares new jobs with existing ones
2. Checks if title, company, and location are similar (85%+ match)
3. Merges duplicates into one entry
4. Tracks all sources where it was found
5. Combines skills from all versions

This prevents seeing the same job multiple times.

## Database Schema

Jobs are stored with this information:

**Basic Details:**
- Job title, company name, location, country, city
- Full job description
- Whether it's remote or on-site

**Classification:**
- Industry (IT or Healthcare)
- Primary category (one of 14)
- Secondary categories (related categories)
- Confidence score

**Skills:**
- Required skills (must have)
- Preferred skills (nice to have)
- All skills combined

**Salary:**
- Minimum salary
- Maximum salary
- Currency (USD, CAD, INR, AUD)

**Status:**
- Is the job still active?
- When was it last checked?
- Current status (active, removed, expired)

**Metadata:**
- Where it was found (LinkedIn, Indeed, etc.)
- Link to original posting
- All sources if it's a duplicate
- When it was scraped and last updated

## Maintenance

### Database Backups

If you're using Docker, backups happen automatically every day:
- Saved to: `./backups/` folder
- Keeps: 7 daily, 4 weekly, 3 monthly backups
- Format: Compressed SQL files

To restore a backup:
```bash
cat backups/daily/jobs_db-2025-01-15.sql.gz | gunzip | \
  docker-compose exec -T postgres psql -U jobscraper jobs_db
```

### Checking if Jobs Are Still Active

The system automatically checks if job postings are still available:
- Runs once a day at 2 AM
- Visits each job URL to see if it still exists
- Marks removed jobs as inactive

To run this check manually:
```bash
python -c "from utils.job_status_checker import get_status_checker; get_status_checker().check_jobs()"
```

### Clearing the Cache

Sometimes you might want to clear cached data:

```bash
# Clear everything
docker-compose exec redis redis-cli FLUSHALL

# Clear only v2 cache (current version)
docker-compose exec redis redis-cli KEYS "v2:*" | xargs redis-cli DEL
```

### Database Updates

When the database structure changes, you need to run migrations:

```bash
# Check current database version
alembic current

# Update to latest version
alembic upgrade head

# Undo last update
alembic downgrade -1
```

## Running Tests

The system includes automated tests to make sure everything works:

```bash
# Run all tests
pytest

# See detailed output
pytest -v

# Check code coverage
pytest --cov

# Run specific test file
pytest tests/test_classifier.py
```

There are 51 tests covering:
- Job classification
- Duplicate detection
- Data validation
- Authentication

## Common Problems

### Problem: Scraper Isn't Finding Jobs

**Possible Causes:**
- Google changed their website layout
- Rate limiting (you're scraping too fast)
- Network connectivity issues

**Solutions:**
- Check the logs in `logs/` folder
- Try running with visible browser: set `HEADLESS_BROWSER=false` in `.env`
- Increase the delay between requests: set `RATE_LIMIT_DELAY_MIN=5`

### Problem: Can't Connect to Database

**Possible Causes:**
- PostgreSQL isn't running
- Wrong credentials in `.env` file
- Database hasn't been created

**Solutions:**
- Check if PostgreSQL is running: `docker-compose ps` or `sudo systemctl status postgresql`
- Verify username and password in `.env` match your PostgreSQL setup
- Make sure you ran the init.sql file

### Problem: Dashboard Won't Load

**Possible Causes:**
- Port 8501 is already in use
- Firewall blocking the port
- Wrong credentials

**Solutions:**
- Try a different port: `streamlit run dashboard/app.py --server.port 8502`
- Check firewall settings
- Verify username/password in `.env` file
- Look at error messages when starting

### Problem: API Returns 401 or 403 Error

**Possible Causes:**
- Authentication is enabled but you didn't provide an API key
- Wrong API key
- API key not in the header

**Solutions:**
- Check if `API_AUTH_ENABLED=true` in `.env`
- Get your API key from `.env` file
- Include it in requests: `curl -H "X-API-Key: your-key" http://localhost:8000/jobs`
- Temporarily disable auth to test: `API_AUTH_ENABLED=false`

### Problem: Running Out of Memory

**Possible Causes:**
- Scraping too many jobs at once
- Not enough RAM

**Solutions:**
- Reduce `MAX_JOBS_PER_SEARCH` in `.env` (try 25 instead of 50)
- Run components separately instead of all together
- Add more swap space
- Increase RAM if on a cloud server

### Problem: Seeing Duplicate Jobs

**Possible Causes:**
- Deduplication threshold too strict
- Different job IDs from different sources

**Solutions:**
- Lower `FUZZY_MATCH_THRESHOLD` in `.env` (try 80 instead of 85)
- This is somewhat expected - same job on LinkedIn and Indeed might not match perfectly
- Review logs to see why specific jobs weren't merged

## Performance Tips

### Make Scraping Faster

- Run multiple scrapers in parallel for different job titles
- Use a faster internet connection
- Increase scraper concurrency in `playwright_scraper.py`

### Make API Faster

- Keep Redis running (it caches results)
- Use smaller `limit` values (like 50 instead of 1000)
- Enable API authentication to prevent abuse

### Reduce Resource Usage

- Scrape less frequently: set `SCRAPE_INTERVAL_HOURS=6` instead of 2
- Reduce jobs per search: set `MAX_JOBS_PER_SEARCH=25`
- Disable job status checking if you don't need it
- Run scraper on a separate machine

## Project Structure

```
Scraping/
├── api/                     # REST API
│   └── main.py             # API routes and logic
├── dashboard/              # Web interface
│   └── app.py             # Dashboard UI
├── models/                 # Database
│   └── database.py        # Table definitions
├── processors/             # Data processing
│   ├── job_classifier.py  # Categorizes jobs
│   ├── deduplication.py   # Finds duplicates
│   └── skills_extractor.py # Extracts skills
├── scrapers/               # Web scrapers
│   ├── playwright_scraper.py  # Main scraper
│   └── google_jobs_scraper.py # Backup scraper
├── utils/                  # Helper functions
│   ├── auth.py            # Password hashing
│   ├── cache.py           # Redis caching
│   ├── validation.py      # Data validation
│   └── job_status_checker.py # Checks if jobs exist
├── tests/                  # Automated tests
├── config/                 # Settings files
│   ├── job_categories.json    # 14 categories, 232 job titles
│   ├── skills_database.json   # 500+ skills
│   └── countries.json         # Supported countries
├── alembic/               # Database migrations
├── logs/                  # Log files
├── backups/               # Database backups
├── main.py               # Main entry point
├── scheduler.py          # Automated scheduling
├── docker-compose.yml    # Docker setup
└── requirements.txt      # Python packages
```

## Configuration Files

### job_categories.json

This file defines what jobs to search for and how to categorize them. It contains:
- 14 job categories
- 232 specific job titles to search for
- Keywords used for automatic classification

Edit this if you want to:
- Search for different types of jobs
- Add new categories
- Change how jobs are classified

### skills_database.json

Contains 500+ technical skills organized into categories:
- Programming languages (Python, Java, JavaScript, etc.)
- Frameworks (React, Django, Spring, etc.)
- Databases (PostgreSQL, MongoDB, MySQL, etc.)
- Cloud platforms (AWS, Azure, Google Cloud)
- DevOps tools (Docker, Kubernetes, Jenkins, etc.)
- Healthcare technologies (Epic, Cerner, HL7, FHIR, etc.)

Edit this to add new skills to recognize.

### countries.json

Lists countries and cities to search in:
- **United States**: New York, San Francisco, Austin, Seattle, Boston, Chicago, Los Angeles, Denver, Miami, Atlanta
- **Canada**: Toronto, Vancouver, Montreal, Calgary, Ottawa, Edmonton
- **India**: Bangalore, Hyderabad, Mumbai, Pune, Delhi, Chennai, Kolkata
- **Australia**: Sydney, Melbourne, Brisbane, Perth, Adelaide, Canberra

Edit this to add new countries or cities.

## Environment Variables Reference

Here's every setting you can configure in the `.env` file:

### Database Settings
- `POSTGRES_HOST` - Where PostgreSQL is (default: localhost)
- `POSTGRES_PORT` - PostgreSQL port (default: 5432)
- `POSTGRES_DB` - Database name (default: jobs_db)
- `POSTGRES_USER` - Username for database
- `POSTGRES_PASSWORD` - Password for database
- `DATABASE_URL` - Full connection string (alternative to above settings)

### Cache Settings
- `REDIS_HOST` - Where Redis is (default: localhost)
- `REDIS_PORT` - Redis port (default: 6379)
- `REDIS_URL` - Full connection string (alternative to above)
- `CACHE_TTL_STATS` - How long to cache statistics in seconds (default: 300)
- `CACHE_TTL_SKILLS` - How long to cache skills in seconds (default: 3600)

### Scraping Settings
- `SCRAPE_INTERVAL_HOURS` - Hours between scraping runs (default: 2)
- `MAX_JOBS_PER_SEARCH` - Maximum jobs per search (default: 50)
- `HEADLESS_BROWSER` - Run browser invisibly (default: true)
- `RATE_LIMIT_DELAY_MIN` - Minimum seconds between requests (default: 2)
- `RATE_LIMIT_DELAY_MAX` - Maximum seconds between requests (default: 5)

### Job Checking Settings
- `CHECK_JOB_STATUS` - Check if jobs still exist (default: true)
- `STATUS_CHECK_INTERVAL_DAYS` - Days between checks (default: 7)
- `STATUS_CHECK_BATCH_SIZE` - How many to check at once (default: 50)
- `MAX_CONCURRENT_CHECKS` - Parallel checks (default: 5)

### Validation Settings
- `FUZZY_MATCH_THRESHOLD` - Similarity % for duplicates (default: 85)
- `MIN_DESCRIPTION_LENGTH` - Minimum description length (default: 50)
- `LOG_VALIDATION_FAILURES` - Log rejected jobs (default: true)

### API Settings
- `API_HOST` - API host (default: 0.0.0.0)
- `API_PORT` - API port (default: 8000)
- `API_AUTH_ENABLED` - Require API key (default: false)
- `API_KEY` - Your API key if auth enabled

### Dashboard Settings
- `DASHBOARD_PORT` - Dashboard port (default: 8501)
- `DASHBOARD_AUTH_ENABLED` - Require login (default: true)
- `DASHBOARD_USERNAME` - Login username (default: admin)
- `DASHBOARD_PASSWORD` - Plaintext password (not recommended)
- `DASHBOARD_PASSWORD_HASH` - Hashed password (recommended)
- `DASHBOARD_PASSWORD_SALT` - Salt for hashed password

### Logging Settings
- `LOG_LEVEL` - How much to log (DEBUG, INFO, WARNING, ERROR)
- `LOG_TO_FILE` - Save logs to files (default: true)
- `LOG_RETENTION` - Keep logs for how long (default: 30 days)

## Security Checklist

If you're running this on a server accessible from the internet:

1. **Change All Default Passwords** - Don't use "changeme123" or "changeme456"
2. **Use Hashed Passwords** - Set `DASHBOARD_PASSWORD_HASH` not `DASHBOARD_PASSWORD`
3. **Enable API Authentication** - Set `API_AUTH_ENABLED=true`
4. **Use Strong API Keys** - Generate random 64+ character keys
5. **Set Up HTTPS** - Use a reverse proxy like Nginx with SSL certificates
6. **Don't Expose Database** - Keep PostgreSQL port 5432 closed to the internet
7. **Update Regularly** - Run `pip install --upgrade` to update packages
8. **Monitor Logs** - Check `logs/` folder regularly for suspicious activity
9. **Test Backups** - Make sure you can restore from your backups
10. **Use a Firewall** - Only allow necessary ports (80, 443)

## What's New

Recent improvements (see `IMPROVEMENTS.md` for details):

- Password hashing with SHA-256 for secure authentication
- API key authentication to control access
- 51 automated tests for reliability
- SQL injection prevention
- Versioned caching system
- Detailed pagination in API responses
- Comprehensive health monitoring
- Automatic daily database backups

## Getting Help

If something isn't working:

1. Check the "Common Problems" section above
2. Look at log files in the `logs/` folder
3. Read `IMPROVEMENTS.md` for recent changes
4. Check test files in `tests/` for usage examples
5. Try running with debugging: `LOG_LEVEL=DEBUG` in `.env`

## License

Free to use for any purpose.
