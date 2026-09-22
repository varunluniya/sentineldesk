# SentinelDesk

A ticket-escalation decision engine that makes a support team's informal
escalation judgment explicit, testable, and versioned — instead of
living only in a senior agent's head.

## The problem

Every support team has an unwritten sense of "this ticket needs to go
up the chain." In practice that judgment is inconsistent: different
agents escalate differently, new hires don't know the rules, and
nobody can point to why a given ticket was or wasn't escalated. A
decision trace turns that tacit judgment into a structured, inspectable
policy that produces the same answer every time, with a stated reason
attached to every decision — the kind of artifact that lets an LLM (or
a person) reason correctly about cases nobody explicitly programmed
for, rather than a rigid if/else block that only covers what someone
thought to write down.

## The policy

```
1. Ticket age > 48 hours          -> Escalate (SLA breach risk)
2. Customer tier = premium        -> Escalate (contractual priority)
3. Genuine legal threat detected  -> Escalate (legal exposure)
4. Refund requested > $5,000      -> Escalate (high financial exposure)
5. Numeric boundaries (age ~48h, refund ~$5,000) are applied literally,
   not softened -- an inconsistent threshold is worse than a strict one.
```

## Running it

```bash
pip install pytest        # only needed to run the test suite
python3 run_demo.py                                    # 4 sample tickets, narrated
python3 cli.py                                          # same as run_demo.py
python3 cli.py --text "I'll sue you" --age 5 --refund 0 # evaluate a custom ticket
python3 -m pytest -v                                    # 7 tests, all passing
```

Sample output is captured in `run_output.txt`.

## A real bug found and fixed while building this

The escalation-relevant part of a ticket is whether it contains a
**genuine legal threat** — not whether it contains the word "legal" at
all. The first version of the threat detector gated its real regex
checks (looking for "lawyer," "sue," "legal action," etc.) behind an
early check for the literal substring `"legal"`. That gate silently
broke the detector: a ticket saying *"I'm going to have my lawyer look
at this"* is a real threat but doesn't contain the substring "legal" at
all, so it was never even checked against the threat patterns and the
ticket sailed through as a non-escalation.

This wasn't caught by reading the code — it looked reasonable. It was
caught by actually running the required edge-case tickets and noticing
the wrong answer: a clear threat wasn't escalating. The fix was to drop
the gate and run the threat-pattern regexes unconditionally against
every ticket's text. A permanent regression test
(`test_real_legal_threat_escalates_even_without_the_word_legal`) locks
the fix in, and a second test documents the *opposite* failure mode on
purpose — a naive "does the text contain 'legal' anywhere" check, kept
in the code specifically to demonstrate why it's wrong (it flags a
harmless ticket that references "your legal team" in an unrelated
context as needing escalation).

## Files

- `decision_trace.py` — the policy text plus `evaluate_ticket()`, which
  returns a structured `Decision` (escalate/no, a human-readable reason,
  and the specific rules that fired) rather than a bare boolean.
- `run_demo.py` — 4 representative tickets (a clear escalation, a clear
  non-escalation, and two edge cases probing the legal-threat detector)
  plus a side-by-side demonstration of the naive-keyword bug.
- `cli.py` — a small command-line wrapper: run the bundled demo, or
  evaluate a one-off custom ticket from the command line.
- `test_decision_trace.py` — 7 pytest tests, including the regression
  test for the bug above and a strict boundary test (47h vs 48.01h).
- `run_output.txt` — captured real output from `run_demo.py`.
