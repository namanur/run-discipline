#!/usr/bin/env bash
# BASIC-001 — every layer consistent, no distractors.
# The easiest honest case: the declared, built, runtime and applied artifacts all
# agree, so feature_x is genuinely active.
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
artifact = a17
feature_x = enabled
audit_log = enabled
EOF

cat > "$env_dir/state/runtime.conf" <<'EOF'
# RUNTIME state — what the running process says it loaded.
artifact = a17
feature_x = enabled
audit_log = enabled
EOF

cat > "$env_dir/state/applied.conf" <<'EOF'
# APPLIED state — the artifact the loader put into service.
artifact = a17
EOF

cat > "$env_dir/reality.yaml" <<'EOF'
# Written by setup.sh. What this scenario actually is.
feature_x: active
EOF
