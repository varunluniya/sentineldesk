#!/usr/bin/env python3
"""
SentinelDesk eval gate. Segments:
  v1_tickets   the 4 original demo tickets keep their v1 decisions
  boundary     literal 48h / 5,000 boundaries
  threat       20 labelled texts: genuine threats vs passing mentions
  repeat       third contact in 7 days escalates
  precedent    an agent's correction is applied to a near-identical ticket
  held_out     10 texts written after tuning; floor 80% (honest generalisation check)
"""

from decision_trace import Ticket
from gen4 import KnowledgeBase, LLMClient, Memory
from gen4.evals import EvalCase, gate, print_and_exit, run_eval
from run_demo import TICKETS
from service import SentinelDeskService
from threat_cases import HELD_OUT, THREAT_CASES


def fresh():
    return SentinelDeskService(Memory(), KnowledgeBase.from_dir("knowledge"), LLMClient(provider="offline"))


def system(inp):
    svc = fresh()
    kind = inp[0]
    if kind == "ticket":
        return svc.evaluate(inp[1])["escalate"]
    if kind == "threat":
        return "legal" in svc.evaluate(Ticket("t", inp[1], 1, "standard", 0))["rules_fired"]
    if kind == "repeat":
        return [svc.evaluate(Ticket(f"r{i}", "Where is my order?", 1, "standard", 0), customer_id="c1")["escalate"]
                for i in range(3)]
    if kind == "precedent":
        text = "Your agent was rude and I am done, expect to hear from the district forum."
        first = svc.evaluate(Ticket("p1", text, 1, "standard", 0))
        svc.override(first["decision_id"], should_escalate=True, legal_threat=True)
        again = svc.evaluate(Ticket("p2", text.replace("done", "finished"), 1, "standard", 0))
        return (first["escalate"], again["escalate"], again["rules_fired"])
    raise ValueError(kind)


V1_EXPECTED = [True, False, True, False]
cases = [EvalCase(t.ticket_id, ("ticket", t), e, "v1_tickets") for t, e in zip(TICKETS, V1_EXPECTED)]
cases += [
    EvalCase("age-48.0", ("ticket", Ticket("b1", "hi", 48.0, "standard", 0)), False, "boundary"),
    EvalCase("age-48.01", ("ticket", Ticket("b2", "hi", 48.01, "standard", 0)), True, "boundary"),
    EvalCase("refund-5000", ("ticket", Ticket("b3", "hi", 1, "standard", 5000)), False, "boundary"),
    EvalCase("refund-5000.01", ("ticket", Ticket("b4", "hi", 1, "standard", 5000.01)), True, "boundary"),
]
cases += [EvalCase(f"threat-{i:02d} {note}", ("threat", text), truth, "threat")
          for i, (text, truth, note) in enumerate(THREAT_CASES)]
cases += [EvalCase(f"heldout-{i:02d} {note}", ("threat", text), truth, "held_out")
          for i, (text, truth, note) in enumerate(HELD_OUT)]
cases.append(EvalCase("third-contact", ("repeat",), [False, False, True], "repeat"))
cases.append(EvalCase("precedent-learned", ("precedent",), (False, True, ["precedent"]), "precedent"))

if __name__ == "__main__":
    report = run_eval(cases, system, runs=3)
    # held_out is reported, with a floor of 80%; everything else must be perfect.
    floors = {s: 1.0 for s in ("v1_tickets", "boundary", "threat", "repeat", "precedent")}
    floors["held_out"] = 0.8
    ok, why = gate(report, min_accuracy=0.9, min_consistency=1.0, segment_floors=floors)
    print_and_exit("SentinelDesk", report, ok, why)
