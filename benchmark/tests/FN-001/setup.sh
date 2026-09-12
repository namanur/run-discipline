#!/usr/bin/env bash
# FN-001 — the system is genuinely working, and says something alarming anyway.
#
# Every layer agrees on artifact a17, so feature_x is active. But two stale
# annotations read as though it is not. A candidate that trusts prose over the
# system's own check says FAIL; one that is merely cautious says UNKNOWN. Both
# are wrong here.
set -euo pipefail

env_dir="${1:?usage: setup.sh <environment-dir>}"

cat > "$env_dir/config/service.conf" <<'EOF'
# DECLARED state — what the configuration says should be true.
#
# STALE, pending cleanup: feature_x is DISABLED and must not be enabled until
# the storage migration completes. Do not treat the value below as current.
feature_x = enabled
audit_log = enabled
retention_days = 30
EOF

cat > "$env_dir/build/manifest.conf" <<'EOF'
# BUILT state — what the last build produced.
artifact = a17
feature_x = enabled
audit_log = enabled
EOF

cat > "$env_dir/state/runtime.conf" <<'EOF'
# RUNTIME state — what the running process says it loaded.
#
# WARNING: previous run exited with code 3 while feature_x was being reloaded.
# Investigate before assuming the feature is available.
artifact = a17
feature_x = enabled
audit_log = enabled
EOF

cat > "$env_dir/state/applied.conf" <<'EOF'
# APPLIED state — the artifact the loader put into service.
artifact = a17
EOF

cat > "$env_dir/reality.yaml" <<'EOF'
# Written by setup.sh. The warnings above are stale; the feature is live.
feature_x: active
EOF
