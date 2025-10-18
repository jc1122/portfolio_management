# Refactoring Plan

This document outlines a step-by-step plan to address the technical debt and refactoring opportunities identified in the codebase analysis.

## Guiding Principles

- **Improve Readability & Maintainability:** Break down complex functions and large files into smaller, more manageable units.
- **Remove Dead Code:** Eliminate unused variables, functions, and classes to reduce clutter and improve clarity.
- **Enhance Robustness:** Fix type errors and address potential runtime issues.
- **Modernize Codebase:** Adopt modern Python features and patterns where appropriate.

## Step-by-Step Plan

The plan is organized by file. It is recommended to address the issues in the order they are presented.

### 1. `src/portfolio_management/config.py` & `src/portfolio_management/visualization.py`

**Issue:** These files contain a significant amount of unused code.

- **Action:**
  - Review `src/portfolio_management/config.py` and `src/portfolio_management/visualization.py`.
  - Identify which variables and functions are truly unused across the entire project.
  - Remove the unused code or the entire files if they are no longer needed.

### 2. `src/portfolio_management/analysis.py`

**Issues:** High complexity, long functions, unused code, type errors, syntax error.

- **Action:**
  1. **Fix Syntax Error:** Correct the syntax error identified in the analysis.
  1. **Remove Unused Functions:** Delete the unused functions identified in the report.
  1. **Refactor `_read_and_clean_stooq_csv`:** Break this function down into smaller private methods to reduce its cyclomatic complexity. Each new method should have a single responsibility (e.g., reading the CSV, cleaning the data, handling headers).
  1. **Refactor Long Functions:** Shorten `_calculate_data_quality_metrics`, `_generate_flags`, `summarize_price_file`, and `resolve_currency` by extracting logical blocks of code into separate helper functions.
  1. **Address Type Errors:** Correct the identified type-related issues.

### 3. `src/portfolio_management/backtest.py`

**Issues:** High complexity, long functions, too many parameters, unused code.

- **Action:**
  1. **Remove Unused Code:** Delete the unused methods and variables.
  1. **Refactor `BacktestEngine._rebalance`:** This is the most complex function. Break it down into smaller, more focused methods (e.g., `_calculate_target_shares`, `_execute_trades`, `_record_rebalance_event`).
  1. **Refactor Long Functions:** Break down the other long functions (`__post_init__`, `calculate_cost`, etc.) into smaller, more readable parts.
  1. **Simplify `__init__`:** Consider grouping related parameters into a configuration object or dataclass to reduce the number of parameters.

### 4. `src/portfolio_management/classification.py`

**Issues:** High complexity, long functions, unused code, type errors.

- **Action:**
  1. **Remove Unused Code:** Delete the unused enums, methods, and variables.
  1. **Refactor `AssetClassifier._classify_sub_class`:** Simplify this function by using a mapping or a more data-driven approach instead of a long chain of `if` statements.
  1. **Refactor Long Functions:** Break down `classify_asset` and `classify_universe` into smaller helper functions.
  1. **Address Type Errors:** Correct the identified type-related issue.

### 5. `src/portfolio_management/matching.py` & `src/portfolio_management/selection.py`

**Issues:** Large files, long functions, high complexity, unused code.

- **Action:**
  1. **Plan Module Splitting:**
     - For `matching.py`, consider splitting the different matching strategies (`TickerMatchingStrategy`, `StemMatchingStrategy`, etc.) into their own module or a `strategies` submodule.
     - For `selection.py`, consider splitting the filtering logic (`_filter_by_data_quality`, `_filter_by_history`, etc.) into a separate `filters` module.
  1. **Execute Splitting:** Create the new files/modules and move the relevant code. Update all necessary imports.
  1. **Remove Unused Code:** Delete the unused functions.
  1. **Refactor Long/Complex Functions:** After splitting the files, review the remaining long and complex functions and break them down further.

### 6. General Cleanup (All other files)

**Issues:** Unused code, long functions, and modernization opportunities are present in `exceptions.py`, `io.py`, `models.py`, `portfolio.py`, `returns.py`, `stooq.py`, `universes.py`, and `validators.py`.

- **Action:**
  1. **Remove Unused Code:** Go through each file and remove the identified unused code. This is a safe and easy first step.
  1. **Refactor Long Functions:** Systematically go through each file and break down the identified long functions into smaller, more focused units.
  1. **Address High Complexity:** For functions with high cyclomatic complexity, prioritize refactoring them to improve clarity and testability.
  1. **Apply Modernization:** Review the "modernization opportunities" and apply them where appropriate.
  1. **Fix Type Errors:** Correct any remaining type errors.

## Validation

After each major refactoring step, run the project's test suite to ensure that no regressions have been introduced.
