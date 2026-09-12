# One task, start to finish

This is a narrative, not a specification. The authoritative instruction set is
`skills/run-discipline/SKILL.md`; this page exists to show the *shape* of a run over time, and the
files that exist at each moment.

**The task:** *"The rate limit we shipped last week isn't working. Find out why."*

---

## Step 0 — Decide whether this deserves a run

Before writing anything, call the tier.

| Question | Answer here |
|---|---|
| Does this change a system? | Not yet — this is an investigation |
| Is a claim going to be made that someone must trust? | **Yes.** "The limit isn't working" is a claim about production |
| Is there a prior finding to retire? | Yes — the recorded belief that the change was deployed |

**Tier: `read`.** Nothing gets modified. No reviewer will be convened unless a prior finding needs
retiring — which, here, it does. So the review is warranted, and that is a decision, not a default.

If the investigation produces a fix, the fix is a **separate run at tier `change`**. Repair is not
covered by an investigation's mandate.

> **On disk right now:** nothing. This step is a decision.

---

## Step 1 — INTAKE: write the criterion before you look

The single most valuable act, and the only one no tool can do for you.

> **Criterion:** `curl -s -o /dev/null -w '%{http_code}'` against the limit endpoint, 200 times in a
> burst, returns at least one `429`. The same command's output is stored before and after.

Note what just happened. Before opening a single log, the run has committed to a command, and to the
value that would prove failure. If the probe returns zero `429`s, the claim is confirmed and no
argument is possible. If it returns one, the claim is dead — regardless of how it feels.

Also written now, because they will be unanswerable later:

- `tier: read`
- the gates: *no writes outside `runs/`; no production change*
- `base_state`: the deployed revision, captured **now**, not reconstructed afterwards
- `session_file`: the transcript path, recorded at intake

> **On disk:**
> ```
> runs/2026-01-08-rate-limit/
> └── TASK.md          ← request, criterion, tier, gates, base_state
> ```
> See `skills/run-discipline/references/task-frontmatter.md` for the field contract.

---

## Step 2 — UNDERSTAND: establish what is *declared*

Read the configuration. Not the running system — the source of truth.

The rate limit is declared. It is in the config, it is committed, it is in the last release tag. **At
this layer, the change is present and correct.**

This is the layer that produces confident wrong answers, and the reason the next step is not optional.

> **On disk:** unchanged. Reading does not yet produce evidence.

---

## Step 3 — Probe each layer separately

This is `declared-vs-effective`, and it is where the run earns its cost. Four probes, four answers,
written as raw output — not as conclusions.

| Layer | Probe | Result |
|---|---|---|
| declared | the config as committed | limit is present, correct value |
| built | the image digest tagged for this release | **the digest predates the change** |
| runtime | the running containers' image digest | an older digest still |
| effective | the burst probe from the criterion | no `429`s |

Four probes. Two of them disagree with what everyone believed, and one of them — *built* — is the
actual defect. Nobody had looked there, because "we shipped it" was a belief rather than an
observation.

**The claim as stated is wrong.** "The rate limit isn't working" is false: the limit is working fine.
It is not *deployed*. The distinction changes the fix entirely — one is a code problem, the other is a
pipeline problem.

> **On disk:**
> ```
> runs/2026-01-08-rate-limit/
> ├── TASK.md
> └── EVIDENCE/
>     ├── declared-config.txt
>     ├── built-image-digest.txt
>     ├── runtime-containers.txt
>     └── effective-burst-probe.txt
> ```

---

## Step 4 — VERIFY: turn evidence into verdicts

Adjudicate, using `evidence-check`. Every verdict names the command that decides it and the file
holding its output. The decisive commands are re-run rather than quoted.

| Claim | Grade | Verdict |
|---|---|---|
| The limit is not deployed | A | **CONFIRMED** — built digest predates the change |
| "The rate limit isn't working" | A | **REFUTED** — the limit is absent, not broken |
| The change reached production | A | **REFUTED** — recorded belief retired |

The third row is the point. A belief that was written down has now been explicitly retired, with the
evidence named. It is marked superseded, not deleted — the record of what was believed is itself
information.

> **On disk:** `LEDGER.md`

---

## Step 5 — REVIEW: an independent reader, evidence only

Convene `acceptance-review` on the evidence bundle. The reviewer sees the criterion and `EVIDENCE/`.
Not this narrative, not the reasoning, not the ledger.

The review may agree, disagree, or refuse. All three are useful. If it agrees with every verdict, that
is worth recording as a fact about the review — agreement is not proof.

> **On disk:** `REVIEW.md`

---

## Step 6 — HUMAN DECISION

The verdicts are ruled on. If the criterion had failed and the work had proceeded anyway, the
**override** would be recorded here — by, why, and when — as a first-class field rather than a
sentence buried in a transcript.

`override: null` is a valid and informative value: it says the gate was not crossed.

> **On disk:** `TASK.md` updated with `verdicts` and `override`.

---

## Step 7 — Close out, and read the gap list

```bash
python3 tools/run_receipt.py --run runs/2026-01-08-rate-limit
```

The receipt is generated and never hand-edited. It reports authored facts, derived facts, and gaps.
**Read the gaps.** A realistic output for a read-only run:

```
No criterion authored — the run has no falsifiable acceptance test.       ← would mean step 1 was skipped
result_state not set — the run's end state is not recorded.
rollback_tested not set.
Transcript not read: runs/2026-01-08-rate-limit/transcript.jsonl.
```

The last three are *not* failures. This run changed nothing, so there is no result state and nothing
to roll back. They are reported because the machine cannot know that — and the correct response is
`n/a` **with the reason**, never an invented value.

> **On disk:** `RECEIPT.md`, `RETROSPECTIVE.md`

---

## Step 8 — Ask whether the record actually works

Hand the run directory — and nothing else — to someone who has not seen the work. Ask them what was
believed, what was observed, what was inferred, what was disputed, what was decided, and what remains
unknown. Score only answers that cite a file.

`blind-reconstruction` describes the procedure and the three failure modes to expect. The caveats are
the output; the score is only the summary.

This step is optional. It is how "a future reader could reconstruct this" stops being an assertion.

---

## The whole run on disk

```
runs/2026-01-08-rate-limit/
├── TASK.md            authored    — criterion, tier, gates, base_state, verdicts, override
├── EVIDENCE/          captured    — one file per command: the command and its exact output
├── LEDGER.md          adjudicated — claim, grade, source, status, supersedes
├── REVIEW.md          independent — verdict from the evidence alone, including dissent
└── RECEIPT.md         generated   — authored vs derived, plus the gap list
```

Five files, four of which exist because a question was asked that a summary could not answer. Strip
away everything else in this repository and those five files are the entire product.

## The two mistakes this walkthrough exists to prevent

1. **Answering at the wrong layer.** "It isn't working" and "it isn't deployed" feel identical from
   the outside and have nothing in common as problems. Step 3 is cheap; skipping it is not.
2. **Recording only what succeeded.** The override, the retired belief, the layer that disagreed, the
   `UNKNOWN` — those are the entries that will matter later. They are also the ones that feel
   unnecessary at the time.
