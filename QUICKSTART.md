# ⚡ Quick Start Guide

Get the job scraping system running in 5 minutes!

## 🚀 Installation (2 minutes)

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Create environment file
cp .env.example .env

# 3. Initialize database
python main.py --init-db
```

## ▶️ Run Everything (1 command)

```bash
./run_all.sh
```

This starts:
- ✅ **Scheduler** (scrapes jobs every hour)
- ✅ **API** at http://localhost:8000
- ✅ **Dashboard** at http://localhost:8501

## 🎯 What Happens Next?

1. **Immediately**: System starts scraping jobs from Google Jobs
2. **In 5-10 minutes**: First batch of jobs appears in dashboard
3. **Every hour**: Automatically scrapes new jobs
4. **In dashboard**: View, filter, and export jobs to Excel

## 📊 Access Your Dashboard

Open http://localhost:8501 in your browser

**Try these:**
- Filter by country (US, Canada, India, Australia)
- Filter by industry (IT, Healthcare)
- View top skills in demand
- Export to Excel (IT jobs, Healthcare jobs, or All)

## 🔌 Access the API

API Documentation: http://localhost:8000/docs

**Quick test:**
```bash
# Get job statistics
curl http://localhost:8000/stats

# Get all US jobs
curl http://localhost:8000/jobs?country=US&limit=10
```

## ⚙️ Customize What Gets Scraped

**Change countries** - Edit `config/countries.json`

**Change job titles** - Edit `config/job_categories.json`

**Change skills** - Edit `config/skills_database.json`

## 🛑 Stop Everything

Press `Ctrl+C` in the terminal running `run_all.sh`

## 📖 Need More Help?

Read the full [README.md](README.md) for:
- Detailed documentation
- Troubleshooting
- Advanced configuration
- API examples
- Deployment options

---

**Questions?** Check the logs in `logs/` directory or review the README.
