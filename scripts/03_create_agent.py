#!/usr/bin/env python3
"""
Step 3 — Create the Agent Builder tools + agent in Kibana.

Tools
  1. bank_kb_search        index_search over bank-support-kb (generic knowledge,
                           hybrid BM25 + semantic).
  2. customer_profile      ES|QL — one customer's profile (incl. DOB) for
                           identity verification, scoped by customer_id.
  3. customer_transactions ES|QL — one customer's recent transactions,
                           scoped by customer_id.

Agent ("Pratham Bank Support Agent") = the three tools + instructions that
verify the caller before disclosing money details and answer "where is my
money" questions from real transaction data.
"""
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

KIBANA_URL = os.environ["KIBANA_URL"].rstrip("/")
KIBANA_KEY = os.environ["KIBANA_API_KEY"]
SPACE = os.getenv("KIBANA_SPACE_ID", "").strip()
KB_INDEX = os.getenv("ES_INDEX", "bank-support-kb")
TXN_INDEX = os.getenv("TXN_INDEX", "bank-transactions")
CUST_INDEX = os.getenv("CUST_INDEX", "bank-customers")
AGENT_ID = os.getenv("AGENT_ID", "pratham-bank-support-agent")

BASE = KIBANA_URL + (f"/s/{SPACE}" if SPACE and SPACE != "default" else "")
API = f"{BASE}/api/agent_builder"
HEADERS = {"Authorization": f"ApiKey {KIBANA_KEY}", "Content-Type": "application/json", "kbn-xsrf": "true"}

TOOLS = [
    {
        "id": "bank_kb_search",
        "type": "index_search",
        "description": (
            "Search the Pratham Bank GENERAL knowledge base for non-personal "
            "questions: interest rates (home/personal loan, FD, savings), fees "
            "and transfer charges (NEFT/IMPS/RTGS/UPI), how to report UPI fraud "
            "(1930, cybercrime.gov.in), blocking a UPI ID or card, RBI rules, "
            "and explainers like 'money debited but transaction failed', refund "
            "timelines and pension credit timing. Use for anything that is NOT "
            "about this specific customer's own transactions."
        ),
        "configuration": {"pattern": KB_INDEX},
    },
    {
        "id": "customer_profile",
        "type": "esql",
        "description": (
            "Fetch ONE customer's profile by customer_id, including their date "
            "of birth, registered mobile last-4, account last-4, products and "
            "account/UPI/KYC status. Use this to VERIFY the caller's identity "
            "(compare the date of birth they tell you) and to answer questions "
            "about account or UPI status. Always pass the authenticated "
            "customer_id from the conversation context."
        ),
        "configuration": {
            "query": (
                f"FROM {CUST_INDEX} | WHERE customer_id == ?customer_id "
                "| KEEP customer_id, name, dob, dob_display, mobile_last4, "
                "account_last4, city, products, kyc_status, upi_status, "
                "account_status | LIMIT 1"
            ),
            "params": {
                "customer_id": {"type": "string", "description": "Authenticated customer id, e.g. CUST1002"}
            },
        },
    },
    {
        "id": "customer_transactions",
        "type": "esql",
        "description": (
            "Fetch ONE customer's recent transactions (newest first) by "
            "customer_id: salary, EMI, UPI, ATM, POS, refunds, pension, "
            "interest — each with amount, channel, counterparty, status "
            "(SUCCESS/PENDING/FAILED/DISPUTED) and balance after. Use this to "
            "answer 'where is my money', balance, 'did my salary/pension come', "
            "'why was money debited', refund status and disputed/suspicious "
            "transactions. Always pass the authenticated customer_id."
        ),
        "configuration": {
            "query": (
                f"FROM {TXN_INDEX} | WHERE customer_id == ?customer_id "
                "| SORT txn_time DESC | KEEP txn_time, type, amount, channel, "
                "counterparty, description, category, status, balance_after "
                "| LIMIT 30"
            ),
            "params": {
                "customer_id": {"type": "string", "description": "Authenticated customer id, e.g. CUST1002"}
            },
        },
    },
]

INSTRUCTIONS = (
    "You are Mitr, the voice banking assistant for Pratham Bank. "
    "Respond only in English — a translation layer handles the caller's language.\n\n"

    "AUTHENTICATED CONTEXT: Every message contains the caller's verified "
    "customer_id and name. Always pass exactly that customer_id to tools. "
    "Never access or reveal another customer's data.\n\n"

    "GREETING — on your FIRST reply in a call only: open with a short, warm "
    "greeting that uses the caller's first name and the bank name, e.g. "
    "'Namaste Priya ji, welcome to Pratham Bank. I am Mitr, your assistant.' "
    "Then continue with verification or the answer in the same reply. Greet "
    "only once per call; do not repeat the greeting on later turns.\n\n"

    "IDENTITY VERIFICATION — once per call, before sharing any account data:\n"
    "Call customer_profile to fetch the caller's profile, then ask: "
    "'Please tell me your date of birth to verify your identity.' "
    "Match day, month, and year against the dob field (accept any spoken format). "
    "If it matches, confirm verification and proceed. "
    "If it does not match, say you cannot share details and suggest visiting a branch. "
    "Never read the date of birth back to the caller. Do not ask again once verified.\n\n"

    "URGENCY DETECTION — classify the caller's intent before answering:\n"
    "URGENT (fraud, unknown debit, blocked card, OTP shared with someone): "
    "Lead immediately with the action steps — call 1930, call customer care "
    "1800-123-4567 to block UPI or card, file at cybercrime.gov.in. "
    "Then briefly confirm the suspicious transaction from customer_transactions.\n"
    "NORMAL (balance, salary, refund, pension, EMI, interest rates): "
    "Answer directly from customer_transactions or bank_kb_search. "
    "State the fact first, then any follow-up detail.\n\n"

    "ANSWERING RULES:\n"
    "- Keep responses concise — about 2-3 sentences (the first greeting turn "
    "may be slightly longer). Be warm and polite, like a helpful bank "
    "representative, not curt.\n"
    "- A short, genuine acknowledgement is welcome (e.g. for fraud: 'I "
    "understand, let's secure your account right away'), but avoid long filler "
    "that delays the actual answer.\n"
    "- Address the caller by their first name occasionally to stay personable.\n"
    "- Quote exact amounts with rupee symbol, dates, and counterparty names "
    "from the transaction data.\n"
    "- For PENDING credits (salary, refund, pension), state it is pending "
    "and give the expected timeline in one sentence.\n"
    "- End with one short follow-up question to keep the conversation going "
    "(e.g. 'Would you like more details?' or 'Anything else I can check?').\n"
    "- Never ask for or accept a UPI PIN, OTP, CVV, or password. "
    "If the caller mentions sharing one, immediately tell them that is a fraud "
    "sign and to call 1930 now.\n\n"

    "FORMATTING: Your response is read aloud by text-to-speech. "
    "Use plain spoken sentences only. No markdown, no asterisks, no bullet "
    "points, no hyphens as list markers, no headings, no special characters."
)

AGENT_PAYLOAD = {
    "id": AGENT_ID,
    "name": "Pratham Bank Support Agent",
    "description": "Voice agent: identity verification, 'where is my money', transactions & UPI fraud.",
    "configuration": {
        "instructions": INSTRUCTIONS,
        "tools": [{"tool_ids": [t["id"] for t in TOOLS]}],
    },
}


def recreate(kind, obj_id, payload):
    requests.delete(f"{API}/{kind}/{obj_id}", headers=HEADERS)
    r = requests.post(f"{API}/{kind}", headers=HEADERS, json=payload)
    if not r.ok:
        print(f"  FAILED to create {kind} '{obj_id}': {r.status_code} {r.text}")
        sys.exit(1)
    print(f"  created {kind}: {obj_id}")


def main():
    print("Deleting existing agent and tools ...")
    requests.delete(f"{API}/agents/{AGENT_ID}", headers=HEADERS)
    for t in TOOLS:
        requests.delete(f"{API}/tools/{t['id']}", headers=HEADERS)
    print("Creating tools ...")
    for t in TOOLS:
        recreate("tools", t["id"], t)
    print("Creating agent ...")
    recreate("agents", AGENT_ID, AGENT_PAYLOAD)
    print(f"\nDone. Agent '{AGENT_ID}' is ready with 3 tools.")


if __name__ == "__main__":
    main()
