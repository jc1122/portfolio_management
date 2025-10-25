# Test Isolation Guidelines

## Why Test Isolation Matters

Tests must be completely independent to ensure:
- Reliable CI/CD (tests pass consistently)
- Debugging efficiency (failures are reproducible)
- Parallel execution (tests can run concurrently)
- Development confidence (local results match CI)

## Automatic Isolation Mechanisms

### 1. Cache Clearing (Automatic)

All caches are automatically cleared before each test via `conftest.py`:
- `PriceLoader` cache
- `StatisticsCache`
- `FactorCache`

**You don't need to do anything** - this happens automatically.

### 2. Random Seed Reset (Automatic)

Random number generators are reset to seed 42 before each test.

### 3. Temporary Directories (Built-in)

Use `tmp_path` fixture for all file I/O in tests:

```python
@pytest.mark.integration
def test_something(tmp_path):
    # tmp_path is automatically cleaned up after test
    test_file = tmp_path / "test.csv"
    # ... use test_file ...
```

## Writing Isolated Tests

### DO:
✅ Use `tmp_path` for all file I/O
✅ Use mock fixtures from `tests/fixtures/mocks.py`
✅ Create fresh objects in each test
✅ Use `@pytest.mark.unit` for fast, pure logic tests

### DON'T:
❌ Write to project directories
❌ Use global variables or module-level state
❌ Depend on test execution order
❌ Share objects between tests
❌ Use fixed file paths (use `tmp_path` instead)

## Validating Test Isolation

Run tests in random order to validate independence:

```bash
# Random order
pytest tests/ --randomly-seed=1

# Different random order
pytest tests/ --randomly-seed=2

# Automated validation script
./scripts/validate_test_isolation.sh
```

If tests fail in random order but pass normally, they have ordering dependencies.

## Debugging Isolation Issues

If you suspect tests are sharing state:

1. **Check for module-level variables:**
   ```bash
   grep -r "^[A-Z_]*\s*=" src/ --include="*.py"
   ```

2. **Check for singleton patterns:**
   ```bash
   grep -r "class.*Singleton\|_instance\s*=" src/ --include="*.py"
   ```

3. **Run tests individually:**
   ```bash
   pytest tests/path/to/test_file.py::test_name -v
   ```

4. **Use `--randomly` to find ordering issues:**
   ```bash
   pytest tests/ --randomly-seed=1 -x  # Stop at first failure
   ```

## Cache Management in Tests

All caches have `clear_cache()` and `get_cache_stats()` methods:

```python
def test_something_with_cache():
    loader = PriceLoader()

    # Cache starts empty (automatic clearing)
    assert loader.get_cache_stats()["cache_entries"] == 0

    # Use cache
    data = loader.load("symbol")
    assert loader.get_cache_stats()["cache_entries"] == 1

    # Manual clear if needed (usually not necessary)
    loader.clear_cache()
```

## Related Documentation

- [Test Organization](TEST_ORGANIZATION.md)
- [CI Test Strategy](CI_TEST_STRATEGY.md)