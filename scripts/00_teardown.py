#!/usr/bin/env python3
"""
Step 0 — Tear down everything this demo created in Elastic.

Deletes:
  - the 3 indices (bank-support-kb, bank-transactions, bank-customers)
  - the Agent Builder agent (current id + the legacy 'bharat-bank-support-agent')
  - the 3 custom tools (bank_kb_search, customer_profile, customer_transactions)

Safe to run repeatedly — missing objects are ignored. It does NOT touch your
inference endpoints (Jina embeddings / Groq) or anything else in the cluster.
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

ES_URL = os.environ["ELASTICSEARCH_URL"].rstrip("/")
ES_KEY = os.environ["ELASTIC_API_KEY"]
KIBANA_URL = os.environ["KIBANA_URL"].rstrip("/")
KIBANA_KEY = os.environ["KIBANA_API_KEY"]
SPACE = os.getenv("KIBANA_SPACE_ID", "").strip()

INDICES = [
    os.getenv("ES_INDEX", "bank-support-kb"),
    os.getenv("TXN_INDEX", "bank-transactions"),
    os.getenv("CUST_INDEX", "bank-customers"),
]
AGENTS = list({os.getenv("AGENT_ID", "pratham-bank-support-agent"),
               "bharat-bank-support-agent"})  # include legacy id
TOOLS = ["bank_kb_search", "customer_profile", "customer_transactions"]

ES_H = {"Authorization": f"ApiKey {ES_KEY}"}
KB_BASE = KIBANA_URL + (f"/s/{SPACE}" if SPACE and SPACE != "default" else "")
KB_API = f"{KB_BASE}/api/agent_builder"
KB_H = {"Authorization": f"ApiKey {KIBANA_KEY}", "kbn-xsrf": "true"}


def _del(label, url, headers):
    try:
        r = requests.delete(url, headers=headers, timeout=30)
        if r.status_code in (200, 204):
            print(f"  deleted {label}")
        elif r.status_code == 404:
            print(f"  {label} not found (ok)")
        else:
            print(f"  {label}: HTTP {r.status_code} {r.text[:200]}")
    except Exception as e:
        print(f"  {label}: error {e}")


def main():
    print("Deleting Agent Builder agents ...")
    for a in AGENTS:
        _del(f"agent {a}", f"{KB_API}/agents/{a}", KB_H)

    print("Deleting Agent Builder tools ...")
    for t in TOOLS:
        _del(f"tool {t}", f"{KB_API}/tools/{t}", KB_H)

    print("Deleting indices ...")
    for i in INDICES:
        _del(f"index {i}", f"{ES_URL}/{i}", ES_H)

    print("\nTeardown complete.")


if __name__ == "__main__":
    main()
