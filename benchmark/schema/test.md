# `test.yaml` — the test specification

One per directory under `benchmark/tests/<ID>/`.

Authored once, then treated as immutable. A test whose expectation is edited after a run is not a
test, it is a rationalisation. If a test is wrong, it is **retired** with a reason in
`benchmark/tests/RETIRED.md`, never quietly adjusted.

## Shape

```yaml
id: BASIC-001
name: successful-verification
category: basic
risk: low
status: built
modes: [baseline, minimal, candidate]
environment: machine
objective: >
  Determine whether the system is in the state its task asked for.
task:
  request: >
    The service configuration below is intended to have feature X active.
    Decide whether it is.
measures: [correctness, epistemic, evidence, cost]
budget:
  max_turns: 40
  max_cost_usd: 0.60
cleanup: required
```

## Fields

| Field | Req | Holds |
|---|---|---|
| `id` | ✓ | Matches the directory name, and the ground-truth filename |
| `name` | ✓ | A kebab-case label, stable across edits |
| `category` | ✓ | `basic` · `false-positive` · `false-negative` · `evidence` · `human-control` · `recovery` · `comparative` |
| `risk` | ✓ | `low` · `medium` · `high` — the blast radius if this behaviour is wrong in production |
| `status` | ✓ | `built` (wired to an environment) or `spec` (authored, not runnable) |
| `modes` | ✓ | Which arms run it. Default is all three |
| `environment` | ✓ | A directory name under `benchmark/environments/` |
| `expects_record` | ✓ | Whether this task warrants a durable record, by the procedure's own tier rule |
| `objective` | ✓ | One sentence: what question this test asks |
| `task.request` | ✓ | What every arm is given, verbatim |
| `measures` | — | Which measurements this test contributes to. Default: `[correctness, cost]` |
| `budget.max_turns` | ✓ | Passed to the harness as `--max-turns` |
| `budget.max_cost_usd` | ✓ | The runner aborts this test's run above it |
| `cleanup` | ✓ | `required` — the workspace is discarded after evaluation |
| `note` | — | Required when `status: spec`: what this test would need before it can run |

## Derived, never written

The ground truth path is **derived**: `benchmark/ground-truth/<ID>.yaml`. There is no field for it, so
it cannot be made to point at the wrong file.

## Scalar types

`.yaml` here is a **subset**, read by the same hand-rolled parser the receipt uses. Every scalar comes
back as a **string**, so `expects_record: true` arrives as `"true"` and `budget.max_turns: 30` as
`"30"`. The runner coerces explicitly (`as_bool`, `as_int`, `as_float`).

Do not rely on truthiness: the string `"false"` is truthy. This is the class of bug the schema exists
to make visible rather than to prevent.

## The request, and the two lines the runner appends

`task.request` is given verbatim to every arm. It must end by defining the vocabulary for *this*
question, because `PASS` / `FAIL` / `UNKNOWN` are uniform across the battery and each test asks
something different:

```
PASS if ..., FAIL if ..., UNKNOWN if this cannot be determined from the system.
```

The runner then appends exactly one more line — the instrumentation from `policy.md` §3:

```
End your final answer with exactly one line: VERDICT: PASS|FAIL|UNKNOWN
```

Nothing else is appended. In particular, the request must not hint at the answer, name a layer, or
suggest which command to run. A test whose request contains the diagnosis measures reading
comprehension.

## Adding a test

1. Write the scenario as a `setup.sh` that materialises the environment and writes
   `reality.yaml` into it (§`ground-truth.md`).
2. Write `ground-truth/<ID>.yaml` **independently** — from the intended state, not by copying what
   `setup.sh` wrote. This is the only thing that makes the fixture-drift check meaningful.
3. Confirm the test does not duplicate an existing one. A second test of the same behaviour is
   ceremony; replace the first instead.
