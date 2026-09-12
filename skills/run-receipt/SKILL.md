---
name: run-receipt
description: Generate and read a run receipt — the derived summary of what a run recorded and, more importantly, the list of what it failed to record. Use when closing out a run, or when reading a run's gap list to decide whether its record can be trusted. Do not use to author content; a receipt is generated from the run and is never hand-edited.
metadata:
  derived_from: "tools/run_receipt.py; research/engineering-system/observability-architecture.md; archive/historical-kill-decision/VERDICT.md ('a read-only run receipt ... explicitly permitted to produce nothing')"
  adaptation_reason: "The reference implementation is repository-specific; the concept is not. A receipt is any deterministic reader that turns a run directory into authored facts, derived facts, and a gap list."
  verification: "On run 2026-09-12-f9-f10-readjudication the receipt caught that result_state and rollback_tested were unset — the fields nobody had filled. It also reported 4 agent calls against 10 evidence files with attribution UNKNOWN."
  known_limitations: "Not byte-reproducible: it embeds a generation timestamp and live version-control status, so two runs on an unchanged tree produce different files. It interprets nothing and stores nothing."
---

# Run receipt

A receipt is a **generated** file. It is derived from the run directory, the session transcript, and
version control; it stores nothing and interprets nothing. If a receipt and the run disagree, the run
is right and the receipt has a bug.

Never hand-edit it. An edited receipt can no longer be trusted as derived, which is its only value.

## Authored vs derived

Keep the two apart, because they carry different authority:

| Authored — no tool can derive it | Derived — no human should retype it |
|---|---|
| The criterion | Session facts: message counts, cost, token totals, context peak |
| The verdicts and the ruling | Delegation facts: which agents were called, with which inputs |
| The override | The evidence inventory |
| Base and result state | Version-control status at generation time |
| Intended skills | The **gap list** |

## The gap list is the point

Everything else in a receipt duplicates something in the run. The gap list is the one output that
exists nowhere else — it is the machine-checkable statement of what the run is missing. Read it
first, and treat every entry as a finding rather than an error.

A receipt's gaps are of two kinds, and the distinction matters:

- **A real omission** — the criterion was never authored; the verdicts are missing; a cited evidence
  file does not exist; the end state was never recorded. These are correctable, and each one is a
  specific thing the run owes.
- **A nag on a run where the field could not honestly be filled** — a read-only run reporting
  `rollback_tested` unset. Report it, and do not invent a value to clear it. `n/a` with a stated
  reason is a value; an invented one is not.

Typical gaps, verbatim from the reference implementation:

```
No criterion authored — the run has no falsifiable acceptance test.
No verdict recorded yet — the run is not closed.
Verdict for F9 cites missing file EVIDENCE/f9-missing.txt.
Delegations vs artifacts: 4 agent call(s); EVIDENCE/ holds 10 file(s).
  Attribution of files to agents is UNKNOWN — not observable.
Transcript not read: no --session given.
result_state not set — the run's end state is not recorded.
rollback_tested not set.
```

## Generating one

```
tools/run_receipt.py --session <path-to-transcript>.jsonl --run runs/<run-id>
```

Reads the run directory, the transcript, and version control. Writes exactly one file:
`runs/<run-id>/RECEIPT.md`. Read-only everywhere else. A human runs it — it is not scheduled, and
nothing depends on it having run.

If the reference tool is unavailable, the concept is what matters: a deterministic reader that
reports authored facts, derived facts, and gaps. Anything that requires a model's judgment does not
belong in a receipt.

## Known limitations

- **Not byte-reproducible.** It embeds a generation time and live version-control status. Two runs on
  an unchanged tree differ. Do not treat the receipt as the integrity anchor for the run — hash the
  evidence files if a real anchor is needed.
- **Not a summary you can trust alone.** If the transcript is unreadable, session facts silently read
  as zero in some implementations. Check that a gap was emitted whenever a section is empty.
- **Cannot see agent internals.** Only the final message and the files written survive, so
  attributing an evidence file to a particular agent is `UNKNOWN — not observable`.
