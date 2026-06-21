#!/usr/bin/env bash
# One-command setup + run for the Pratham Bank Voice Agent demo.
set -e
cd "$(dirname "$0")"

if [ ! -f .env ]; then
  echo "❌ No .env found. Copy .env.example to .env and fill in your keys."
  exit 1
fi

echo "📦 Installing dependencies..."
pip install -q -r requirements.txt

echo "🗂️  [1/3] Creating Elasticsearch index..."
python scripts/01_create_index.py

echo "📥 [2/3] Ingesting knowledge base (with Jina embeddings)..."
python scripts/02_ingest_data.py

echo "🤖 [3/3] Creating Agent Builder tool + agent..."
python scripts/03_create_agent.py

echo ""
echo "✅ Setup complete. Starting the voice agent at http://localhost:8000"
echo ""
cd backend
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
