#!/usr/bin/env python3
"""
Step 1 — Create the three Elasticsearch indices used by the demo.

1. bank-support-kb   (GENERIC knowledge) — semantic_text + plaintext.
                     Loan/FD rates, charges, fraud procedures, refund/pension
                     timelines. Searched semantically via the Jina endpoint.

2. bank-transactions (PRIVATE data) — structured per-customer transaction
                     history. Queried with ES|QL, scoped to one customer.

3. bank-customers    (PRIVATE data) — one profile per customer incl. DOB used
                     for lightweight identity verification on the call.
"""
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

ES_URL = os.environ["ELASTICSEARCH_URL"].rstrip("/")
ES_KEY = os.environ["ELASTIC_API_KEY"]
KB_INDEX = os.getenv("ES_INDEX", "bank-support-kb")
TXN_INDEX = os.getenv("TXN_INDEX", "bank-transactions")
CUST_INDEX = os.getenv("CUST_INDEX", "bank-customers")
INFERENCE_ID = os.getenv("INFERENCE_ID", ".jina-embeddings-v5-text-small")

HEADERS = {"Authorization": f"ApiKey {ES_KEY}", "Content-Type": "application/json"}

KB_MAPPING = {
    "mappings": {
        "_meta": {"description": (
            "Bharat Bank GENERIC knowledge base: loan & deposit interest rates, "
            "fees and charges, UPI/banking fraud handling, and 'where is my "
            "money' explainers (failed-transaction auto-reversal, refund and "
            "pension timelines). Used by a voice agent for general questions."
        )},
        "properties": {
            "title": {"type": "text"},
            "category": {"type": "keyword"},
            "tags": {"type": "keyword"},
            "content": {"type": "text", "copy_to": "content_semantic"},
            "content_semantic": {"type": "semantic_text", "inference_id": INFERENCE_ID},
        },
    }
}

TXN_MAPPING = {
    "mappings": {
        "_meta": {"description": (
            "Bharat Bank PRIVATE customer transaction history: credits and "
            "debits (salary, EMI, UPI, ATM, POS, refunds, pension, interest) "
            "with amount, channel, counterparty, status and running balance. "
            "Query scoped to a single customer_id."
        )},
        "properties": {
            "txn_id": {"type": "keyword"},
            "customer_id": {"type": "keyword"},
            "account_no": {"type": "keyword"},
            "txn_time": {"type": "date"},
            "type": {"type": "keyword"},
            "amount": {"type": "double"},
            "currency": {"type": "keyword"},
            "channel": {"type": "keyword"},
            "counterparty": {"type": "keyword"},
            "description": {"type": "text"},
            "category": {"type": "keyword"},
            "status": {"type": "keyword"},
            "balance_after": {"type": "double"},
        },
    }
}

CUST_MAPPING = {
    "mappings": {
        "_meta": {"description": (
            "Bharat Bank PRIVATE customer profiles: name, account, registered "
            "mobile (last 4), date of birth (for identity verification), KYC / "
            "UPI / account status, products and city."
        )},
        "properties": {
            "customer_id": {"type": "keyword"},
            "name": {"type": "keyword"},
            "account_no": {"type": "keyword"},
            "account_last4": {"type": "keyword"},
            "mobile_last4": {"type": "keyword"},
            "dob": {"type": "keyword"},
            "dob_display": {"type": "keyword"},
            "email_masked": {"type": "keyword"},
            "city": {"type": "keyword"},
            "preferred_language": {"type": "keyword"},
            "products": {"type": "keyword"},
            "kyc_status": {"type": "keyword"},
            "upi_status": {"type": "keyword"},
            "account_status": {"type": "keyword"},
        },
    }
}

INDICES = [(KB_INDEX, KB_MAPPING), (TXN_INDEX, TXN_MAPPING), (CUST_INDEX, CUST_MAPPING)]


def main():
    for index, mapping in INDICES:
        if requests.head(f"{ES_URL}/{index}", headers=HEADERS).status_code == 200:
            print(f"Index '{index}' exists — deleting for a clean run.")
            requests.delete(f"{ES_URL}/{index}", headers=HEADERS)
        print(f"Creating index '{index}' ...")
        r = requests.put(f"{ES_URL}/{index}", headers=HEADERS, json=mapping)
        if not r.ok:
            print(f"  FAILED: {r.status_code} {r.text}")
            sys.exit(1)
        print(f"  OK")
    print("\nAll indices created.")


if __name__ == "__main__":
    main()
