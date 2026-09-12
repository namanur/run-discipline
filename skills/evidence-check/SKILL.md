---
name: evidence-check
description: Settle a claim or retire a stale finding as CONFIRMED, REFUTED, or UNKNOWN by re-running the decisive command yourself and grading the result. Use when a finding, prior report, or conclusion must be settled, and when a claim that was true once needs re-checking against the current system rather than accumulating in the record. Do not use for collecting general facts, and do not use for judging the quality of someone else's reasoning about evidence.
metadata:
  derived_from: "research/research-methodology.md §2 (evidence grades A-G); runs/2026-09-12-f9-f10-readjudication/LEDGER.md; archive/historical-kill-decision/_review/BLIND-reconstruction-test.md (the three structural gaps)"
  adaptation_reason: "Research grading applied to a running system rather than a literature, and extended with REFUTED so a stale finding can be explicitly retired instead of quietly dropped."
  verification: "Re-ran every decisive command in runs/2026-09-12-f9-f10-readjudication/ and overturned a wrong intermediate grade in docs/environment-inventory.md. That correction is the measured effect of this procedure."
  known_limitations: "Cannot see agent internals or the reasoning behind a claim. Grades are human-readable, not machine-checkable. It cannot detect a fabricated evidence file, because an independent reviewer usually reads the same files."
---

# Evidence check

You did not write the work you are judging. Assume it is wrong until a command says otherwise.

## The verdict vocabulary is exactly three words

`CONFIRMED` · `REFUTED` · `UNKNOWN`

Never "probably", "likely", "partially", or "mostly". A claim with a qualifier belongs in the
qualification column, not in the verdict.

## Re-run the decisive command yourself

A claim supported only by another agent's summary is **not grade A**. Reproduce the observation:

1. Read the claim and its stated source.
2. Identify the smallest command whose output decides it.
3. Run it yourself, now. Not the command the author says they ran — the command that decides.
4. Store the exact command and its exact output as one evidence file.
5. Only then write the verdict.

If you cannot identify such a command, the verdict is `UNKNOWN` and the reason is the finding.

## Grades

| Grade | Source of the claim |
|---|---|
| **A** | You ran the command and read the output yourself |
| **B** | A specification |
| **C** | Documentation |
| **D** | A README |
| **E** | An article |
| **F** | Independent analysis |
| **G** | A code snippet |

A prior report's statement is not grade A, however authoritative it reads. Grades B–G can support an
`UNKNOWN`; only A supports a verdict.

## Rules

- **`UNKNOWN` is a valid result and is never inferred.** If no command decides it, write
  `UNKNOWN — not observable` and name what would have decided it.
- **State the surveyed set.** "No evidence found" means "none in the files and probes I examined",
  never "none exists."
- **Keep contradictions.** If two observations conflict, keep both and mark the contradiction. Do not
  reconcile silently, and do not average them.
- **Downgrade, never delete.** A claim that no longer holds becomes `stale` or `superseded_by`, with
  the new evidence named. Deleting it destroys the record of what was believed.
- **A claim true for the wrong reason is two facts.** Record the correct observation *and* the
  inaccurate original claim, separately.
- **Do not grade intent** — only what a command can decide.
- **Re-observe, don't re-quote.** An observation from a prior run is not evidence; the system may have
  moved. That is the entire reason a stale finding gets re-checked at all.

## Output — the ledger

One row per claim:

| claim | grade | source | status | contradicts | superseded_by |
|---|---|---|---|---|---|
| <the claim, in its original wording> | A–G | <the evidence file you produced> | CONFIRMED / REFUTED / UNKNOWN | <other claim, or —> | <newer claim, or —> |

Keep the claim's original wording. A claim re-worded before it is tested has already been judged.

## Known limitations

- A self-selected command can be the wrong command, or a favourable one. Nothing here prevents that;
  an independent reviewer reading only the evidence is the available check.
- Evidence files are plain text and nothing hashes them by default. A byte-size record detects
  truncation but not substitution — hash each file if the record needs an integrity anchor.
- If the evidence is empty or insufficient, the verdict is `UNKNOWN`. Record the insufficiency
  rather than substituting a plausible account.
