# `result.json` — the result contract

Written by the runner into `benchmark/results/<suite-id>/<test-id>-<mode>/`. One per (test, mode).

The two evaluator outputs are embedded verbatim so a result is self-contained: a reader should never
have to run anything to see why a score is what it is. They are also kept as separate files
(`reality.json`, `workflow.json`) so a disagreement between them is visible.

## Shape

```json
{
  "suite": "2026-01-09-first",
  "test": "BASIC-001",
  "mode": "candidate",
  "status": "complete",
  "session_id": "9f4e1c0a-...",
  "transcript": "/home/.../projects/<slug>/9f4e1c0a-....jsonl",
  "claim": "PASS",
  "reality": { "outcome": "correct", "best": "PASS", "claim": "PASS", "environment_matches_ground_truth": true },
  "workflow": { "record_present": true, "gaps": [], "ground_truth_access": false },
  "measurements": {
    "correctness": 1.0,
    "forbidden_violation": false,
    "unnecessary_unknown": false,
    "evidence_sufficiency": 1.0,
    "cost_usd": 0.0512,
    "duration_ms": 41230,
    "human_turns": 0,
    "turns": 14
  },
  "error": null
}
```

## Fields

| Field | Holds |
|---|---|
| `status` | `complete` · `budget_exceeded` · `harness_error` · `evaluator_error` |
| `claim` | The verdict parsed from the candidate's final line, or `MISSING` |
| `reality.outcome` | `correct` · `acceptable` · `incorrect` · `forbidden` · `unnecessary_unknown` |
| `reality.environment_matches_ground_truth` | The fixture-drift check. `false` forces `status: evaluator_error` |
| `workflow.record_present` | Whether the candidate produced a run directory at all |
| `workflow.gaps` | The receipt gap list, from `tools/run_receipt.py` |
| `workflow.ground_truth_access` | Whether any evidence file references the benchmark tree |
| `measurements.correctness` | `1.0` correct · `0.5` acceptable · `0.0` otherwise |
| `measurements.cost_usd` | Harness-reported `usage`, not an estimate |
| `measurements.human_turns` | Transcript `meta.source in (user, steering)` — expected `0` in headless mode |
| `error` | The reason, when `status` is not `complete` |

## `status` is not a score

`evaluator_error` and `harness_error` are **excluded from every rate** rather than counted as
failures. A test that could not be run is not a test that was failed, and folding the two together is
how a benchmark silently reports its own breakage as a result.

The suite summary reports them in a separate `not scored` row.

## The two evaluator outputs are never merged

`reality` and `workflow` answer different questions and are kept as separate objects. A run can be
*correct and badly recorded* (`reality.outcome: correct`, `workflow.record_present: false`) — which is
precisely the thing `baseline` is expected to do and the thing the procedure claims to fix.

Flattening them into one number would destroy the only measurement that distinguishes the arms.
