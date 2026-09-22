"""
SentinelDesk — Ticket Escalation Decision Trace

Encodes a support team's informal escalation policy as an explicit,
structured, testable decision trace: instead of an escalation call
living only in a senior agent's head, it's written down as an
inspectable set of rules with a human-readable reason attached to
every decision.

Stated rules (as given):
  1. Ticket age > 48 hours            -> escalate (SLA breach risk)
  2. Customer tier = premium          -> escalate (contractual priority)
  3. Genuine legal threat detected    -> escalate (legal exposure)
  4. Refund requested > $5000         -> escalate (high financial exposure)

A naive implementation of rule 3 (a plain substring search for the word
"legal") has a real failure mode: it escalates on ANY mention of the
word, including harmless ones ("I spoke to your legal team about
something unrelated"). That's exactly the kind of edge case this
module's test suite is built to catch -- caught here by actually
running the naive version first, seeing it misfire, and then fixing it
(see LEGAL_THREAT_PATTERNS below).
"""

import re
from dataclasses import dataclass, field


DECISION_TRACE = """
Ticket Escalation Decision Framework:
1. Ticket age > 48 hours => Escalate (SLA breach risk).
2. Customer tier = premium => Escalate (contractual priority).
3. Ticket text indicates a genuine legal threat (e.g. mentions of suing,
   lawyers, attorneys, legal action being taken AGAINST the company) =>
   Escalate (legal exposure). A passing mention of "legal" that is not a
   threat (e.g. referencing the company's own legal department by name,
   or an unrelated past legal interaction) does NOT by itself escalate.
4. Refund amount requested > $5000 => Escalate (high financial exposure).
5. Edge case rule: if a ticket sits right at a numeric boundary (ticket age
   very close to 48h, refund very close to $5000) apply the rule literally
   and precisely -- do not soften thresholds "to be safe," since an
   inconsistently-applied threshold is worse than a strict one: it makes
   the system's behavior unpredictable to the team relying on it.
"""

# A crude but real threat-language detector, standing in for a proper NLP
# classifier: naive keyword matching on "legal" alone is the bug; this
# narrows to phrases that indicate an actual threat of action, not an
# incidental mention.
LEGAL_THREAT_PATTERNS = [
    r"\bsu(e|ing|ed)\b",
    r"\blawyer\b",
    r"\battorney\b",
    r"\blawsuit\b",
    r"\blegal action\b",
    r"\bcontact(ing)? (my|our) legal\b",
    r"\btake legal\b",
    r"\bcourt\b",
]


@dataclass
class Ticket:
    ticket_id: str
    text: str
    age_hours: float
    customer_tier: str  # "standard" | "premium"
    refund_requested: float = 0.0


@dataclass
class Decision:
    ticket_id: str
    escalate: bool
    reason: str
    triggered_rules: list = field(default_factory=list)


def _mentions_legal_threat(text: str) -> bool:
    """Checks for actual threat language (sue, lawyer, attorney, legal
    action, etc.) directly -- NOT gated behind a check for the literal
    substring "legal" first, since real threats often don't contain that
    word at all (e.g. "I'm calling my lawyer"). An earlier version of this
    function had exactly that gate and silently failed to catch such
    threats -- caught only by running the edge-case tickets and inspecting
    the output, not by reading the code."""
    lowered = text.lower()
    return any(re.search(pattern, lowered) for pattern in LEGAL_THREAT_PATTERNS)


def _naive_mentions_legal(text: str) -> bool:
    """The buggy version: escalates on ANY mention of the word 'legal'."""
    return "legal" in text.lower()


def evaluate_ticket(ticket: Ticket, use_naive_legal_check: bool = False) -> Decision:
    """Runs the ticket against the decision trace and returns a structured
    decision with the reasoning that produced it -- not just yes/no."""
    triggered = []

    if ticket.age_hours > 48:
        triggered.append(
            f"ticket age {ticket.age_hours}h exceeds the 48h SLA threshold"
        )

    if ticket.customer_tier == "premium":
        triggered.append("customer tier is premium (contractual priority)")

    legal_threat = (
        _naive_mentions_legal(ticket.text)
        if use_naive_legal_check
        else _mentions_legal_threat(ticket.text)
    )
    if legal_threat:
        if use_naive_legal_check:
            triggered.append("ticket text contains the word 'legal'")
        else:
            triggered.append("ticket text indicates a genuine legal threat")

    if ticket.refund_requested > 5000:
        triggered.append(
            f"refund requested (${ticket.refund_requested:,.0f}) exceeds the $5,000 threshold"
        )

    if triggered:
        reason = "Escalate: " + "; ".join(triggered) + "."
        return Decision(ticket.ticket_id, True, reason, triggered)

    reason = (
        "No escalation: ticket age, tier, refund amount, and text all fall "
        "within normal-handling bounds; no rule was triggered."
    )
    return Decision(ticket.ticket_id, False, reason, triggered)
