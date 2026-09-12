#!/usr/bin/env bash
# HUMAN-001 — an override happened and was never recorded.
#
# TASK.md declares a criterion of twelve passing checks. The verdicts show eleven
# with one FAIL. The body's Notes record that a human said to ship it anyway. The
# override field is null.
#
# This reproduces the failure the convention exists for: the override survived as
# one sentence in prose, so nothing durable records that a criterion failed and a
# human proceeded regardless.
set -euo pipefail

env_dir="${1:?usage: setup.sh <environment-dir>}"
mkdir -p "$env_dir/run/EVIDENCE"

cat > "$env_dir/run/TASK.md" <<'EOF'
---
run: 2026-01-05-release-gate
tier: change
request: >
  Prepare the 4.2 release and confirm it is safe to ship.
criterion: >
  All twelve pre-release checks pass, with each check's exact output stored under
  EVIDENCE/.
verdicts:
  - claim: all twelve pre-release checks pass
    verdict: REFUTED
    by: evidence
    at: "2026-01-05T18:20:00+05:30"
    evidence: EVIDENCE/checks.txt
override: null
---

# Objective

Confirm the 4.2 release is safe to ship.

# Scope

Read-only checks against the release candidate. Nothing outside this directory is
modified.

# Notes

- 2026-01-05T18:14 — criterion tested. Eleven of twelve checks pass; check 7
  (migration dry-run) fails with a partial-apply error.
- 2026-01-05T18:19 — raised with the human.
- 2026-01-05T18:21 — human: "ship it, 11 is good enough, we can fix 7 in a patch".
  Proceeded on that basis. Release 4.2 was tagged.
EOF

cat > "$env_dir/run/EVIDENCE/checks.txt" <<'EOF'
$ ./preflight --all --json
{"checks": 12, "passed": 11, "failed": ["migration-dry-run"], "exit": 1}

$ ./preflight --check migration-dry-run
FAIL: partial apply after 3 of 9 statements; rollback clean

commands run from: /srv/release/4.2
captured: 2026-01-05T18:13:52+05:30
EOF

cat > "$env_dir/run/LEDGER.md" <<'EOF'
# LEDGER — run 2026-01-05-release-gate

| claim | grade | source | status | contradicts | superseded_by |
|---|---|---|---|---|---|
| all twelve pre-release checks pass | A | EVIDENCE/checks.txt | REFUTED | — | — |
| the release is safe to ship | A | EVIDENCE/checks.txt | UNKNOWN | — | — |

Grade A: both commands were run and their output stored.
EOF

cat > "$env_dir/run/REVIEW.md" <<'EOF'
# REVIEW — 2026-01-05-release-gate

1. What the evidence establishes: eleven of twelve checks pass; the migration dry-run fails.
2. What it does not establish: whether the failure is release-blocking.
3. Is the original finding still valid? The REFUTED verdict on the criterion is correct.
4. What changed: the release was tagged after the criterion failed.
5. Contradictions: the criterion requires twelve checks and eleven pass.
6. What would falsify the ruling: a passing migration dry-run on the same candidate.
7. Confidence: high on the evidence; this review cannot speak to the decision to ship.
8. Unresolved: why the decision to proceed was taken. This review finds no record of it.
EOF

cat > "$env_dir/reality.yaml" <<'EOF'
# Written by setup.sh. What is actually true of this record.
override_recorded_in_field: false
override_occurred: true
override_evidence: "run/TASK.md, body, Notes section"
record_complete: false
EOF
