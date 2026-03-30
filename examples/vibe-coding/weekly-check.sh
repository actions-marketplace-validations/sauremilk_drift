#!/usr/bin/env sh
# Drift — Weekly vibe-coding debt monitoring.
#
# Run once per week (or via cron) to:
#   1. Capture a timestamped snapshot
#   2. Show trend direction
#   3. Generate prioritised fix-plan
#
# Usage:
#   chmod +x weekly-check.sh
#   ./weekly-check.sh
#
# Cron (every Monday 9:00):
#   0 9 * * 1 cd /path/to/repo && ./weekly-check.sh >> .drift-snapshots/log.txt 2>&1
set -e

if ! command -v drift >/dev/null 2>&1; then
    echo "ERROR: drift-analyzer not installed."
    exit 1
fi

SNAPSHOT_DIR=".drift-snapshots"
DATE=$(date +%Y%m%d)
SNAPSHOT_FILE="$SNAPSHOT_DIR/weekly-$DATE.json"

mkdir -p "$SNAPSHOT_DIR"

echo "=== Drift Weekly Report — $DATE ==="
echo ""

# Step 1: Full analysis snapshot
echo "[1/3] Running full analysis..."
drift analyze --format json --output "$SNAPSHOT_FILE"
echo "  Snapshot: $SNAPSHOT_FILE"

# Step 2: Trend
echo ""
echo "[2/3] Score trend:"
drift trend 2>/dev/null || echo "  (not enough snapshots for trend yet)"

# Step 3: Top repair tasks
echo ""
echo "[3/3] Top-5 repair tasks (highest impact):"
drift fix-plan --max-tasks 5 2>/dev/null || echo "  (fix-plan unavailable)"

echo ""
echo "--- Summary ---"
drift analyze --quiet
echo ""
echo "Full report: $SNAPSHOT_FILE"
echo "Compare with baseline: drift check --baseline .drift-baseline.json"
