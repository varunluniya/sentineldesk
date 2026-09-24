#!/usr/bin/env python3
"""
Seed SentinelDesk with 60 days of synthetic support-ticket history.

    python seed.py [--reset] [--if-empty]

About 520 tickets from 160 customers of a fictional consumer-lending app
(8% on the premium tier), replayed in date order through the real service
so the repeat-contact rule sees each customer's actual history. Ticket
texts are drawn from routine requests, frustrated follow-ups, genuine
legal/regulatory threats (including Indian routes: legal notice, consumer
forum, ombudsman, RBI), and look-alikes that are not threats (a colleague
named Sue, "your legal team", a food court). Agents review about 30% of
tickets and correct the system when it is wrong, which creates precedents.
All data is synthetic.
"""

from datetime import timedelta
from pathlib import Path

from decision_trace import Ticket
from gen4 import Memory
from gen4.seedkit import NOW, already_seeded, args, iso, mark
from service import SentinelDeskService

DAYS, N_CUSTOMERS = 60, 160

ROUTINE = [
    "My EMI date needs to move from the 5th to the 10th, how do I do that?",
    "The app logs me out every time I open it.",
    "I was charged a processing fee twice on loan {loan}.",
    "Can you send me the foreclosure statement for loan {loan}?",
    "My card is blocked after three wrong PIN attempts.",
    "Refund for the cancelled order has not reached my account yet.",
    "Please update my address, I have moved to Pune.",
    "Why is my credit limit lower than last month?",
    "Sue from your support team was very helpful yesterday, just closing the loop.",
    "I spoke to your legal team last month about a GST invoice; separately, the app is slow.",
    "I met your rep at the food court in the mall and he said to write here.",
    "The legal name on my account is misspelt, please fix it.",
    "Is it legal to prepay the loan in part? What are the charges?",
]
FRUSTRATED = [
    "This is the third time I am writing about loan {loan}. Nobody replies.",
    "Your agent promised a callback two days ago. Still nothing. Very disappointed.",
    "I'm not going to sue, I just want my money back for the double charge.",
    "Fix this today or I will close all my accounts with you.",
]
THREATS = [
    "If this is not resolved by Friday I will send you a legal notice.",
    "I am taking this to the consumer forum next week.",
    "My advocate will be in touch about the wrongful late fees.",
    "I have already escalated this to the banking ombudsman.",
    "I will file a complaint with the RBI about your recovery agents.",
    "My lawyer is reviewing the loan agreement you sent.",
    "We will take legal action against your company.",
    "Complaint registered with the IRDAI about the insurance you bundled, reference attached.",
]
TRICKY_NON_THREAT = ["My brother is a lawyer and says the charge is fine, I just want it explained."]


def main():
    a, rng = args("data/sentineldesk.db", "Seed SentinelDesk with synthetic ticket history")
    Path(a.db).parent.mkdir(parents=True, exist_ok=True)
    mem = Memory(a.db)
    if a.if_empty and already_seeded(mem):
        print(f"{a.db} already has data -- skipping seed")
        return
    svc = SentinelDeskService(memory=mem)
    customers = [{"id": f"C-{k:04d}", "tier": "premium" if rng.random() < 0.08 else "standard",
                  "activity": rng.choice([1, 1, 1, 2, 3, 6])} for k in range(1, N_CUSTOMERS + 1)]
    tickets = []
    for c in customers:
        for _ in range(c["activity"]):
            start = rng.uniform(0, DAYS)
            tickets.append((start, c))
            # a noisy customer comes back within days
            if c["activity"] >= 3 and rng.random() < 0.6:
                tickets.append((max(0.05, start - rng.uniform(0.5, 4)), c))
    tickets.sort(key=lambda x: -x[0])   # oldest first

    stats = {"tickets": 0, "escalated": 0, "reviewed_by_agent": 0, "overrides": 0, "precedents": 0}
    for i, (days_ago, c) in enumerate(tickets):
        kind = rng.choices(["routine", "frustrated", "threat", "tricky"], [0.66, 0.2, 0.11, 0.03])[0]
        text = rng.choice({"routine": ROUTINE, "frustrated": FRUSTRATED, "threat": THREATS,
                           "tricky": TRICKY_NON_THREAT}[kind]).format(loan=f"LN{rng.randint(100000, 999999)}")
        age = round(min(120, rng.expovariate(1 / 18)), 1)
        refund = rng.choice([0] * 8 + [rng.randint(200, 4800), rng.randint(5200, 40000)])
        t = Ticket(f"TK-{30000 + i}", text, age, c["tier"], refund)
        when = NOW - timedelta(days=days_ago)
        r = svc.evaluate(t, customer_id=c["id"], now=when)
        stats["tickets"] += 1
        stats["escalated"] += r["escalate"]
        true_threat = kind == "threat"
        should = true_threat or age > 48 or c["tier"] == "premium" or refund > 5000 or "repeat" in r["rules_fired"]
        system_legal = "legal" in r["rules_fired"] or "precedent" in r["rules_fired"]
        disagree = should != r["escalate"] or true_threat != system_legal
        if disagree and rng.random() < 0.8 or rng.random() < 0.25:
            stats["reviewed_by_agent"] += 1
            before = len(mem.facts(predicate="legal_precedent"))
            svc.override(r["decision_id"], should_escalate=should,
                         legal_threat=true_threat if true_threat != system_legal else None,
                         agent=rng.choice(["asha", "rahul", "meera", "imran"]))
            stats["overrides"] += disagree
            stats["precedents"] += len(mem.facts(predicate="legal_precedent")) - before
            mem.backdate(r["decision_id"], when.isoformat(), iso(max(0.01, days_ago - 0.2)))

    rates = svc.override_rates()
    mark(mem, "sentineldesk", a.seed, stats)
    print(f"seeded {a.db}: {stats}")
    print("override rate per rule:", {k: v["rate"] for k, v in rates["per_rule"].items() if v["fired"]},
          "missed:", rates["missed_escalations"])


if __name__ == "__main__":
    main()
