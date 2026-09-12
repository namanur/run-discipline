# Benchmark policy

Not advisory. The runner emits these comparisons mechanically, so a rule that fires is a decision
already taken.

---

## 1. The rules

| Condition | Conclusion | Action |
|---|---|---|
| `candidate ≤ minimal` | **SIMPLIFY** | Five of the six skills are ceremony. Cut back to the five-line core |
| `candidate < baseline` | **INVESTIGATE** | The procedure is worse than nothing. Identify which skill caused it |
| `ceremony ≫ risk reduction` | **SIMPLIFY** | Ceremony is tokens, wall time and human turns; risk reduction is forbidden-violations avoided |
| `claim not independently evaluable` | **UNKNOWN** | Written as `UNKNOWN`, never inferred. An unmeasurable claim is not a passing claim |
| `repeated runs show no benefit` | **DELETE** | Delete the feature. The research survives either way |

## 2. The benchmark is allowed to kill the project

Not metaphorically. If `candidate ≤ minimal` holds across the suite, the correct action is to delete
five of the six skills and keep the five lines. That is a **successful** benchmark result, not a
failure of the benchmark.

The inverse is also true: if this suite cannot distinguish the modes, the benchmark has failed and
needs better fixtures — not a better score.

## 3. Instrumentation is not treatment

Every arm — baseline included — is told to end its final answer with:

```
VERDICT: PASS|FAIL|UNKNOWN
```

That is **instrumentation**. Without a machine-readable claim there is nothing to score, and the three
arms would not be comparable.

It is not part of the procedure under test. It follows that the baseline arm is slightly *helped* by
the measurement apparatus: it is told to name its conclusion, which is a small part of what the
procedure teaches. The comparison is therefore **conservative** — if the candidate loses to baseline
anyway, it loses despite baseline holding an advantage it would not have in real use.

## 4. What each measurement cannot show

| Measurement | Source | Cannot show |
|---|---|---|
| Correctness | `reality.py`, deterministic | Whether the fixture resembles real work |
| Forbidden violations | `reality.py` | Whether a forbidden answer was reached by bad luck or bad method |
| Unnecessary refusals | `reality.py` | Whether the candidate was right to be unsure *in general* |
| Evidence sufficiency | `workflow.py` | Whether the evidence was **true** — only that it was present, cited and re-runnable |
| Reconstruction | a blind reader, opt-in | Whether the record was honest; a well-written record of a fabrication passes |
| Cost | harness `usage` | Human time |
| Human turns | transcript `meta.source` | Whether the human read anything |

Two measurements have no source at all and are therefore not reported: **whether the human
understood the record**, and **whether the change was the right change**. Both are out of scope
because no command decides them.

## 5. The first rule

**A number nobody can reproduce is not a result.**

Every published rate links to its individual `RESULT.md` files, their transcripts, and both evaluator
outputs. A rate without its runs is withdrawn, not caveated.

## 6. What this benchmark is not allowed to become

No database. No workflow engine. No event store. No dashboard. No agent swarm. No benchmark agent.

The scoreboard is a Markdown file and the storage is a directory. If the benchmark needs a service to
report its own results, it has become the thing it was built to judge.
