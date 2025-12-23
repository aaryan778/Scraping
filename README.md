# 💼 Job Scraping System

**Automated job scraping system** that collects job listings from multiple sources (Google Jobs aggregator), extracts skills using AI/NLP, and provides an interactive dashboard for visualization and export.

## 🌟 Features

### ✅ **What This System Does**

- **🔍 Automated Scraping**: Scrapes jobs from Google Jobs (aggregates Indeed, LinkedIn, Glassdoor, ZipRecruiter, Monster, and 100+ job boards)
- **⏰ Hourly Updates**: Automatically refreshes job data every hour
- **🧠 Skills Extraction**: Uses NLP to extract technical skills from job descriptions
- **🎯 Smart Classification**: Categorizes jobs into Frontend, Backend, Full Stack, Healthcare IT, etc.
- **🌍 Multi-Country**: Supports US, Canada, India, and Australia
- **📊 Interactive Dashboard**: Beautiful Streamlit dashboard with visualizations
- **📥 Excel Export**: Export jobs to Excel (IT only, Healthcare only, or combined)
- **🚀 REST API**: FastAPI for programmatic access
- **💯 100% Free**: No paid services required!

### 🎯 **Target Industries & Roles**

**IT Roles:**
- Frontend: React, Vue.js, Angular, UI/UX developers
- Backend: Python, Java, Node.js, DevOps engineers
- Full Stack: Software engineers, full stack developers
- Specialized: Data engineers, ML engineers, Security engineers

**Healthcare IT:**
- EHR/EMR Developers
- FHIR/HL7 Developers
- Healthcare software engineers
- Medical informatics specialists
- Healthcare data analysts

### 📊 **Data Collected**

For each job:
- Title, Company, Location (Country, City)
- Job Description
- Skills (Required & Preferred) - 500+ skills database
- Category (Frontend/Backend/etc.)
- Industry (IT/Healthcare)
- Experience Level (Junior/Mid/Senior)
- Salary Range (when available)
- Source Platform (LinkedIn, Indeed, etc.)
- Remote/On-site status

---

## 🚀 Quick Start

### 1️⃣ **Installation**

```bash
# Clone the repository
git clone <repo-url>
cd Scraping

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
```

### 2️⃣ **Setup**

```bash
# Initialize the database
python main.py --init-db
```

### 3️⃣ **Run Everything (Easiest!)**

```bash
# This starts:
# - Scheduler (scrapes every hour)
# - API server (http://localhost:8000)
# - Dashboard (http://localhost:8501)

./run_all.sh
```

**That's it!** The system will:
1. Immediately start scraping jobs
2. Update every hour automatically
3. Provide dashboard at http://localhost:8501
4. Provide API at http://localhost:8000/docs

---

## 📖 Usage Guide

### 🎯 **Running Individual Components**

#### **Option 1: Run One-Time Scrape**
```bash
python main.py --scrape --max-jobs 50
```

#### **Option 2: Run Scheduler Only** (hourly updates)
```bash
python main.py --schedule --interval 1
```

#### **Option 3: Run Dashboard Only**
```bash
python main.py --dashboard
# Or directly:
streamlit run dashboard/app.py
```

#### **Option 4: Run API Only**
```bash
python main.py --api
# Or directly:
uvicorn api.main:app --reload
```

### 📊 **Using the Dashboard**

Open http://localhost:8501 in your browser.

**Features:**
- **Overview Tab**: Charts showing jobs by industry, category, experience level
- **Geographic Tab**: Jobs by country, city, remote vs on-site
- **Skills Tab**: Top skills in demand, skills by category
- **Job Listings Tab**: Browse and search all jobs
- **Export Tab**: Export to Excel (IT, Healthcare, or All)

**Filters:**
- Country (US, Canada, India, Australia)
- Industry (IT, Healthcare)
- Category (Frontend, Backend, Full Stack, etc.)
- Remote Only toggle

**Export Options:**
1. Export IT jobs only → `IT_jobs.xlsx`
2. Export Healthcare jobs only → `Healthcare_jobs.xlsx`
3. Export all jobs → `All_jobs.xlsx`
4. Custom export with current filters

### 🔌 **Using the REST API**

API Documentation: http://localhost:8000/docs

**Example API Calls:**

```bash
# Get all jobs
curl http://localhost:8000/jobs

# Filter by country
curl http://localhost:8000/jobs?country=US

# Filter by industry
curl http://localhost:8000/jobs?industry=IT

# Filter by skill
curl http://localhost:8000/jobs?skill=python

# Get statistics
curl http://localhost:8000/stats

# Get top skills
curl http://localhost:8000/skills

# Get recent jobs (last 24 hours)
curl http://localhost:8000/recent-jobs?hours=24
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    AUTOMATED SCHEDULER                       │
│                  (Runs every 1 hour)                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                   GOOGLE JOBS SCRAPER                        │
│  (Selenium - scrapes Indeed, LinkedIn, Glassdoor, etc.)     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  SKILLS EXTRACTION                           │
│    (NLP + Rule-based - extracts 500+ technical skills)      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  JOB CLASSIFICATION                          │
│   (Categorizes: Frontend/Backend/Healthcare/etc.)           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                   SQLITE DATABASE                            │
│            (Stores all job data)                             │
└───────┬──────────────────────────────────────┬──────────────┘
        │                                       │
        ▼                                       ▼
┌──────────────────┐                  ┌──────────────────┐
│   REST API       │                  │   DASHBOARD      │
│  (FastAPI)       │                  │  (Streamlit)     │
│  Port 8000       │                  │  Port 8501       │
└──────────────────┘                  └──────────────────┘
```

---

## 📁 Project Structure

```
Scraping/
├── README.md                    # This file
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment variables template
├── main.py                      # Main CLI entry point
├── scheduler.py                 # Hourly scheduler
├── run_all.sh                   # Run all services script
│
├── config/                      # Configuration files
│   ├── job_categories.json      # Job categories (IT, Healthcare)
│   ├── skills_database.json     # 500+ skills database
│   └── countries.json           # Countries configuration
│
├── models/                      # Database models
│   ├── database.py              # SQLAlchemy models
│   ├── schemas.py               # Pydantic schemas
│   └── __init__.py
│
├── scrapers/                    # Scraping modules
│   ├── google_jobs_scraper.py   # Google Jobs scraper (Selenium)
│   ├── job_scraper_main.py      # Main orchestrator
│   └── __init__.py
│
├── processors/                  # Data processing
│   ├── skills_extractor.py      # NLP skills extraction
│   ├── job_classifier.py        # Job classification
│   └── __init__.py
│
├── api/                         # REST API
│   ├── main.py                  # FastAPI application
│   └── __init__.py
│
├── dashboard/                   # Dashboard
│   └── app.py                   # Streamlit dashboard
│
├── data/                        # Data storage
│   ├── raw/                     # Raw scraped data
│   ├── processed/               # Processed data
│   └── exports/                 # Excel exports
│
├── logs/                        # Application logs
└── tests/                       # Unit tests
```

---

## ⚙️ Configuration

### **Environment Variables** (`.env`)

```bash
# Database
DATABASE_URL=sqlite:///./jobs.db

# Scraping
SCRAPE_INTERVAL_HOURS=1
MAX_JOBS_PER_SEARCH=100

# Countries (comma-separated)
COUNTRIES=US,Canada,India,Australia

# Industries
INDUSTRIES=IT,Healthcare

# API
API_HOST=0.0.0.0
API_PORT=8000

# Dashboard
DASHBOARD_PORT=8501
```

### **Job Categories** (`config/job_categories.json`)

Customize which job titles to search for. Currently includes:
- **IT**: 50+ job titles (Frontend, Backend, Full Stack, Specialized)
- **Healthcare**: 20+ healthcare IT job titles

### **Skills Database** (`config/skills_database.json`)

500+ technical skills across:
- Programming languages
- Frontend frameworks
- Backend frameworks
- Databases
- Cloud platforms
- DevOps tools
- Healthcare-specific (HL7, FHIR, Epic, Cerner, etc.)

---

## 🛠️ How It Works

### **1. Scraping Process**

1. **Search Google Jobs** for each job title + country combination
2. **Extract job cards** from search results
3. **Click each job** to get full details
4. **Parse job data**: title, company, location, description, URL, etc.
5. **Determine source**: LinkedIn, Indeed, Glassdoor, etc.

### **2. Skills Extraction**

Three methods combined:
1. **Direct matching**: Matches against 500+ skills database
2. **Pattern extraction**: "experience with X", "proficient in Y"
3. **Bullet point extraction**: Common in job descriptions

Separates into:
- **Required skills**: From "required", "must have" sections
- **Preferred skills**: From "nice to have", "preferred" sections

### **3. Classification**

**Industry**: IT or Healthcare (based on keywords)

**Category**:
- Frontend: React, Vue, Angular, etc.
- Backend: Python, Java, Node.js, etc.
- Full Stack: Software Engineer, Full Stack Developer
- Specialized: Data, ML, Security, QA
- Healthcare IT: EHR, EMR, FHIR developers
- Healthcare Data: Healthcare analysts

**Experience Level**: Junior, Mid, Senior (based on title and description)

### **4. Storage & Access**

- **Database**: SQLite (can upgrade to PostgreSQL)
- **API**: FastAPI provides REST endpoints
- **Dashboard**: Streamlit provides interactive UI
- **Export**: Pandas exports to Excel

---

## 🔧 Customization

### **Add More Countries**

Edit `config/countries.json`:

```json
{
  "name": "Germany",
  "code": "DE",
  "google_jobs_location": "Germany",
  "major_cities": ["Berlin", "Munich", "Hamburg"]
}
```

### **Add More Job Titles**

Edit `config/job_categories.json`:

```json
"IT": {
  "Frontend": [
    "Your Custom Job Title"
  ]
}
```

### **Add More Skills**

Edit `config/skills_database.json`:

```json
"your_category": [
  "Skill 1", "Skill 2", "Skill 3"
]
```

### **Change Scraping Interval**

```bash
# Scrape every 2 hours
python scheduler.py --interval 2

# Scrape every 30 minutes
python scheduler.py --interval 0.5
```

### **Change Max Jobs Per Search**

```bash
python main.py --scrape --max-jobs 100
```

---

## 📊 Data Sources

The system scrapes **Google Jobs**, which aggregates from:

- ✅ LinkedIn
- ✅ Indeed
- ✅ Glassdoor
- ✅ ZipRecruiter
- ✅ Monster
- ✅ CareerBuilder
- ✅ SimplyHired
- ✅ Dice
- ✅ Company career pages
- ✅ 100+ other job boards

**Why Google Jobs?**
- Free, no API required
- Aggregates from all major job boards
- Always up-to-date
- No rate limiting issues
- Includes source URL to original posting

---

## 🆘 Troubleshooting

### **Issue: Chrome driver not found**
```bash
# The system auto-downloads ChromeDriver
# If issues persist, install manually:
pip install webdriver-manager --upgrade
```

### **Issue: Database locked**
```bash
# Stop all running services
pkill -f scheduler.py
pkill -f streamlit
pkill -f uvicorn

# Delete database and reinitialize
rm jobs.db
python main.py --init-db
```

### **Issue: No jobs scraped**
- Check internet connection
- Google may block automated requests temporarily (wait 15 min)
- Try running with `headless=False` to see what's happening
- Check logs in `logs/scheduler.log`

### **Issue: Skills not extracted**
- Skills extraction is rule-based, some jobs may have 0 skills
- Add more skills to `config/skills_database.json`
- Check job description format

---

## 🎯 Performance

**Scraping Speed**:
- ~2-3 seconds per job
- ~50 jobs in 2-3 minutes
- 13 job titles × 4 countries × 50 jobs = ~2,600 jobs in ~2 hours

**Database**:
- SQLite handles 100K+ jobs easily
- Can upgrade to PostgreSQL for production

**Memory**:
- ~200-500 MB RAM during scraping
- ~100 MB for dashboard

---

## 🚀 Production Deployment

### **Option 1: Run on Server**

```bash
# Install as systemd service (Linux)
sudo nano /etc/systemd/system/job-scraper.service
```

```ini
[Unit]
Description=Job Scraper Service
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/Scraping
ExecStart=/path/to/venv/bin/python scheduler.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable job-scraper
sudo systemctl start job-scraper
```

### **Option 2: Docker** (Coming Soon)

### **Option 3: Cloud VM**
- Deploy on AWS EC2, Google Cloud VM, or DigitalOcean
- Run `./run_all.sh` in a tmux/screen session

---

## 📈 Future Enhancements

Potential improvements:
- [ ] Add more job sources (direct scraping)
- [ ] OpenAI integration for better skills extraction
- [ ] Email notifications for new jobs matching criteria
- [ ] Job recommendations based on skills
- [ ] Salary prediction ML model
- [ ] Mobile app
- [ ] Docker containerization
- [ ] Authentication for dashboard
- [ ] Job alerts via Telegram/Slack

---

## 📝 License

MIT License - See LICENSE file

---

## 🙏 Credits

Built with:
- **Selenium**: Web scraping
- **FastAPI**: REST API
- **Streamlit**: Dashboard
- **SQLAlchemy**: Database ORM
- **Pandas**: Data processing
- **Plotly**: Visualizations
- **APScheduler**: Task scheduling
- **spaCy**: NLP (optional)

---

## 📧 Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Check existing documentation
- Review logs in `logs/` directory

---

**Happy Job Hunting! 🚀**
