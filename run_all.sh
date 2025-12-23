#!/bin/bash

# Job Scraping System - Run All Components
# This script starts the scheduler, API, and dashboard in parallel

echo "╔══════════════════════════════════════════════════════╗"
echo "║     JOB SCRAPING SYSTEM - STARTING ALL SERVICES     ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# Create logs directory
mkdir -p logs

# Initialize database
echo "📦 Initializing database..."
python main.py --init-db
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down all services..."
    kill $(jobs -p) 2>/dev/null
    echo "✅ All services stopped"
    exit 0
}

trap cleanup INT TERM

# Start scheduler in background
echo "⏰ Starting scheduler (hourly updates)..."
python scheduler.py --interval 1 > logs/scheduler.log 2>&1 &
SCHEDULER_PID=$!
echo "   Scheduler PID: $SCHEDULER_PID"
echo "   Logs: logs/scheduler.log"
echo ""

# Wait a bit for first scrape to start
sleep 5

# Start API in background
echo "🚀 Starting API server on http://localhost:8000..."
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 > logs/api.log 2>&1 &
API_PID=$!
echo "   API PID: $API_PID"
echo "   Logs: logs/api.log"
echo "   API Docs: http://localhost:8000/docs"
echo ""

# Start dashboard in foreground
echo "📊 Starting dashboard on http://localhost:8501..."
echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║                   SERVICES RUNNING                   ║"
echo "╠══════════════════════════════════════════════════════╣"
echo "║  Dashboard:  http://localhost:8501                   ║"
echo "║  API:        http://localhost:8000                   ║"
echo "║  API Docs:   http://localhost:8000/docs              ║"
echo "║  Scheduler:  Running every 1 hour                    ║"
echo "╠══════════════════════════════════════════════════════╣"
echo "║  Press Ctrl+C to stop all services                   ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

streamlit run dashboard/app.py --server.port 8501

# If dashboard exits, cleanup
cleanup
