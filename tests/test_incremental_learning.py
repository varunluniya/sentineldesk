"""
Incremental-loading fix: override_rates() used to re-pull and re-scan every decision+
outcome this system had ever logged on every call -- and override() calls
it after every single agent verdict, making it the hottest full-rescan in
this repo (the classic full-rescan mistake). These tests prove the incremental
replacement (running per-rule totals merged from only the NEW outcomes
since the last watermark) is idempotent and matches a from-scratch
recompute.
"""
from decision_trace import Ticket
from gen4 import KnowledgeBase, LLMClient, Memory
from service import SentinelDeskService


def T(text, age=1, tier="standard", refund=0):
    return Ticket("t", text, age, tier, refund)


def _svc():
    return SentinelDeskService(Memory(), KnowledgeBase.from_dir("knowledge"), LLMClient(provider="offline"))


def test_override_rates_is_idempotent_no_double_counting():
    svc = _svc()
    for k in range(5):
        r = svc.evaluate(T("hi", tier="premium"), customer_id=f"c{k}")
        svc.override(r["decision_id"], should_escalate=(k >= 2))

    first = svc.override_rates()
    second = svc.override_rates()
    third = svc.override_rates()
    assert first == second == third


def test_override_rates_picks_up_new_overrides_after_more_are_recorded():
    svc = _svc()
    for k in range(3):
        r = svc.evaluate(T("hi", tier="premium"), customer_id=f"c{k}")
        svc.override(r["decision_id"], should_escalate=False)
    first = svc.override_rates()
    assert first["per_rule"]["premium"]["fired"] == 3

    for k in range(3, 6):
        r = svc.evaluate(T("hi", tier="premium"), customer_id=f"c{k}")
        svc.override(r["decision_id"], should_escalate=False)
    second = svc.override_rates()
    assert second["per_rule"]["premium"]["fired"] == 6
    assert second["per_rule"]["premium"]["overridden"] == 6


def test_override_rates_matches_a_from_scratch_recompute():
    """Cross-check the incremental per-rule totals against an independent
    full re-derivation straight from memory.decisions() -- what
    override_rates() used to do on every call -- to prove the fix is
    mathematically equivalent, not just internally consistent."""
    from service import RULE_HEADINGS
    from gen4 import feedback as fb

    svc = _svc()
    for k in range(4):
        r = svc.evaluate(T("legal action incoming", age=50, tier="premium", refund=9000), customer_id=f"c{k}")
        svc.override(r["decision_id"], should_escalate=(k % 2 == 0))

    incremental = svc.override_rates()

    done = svc.memory.decisions(system="sentineldesk", with_outcome=True)
    rates = {}
    for rule in RULE_HEADINGS:
        fired = [d for d in done if rule in d["output"]["rules_fired"]]
        wrong = sum(1 for d in fired if not d["outcome"]["should_escalate"])
        rates[rule] = {"fired": len(fired), "overridden": wrong, "rate": fb.rate(wrong, len(fired))}
    missed = sum(1 for d in done if not d["output"]["escalate"] and d["outcome"]["should_escalate"])
    assert incremental == {"per_rule": rates, "missed_escalations": missed}
