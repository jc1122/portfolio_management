# GitHub Actions Test Dependency Fix

## Problem

Integration tests in `tests/integration/test_synthetic_workflow.py` were failing in GitHub Actions with 3 failures (FFF):

- `test_portfolio_construction_success`
- `test_portfolio_construction_insufficient_history`
- `test_backtesting_strategies`

## Root Cause

The `PyPortfolioOpt` package requires `empyrical` (or `empyrical-reloaded`) as a dependency for calculating financial performance metrics. This dependency was not explicitly listed in `requirements.txt` or `pyproject.toml`, causing installation failures in GitHub Actions.

Additionally, the GitHub Actions workflow was configured to allow these dependencies to fail silently:

```yaml
python -c "import pypfopt; print('PyPortfolioOpt OK')" || echo "Warning: PyPortfolioOpt not available"
python -c "import riskparityportfolio; print('riskparityportfolio OK')" || echo "Warning: riskparityportfolio not available"
```

This meant that even when the packages failed to install, the workflow would continue and tests would fail later with unclear error messages.

## Solution

1. **Added `empyrical-reloaded>=0.5.0`** to both `requirements.txt` and `pyproject.toml`

   - `empyrical-reloaded` is the actively maintained fork of `empyrical`
   - Required by PyPortfolioOpt for calculating Sharpe ratios and other financial metrics

1. **Updated GitHub Actions workflow** (`.github/workflows/tests.yml`)

   - Added explicit verification: `python -c "import empyrical; print('empyrical-reloaded OK')"`
   - Removed soft failure (`|| echo "Warning"`) for `pypfopt` and `riskparityportfolio`
   - Now the workflow will fail early if these critical dependencies can't be installed

## Files Changed

- `requirements.txt` - Added empyrical-reloaded dependency
- `pyproject.toml` - Added empyrical-reloaded to project dependencies
- `.github/workflows/tests.yml` - Updated dependency verification to fail properly

## Expected Outcome

With `empyrical-reloaded` installed:

- `PyPortfolioOpt` will install successfully
- `riskparityportfolio` will install successfully
- Integration tests will pass:
  - `test_portfolio_construction_success` - Can now create portfolios with all strategies
  - `test_portfolio_construction_insufficient_history` - Can now test error handling
  - `test_backtesting_strategies` - Can now run backtests with all strategies

## Dependencies Chain

```
PyPortfolioOpt
├── pandas (✓ already in requirements)
├── numpy (✓ already in requirements)
├── scipy (✓ already in requirements)
├── cvxpy (✓ already in requirements)
└── empyrical (✗ MISSING - now added as empyrical-reloaded)

riskparityportfolio
├── numpy (✓ already in requirements)
├── scipy (✓ already in requirements)
└── pandas (✓ already in requirements)
```

## Verification

To verify the fix locally:

```bash
pip install -r requirements.txt
python -c "import empyrical; print('empyrical OK')"
python -c "import pypfopt; print('PyPortfolioOpt OK')"
python -c "import riskparityportfolio; print('riskparityportfolio OK')"
pytest tests/integration/test_synthetic_workflow.py -v
```

## Security

- Verified no known vulnerabilities in `empyrical-reloaded>=0.5.0` using GitHub Advisory Database
- All other dependencies remain unchanged
