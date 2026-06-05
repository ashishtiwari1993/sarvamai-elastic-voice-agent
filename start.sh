#!/usr/bin/env bash
# Start ONLY the voice-agent server (assumes indices + agent already exist).
# For first-time data setup instead, use ./run_demo.sh
set -e
cd "$(dirname "$0")"

if [ ! -f .env ]; then
  echo "❌ No .env found. Copy .env.example to .env and fill in your keys."
  exit 1
fi

echo "📦 Ensuring dependencies are installed..."
pip install -q -r requirements.txt

echo "✅ Starting Bharat Bank · Mitra at http://localhost:8000"
echo "   (Ctrl+C to stop)"
echo ""
cd backend
exec uvicorn app:app --host 0.0.0.0 --port 8000 --reload
