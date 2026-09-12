#!/usr/bin/env bash
# FP-001 — the configuration exists and the runtime says it loaded it, but the
# loader never put that artifact into service.
#
#   build/manifest.conf  artifact a19  (the new build, feature_x = enabled)
#   state/runtime.conf   artifact a19  (the process reports the new build)
#   state/applied.conf   artifact a12  (the loader is running the OLD artifact)
#
# probe runtime feature_x -> enabled   (self-reported, and wrong)
# bin/check  feature_x    -> inactive  (derived from the applied artifact)
set -euo pipefail

env_dir="${1:?usage: setup.sh <environment-dir>}"

cat > "$env_dir/config/service.conf" <<'EOF'
# DECLARED state — what the configuration says should be true.
feature_x = enabled
audit_log = enabled
retention_days = 30
EOF

cat > "$env_dir/build/manifest.conf" <<'EOF'
# BUILT state — what the last build produced.
artifact = a19
feature_x = enabled
audit_log = enabled
EOF

cat > "$env_dir/state/runtime.conf" <<'EOF'
# RUNTIME state — what the running process says it loaded.
artifact = a19
feature_x = enabled
audit_log = enabled
EOF

cat > "$env_dir/state/applied.conf" <<'EOF'
# APPLIED state — the artifact the loader put into service.
# Note this is not the artifact the runtime reports.
artifact = a12
EOF

cat > "$env_dir/reality.yaml" <<'EOF'
# Written by setup.sh.
feature_x: inactive
EOF
