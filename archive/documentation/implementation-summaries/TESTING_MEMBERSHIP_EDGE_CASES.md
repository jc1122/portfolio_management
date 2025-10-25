# Running Membership Policy Edge Case Tests

## Prerequisites

Ensure you have all dependencies installed:

```bash
pip install -e .
pip install -r requirements-dev.txt
```

## Running the Tests

### Run all membership policy tests:

```bash
pytest tests/portfolio/test_membership.py -v
```

### Run specific test classes:

```bash
# Buffer zone edge cases (7 tests)
pytest tests/portfolio/test_membership.py::TestBufferZoneEdgeCases -v

# Boundary conditions (6 tests)
pytest tests/portfolio/test_membership.py::TestBoundaryConditions -v

# Policy constraint conflicts (7 tests)
pytest tests/portfolio/test_membership.py::TestPolicyConstraintConflicts -v

# Special scenarios (6 tests)
pytest tests/portfolio/test_membership.py::TestSpecialScenarios -v
```

### Run specific test methods:

```bash
# Test buffer zone entry
pytest tests/portfolio/test_membership.py::TestBufferZoneEdgeCases::test_asset_enters_buffer_zone -v

# Test all assets failing criteria
pytest tests/portfolio/test_membership.py::TestBoundaryConditions::test_all_current_holdings_fail_criteria -v

# Test policy conflicts
pytest tests/portfolio/test_membership.py::TestPolicyConstraintConflicts::test_min_holding_vs_max_removed_conflict -v
```

### Run with coverage:

```bash
pytest tests/portfolio/test_membership.py --cov=src/portfolio_management/portfolio/membership --cov-report=term-missing
```

## Expected Results

All 45 tests should pass:

- 10 tests in `TestMembershipPolicy` (validation and creation)
- 9 tests in `TestApplyMembershipPolicy` (basic functionality)
- 7 tests in `TestBufferZoneEdgeCases` (buffer zone transitions)
- 6 tests in `TestBoundaryConditions` (boundary scenarios)
- 7 tests in `TestPolicyConstraintConflicts` (constraint interactions)
- 6 tests in `TestSpecialScenarios` (unusual edge cases)

## Test Categories

### 1. Buffer Zone Transitions (Issue Requirement)

Tests that validate buffer zone behavior:

- Assets entering buffer zone (rank 31-50 with top_k=30, buffer=50)
- Assets exiting buffer zone (drops below buffer_rank)
- Assets oscillating around buffer boundary
- Multiple assets in buffer zone
- Empty buffer zone (all ranks \< top_k)
- Buffer disabled (buffer_rank=None)
- Buffer at top_k boundary

### 2. All Assets Failing Criteria (Issue Requirement)

Tests that validate handling when assets fail selection criteria:

- All current holdings outside both top_k and buffer
- All holdings protected despite failing criteria
- Holdings missing from preselected ranks

### 3. Boundary Conditions (Issue Requirement)

Tests that validate exact boundary behaviors:

- Single asset portfolio
- Empty portfolio (initial construction)
- Exact top_k boundary (rank = top_k)
- Exact buffer boundary (rank = buffer_rank)
- All assets with equal rank (ties)
- Extremely large buffer (buffer > universe size)

### 4. Policy Conflict Scenarios (Issue Requirement)

Tests that validate policy constraint interactions:

- min_holding_periods vs max_removed_assets conflict
- max_new_assets vs top_k conflict
- Buffer keeps more assets than top_k
- Zero constraint values (max_new=0, max_removed=0, min_holding=0)
- Multiple policies active simultaneously at limits

## Interpreting Test Results

### Successful Test Run

```
tests/portfolio/test_membership.py::TestMembershipPolicy::test_default_policy PASSED
tests/portfolio/test_membership.py::TestMembershipPolicy::test_disabled_policy PASSED
...
tests/portfolio/test_membership.py::TestSpecialScenarios::test_multiple_policies_all_at_limits PASSED

============================== 45 passed in 0.50s ==============================
```

### Test Failure Example

If a test fails, pytest will show:

- Which test failed
- The assertion that failed
- The actual vs expected values
- Full traceback

Example:

```
tests/portfolio/test_membership.py::TestBufferZoneEdgeCases::test_asset_enters_buffer_zone FAILED

    def test_asset_enters_buffer_zone(self) -> None:
        ...
>       assert "GOOGL" in result
E       AssertionError: assert 'GOOGL' in ['AAPL', 'MSFT', ...]
```

## Debugging Failed Tests

1. **Read the test docstring** to understand what scenario is being tested
1. **Check the assertion message** to see what failed
1. **Add print statements** to inspect intermediate values:
   ```python
   print(f"Current holdings: {current_holdings}")
   print(f"Result: {result}")
   print(f"Buffered assets: {buffered_assets}")
   ```
1. **Run with verbose output**: `pytest -vv -s`
1. **Use pytest debugger**: `pytest --pdb` to drop into debugger on failure

## Validating Without Running Tests

If you cannot install dependencies, you can validate test structure:

```bash
python3 /tmp/validate_tests.py
```

This validates:

- Syntax is correct
- All test classes are present
- All critical test methods exist
- No import or structural errors

## Next Steps After Tests Pass

1. Review coverage report to identify any missing scenarios
1. Consider adding integration tests for multi-period rebalancing
1. Update main documentation with edge case handling notes
1. Consider adding property-based tests (hypothesis) for exhaustive validation
