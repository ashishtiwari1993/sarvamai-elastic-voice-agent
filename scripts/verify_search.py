#!/usr/bin/env python3
"""
Quick check that semantic_text search works on the knowledge base.
Runs a natural-language query that shares no keywords with the stored title,
proving the Jina embeddings are doing the work.
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()
ES_URL = os.environ["ELASTICSEARCH_URL"].rstrip("/")
ES_KEY = os.environ["ELASTIC_API_KEY"]
INDEX = os.getenv("ES_INDEX", "bank-support-kb")
HEADERS = {"Authorization": f"ApiKey {ES_KEY}", "Content-Type": "application/json"}

QUERIES = [
    "a stranger emptied my bank account using a payment app",
    "I cannot remember the secret number for my payments",
    "my plastic card is missing",
]

for q in QUERIES:
    body = {
        "size": 3,
        "query": {"semantic": {"field": "content_semantic", "query": q}},
        "_source": ["title", "category"],
    }
    r = requests.post(f"{ES_URL}/{INDEX}/_search", headers=HEADERS, json=body)
    r.raise_for_status()
    hits = r.json()["hits"]["hits"]
    print(f"\nQ: {q}")
    for h in hits:
        print(f"   {h['_score']:.3f}  [{h['_source']['category']}]  {h['_source']['title']}")
