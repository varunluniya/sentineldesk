# Day 47 changelog — SentinelDesk

## Finding

`override_rates()` re-pulled and re-scanned every decision+outcome the
system had ever logged, on every call. `override()` calls it after every
single agent verdict, so this was the hottest full-rescan in this repo
(Guide 5's Mistake 5) — one re-aggregation of the entire ticket history
per human correction.

## Changes

- `gen4/memory.py`, `gen4/feedback.py` — kernel fix (shared across the
  portfolio; see LendFair's changelog): `fact_history`,
  `decisions(outcome_since=...)`, the `outcome_ts` fix, the
  `(system, ts DESC)` index, and the `new_rows_since` / `mark_processed` /
  `accumulate` primitives.

- `service.py`
  - `override_rates()` rewritten (`LEARN_KEY = "sentineldesk_overrides"`,
    `LEARN_GRACE_DAYS = 1`): pulls only outcomes since the last watermark
    via `new_rows_since()`, and merges per-rule fired/overridden counts
    plus a missed-escalations count into running totals via
    `accumulate()`, instead of re-deriving every rate from the full
    decision history on every override.

- `tests/test_incremental_learning.py` — new, 3 tests: idempotency,
  picking up new overrides after more are recorded, and a direct
  cross-check of the incremental per-rule totals against an independent
  from-scratch recompute straight from `memory.decisions()` (what
  `override_rates()` used to do) to prove mathematical equivalence.

## Verification

- `pytest -q` → 17/17 passed (14 original + 3 new).
- `run_evals.py` → GATE PASS; two held-out-set failures
  (`heldout-08`/`heldout-09`) are present identically before and after the
  fix — confirmed via `git stash` comparison to be a pre-existing, unrelated
  limitation of the legal-threat detector, not a regression introduced here.
- `seed.py --reset` → identical to pre-fix baseline (495 tickets, 243
  escalated, same per-rule override rates, `missed: 1`).
- `compare_v1_v2.py` → identical to pre-fix baseline (v2 20/20 on the
  curated set, 8/10 on held-out, same two known misses).

No behavioral change in any observable output.
