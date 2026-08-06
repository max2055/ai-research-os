#!/usr/bin/env bash
# launchd wrapper (B-021): run discovery for every due Channel, then the
# retention sweep. Per-channel failures are logged but do not abort the
# sweep; the discovery per-channel lock prevents overlapping runs and the
# Job Run record captures each outcome. Safe to run on every launchd tick.
set -uo pipefail

ROOT="/Users/max/Coding/57-AI-Research-OS"
PYTHON="/Users/max/.venvs/ai-research-os/bin/python"
CLI="$ROOT/09_Automation/research_os.py"
LOG_DIR="$ROOT/09_Automation/launchd/logs"
mkdir -p "$LOG_DIR"

cd "$ROOT" || exit 1
AS_OF="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

{
  echo "=== discovery sweep $(date -u +%Y-%m-%dT%H:%M:%SZ) as_of=$AS_OF ==="
  while IFS= read -r CHN; do
    [ -n "$CHN" ] || continue
    echo "-- discover $CHN --"
    "$PYTHON" "$CLI" --root "$ROOT" jobs run discover --target "$CHN" 2>&1 \
      || echo "discover $CHN FAILED (see Job Run record)"
  done < <("$PYTHON" "$CLI" --root "$ROOT" discover due --as-of "$AS_OF" 2>&1)

  echo "-- retention sweep --"
  "$PYTHON" "$CLI" --root "$ROOT" jobs run expire 2>&1 \
    || echo "expire sweep FAILED (see Job Run record)"
} >> "$LOG_DIR/sweep.log" 2>&1
