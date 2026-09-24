import pytest

from decision_trace import Ticket
from gen4 import KnowledgeBase, LLMClient, Memory
from service import SentinelDeskService


@pytest.fixture
def svc():
    return SentinelDeskService(Memory(), KnowledgeBase.from_dir("knowledge"), LLMClient(provider="offline"))


def T(text, age=1, tier="standard", refund=0):
    return Ticket("t", text, age, tier, refund)


def test_every_fired_rule_is_cited(svc):
    r = svc.evaluate(T("I will send a legal notice", age=50, tier="premium", refund=9000))
    assert set(r["rules_fired"]) == {"age", "premium", "refund", "legal"}
    headings = {c["heading"] for c in r["trace"]["retrieval"]}
    assert {"Rule 1: SLA breach risk", "Rule 3: Genuine legal threat"} <= headings


def test_name_sue_does_not_escalate_but_is_explained(svc):
    r = svc.evaluate(T("Sue from billing sorted it, thanks"))
    assert not r["escalate"]
    assert r["legal_threat"]["suppressed"]


def test_repeat_contact_is_per_customer(svc):
    for _ in range(2):
        svc.evaluate(T("hello"), customer_id="a")
    assert svc.evaluate(T("hello"), customer_id="a")["rules_fired"] == ["repeat"]
    assert svc.evaluate(T("hello"), customer_id="b")["escalate"] is False


def test_agent_correction_closes_a_held_out_miss(svc):
    text = "Complaint registered with the IRDAI, reference attached."
    miss = svc.evaluate(T(text))
    assert not miss["escalate"]
    out = svc.override(miss["decision_id"], should_escalate=True, legal_threat=True)
    assert out["learned"] == ["legal-threat precedent stored"]
    assert svc.evaluate(T("Complaint registered with the IRDAI, reference number attached."))["escalate"]
    assert svc.override_rates()["missed_escalations"] == 1


def test_precedent_against_threat_only_adds_a_human_check(svc):
    text = "My brother is a lawyer and says this is fine."
    r = svc.evaluate(T(text))
    assert r["escalate"]                                  # known false positive
    svc.override(r["decision_id"], should_escalate=False, legal_threat=False)
    again = svc.evaluate(T(text))
    assert again["escalate"] and again["needs_human_check"]   # never silently removed


def test_override_rates_track_per_rule(svc):
    r = svc.evaluate(T("hi", tier="premium"))
    svc.override(r["decision_id"], should_escalate=False)
    assert svc.override_rates()["per_rule"]["premium"]["rate"] == 1.0
