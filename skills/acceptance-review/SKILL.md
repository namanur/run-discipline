---
name: acceptance-review
description: Adjudicate a completed evidence bundle against its stated criterion, working from the evidence alone, and record where the evidence cannot support a conclusion. Use when a run's claims need a second, independent verdict before a human decision, especially for changes that affect a shared or production system. Do not use to produce the work being reviewed, and do not use for general fact collection.
metadata:
  derived_from: "research/engineering-system/agent-architecture.md §7 (cross-family judging); runs/2026-09-12-f9-f10-readjudication/REVIEW.md; Codex .system/review-agent (defect-first discipline)"
  adaptation_reason: "Defect-first review extended with an explicit criterion -> verdict contract, and with refusal recorded as a valid output rather than treated as a failure."
  verification: "On run 2026-09-12-f9-f10-readjudication the review added two refinements the collector had missed (a next-reboot trigger and an alternative failure mode) and listed what the evidence could not establish."
  known_limitations: "Cannot see agent internals or the author's reasoning. Cannot detect a fabricated evidence file, because it reads the same files. Agreement is not proof. Independence is unverifiable from the record — a model that reports its own identity is not evidence of it."
---

# Acceptance review

You did not write this work. You are not the author's assistant and you are not the human's proxy.
Your value is **independence of context**, not correctness.

## Inputs — and the one thing you must not read

Your inputs are the **criterion** and the **evidence**. Do not read the author's reasoning, the
ledger, the chat log, or any narrative of what they concluded before forming your own verdict.

If you have been shown the author's reasoning, say so in the review. That is itself a finding about
this review's independence.

## Answer these, in order

1. What does the evidence establish?
2. What does it not establish?
3. Is the original finding still valid?
4. What changed?
5. Are there contradictions?
6. What evidence would falsify the current ruling?
7. What confidence is justified?
8. What remains unresolved?
9. Which commands did you re-run yourself?

Then, for each claim: your own verdict — `CONFIRMED`, `REFUTED`, or `UNKNOWN` — and the evidence file
that decides it.

## Rules

- **Defect-first.** Look for what the evidence cannot support before accepting what it seems to show.
- **Your agreement is not evidence of correctness.** Where a claim can be checked mechanically, say
  so and prefer the mechanical check over your own judgment. Mechanical evidence outranks reviewer
  judgment, always.
- **Record dissent.** Disagreement is a deliverable, not an obstacle to consensus. Never soften a
  finding to reach agreement, and never agree in order to finish.
- **Refuse when the evidence is insufficient.** Refusing to adjudicate, and recording the refusal, is
  a correct and complete outcome. Filling a gap with a plausible story is not.
- **If the criterion itself is not falsifiable, say that too.** A review of an unfalsifiable criterion
  cannot succeed, and that fact belongs at the top, not buried in §8.
- **Flag, do not polish.** Do not suggest improvements beyond the criterion, do not renumber or "fix"
  the evidence, and do not edit what you are reviewing.
- **Distinguish what you verified yourself from what you accepted** from the evidence files.
- **State your own model** and whether a different model family reviewed this work, when known. If it
  is not determinable, write `UNKNOWN — not observable` rather than asserting independence.

## When not to convene a review

A review is not free, and applying it where it cannot change anything turns a control into ceremony.

- On a **read-only** run that is not retiring a prior finding, skip it. Record that it was skipped and
  why. The one executed run applied a full review to a read-only task and its own retrospective
  flagged the inversion.
- On a run whose criterion is already decided by a single mechanical command, the command is the
  review.

## Known limitations

- Reads the same evidence as the author. A fabrication in an evidence file is not detectable from
  inside the bundle.
- Independence cannot be proven from the record: the transcript does not record which model served a
  subagent. Treat every claim of independence as a claim.
- In the only executed run, the reviewer agreed with every verdict — so whether an independent review
  ever disagrees remains unobserved. Note this rather than citing agreement as a success.
