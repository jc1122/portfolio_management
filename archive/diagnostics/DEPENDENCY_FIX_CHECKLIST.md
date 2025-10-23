# Quick Reference: Dependency Fix Checklist

## ✅ Completed Tasks

- \[x\] Identified missing dependencies (jax, jaxlib, quadprog)
- \[x\] Updated `requirements.txt` with missing packages
- \[x\] Updated `pyproject.toml` with missing packages
- \[x\] Set appropriate version constraints (>=0.3.0 for jax/jaxlib)
- \[x\] Created verification script (`test_dependencies.py`)
- \[x\] Tested in local environment (Python 3.9)
- \[x\] Tested in fresh virtual environment
- \[x\] Verified all imports work without errors or warnings
- \[x\] Documented changes in `GITHUB_ACTIONS_FIX.md`

## 📋 Summary of Changes

### Files Modified:

1. **requirements.txt** - Added jax, jaxlib, quadprog
1. **pyproject.toml** - Added jax, jaxlib, quadprog to dependencies

### Files Created:

1. **test_dependencies.py** - Dependency verification script
1. **GITHUB_ACTIONS_FIX.md** - Detailed fix documentation
1. **DEPENDENCY_FIX_CHECKLIST.md** - This file

## 🧪 Verification Commands

Run these to verify the fix:

```bash
# Test all dependencies
python test_dependencies.py

# Test individual imports
python -c "import pandas; import numpy; import yaml; import scipy; import cvxpy; print('Core dependencies OK')"
python -c "import empyrical; print('empyrical-reloaded OK')"
python -c "import pypfopt; print('PyPortfolioOpt OK')"
python -c "import riskparityportfolio; print('riskparityportfolio OK')"
```

## 🚀 Next Steps

1. **Commit changes:**

   ```bash
   git add requirements.txt pyproject.toml test_dependencies.py
   git commit -m "fix: Add missing dependencies for riskparityportfolio (jax, jaxlib, quadprog)"
   ```

1. **Push to trigger CI:**

   ```bash
   git push origin main
   ```

1. **Monitor GitHub Actions:**

   - Check `.github/workflows/tests.yml` workflow
   - Verify "Verify critical dependencies" step passes
   - Confirm all tests complete successfully

## 📌 Key Points

- **jax/jaxlib**: Required by riskparityportfolio for numerical computations
- **quadprog**: Optional but eliminates warnings, enables SCA optimizer
- **Version constraint**: `>=0.3.0` works with Python 3.9-3.12
- **No workflow changes needed**: Existing `.github/workflows/tests.yml` is correct

## 🔍 Troubleshooting

If CI still fails:

1. Check Python version in workflow (should be 3.12)
1. Verify requirements.txt and pyproject.toml are in sync
1. Check for network/timeout issues during pip install
1. Review full error logs in GitHub Actions

## ✨ Expected Output

When successful, you should see:

```
Core dependencies OK
empyrical-reloaded OK
PyPortfolioOpt OK
riskparityportfolio OK
portfolio_management package OK
```

No warnings or errors!
