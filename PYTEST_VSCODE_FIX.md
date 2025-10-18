# VS Code pytest Configuration Fix

## Problem

Tests run successfully from the command line but fail in the VS Code pytest extension with import errors (usually module not found errors like `ModuleNotFoundError: No module named 'portfolio_management'`).

## Root Cause

The VS Code pytest extension wasn't properly configured to use the `pythonpath` setting from `pyproject.toml`. The extension needs explicit configuration to add the `src/` directory to Python's search path.

## Solution Applied

### 1. Updated `.vscode/settings.json`

The following changes have been made:

```json
{
    "python.defaultInterpreterPath": "/usr/local/python/current/bin/python",
    "python.testing.pytestArgs": [
        "tests",
        "--tb=short"
    ],
    "python.testing.unittestEnabled": false,
    "python.testing.pytestEnabled": true,
    "python.analysis.typeCheckingMode": "basic",
    "python.analysis.include": [
        "src",
        "tests",
        "scripts"
    ],
    "python.analysis.exclude": [
        "data/**",
        "archive/**"
    ],
    "files.exclude": {
        "data/": true,
        "archive/": true,
        "**/__pycache__": true,
        "**/*.egg-info": true
    }
}
```

**Key changes:**

- Added `"--tb=short"` to `python.testing.pytestArgs` for better error reporting
- Added `python.analysis.include` to tell Pylance to analyze `src/`, `tests/`, and `scripts/`
- Added `python.analysis.exclude` to prevent Pylance from scanning the large `data/` and `archive/` directories (performance improvement)
- Added `files.exclude` to hide these directories in the file explorer

### 2. Existing Configuration in `pyproject.toml`

The project already has proper pytest configuration:

```toml
[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
norecursedirs = ["data", "archive", ".git", "__pycache__", "*.egg-info"]
markers = [
  "integration: marks tests as integration tests",
  "slow: marks tests as slow",
]
addopts = "--strict-markers"
```

This works fine from the command line because pytest reads this file directly.

## Verification Steps

1. **Reload VS Code**: Press `Ctrl+Shift+P` → "Developer: Reload Window" or just close and reopen VS Code
1. **Verify Python interpreter**:
   - Open the Command Palette (`Ctrl+Shift+P`)
   - Type "Python: Select Interpreter"
   - Ensure `/usr/local/python/current/bin/python` is selected (or your project's Python interpreter)
1. **Run tests from VS Code**:
   - Open the Test Explorer (`Ctrl+Shift+Alt+T` or via the Activity Bar)
   - Click the play button to run all tests, or run individual tests
   - Tests should now pass with proper imports resolved

## Alternative: Run from Terminal (Always Works)

If you continue to have issues, you can always run tests from the integrated terminal:

```bash
python -m pytest tests -v
```

Or with coverage:

```bash
python -m pytest tests -v --cov=portfolio_management --cov-report=html
```

The terminal approach bypasses the VS Code pytest extension and uses pytest directly with the `pyproject.toml` configuration.

## Why This Happens

- VS Code's pytest extension doesn't automatically read all configuration from `pyproject.toml` regarding `pythonpath`
- The extension needs explicit guidance about which directories contain code and which should be excluded
- Pylance (the Python language server) also benefits from explicit include/exclude settings to avoid scanning large data directories

## Additional Notes

- The `conftest.py` file in `tests/` also has a fallback mechanism that adds the repo root to `sys.path`, providing extra resilience
- The `norecursedirs` setting in `pyproject.toml` prevents pytest from accidentally collecting tests from the massive `data/` directory (which contains 70K+ files)
- Future tool configurations should similarly exclude `data/` and `archive/` directories for performance
