# SentinelDesk — FDE Framework Build Notes

## Part 1 — Problem Reframing

| Step | Output |
|---|---|
| Ordinary problem | "Decide which support tickets to escalate." |
| Lever 1: Data liquidity | A customer's contact history exists in the helpdesk but is never read at decision time. Agents' corrections ("this was actually a legal threat") are lost in ticket notes. |
| Lever 2: Network effect | Every agent correction becomes a precedent that applies to every future look-alike ticket. Override rates per rule tell the support lead which rules are miscalibrated. |
| Lever 3: Algorithmic leverage | Intent classification with guards (negation, personal names, non-legal senses) and India-specific legal routes (legal notice, consumer forum, ombudsman, advocate, FIR, RBI/IRDAI), plus precedent matching. |
| Lever 4: First principles × JTBD | The support lead's job is "no legal, contractual or churn risk slips through, and I can defend every call". Explainability is the product. |
| Extraordinary problem | **An escalation system that applies hard policy literally, reads legal-threat intent rather than keywords, remembers each customer's contact pattern, and learns from every agent correction without ever silently removing an escalation.** |
| Rating | 4 / 5 |

## Part 2 — Design the Eval

**Outcome of intelligence**
- Hard-rule boundaries are exact (48.0h does not escalate, 48.01h does; 5,000 does not, 5,000.01 does).
- Legal-threat detection is 100% on the 20-text development set and at least 80% on a 10-text held-out set written after tuning.
- A third contact in 7 days escalates. An agent correction applies to the next look-alike ticket.

**EQ(PRE)**
| Angle | Hypothesis |
|---|---|
| Causal | Keyword presence is treated as threat intent, so "Sue from billing" and "I'm not going to sue" escalate. |
| Context | Each ticket is judged alone. The third angry ticket this week looks like the first. |
| Consistency | Agents disagree with the detector, and nobody records it, so the same mistake repeats. |

**EQ(POST), cheapest first**
1. Prompt: the optional live-model intent check returns a strict boolean. Disagreement with the rules means escalate and add a human check.
2. Context/retrieval: guards, regional legal vocabulary, the repeat-contact rule from memory, and policy citations.
3. Feedback: agent overrides → precedents (can add an escalation or check, never remove one) and per-rule override rates.

**Executable:** `python run_evals.py` runs 40 cases × 3 runs. Overall ≥ 90%, the held-out segment ≥ 80%, everything else 100%.

## Part 3 — Gen-4 Architecture

| Layer | What SentinelDesk does |
|---|---|
| Retrieval | `knowledge/escalation_policy.md`. Each fired rule cites its section. |
| Context | The customer's contacts in the last 7 days, tier, ticket age. |
| Memory | Every decision with text and fields, keyed by customer; agent overrides; precedents (token sets and the agent's call). |
| Feedback | `POST /override` stores precedents when the agent's legal call differs from the system's. `GET /metrics` gives override rate per rule and missed escalations. |

The model is optional. With an API key, a live model classifies threat intent alongside the rules. The system escalates if either says threat, and flags disagreements for a human.

## Part 4 — Implementation Plan

| Component | Priority | Estimate | Status |
|---|---|---|---|
| Intent classifier with guards + regional vocabulary | MVP | 0.5 day | done |
| Development set (20) and held-out set (10) | MVP | 0.25 day | done |
| Repeat-contact rule from customer memory | MVP | 0.25 day | done |
| Agent overrides → precedents, override-rate metrics | MVP | 0.5 day | done |
| Optional live-model intent check + disagreement flag | MVP | 0.25 day | done |
| API, Docker, CI | MVP | 0.5 day | done |
| Helpdesk webhook (Freshdesk/Zendesk) | nice-to-have | 1 day | future |
| Hindi/Hinglish threat vocabulary | nice-to-have | 1 day | future |
| Sentiment trend as a context signal | future | 1 day | future |

## Part 5 — Prove It

**Visible change** (`python compare_v1_v2.py`, output in `run_output_v1_vs_v2.txt`):

| | v1 regex | v2 intent classifier |
|---|---|---|
| Development set (20) | 11 / 20 (6 missed threats, 3 false escalations) | **20 / 20** |
| Held-out set (10, written after tuning) | 5 / 10 | **8 / 10** |
| Missed: "legal notice", "consumer forum", "advocate", "ombudsman", "RBI complaint", "FIR" | missed | caught |
| False escalations: "Sue from billing", "not going to sue", "food court" | escalated | not escalated, with the reason shown |

The two held-out misses (a passive-voice IRDAI complaint, and "my brother is a lawyer") are reported, not hidden. The test suite shows the designed remedy: one agent correction turns the IRDAI miss into a precedent, and the next look-alike ticket escalates.
