#!/bin/bash
# Validate that tests are independent and can run in any order

set -e

echo "==================================="
echo "Test Isolation Validation"
echo "==================================="

# Run 1: Normal order
echo ""
echo "Run 1: Normal order..."
python -m pytest tests/ -v --tb=short -q > /tmp/test_run_1.txt 2>&1 || true

# Run 2: Random order (seed 1)
echo "Run 2: Random order (seed 1)..."
python -m pytest tests/ -v --tb=short -q --randomly-seed=1 > /tmp/test_run_2.txt 2>&1 || true

# Run 3: Random order (seed 2)
echo "Run 3: Random order (seed 2)..."
python -m pytest tests/ -v --tb=short -q --randomly-seed=2 > /tmp/test_run_3.txt 2>&1 || true

# Run 4: Reverse order
echo "Run 4: Reverse order..."
python -m pytest tests/ -v --tb=short -q --randomly-seed=0 --randomly-dont-shuffle-modules > /tmp/test_run_4.txt 2>&1 || true

# Compare results
echo ""
echo "Comparing results..."

# Extract pass/fail counts
for i in 1 2 3 4; do
    echo "Run $i:"
    grep -E "passed|failed" /tmp/test_run_$i.txt | tail -1 || echo "  Could not parse results"
done

echo ""
echo "==================================="
echo "If all runs have the same pass/fail counts, tests are independent!"
echo "If counts differ, there are test ordering dependencies."
echo "==================================="