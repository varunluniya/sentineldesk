"""
Legal-threat classifier v2 — threat *intent*, not keywords.

v1 fixed the "only check if the word 'legal' appears" bug, but a regex list
still fails both ways on real support text:
    false positive  "Sue from your billing team was great"      (a name)
    false positive  "I'm not going to sue, I just want a refund" (negated)
    false positive  "met your rep at the food court"             (not a court)
    missed          "I will send you a legal notice"             (common in India)
    missed          "taking this to the consumer forum"
    missed          "my advocate will be in touch"
    missed          "escalating to the banking ombudsman"

v2 checks threat phrases (including India-specific legal and regulatory
routes), then applies guards for negation, personal names, and non-legal
senses of "court". Returns the matched evidence so every call is explainable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

THREAT_PATTERNS = [
    (r"\b(sue|suing|sued)\b", "sue"),
    (r"\blaw ?suit\b", "lawsuit"),
    (r"\b(my|our|a) (lawyer|attorney|advocate|solicitor|legal counsel)s?\b", "lawyer"),
    (r"\b(lawyer|attorney|advocate|solicitor)s? (will|is going to|are going to)\b", "lawyer"),
    (r"\blegal (action|notice|proceedings|recourse)\b", "legal action/notice"),
    (r"\b(take|taking|drag|dragging|see|seeing) (you|this|it|them|your company)\b.{0,20}\bcourt\b", "court"),
    (r"\b(file|filing|lodge|lodging) (a |an )?(case|suit|fir|police complaint)\b", "file a case"),
    (r"\bcomplaint (with|to) (the )?(rbi|sebi|irdai|regulator|police|consumer)", "regulator"),
    (r"\bconsumer (forum|court|commission)\b", "consumer forum"),
    (r"\b(ombudsman|small claims)\b", "ombudsman/small claims"),
    (r"\b(report|reporting|complain|complaining) (you )?to (the )?(rbi|sebi|irdai|regulator|police)\b", "regulator"),
]
NEGATIONS = re.compile(
    r"\b(not|never|no need|don't|dont|won't|wont|no intention|not planning|not going)\b[^.!?]{0,25}$")
# a capitalised "Sue" used as a person: "Sue from billing", "spoke to Sue"
NAME_CONTEXT = re.compile(r"\bSue\b\s+(from|at|in|on|was|is|said|helped|told|kindly)\b|"
                          r"\b([Ss]poke|[Tt]alked|[Cc]hatted|[Tt]hanks|[Tt]hank you|[Aa]gent|with)\s+(to\s+)?Sue\b")
NON_LEGAL_COURT = re.compile(r"\b(food|tennis|basketball|badminton|squash) court\b")


@dataclass
class ThreatResult:
    threat: bool
    evidence: list = field(default_factory=list)
    suppressed: list = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"threat": self.threat, "evidence": self.evidence, "suppressed": self.suppressed}


def classify(text: str) -> ThreatResult:
    lowered = text.lower()
    evidence, suppressed = [], []
    for pattern, label in THREAT_PATTERNS:
        for m in re.finditer(pattern, lowered):
            span = text[m.start():m.end()]
            before = lowered[max(0, m.start() - 60):m.start()]
            before = re.split(r"[.!?;,]| but ", before)[-1]
            if label == "sue" and NAME_CONTEXT.search(text[max(0, m.start() - 20):m.end() + 20]):
                suppressed.append(f"'{span}' looks like a person's name")
                continue
            if label == "court" and NON_LEGAL_COURT.search(lowered[max(0, m.end() - 20):m.end()]):
                suppressed.append(f"'{span}' is not a law court")
                continue
            if NEGATIONS.search(before):
                suppressed.append(f"'{span}' is negated")
                continue
            evidence.append(f"{label}: '{span}'")
    evidence = list(dict.fromkeys(evidence))
    return ThreatResult(bool(evidence), evidence, suppressed)
