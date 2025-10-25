# Testing Documentation

This directory contains comprehensive testing documentation for the portfolio management system.

## Quick Links

- [Test Organization](overview.md) - Test structure and running tests
- [Test Strategy](test_strategy.md) - Testing philosophy and best practices
- [Unit Testing](unit_testing.md) - Unit test guidelines and examples
- [Integration Testing](integration_testing.md) - Integration test patterns
- [Long History Tests](long_history_tests.md) - Comprehensive long-term validation

## Overview

The portfolio management system has a comprehensive test suite organized by package structure:

```
tests/
├── core/          # Core utilities and configuration
├── data/          # Data management and I/O
├── assets/        # Asset selection and classification
├── analytics/     # Returns calculation
├── portfolio/     # Portfolio construction strategies
├── backtesting/   # Backtest engine and metrics
├── reporting/     # Visualization and reports
├── integration/   # End-to-end workflow tests
└── scripts/       # CLI tool tests
```

## Test Categories

### Unit Tests
- Fast, isolated component tests
- Mock external dependencies
- Test single functions or classes
- See [unit_testing.md](unit_testing.md)

### Integration Tests
- Test multiple components together
- Use real data where possible
- Validate end-to-end workflows
- See [integration_testing.md](integration_testing.md)

### Long-History Tests
- Validate with 20 years of data
- Test all features together
- Ensure determinism and correctness
- See [long_history_tests.md](long_history_tests.md)

## Running Tests

### Quick Start

```bash
# Run all tests
pytest tests/

# Run specific package tests
pytest tests/portfolio/
pytest tests/backtesting/

# Run with coverage
pytest tests/ --cov=src/portfolio_management --cov-report=term-missing

# Run in parallel
pytest tests/ -n auto
```

### By Category

```bash
# Unit tests only
pytest tests/ -m "not integration"

# Integration tests only
pytest tests/integration/

# Long-history tests (slow)
pytest tests/integration/test_long_history_comprehensive.py -v
```

### Performance

```bash
# Skip slow tests during development
pytest tests/ -m "not slow"

# Run only fast tests
pytest tests/ --ignore=tests/scripts/test_prepare_tradeable_data.py
```

## Test Quality Metrics

### Current Status
- **Total Tests**: 231+ tests
- **Coverage**: ~85% overall
- **Core Coverage**: ~90% on critical paths
- **Pass Rate**: 100% (excluding optional dependencies)

### Coverage Requirements
- **Overall**: 80%+ required
- **Core Modules**: 90%+ required
- **Critical Paths**: 95%+ required
- **New Features**: Must include tests

## Best Practices

1. **Test Organization**: Mirror package structure
2. **Test Isolation**: Each test should be independent
3. **Clear Naming**: Use descriptive test names
4. **Documentation**: Add docstrings to complex tests
5. **Fixtures**: Reuse setup code via fixtures
6. **Markers**: Use pytest markers for categorization
7. **Coverage**: Maintain high coverage standards

## CI/CD Integration

Tests run automatically on:
- Pull requests
- Commits to main branch
- Nightly builds (includes slow tests)

Configuration: `.github/workflows/tests.yml`

## Troubleshooting

If tests fail, see:
- [Troubleshooting Guide](../troubleshooting.md)
- Test-specific sections in this directory
- Individual test docstrings for context

## Contributing

When adding new features:

1. **Write tests first** (TDD approach recommended)
2. **Place in correct package** (mirror production structure)
3. **Add integration tests** for end-to-end validation
4. **Update documentation** in this directory
5. **Verify coverage** meets requirements

## Related Documentation

- [Troubleshooting Guide](../troubleshooting.md) - Debugging test failures
- [Test Strategy](test_strategy.md) - Testing philosophy
- [Best Practices](../best_practices.md) - General development guidelines
- [Architecture](../architecture/ARCHITECTURE_DIAGRAM.md) - System architecture
