#!/usr/bin/env bash
set -euo pipefail

RAW_LOG="${DMR_RAW_LOG:-/data/dmr/raw.log}"
EXTRA_ARGS="${DMR_EXTRA_ARGS:-}"

mkdir -p "$(dirname "$RAW_LOG")"
touch "$RAW_LOG"

if [[ -n "$EXTRA_ARGS" ]]; then
  read -r -a extra_args <<< "$EXTRA_ARGS"
else
  extra_args=()
fi

set -o pipefail
dsd-fme "$@" "${extra_args[@]}" 2>&1 | tee -a "$RAW_LOG"
