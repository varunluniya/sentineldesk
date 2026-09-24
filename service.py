"""
SentinelDesk intelligent service — ticket escalation with Gen-4 layers.

    Retrieval  escalation policy; every triggered rule is cited
    Context    the customer's recent contacts (repeat-contact rule), tier, age
    Memory     every ticket decision, agent overrides, precedents
    Feedback   agent corrections of the legal-threat call become precedents;
               override rates per rule are tracked for the support lead

v1 encoded four rules and a regex threat detector. v2 keeps the hard rules
exactly (literal boundaries), replaces the regex with an intent classifier
(negation, names, India-specific legal routes), adds a repeat-contact rule
from customer memory, and learns from agent corrections via precedents.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from decision_trace import Ticket
from gen4 import Context, KnowledgeBase, LLMClient, Memory, Trace
from gen4 import feedback as fb
from gen4.retrieval import tokenize
from threat import classify

SYSTEM = "sentineldesk"
HERE = Path(__file__).parent
AGE_LIMIT_H = 48
REFUND_LIMIT = 5000
REPEAT_CONTACTS = 3
REPEAT_WINDOW_DAYS = 7
PRECEDENT_SIMILARITY = 0.6
RULE_HEADINGS = {"age": "Rule 1: SLA breach risk", "premium": "Rule 2: Premium tier",
                 "legal": "Rule 3: Genuine legal threat", "refund": "Rule 4: High refund",
                 "repeat": "Rule 5: Repeat contact", "precedent": "Precedents"}


def _jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


class SentinelDeskService:
    def __init__(self, memory: Memory | None = None, kb: KnowledgeBase | None = None,
                 llm: LLMClient | None = None):
        self.memory = memory or Memory(os.environ.get("GEN4_DB", HERE / "data" / f"{SYSTEM}.db"))
        self.kb = kb or KnowledgeBase.from_dir(HERE / "knowledge")
        self.llm = llm or LLMClient()

    def recent_contacts(self, customer_id: str) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=REPEAT_WINDOW_DAYS)
        return sum(1 for d in self.memory.history(f"customer:{customer_id}", limit=100)
                   if datetime.fromisoformat(d["ts"]) >= cutoff)

    def _precedent(self, text: str) -> dict | None:
        toks = set(tokenize(text))
        best = None
        for f in self.memory.facts(predicate="legal_precedent"):
            p = f["object"]
            s = _jaccard(toks, set(p["tokens"]))
            if s >= PRECEDENT_SIMILARITY and (best is None or s > best["similarity"]):
                best = {**p, "similarity": round(s, 3), "decision_id": f["subject"].split(":", 1)[1]}
        return best

    def _llm_threat(self, text: str) -> bool | None:
        if not self.llm.is_live:
            return None
        r = self.llm.complete_json(
            "Is this customer support message a genuine threat of legal or regulatory action against the "
            f'company? Message: """{text}"""\nReturn {{"threat": true|false, "reason": "..."}}',
            offline=lambda: {"threat": None}, validate=lambda d: isinstance(d.get("threat"), bool))
        return r.get("threat")

    # -- decision -----------------------------------------------------------------------
    def evaluate(self, t: Ticket, customer_id: str | None = None) -> dict:
        trace = Trace()
        fired: list[tuple[str, str]] = []
        if t.age_hours > AGE_LIMIT_H:
            fired.append(("age", f"ticket age {t.age_hours}h exceeds the {AGE_LIMIT_H}h SLA threshold"))
        if t.customer_tier == "premium":
            fired.append(("premium", "customer tier is premium (contractual priority)"))
        if t.refund_requested > REFUND_LIMIT:
            fired.append(("refund", f"refund requested ({t.refund_requested:,.0f}) exceeds {REFUND_LIMIT:,}"))

        rule_threat = classify(t.text)
        model_threat = self._llm_threat(t.text)
        precedent = self._precedent(t.text)
        needs_check = model_threat is not None and model_threat != rule_threat.threat
        legal = rule_threat.threat or bool(model_threat)
        if legal:
            fired.append(("legal", "genuine legal/regulatory threat: " + "; ".join(rule_threat.evidence or ["model"])))
        if precedent:
            if precedent["threat"] and not legal:
                fired.append(("precedent", f"resembles ticket {precedent['decision_id']} that an agent "
                                           f"marked as a legal threat (similarity {precedent['similarity']})"))
            elif not precedent["threat"] and legal:
                needs_check = True

        prior = self.recent_contacts(customer_id) if customer_id else 0
        if customer_id and prior + 1 >= REPEAT_CONTACTS:
            fired.append(("repeat", f"contact #{prior + 1} from this customer within {REPEAT_WINDOW_DAYS} days"))

        trace.context = (Context().add("customer_contacts_7d", prior, "repeat-contact rule")
                         .add("tier", t.customer_tier).add("age_hours", t.age_hours)).as_dict()
        trace.memory = {"precedent": precedent and {k: precedent[k] for k in ("decision_id", "similarity", "threat")},
                        "customer_tickets_on_file": prior}
        trace.model = {"provider": self.llm.provider, "model_threat": model_threat,
                       "rule_threat": rule_threat.as_dict()}
        passages = []
        for rule, _ in fired or [("none", "")]:
            passages += self.kb.search(RULE_HEADINGS.get(rule, "passing mention is not a threat"), k=1)
        trace.cite({(p.source, p.heading): p for p in passages}.values())

        escalate = bool(fired)
        reason = ("Escalate: " + "; ".join(msg for _, msg in fired) + ".") if escalate else \
            "No escalation: age, tier, refund, contact history and text all within normal handling."
        out = {"ticket_id": t.ticket_id, "escalate": escalate, "rules_fired": [r for r, _ in fired],
               "reason": reason, "needs_human_check": needs_check,
               "legal_threat": rule_threat.as_dict()}
        did = self.memory.record_decision(SYSTEM, f"customer:{customer_id}" if customer_id else t.ticket_id,
                                          {"text": t.text, "age_hours": t.age_hours, "tier": t.customer_tier,
                                           "refund": t.refund_requested}, out)
        return {"decision_id": did, **out, "trace": trace.as_dict()}

    # -- feedback --------------------------------------------------------------------------
    def override(self, decision_id: str, should_escalate: bool, legal_threat: bool | None = None,
                 agent: str = "agent", note: str = "") -> dict:
        d = self.memory.get_decision(decision_id)
        if not d:
            raise KeyError(decision_id)
        self.memory.record_outcome(decision_id, {"should_escalate": should_escalate,
                                                 "legal_threat": legal_threat, "agent": agent, "note": note})
        learned = []
        was_legal = "legal" in d["output"]["rules_fired"] or "precedent" in d["output"]["rules_fired"]
        if legal_threat is not None and legal_threat != was_legal:
            self.memory.add_fact(f"precedent:{decision_id}", "legal_precedent",
                                 {"tokens": sorted(set(tokenize(d["features"]["text"]))),
                                  "threat": legal_threat, "text": d["features"]["text"][:300]}, source=agent)
            learned.append("legal-threat precedent stored")
        return {"learned": learned, "override_rates": self.override_rates()}

    def override_rates(self) -> dict:
        done = self.memory.decisions(system=SYSTEM, with_outcome=True)
        rates = {}
        for rule in RULE_HEADINGS:
            fired = [d for d in done if rule in d["output"]["rules_fired"]]
            wrong = sum(1 for d in fired if not d["outcome"]["should_escalate"])
            rates[rule] = {"fired": len(fired), "overridden": wrong, "rate": fb.rate(wrong, len(fired))}
        missed = sum(1 for d in done if not d["output"]["escalate"] and d["outcome"]["should_escalate"])
        self.memory.add_fact("model:sentineldesk", "override_rates", rates)
        return {"per_rule": rates, "missed_escalations": missed}
