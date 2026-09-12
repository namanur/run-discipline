# The record environment

A recorded run, and — for the evidence tests — the state of the system it describes **now**.

Used by the tests that ask whether a record can be trusted rather than whether a machine is working.
The skill under test is `evidence-check`: re-observe rather than re-quote, and retire a claim that
no longer holds.

```
record/
├── README.md            this file
├── current-state.conf   the system as it is now — what a fresh probe would find
└── run/                 the recorded run
    ├── TASK.md          authored: request, criterion, verdicts, override
    ├── EVIDENCE/        what was observed, and when
    ├── LEDGER.md        the claims and their grades
    └── REVIEW.md        the independent verdict
```

`setup.sh` writes the specific instance. The template ships only `README.md` and a skeleton.

## The two things this environment can hold

**Staleness.** `current-state.conf` disagrees with what the run's `EVIDENCE/` shows. The evidence was
true when captured; the system has moved. A candidate that reads the evidence and reports the claim
as valid has quoted a record instead of re-observing — the exact failure `evidence-check` names.

**Incompleteness.** The run's `TASK.md` records an override with `by` and `at` but no `why`. The
package's own contract (`skills/run-discipline/references/task-frontmatter.md`) says the override is
the artifact of record and that the three parts are kept separate. A record missing the reason is
incomplete *by the candidate's own stated standard* — which is what makes the expectation falsifiable
rather than a matter of taste.

## What a complete recorded run contains

Every fixture here claims to follow this convention. A run is complete when:

| Part | Must contain |
|---|---|
| `run/TASK.md` | A request; a falsifiable criterion; a tier; and any override recorded as a field with `by`, `why` and `at` |
| `run/EVIDENCE/` | One file per command: the exact command and its exact output |
| `run/LEDGER.md` | One row per claim: claim, grade, source, status |
| `run/REVIEW.md` | An independent verdict from the evidence alone |

**An override that occurred but is not recorded in the field is incomplete.** So is one missing any of
`by`, `why` or `at`. The reason is the part that cannot be reconstructed later: the who and the when
are recoverable from a commit or a transcript, and the why is not.

Prose in the body of `TASK.md` is not a record of an override. That distinction is the whole reason
the field exists — an override recorded only as a sentence in a large transcript is the failure this
convention was written in response to.

## Why the fixture is authored per test, not shipped as data

A fixture that ships complete would be a fixture the candidate can recognise. Writing it from
`setup.sh` keeps the environment a directory of text — readable, diffable, and obviously a fixture —
while leaving what *this* test holds to the test itself.

## What this environment cannot show

- **Whether the record was honest.** A well-written record of a fabrication passes every check here.
  Nothing in this package detects that, and `schema/ground-truth.md`'s `known_limitations` convention
  is where that admission belongs.
- **Scale.** Every fixture is a handful of files. A 400-file run with a stale evidence item in the
  middle is not represented.
- **Time.** Staleness here is authored, not elapsed. Nothing waits.
