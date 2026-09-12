# The benchmark

A machine for measuring whether the procedure in [`../skills/`](../skills/) actually helps.

The procedure is the **candidate under test**. This directory is the judge, and it is allowed to
find that the candidate is ceremony. See [`policy.md`](policy.md).

```
                         run-discipline
                              │
                 ┌────────────┴────────────┐
                 │                         │
            PROCEDURE                  BENCHMARK
          skills/*/SKILL.md        tests · ground truth
                 │                  evaluators · results
                 │                         │
                 └────────────┬────────────┘
                              │
                         MCP interface
```

The MCP server exposes the benchmark; it does not become it.

---

## The question it answers

Not *"can an agent solve this task"* — that measures the agent. The question is:

> Does a disciplined workflow produce more **trustworthy claims** than an agent working without one?

Which is why every test ends in a claim and every claim is checked twice: once against the system,
and once against the rules the claimant said it was following.

## The three arms

| Arm | Flags | What it gets |
|---|---|---|
| `baseline` | `--no-skills` | The task. An ordinary agent. Nothing else |
| `minimal` | `--no-skills` | The task, plus the five-line discipline as prompt text |
| `candidate` | `--no-skills --skill ../skills` | The task, plus the six skills, discoverable |

**`minimal` is the arm that matters.** It is the package's own claim about what survives compression —
criterion, before, change, after, deviation. If `candidate` cannot beat it, five of the six skills are
ceremony and `policy.md` says what to do about that.

`--no-skills --skill <path>` is exactly the isolation required — *no skills at all except these* — and
it is harness-supported rather than a hack.

## How a test runs

1. A workspace is created in a temp directory, **outside this repository**.
2. The environment template is copied in and the test's `setup.sh` writes the scenario.
3. The arm's prompt is built — the test's `task.request`, one vocabulary line, one instrumentation line.
4. The harness runs it headless, returning a JSON result frame with usage, duration and session id.
5. Both evaluators run, with disjoint inputs.
6. The workspace is discarded; the result is kept.

## The two evaluators

| | Inputs | Asks | Never reads |
|---|---|---|---|
| [`reality.py`](evaluators/reality.py) | the claim, the environment, the ground truth | **Was the claim true?** | the run directory |
| [`workflow.py`](evaluators/workflow.py) | the workspace's run directory | **Did it follow its own rules?** | ground truth, environment |

This separation is the whole design. Without it, *"the evidence says PASS"* quietly becomes *"the
benchmark says PASS"* — the workflow grading itself. A test asserts the two argument surfaces share no
input, so the separation cannot rot.

With a fixture environment, **`reality.py` is fully deterministic.** No model judges whether the
candidate was right; a comparison does.

A run can be *correct and badly recorded* — `reality.outcome: correct` with `workflow.record_present:
false`. That combination is what `baseline` is expected to produce, and it is the only measurement
that distinguishes the arms. The two outputs are never merged into one number.

## Ground truth, and where it lives

`ground-truth/<ID>.yaml` defines `best`, `acceptable` and `forbidden`, and is read by `reality.py`
only. It is never copied into a workspace.

Each ground truth also declares `environment_final_state`. `setup.sh` writes its own account into the
environment's `reality.yaml`. When those disagree, **nothing is scored**: the result is
`evaluator_error: fixture drifted`. That check is what stops a suite from slowly accumulating fixtures
that no longer test what their names claim.

`UNKNOWN` is never free. A refusal where an answer was available is scored as an **unnecessary
refusal**, on its own axis, distinct from a forbidden answer — the two are different failure modes and
merging them hides which occurred. Every category is required to contain at least one test that
forbids `UNKNOWN`, enforced by `tools/test_benchmark.py`, because a battery that never punishes
refusal can be won by refusing everything.

## Running it

```bash
python3 benchmark/runners/run_benchmark.py --suite first --mode candidate --dry-run
python3 benchmark/runners/run_benchmark.py --test BASIC-001 --mode candidate
python3 benchmark/runners/run_benchmark.py --suite first --mode candidate --budget-usd 5.00
```

`--dry-run` prints the plan and an estimate and **spends nothing**. Always run it first: the full
battery is 12 tests × 3 modes, which is 36 agent sessions before any repeat.

Results land in `benchmark/results/<suite-id>/`, with one `RESULT.md` per (test, mode), both raw
evaluator outputs, and a `SUITE.md` that applies [`policy.md`](policy.md) mechanically.

## What the numbers mean

Every published rate links to the individual results, their transcripts, and both evaluator outputs.
A rate without its runs is withdrawn, not caveated.

Two things the numbers cannot show, and which no row reports:

- **Whether the fixtures resemble real work.** They are small, authored, and recognisable. That
  lifts all three arms equally, so the **comparison** survives even though the absolute pass rate does
  not mean much. Any number that ignores this is a number about `cmd`, not about the procedure.
- **Whether the human understood the record.** Nothing measures it. It is `UNKNOWN`, and it stays
  `UNKNOWN`.

## Residual risk

**A candidate can read any file in its workspace, and the workspace is a temp directory the candidate
can navigate from.** Ground truth is never copied in, and `workflow.py` flags any evidence file that
references the benchmark tree — but a candidate that reconstructs the path and reads it undetected is
possible.

This is documented rather than hidden, and it is why `policy.md` §5 requires every rate to link to its
runs: a reader can inspect the evidence for exactly this. Proper isolation needs a container, which is
a later decision, not an oversight.

## Status

Six of twelve tests are executable; the rest are [`status: spec`](schema/test.md) with a stated
blocker. No comparative suite has been run. Until one has, this directory is an instrument that has
been built and not yet used — which is a claim with no evidence behind it, and is exactly the kind of
claim the package it measures was designed to catch.
