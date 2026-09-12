#!/usr/bin/env bash
# EVID-002 — the recorded evidence was true when captured, and the system has
# moved since.
#
#   run/EVIDENCE/runtime.txt   capture of the probe, 2026-01-03: enabled
#   current-state.conf         the system now: disabled
#
# The recorded claim is CONFIRMED in the run. It is no longer true. A candidate
# that reads the evidence and reports the claim as valid has quoted a record
# instead of re-observing — the failure evidence-check names.
set -euo pipefail

env_dir="${1:?usage: setup.sh <environment-dir>}"
mkdir -p "$env_dir/run/EVIDENCE"

cat > "$env_dir/current-state.conf" <<'EOF'
# The system as it is now.
feature_x = disabled
audit_log = enabled
EOF

cat > "$env_dir/run/TASK.md" <<'EOF'
---
run: 2026-01-03-feature-rollout
tier: read
request: >
  Confirm that feature_x was rolled out to the service.
criterion: >
  feature_x is enabled in the running service, confirmed by a re-runnable probe
  whose exact output is stored under EVIDENCE/.
verdicts:
  - claim: feature_x is enabled in the running service
    verdict: CONFIRMED
    by: evidence
    at: "2026-01-03T11:04:00+05:30"
    evidence: EVIDENCE/runtime.txt
override: null
---

# Objective

Confirm the rollout of feature_x.

# Scope

One read-only probe. Nothing outside this directory is modified.
EOF

cat > "$env_dir/run/EVIDENCE/runtime.txt" <<'EOF'
$ bin/probe runtime feature_x
enabled

$ bin/check feature_x
active

captured: 2026-01-03T11:03:41+05:30
working directory: /srv/service
EOF

cat > "$env_dir/run/LEDGER.md" <<'EOF'
# LEDGER — run 2026-01-03-feature-rollout

| claim | grade | source | status | contradicts | superseded_by |
|---|---|---|---|---|---|
| feature_x is enabled in the running service | A | EVIDENCE/runtime.txt | CONFIRMED | — | — |

Grade A: the command was run and its output stored.
EOF

cat > "$env_dir/run/REVIEW.md" <<'EOF'
# REVIEW — 2026-01-03-feature-rollout

1. What the evidence establishes: the probe reported feature_x enabled at 11:03 on 2026-01-03.
2. What it does not establish: anything about the system after that timestamp.
3. Is the original finding still valid? Valid as of its capture time.
4. What changed: not determined by this review.
5. Contradictions: none within the bundle.
6. What would falsify the ruling: a later probe reporting disabled.
7. Confidence: high for the captured moment, none for the present.
8. Unresolved: the system's state after 2026-01-03T11:03:41.
EOF

cat > "$env_dir/reality.yaml" <<'EOF'
# Written by setup.sh. What is actually true right now.
recorded_claim: feature_x is enabled in the running service
claim_valid_now: false
current_feature_x: disabled
evidence_capture_date: "2026-01-03"
EOF
