---
name: blind-reconstruction
description: Test whether a completed run is actually reconstructable by giving a fresh reader the run directory alone and scoring what they can answer. Use after a run whose record matters, when a record's sufficiency is disputed, or when deciding whether a convention is worth repeating. Do not use to judge the quality of the work itself — it tests the record, not the result.
metadata:
  derived_from: "archive/historical-kill-decision/_review/BLIND-reconstruction-test.md (14/14); runs/2026-09-12-f9-f10-readjudication/RETROSPECTIVE.md (11/11 with caveats); Reproducible/adaptation-catalog.md"
  adaptation_reason: "The strongest falsification instrument this work produced. Written as a reusable procedure because it converts 'a future reader will be able to reconstruct this' from an assertion into a measurement."
  verification: "Run twice with recorded results: 14 of 14 questions on the original run, 11 of 11 with three caveats on the operational run. Both times the caveats were more informative than the score."
  known_limitations: "Tests one reader on one run; the score is not a rate. A passing reader does not prove the record is true — only that it is legible. The reader's own knowledge can mask gaps in the record."
---

# Blind reconstruction

The claim this tests is usually stated as *"a future reader will be able to reconstruct what
happened."* That is an assertion until somebody tries it. This procedure tries it.

## Procedure

1. **Choose a reader with no prior context** — a fresh session, or a sub-agent, or a person who has
   not seen the work.
2. **Give it the run directory and nothing else.** No repository context, no design documents, no
   chat history, no author's narration.
3. **Ask reconstruction questions**, in writing, before it reads anything:
   - What was believed before this work started, and on what evidence?
   - What was asked, and what would count as done?
   - What was actually observed, and by which command?
   - What was inferred rather than observed?
   - What was disputed, and by whom?
   - What did the human decide — and did they override anything?
   - What changed as a result?
   - What remains unknown or unresolved?
   - What did this cost?
   - How would I continue from here?
4. **Score each answer.** Count an answer only if the reader cites the file that supports it. A
   confident answer with no citation is a **gap in the record**, not a correct answer.
5. **Write down the caveats.** They are the output. The score is the summary.

## The caveats are the finding

Both times this ran, the caveats were more useful than the score. The three failure modes to expect:

| Caveat | What it means |
|---|---|
| **Primary sources are cited, not included** | The run quotes a prior report that lives outside it. Reconstruction then depends on a file the reader cannot check. Record the path *and* whether it is expected to survive. |
| **Process claims are self-attested** | "Independent reviewer", "read-only", "human ruled" are asserted *inside* the record. Only the transcript, which lives outside the run, could substantiate them. |
| **Contradictions the record should keep** | A reader will notice that one file says the reviewer was one model and another says a different one. Keep the contradiction visible; it is what the record actually supports. |

A caveat is a finding, not a defect to fix immediately. Fixing it before the evidence justifies the
addition re-creates the over-recording this procedure exists to catch.

## Reading the result

- **Full marks with caveats** — the record is usable. The caveats tell you what it cannot prove.
- **Misses on observation questions** — the evidence is missing or does not name its command.
- **Misses on decision questions** — the criterion, the verdicts, or the override were never authored.
- **A reader who answers from background knowledge rather than the files** — the test is void. Their
  fluency is not the record's legibility.

## Known limitations

- One reader on one run is an existence proof, not a rate.
- A reader who shares the author's assumptions will fill gaps the record leaves open, and score
  higher than a stranger would.
- It tests legibility, not truth. A well-written record of a fabricated observation passes.
- It is not free — running it costs a session. Reserve it for runs whose record matters, and for
  deciding whether a convention is worth keeping.
