import os
import tempfile

os.environ["GEN4_DB"] = os.path.join(tempfile.mkdtemp(), "t.db")
os.environ["GEN4_LLM_PROVIDER"] = "offline"

from fastapi.testclient import TestClient  # noqa: E402

from app import app  # noqa: E402

c = TestClient(app)


def test_evaluate_and_override():
    r = c.post("/evaluate", json={"ticket_id": "T1", "text": "Taking this to the consumer forum",
                                  "age_hours": 2, "customer_id": "c9"}).json()
    assert r["escalate"] and "legal" in r["rules_fired"]
    o = c.post("/override", json={"decision_id": r["decision_id"], "should_escalate": True}).json()
    assert o["override_rates"]["per_rule"]["legal"]["fired"] == 1
    assert c.post("/override", json={"decision_id": "x", "should_escalate": True}).status_code == 404
    assert c.post("/evaluate", json={"ticket_id": "T2", "text": "x", "age_hours": -1}).status_code == 422
