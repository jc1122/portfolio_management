#!/bin/bash
# Archive legacy Sprint 2 documentation files
# Run from repository root: bash scripts/archive_sprint2_docs.sh

set -e

echo "🧹 Archiving Sprint 2 Documentation..."

# Create archive directories
mkdir -p archive/sprint2/{implementations,testing,planning}
mkdir -p archive/cleanup

# Move Sprint planning/review documents
echo "📋 Moving Sprint 2 planning documents..."
mv SPRINT_2_AGENT_ASSIGNMENTS.md archive/sprint2/planning/ 2>/dev/null || true
mv SPRINT_2_ASSIGNMENT.md archive/sprint2/planning/ 2>/dev/null || true
mv SPRINT_2_DEPLOYMENT_SUMMARY.md archive/sprint2/ 2>/dev/null || true
mv SPRINT_2_PHASE_1_COMPLETION.md archive/sprint2/ 2>/dev/null || true
mv SPRINT_2_QUICK_START.md archive/sprint2/ 2>/dev/null || true
mv SPRINT_2_REVIEW_REPORT.md archive/sprint2/ 2>/dev/null || true
mv SPRINT_2_VISUAL_SUMMARY.md archive/sprint2/ 2>/dev/null || true

# Move Sprint 3 planning (not yet executed)
echo "📋 Moving Sprint 3 planning documents..."
mv SPRINT_3_AGENT_ASSIGNMENTS.md archive/sprint2/planning/ 2>/dev/null || true
mv SPRINT_3_PLAN.md archive/sprint2/planning/ 2>/dev/null || true

# Move implementation summaries
echo "⚙️  Moving implementation summaries..."
mv BENCHMARK_QUICK_START.md archive/sprint2/implementations/ 2>/dev/null || true
mv CACHE_BENCHMARK_IMPLEMENTATION.md archive/sprint2/implementations/ 2>/dev/null || true
mv CACHING_EDGE_CASES_SUMMARY.md archive/sprint2/implementations/ 2>/dev/null || true
mv CARDINALITY_IMPLEMENTATION_SUMMARY.md archive/sprint2/implementations/ 2>/dev/null || true
mv EDGE_CASE_TESTS_SUMMARY.md archive/sprint2/implementations/ 2>/dev/null || true
mv ENHANCED_ERROR_HANDLING_SUMMARY.md archive/sprint2/implementations/ 2>/dev/null || true
mv FAST_IO_BENCHMARKS_SUMMARY.md archive/sprint2/implementations/ 2>/dev/null || true
mv FAST_IO_IMPLEMENTATION.md archive/sprint2/implementations/ 2>/dev/null || true
mv IMPLEMENTATION_SUMMARY.md archive/sprint2/implementations/ 2>/dev/null || true
mv IMPLEMENTATION_SUMMARY_PIT_EDGE_CASES.md archive/sprint2/implementations/ 2>/dev/null || true
mv INTEGRATION_COMPLETE.md archive/sprint2/implementations/ 2>/dev/null || true
mv LONG_HISTORY_TESTS_IMPLEMENTATION_SUMMARY.md archive/sprint2/implementations/ 2>/dev/null || true
mv MEMBERSHIP_EDGE_CASE_IMPLEMENTATION.md archive/sprint2/implementations/ 2>/dev/null || true
mv PRESELECTION_ROBUSTNESS_SUMMARY.md archive/sprint2/implementations/ 2>/dev/null || true
mv TECHNICAL_INDICATORS_IMPLEMENTATION.md archive/sprint2/implementations/ 2>/dev/null || true

# Move testing documentation
echo "🧪 Moving testing documentation..."
mv REQUIREMENTS_COVERAGE.md archive/sprint2/testing/ 2>/dev/null || true
mv TESTING_INSTRUCTIONS.md archive/sprint2/testing/ 2>/dev/null || true
mv TESTING_MEMBERSHIP_EDGE_CASES.md archive/sprint2/testing/ 2>/dev/null || true

# Move cleanup documentation
echo "🧹 Moving cleanup documentation..."
mv CLEANUP_SUMMARY_2025-10-23.md archive/cleanup/ 2>/dev/null || true
mv REFACTORING_SUMMARY.md archive/cleanup/ 2>/dev/null || true

# Create archive README
cat > archive/sprint2/README.md << 'EOF'
# Sprint 2 Archive

This directory contains documentation from Sprint 2 (October 2025), which delivered:

- Factor-based preselection (momentum, low-volatility, combined)
- Membership policy with turnover controls
- Point-in-time (PIT) eligibility (no-lookahead backtesting)
- Factor and PIT eligibility caching
- Optional fast IO (polars/pyarrow)

All features are now integrated into the main codebase and documented in `docs/`.

## Directory Structure

- `planning/` - Sprint 2 & 3 planning documents
- `implementations/` - Feature implementation summaries
- `testing/` - Testing instructions and coverage reports
- `SPRINT_2_*.md` - Sprint completion reports and reviews

## Status

✅ **Sprint 2:** Complete (all features merged to main)
📋 **Sprint 3:** Planning only (not yet executed)

See `memory-bank/progress.md` for current development status.
EOF

echo ""
echo "✅ Archive complete!"
echo ""
echo "📊 Summary:"
echo "  - Sprint 2 planning: $(ls archive/sprint2/planning/*.md 2>/dev/null | wc -l) files"
echo "  - Implementations: $(ls archive/sprint2/implementations/*.md 2>/dev/null | wc -l) files"
echo "  - Testing docs: $(ls archive/sprint2/testing/*.md 2>/dev/null | wc -l) files"
echo "  - Cleanup docs: $(ls archive/cleanup/*.md 2>/dev/null | wc -l) files"
echo ""
echo "🎯 Next steps:"
echo "  1. Review CODEBASE_CLEANUP_ANALYSIS.md"
echo "  2. Create QUICKSTART.md for new users"
echo "  3. Validate examples/ scripts"
echo "  4. Update memory bank"
