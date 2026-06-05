#!/usr/bin/env python3
"""
Dynamic transaction generator for the "Where is my money?" demo.

Produces 100+ transactions across the four demo customers, with timestamps
spread over the LAST 30 DAYS relative to *now*. Because dates are computed at
run time, re-running the ingest (today, or in six months) always yields data
in the now-30d → now window. The customer "story hooks" (disputed UPI debit,
pending refund, delayed pension, etc.) are anchored to recent day-offsets so
they stay current on every run.

Balances are kept consistent and non-negative: each customer's starting balance
is set to (floor + total posted debits), which guarantees the running balance
never drops below their floor.

Run directly to write a fresh snapshot to data/transactions.json:
    python scripts/generate_transactions.py
"""
import os
import json
import random
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))

# (display name, upi handle, category, (min_amt, max_amt))
UPI_DEBIT_MERCHANTS = [
    ("Swiggy", "swiggy@ybl", "Food", (120, 650)),
    ("Zomato", "zomato@ibl", "Food", (150, 720)),
    ("BigBasket", "bigbasket@ybl", "Groceries", (400, 2200)),
    ("Blinkit", "blinkit@ybl", "Groceries", (150, 900)),
    ("Reliance Smart", "relsmart@ybl", "Groceries", (500, 3000)),
    ("Amazon", "amazonpay@apl", "Shopping", (300, 4500)),
    ("Myntra", "myntra@ybl", "Shopping", (600, 3500)),
    ("Flipkart", "flipkart@axl", "Shopping", (400, 3800)),
    ("Jio Recharge", "jio@ybl", "Telecom", (199, 999)),
    ("Airtel Recharge", "airtel@ybl", "Telecom", (199, 999)),
    ("Electricity Bill", "discom@sbi", "Utilities", (800, 3200)),
    ("Indian Oil Petrol", "ioc@ybl", "Fuel", (500, 2500)),
    ("Apollo Pharmacy", "apollo@ybl", "Healthcare", (150, 1800)),
    ("Uber", "uber@ybl", "Transport", (80, 520)),
    ("Ola Cabs", "ola@ybl", "Transport", (90, 540)),
    ("Local Kirana Store", "kirana@paytm", "Groceries", (100, 800)),
]

INCOMING_SENDERS = [
    ("Rahul Sharma", "Transfer"),
    ("Amit Patel", "Transfer"),
    ("Sneha Reddy", "Transfer"),
    ("Vikram Singh", "Transfer"),
]


def _dt(now, days_ago, hour=None, minute=None, rnd=None):
    base = now - timedelta(days=days_ago)
    h = hour if hour is not None else (rnd.randint(8, 21) if rnd else 12)
    m = minute if minute is not None else (rnd.randint(0, 59) if rnd else 0)
    return base.replace(hour=h, minute=m, second=0, microsecond=0)


def _txn(cust, dt, ttype, amount, channel, counterparty, desc, category, status):
    return {
        "customer_id": cust["customer_id"],
        "account_no": cust["account_no"],
        "txn_time": dt,  # datetime for now; isoformat applied later
        "type": ttype,
        "amount": int(round(amount)),
        "currency": "INR",
        "channel": channel,
        "counterparty": counterparty,
        "description": desc,
        "category": category,
        "status": status,
        "balance_after": None,
    }


def _routine(cust, now, rnd, count):
    """Random everyday UPI activity over the last 30 days (mostly debits)."""
    events = []
    for _ in range(count):
        days_ago = rnd.randint(1, 30)
        if rnd.random() < 0.10:  # ~10% incoming transfers for variety
            sender, cat = rnd.choice(INCOMING_SENDERS)
            amt = rnd.choice([200, 300, 500, 750, 1000, 1500, 2000])
            events.append(_txn(cust, _dt(now, days_ago, rnd=rnd), "credit", amt,
                               "UPI", sender, f"UPI received from {sender}", cat, "SUCCESS"))
        else:
            name, handle, cat, (lo, hi) = rnd.choice(UPI_DEBIT_MERCHANTS)
            amt = rnd.randint(lo, hi)
            events.append(_txn(cust, _dt(now, days_ago, rnd=rnd), "debit", amt,
                               "UPI", handle, f"UPI payment to {name}", cat, "SUCCESS"))
    return events


def _finalise(cust, events, floor):
    """Sort chronologically and assign consistent, non-negative balances."""
    posted_debits = sum(e["amount"] for e in events if e["type"] == "debit" and e["status"] == "SUCCESS")
    balance = floor + posted_debits  # guarantees running balance >= floor
    events.sort(key=lambda e: e["txn_time"])
    for i, e in enumerate(events, 1):
        if e["status"] == "SUCCESS":
            balance += e["amount"] if e["type"] == "credit" else -e["amount"]
        # PENDING / FAILED do not change the posted balance
        e["balance_after"] = int(balance)
        e["txn_id"] = f"{cust['customer_id']}-{i:03d}"
        e["txn_time"] = e["txn_time"].astimezone(IST).isoformat()
    return events


def generate(customers):
    """Return a list of transaction dicts for all customers (dynamic dates)."""
    by_id = {c["customer_id"]: c for c in customers}
    now = datetime.now(IST).replace(microsecond=0)
    all_txns = []

    # ── CUST1001 Rajesh — salaried, lots of activity, pending refund ──
    c = by_id["CUST1001"]; rnd = random.Random(1001)
    ev = _routine(c, now, rnd, 40)
    ev += [
        _txn(c, _dt(now, 4, 10, 0), "credit", 120000, "SALARY", "TechCorp India Pvt Ltd",
             "Salary credit - TechCorp India Pvt Ltd", "Salary", "SUCCESS"),
        _txn(c, _dt(now, 3, 6, 30), "debit", 38500, "EMI", "Bharat Bank Home Loan LN44567",
             "Home loan EMI auto-debit (loan a/c LN44567)", "Loan EMI", "SUCCESS"),
        _txn(c, _dt(now, 1, 8, 30), "debit", 10000, "ACH", "ABC Bluechip Mutual Fund",
             "Auto-debit SIP - ABC Bluechip Mutual Fund", "Investment", "SUCCESS"),
        _txn(c, _dt(now, 1, 16, 0), "debit", 10000, "ATM", "ATM MG Road, Bengaluru",
             "ATM cash withdrawal - MG Road, Bengaluru", "Cash", "SUCCESS"),
        _txn(c, _dt(now, 26, 18, 30), "credit", 842, "INTEREST", "Bharat Bank",
             "Savings account interest credit", "Interest", "SUCCESS"),
        _txn(c, _dt(now, 2, 12, 0), "credit", 2499, "REFUND", "Flipkart order FK7783421",
             "Refund processing for Flipkart order FK7783421 - not yet credited", "Refund", "PENDING"),
    ]
    all_txns += _finalise(c, ev, floor=15000)

    # ── CUST1002 Priya — disputed UPI debit (fraud) ──
    c = by_id["CUST1002"]; rnd = random.Random(1002)
    ev = _routine(c, now, rnd, 28)
    ev += [
        _txn(c, _dt(now, 4, 10, 5), "credit", 85000, "SALARY", "Infotech Solutions Pvt Ltd",
             "Salary credit - Infotech Solutions Pvt Ltd", "Salary", "SUCCESS"),
        _txn(c, _dt(now, 2, 14, 46), "debit", 14999, "UPI", "quickpay@okaxis",
             "UPI payment to QUICKPAY (P2M) - flagged as disputed by customer", "Suspicious", "DISPUTED"),
        _txn(c, _dt(now, 2, 14, 48), "debit", 14999, "UPI", "quickpay@okaxis",
             "UPI payment attempt to QUICKPAY (P2M) - declined by fraud monitoring", "Suspicious", "FAILED"),
        _txn(c, _dt(now, 1, 9, 0), "credit", 500, "UPI", "Rahul Sharma",
             "UPI received from Rahul Sharma", "Transfer", "SUCCESS"),
    ]
    all_txns += _finalise(c, ev, floor=20000)

    # ── CUST1003 Anil — pensioner, this month's pension pending ──
    c = by_id["CUST1003"]; rnd = random.Random(1003)
    ev = _routine(c, now, rnd, 16)
    ev += [
        _txn(c, _dt(now, 29, 7, 0), "credit", 32000, "PENSION", "Treasury / CPAO",
             "Monthly pension credit (previous month)", "Pension", "SUCCESS"),
        _txn(c, _dt(now, 2, 10, 0), "credit", 32000, "PENSION", "Treasury / CPAO",
             "Monthly pension credit (current month) - processing, not yet credited", "Pension", "PENDING"),
        _txn(c, _dt(now, 8, 10, 45), "debit", 20000, "ATM", "ATM Hazratganj, Lucknow",
             "ATM cash withdrawal - Hazratganj, Lucknow", "Cash", "SUCCESS"),
    ]
    all_txns += _finalise(c, ev, floor=8000)

    # ── CUST1004 Sunita — basic account, pending Meesho refund ──
    c = by_id["CUST1004"]; rnd = random.Random(1004)
    ev = _routine(c, now, rnd, 12)
    ev += [
        _txn(c, _dt(now, 7, 17, 30), "credit", 5000, "UPI", "Manoj Kumar",
             "UPI received from Manoj Kumar (son)", "Transfer", "SUCCESS"),
        _txn(c, _dt(now, 4, 15, 40), "debit", 2499, "UPI", "meesho@ybl",
             "UPI payment to Meesho for order MSH556677", "Shopping", "SUCCESS"),
        _txn(c, _dt(now, 1, 13, 20), "credit", 2499, "REFUND", "Meesho return MSH556677",
             "Refund processing for Meesho return MSH556677 - not yet credited", "Refund", "PENDING"),
    ]
    all_txns += _finalise(c, ev, floor=800)

    return all_txns


if __name__ == "__main__":
    HERE = os.path.dirname(os.path.abspath(__file__))
    DATA = os.path.join(HERE, "..", "data")
    with open(os.path.join(DATA, "customers.json"), encoding="utf-8") as f:
        custs = json.load(f)
    txns = generate(custs)
    out = os.path.join(DATA, "transactions.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(txns, f, ensure_ascii=False, indent=2)
    span_min = min(t["txn_time"] for t in txns)
    span_max = max(t["txn_time"] for t in txns)
    print(f"Generated {len(txns)} transactions across {len({t['customer_id'] for t in txns})} customers.")
    print(f"Date range: {span_min}  ->  {span_max}")
    print(f"Snapshot written to {out}")
