#!/usr/bin/env sh
# Drift — Baseline setup for vibe-coding debt ratchet.
#
# Creates an initial baseline snapshot and configures the delta gate
# so that drift score can only decrease (ratchet pattern).
#
# Usage:
#   chmod +x setup-baseline.sh
#   ./setup-baseline.sh
#
# After running:
#   1. .drift-baseline.json is created (commit this file)
#   2. First snapshot is stored in .drift-snapshots/
#   3. You can manually enable fail_on_delta in drift.yaml
set -e

if ! command -v drift >/dev/null 2>&1; then
    echo "ERROR: drift-analyzer not installed."
    echo "Install with: pip install drift-analyzer"
    exit 1
fi

echo "=== Drift Baseline Setup ==="
echo ""

# Step 1: Validate configuration
echo "[1/4] Validating drift configuration..."
if [ -f "drift.yaml" ]; then
    drift validate --config drift.yaml
else
    echo "  No drift.yaml found — using default configuration."
    echo "  Copy examples/vibe-coding/drift.yaml for vibe-coding-optimised settings."
fi

# Step 2: Run initial analysis and capture baseline
echo ""
echo "[2/4] Running initial analysis (this is your Day 0 baseline)..."
mkdir -p .drift-snapshots
drift analyze --format json --output .drift-snapshots/baseline-$(date +%Y%m%d).json
echo "  Snapshot saved to .drift-snapshots/"

# Step 3: Create baseline for delta comparison
echo ""
echo "[3/4] Creating drift baseline..."
drift baseline --output .drift-baseline.json
echo "  Baseline saved to .drift-baseline.json"

# Step 4: Show results
echo ""
echo "[4/4] Baseline established."
echo ""
echo "--- Initial Drift Report ---"
drift analyze --quiet
echo ""
echo "Next steps:"
echo "  1. Commit .drift-baseline.json to your repository"
echo "  2. Add .drift-snapshots/ to .gitignore (local tracking only)"
echo "  3. Uncomment fail_on_delta in drift.yaml to enable the ratchet gate"
echo "  4. Run 'drift fix-plan' to see prioritised repair tasks"
echo ""
echo "Weekly tracking:"
echo "  drift analyze -f json -o .drift-snapshots/weekly-\$(date +%Y%m%d).json"
echo "  drift trend"
