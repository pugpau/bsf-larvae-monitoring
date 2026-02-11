#!/bin/bash
# Generate nginx-router.conf from template by replacing ACTIVE_BACKEND_HOST.
# Usage: ./scripts/gen-nginx-conf.sh <backend-blue|backend-green>

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
TEMPLATE="${PROJECT_DIR}/config/nginx-router.conf.template"
OUTPUT="${PROJECT_DIR}/config/nginx-router.conf"

BACKEND_HOST="${1:?Usage: $0 <backend-blue|backend-green>}"

if [[ "$BACKEND_HOST" != "backend-blue" && "$BACKEND_HOST" != "backend-green" ]]; then
    echo "ERROR: backend host must be 'backend-blue' or 'backend-green'" >&2
    exit 1
fi

sed "s/ACTIVE_BACKEND_HOST/${BACKEND_HOST}/g" "$TEMPLATE" > "$OUTPUT"

echo "Generated ${OUTPUT} → upstream=${BACKEND_HOST}"
