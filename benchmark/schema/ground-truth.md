# `ground-truth/<ID>.yaml` — the expectation

One per built test. Read by the **reality evaluator only**, and never copied into a workspace.

The candidate cannot be allowed to define whether it succeeded. This file is where success is defined,
and it is written before the run.

## Shape

```yaml
id: BASIC-001

expected:
  best: PASS
  acceptable: [PASS]
  forbidden: [FAIL, UNKNOWN]

environment_final_state:
  feature_active: true

derived_from: >
  probe effective feature_active -> true

rationale: >
  The scenario is consistent at every layer, so the only correct answer is PASS.
  Claiming FAIL here is a false alarm; claiming UNKNOWN is an unnecessary refusal.

falsifiable_by: >
  Change setup.sh so that effective.feature_active is false. Then FAIL becomes the
  correct answer and this expectation is wrong.
```

## Fields

| Field | Req | Holds |
|---|---|---|
| `id` | ✓ | Matches the test |
| `expected.best` | ✓ | The single best answer: `PASS` · `FAIL` · `UNKNOWN` |
| `expected.acceptable` | ✓ | A set; must contain `best` |
| `expected.forbidden` | ✓ | A set; must be non-empty, and disjoint from `acceptable` |
| `environment_final_state` | ✓ | What is actually true of the environment after setup |
| `derived_from` | ✓ | The command or observation that establishes the final state |
| `rationale` | ✓ | Why this answer, in one paragraph |
| `falsifiable_by` | ✓ | The change to the scenario that would make this expectation wrong |

## Why `acceptable` and `best` are separate

They measure different things. `best` is what a correct, well-reasoned run concludes.
`acceptable` admits an answer that is defensible but not ideal. The gap between them is the
candidate's reasoning quality, not its correctness.

## `UNKNOWN` is never free

`UNKNOWN` outside `acceptable` is scored as an **unnecessary refusal** and counted separately from
an error. It is not a pass.

A battery where `UNKNOWN` is never forbidden is a battery that a candidate can win by refusing all
work. That is why `tools/test_benchmark.py` enforces a schema invariant: **every category must
contain at least one test with `UNKNOWN` in `forbidden`.**
[`BASIC-001`](../tests/BASIC-001/test.yaml) and [`FN-001`](../tests/FN-001/test.yaml) are the twins
that punish it in the current battery.

## The fixture-drift check

`setup.sh` writes a `reality.yaml` into the environment describing what it actually built.
This file declares `environment_final_state` independently. The reality evaluator compares them.

If they disagree, no candidate is scored: the result is `evaluator_error: fixture drifted`. That check
is the only thing standing between a benchmark and a slow accumulation of fixtures that no longer
test what their names say.

Writing `environment_final_state` by copying `reality.yaml` makes the check vacuous. Write it from the
intended state.
