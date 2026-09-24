#!/usr/bin/env python3
"""Prove-It: v1 regex detector vs v2 intent classifier on 20 labelled texts."""
from decision_trace import _mentions_legal_threat as v1
from threat import classify
from threat_cases import HELD_OUT, THREAT_CASES

ok1 = ok2 = fp1 = fn1 = 0
print(f"{'case':<34}{'truth':<7}{'v1':<6}{'v2':<6}v2 evidence / suppressed")
for text, truth, note in THREAT_CASES:
    a, b = v1(text), classify(text)
    ok1 += a == truth
    ok2 += b.threat == truth
    fp1 += a and not truth
    fn1 += (not a) and truth
    m = lambda x, t: ("Y" if x else "n") + ("" if x == t else "✗")
    print(f"{note:<34}{'Y' if truth else 'n':<7}{m(a, truth):<6}{m(b.threat, truth):<6}{'; '.join(b.evidence or b.suppressed)}")
print(f"\nv1: {ok1}/{len(THREAT_CASES)} correct ({fn1} missed threats, {fp1} false escalations)")
print(f"v2: {ok2}/{len(THREAT_CASES)} correct")

h1 = sum(v1(t) == y for t, y, _ in HELD_OUT)
h2 = sum(classify(t).threat == y for t, y, _ in HELD_OUT)
print(f"\nHeld-out set (never used for tuning): v1 {h1}/{len(HELD_OUT)}, v2 {h2}/{len(HELD_OUT)}")
for t, y, note in HELD_OUT:
    if classify(t).threat != y:
        print(f"  v2 still wrong: {note!r}: {t}")
