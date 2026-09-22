"""Unit tests for the escalation decision trace. Run with: pytest"""

from decision_trace import Ticket, evaluate_ticket


def test_refund_over_threshold_escalates():
    t = Ticket("t1", "please refund me", age_hours=1, customer_tier="standard", refund_requested=8000)
    d = evaluate_ticket(t)
    assert d.escalate is True
    assert "refund" in d.reason.lower()


def test_normal_ticket_does_not_escalate():
    t = Ticket("t2", "package was a day late", age_hours=2, customer_tier="standard", refund_requested=50)
    d = evaluate_ticket(t)
    assert d.escalate is False


def test_real_legal_threat_escalates_even_without_the_word_legal():
    # regression test for the exact bug caught by actually running the demo:
    # "lawyer" doesn't contain the substring "legal", so a naive gate on
    # that substring silently missed this real threat.
    t = Ticket("t3", "I'm going to have my lawyer look at this contract", age_hours=10,
               customer_tier="standard", refund_requested=0)
    d = evaluate_ticket(t)
    assert d.escalate is True


def test_benign_mention_of_legal_does_not_escalate():
    t = Ticket("t4", "I spoke to your legal team last month about licensing, unrelated to this",
               age_hours=47, customer_tier="standard", refund_requested=4990)
    d = evaluate_ticket(t)
    assert d.escalate is False


def test_naive_legal_check_has_the_false_positive_bug():
    # documents the bug the fixed version avoids -- naive substring match
    # escalates on ANY mention of "legal", including benign ones.
    t = Ticket("t5", "I spoke to your legal team last month, unrelated matter",
               age_hours=1, customer_tier="standard", refund_requested=0)
    d = evaluate_ticket(t, use_naive_legal_check=True)
    assert d.escalate is True  # this IS the bug, asserted here on purpose


def test_premium_tier_escalates():
    t = Ticket("t6", "just a question", age_hours=1, customer_tier="premium", refund_requested=0)
    d = evaluate_ticket(t)
    assert d.escalate is True


def test_ticket_age_boundary_is_strict_not_soft():
    just_under = Ticket("t7a", "no issues", age_hours=48, customer_tier="standard", refund_requested=0)
    just_over = Ticket("t7b", "no issues", age_hours=48.01, customer_tier="standard", refund_requested=0)
    assert evaluate_ticket(just_under).escalate is False
    assert evaluate_ticket(just_over).escalate is True
