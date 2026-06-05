#!/usr/bin/env python3
"""
Step 2 — Bulk ingest all three datasets.

  data/knowledge_base.json  -> bank-support-kb   (triggers Jina embeddings)
  data/customers.json       -> bank-customers     (private)
  <generated dynamically>   -> bank-transactions (private, dates = last 30 days)

Transactions are produced by scripts/generate_transactions.py at run time, so
every ingest yields fresh data in the now-30d → now window. A snapshot of the
generated rows is also written to data/transactions.json for inspection.
"""
import os
import sys
import json
import time
import requests
from dotenv import load_dotenv

# allow importing the generator (this script's own directory)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_transactions import generate

load_dotenv()

ES_URL = os.environ["ELASTICSEARCH_URL"].rstrip("/")
ES_KEY = os.environ["ELASTIC_API_KEY"]
KB_INDEX = os.getenv("ES_INDEX", "bank-support-kb")
TXN_INDEX = os.getenv("TXN_INDEX", "bank-transactions")
CUST_INDEX = os.getenv("CUST_INDEX", "bank-customers")

HEADERS = {"Authorization": f"ApiKey {ES_KEY}", "Content-Type": "application/json"}
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")


def load_json(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


def bulk(index, docs, id_field, strip=()):
    lines = []
    for d in docs:
        doc = {k: v for k, v in d.items() if k not in strip}
        lines.append(json.dumps({"index": {"_index": index, "_id": d[id_field]}}))
        lines.append(json.dumps(doc, ensure_ascii=False))
    body = ("\n".join(lines) + "\n").encode("utf-8")
    r = requests.post(f"{ES_URL}/_bulk", headers=HEADERS, data=body)
    if not r.ok:
        print(f"  Bulk failed: {r.status_code} {r.text}")
        sys.exit(1)
    if r.json().get("errors"):
        for item in r.json()["items"]:
            err = item.get("index", {}).get("error")
            if err:
                print("  doc error:", item["index"]["_id"], err)
        sys.exit(1)
    requests.post(f"{ES_URL}/{index}/_refresh", headers=HEADERS)


def count(index):
    return requests.get(f"{ES_URL}/{index}/_count", headers=HEADERS).json().get("count")


def main():
    customers = load_json("customers.json")

    # 1) Generic knowledge base (semantic_text)
    kb = load_json("knowledge_base.json")
    print(f"Ingesting {len(kb)} KB docs -> {KB_INDEX} (running Jina embeddings)...")
    bulk(KB_INDEX, kb, "id")
    time.sleep(1); print(f"  {KB_INDEX}: {count(KB_INDEX)} documents")

    # 2) Customers (private)
    print(f"Ingesting {len(customers)} customers -> {CUST_INDEX} ...")
    bulk(CUST_INDEX, customers, "customer_id", strip=("hook",))  # 'hook' is demo-only
    time.sleep(1); print(f"  {CUST_INDEX}: {count(CUST_INDEX)} documents")

    # 3) Transactions (private, generated dynamically with last-30-day dates)
    txns = generate(customers)
    with open(os.path.join(DATA, "transactions.json"), "w", encoding="utf-8") as f:
        json.dump(txns, f, ensure_ascii=False, indent=2)
    print(f"Ingesting {len(txns)} generated transactions -> {TXN_INDEX} ...")
    bulk(TXN_INDEX, txns, "txn_id")
    time.sleep(1); print(f"  {TXN_INDEX}: {count(TXN_INDEX)} documents")

    print("\nAll data ingested.")


if __name__ == "__main__":
    main()
