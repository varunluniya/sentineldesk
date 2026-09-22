"""
Runs 4 representative support tickets against the decision trace:
  1. A clear escalation
  2. A clear non-escalation
  3. An edge case that SHOULD escalate (a real legal threat, phrased casually)
  4. An edge case that should NOT escalate (mentions "legal" but isn't a
     threat, and sits just under the refund/age thresholds)

Also demonstrates the naive-keyword-matching bug on ticket 4, to show the
failure mode this design is specifically built to avoid.
"""

from decision_trace import Ticket, evaluate_ticket, DECISION_TRACE


TICKETS = [
    Ticket(
        ticket_id="T-101 (clear escalation)",
        text="I need a refund for my last two orders, this is unacceptable.",
        age_hours=5,
        customer_tier="standard",
        refund_requested=8000,
    ),
    Ticket(
        ticket_id="T-102 (clear non-escalation)",
        text="My package arrived a day late, just wanted to flag it, no big deal.",
        age_hours=2,
        customer_tier="standard",
        refund_requested=50,
    ),
    Ticket(
        ticket_id="T-103 (edge case: SHOULD escalate)",
        text=(
            "This is the third time this has happened and honestly at this "
            "point I'm going to have my lawyer look at the contract you sent me."
        ),
        age_hours=10,
        customer_tier="standard",
        refund_requested=0,
    ),
    Ticket(
        ticket_id="T-104 (edge case: should NOT escalate)",
        text=(
            "I spoke to your legal team last month about an unrelated licensing "
            "question -- separately, this shipping delay is pretty frustrating."
        ),
        age_hours=47,
        customer_tier="standard",
        refund_requested=4990,
    ),
]


def main():
    print("=" * 78)
    print("DECISION TRACE (the structured policy every ticket is evaluated against):")
    print(DECISION_TRACE)
    print("=" * 78)

    print("\n--- Fixed decision trace (contextual legal-threat detection) ---\n")
    for ticket in TICKETS:
        decision = evaluate_ticket(ticket)
        print(f"[{ticket.ticket_id}]")
        print(f"  Escalate: {decision.escalate}")
        print(f"  Reason:   {decision.reason}")
        print()

    print("=" * 78)
    print("BUG DEMONSTRATION: naive substring match on the word 'legal'")
    print("(shows why contextual detection was necessary for T-104)")
    print("=" * 78)
    naive_decision = evaluate_ticket(TICKETS[3], use_naive_legal_check=True)
    print(f"\n[{TICKETS[3].ticket_id}] under NAIVE keyword matching:")
    print(f"  Escalate: {naive_decision.escalate}  <-- WRONG, this is a false positive")
    print(f"  Reason:   {naive_decision.reason}")
    print(
        "\nThe naive version escalates T-104 purely because the word 'legal' "
        "appears anywhere in the text, even in a harmless, unrelated mention. "
        "The fixed version in decision_trace.py checks for actual threat "
        "language (sue, lawyer, attorney, legal action, etc.) instead of a "
        "bare substring match, which is what correctly keeps T-104 from "
        "escalating while still correctly escalating T-103's real threat."
    )


if __name__ == "__main__":
    main()
