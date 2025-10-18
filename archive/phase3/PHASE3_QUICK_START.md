# Phase 3 Quick Start Guide for Agents

## 🎯 Current Objective

Implement Asset Selection & Universe Management system (Phase 3)

## 📋 Implementation Documents

1. **PHASE3_PORTFOLIO_SELECTION_PLAN.md** - High-level design and architecture
1. **PHASE3_IMPLEMENTATION_TASKS.md** - Detailed task-by-task instructions (THIS IS YOUR PRIMARY GUIDE)

## 🚀 How to Use This Guide

### For Each Work Session:

1. **Read the session boot checklist** from `AGENTS.md`
1. **Check current progress** in `memory-bank/progress.md` and `memory-bank/activeContext.md`
1. **Pick the next unchecked task** from `PHASE3_IMPLEMENTATION_TASKS.md`
1. **Follow the task steps exactly** - each task has:
   - File to create/modify
   - Detailed implementation steps
   - Deliverables
   - Test requirements
   - Validation commands
1. **Test immediately** after implementation using provided validation commands
1. **Update the task checklist** in `PHASE3_IMPLEMENTATION_TASKS.md` (check the box)
1. **Update memory bank** if significant progress or decisions made

## 📊 Current Status

**Branch:** `portfolio-construction`
**Phase:** 3 - Asset Selection & Universe Management
**Stage:** Ready to start Stage 1, Task 1.1

**Progress:** 0/45 tasks complete (0%)

**Data Ready:**

- ✅ 5,560 matched instruments
- ✅ 4,498 price files exported
- ✅ Data quality metadata available

## 🎬 Next Immediate Actions

Start with **Stage 1: Asset Selection Core**

### Task 1.1: Create Data Models (2 hours) - START HERE

```bash
# 1. Create the file
touch src/portfolio_management/selection.py

# 2. Follow steps in PHASE3_IMPLEMENTATION_TASKS.md Task 1.1
# 3. Implement FilterCriteria dataclass
# 4. Implement SelectedAsset dataclass
# 5. Add validation methods
# 6. Validate:
python -c "from src.portfolio_management.selection import FilterCriteria, SelectedAsset; print('✓ Models imported')"
mypy src/portfolio_management/selection.py
```

### Task 1.2: Data Quality Filter (2 hours) - NEXT

After Task 1.1 is complete and validated, move to Task 1.2

## 🧪 Testing Strategy

- **Write tests as you go** - don't save all testing for the end
- **Use existing test fixtures** from `tests/fixtures/`
- **Create new fixtures** as needed (Task 1.7)
- **Run tests after each task** using the validation commands
- **Target: ≥80% coverage** for new modules

## 📁 New Files to Create

### Stage 1:

- `src/portfolio_management/selection.py`
- `tests/test_selection.py`
- `tests/fixtures/selection_test_data.csv`
- `scripts/select_assets.py`
- `tests/scripts/test_select_assets.py`

### Stage 2:

- `src/portfolio_management/classification.py`
- `tests/test_classification.py`
- `scripts/classify_assets.py`
- `tests/scripts/test_classify_assets.py`

### Stage 3:

- `src/portfolio_management/returns.py`
- `tests/test_returns.py`
- `scripts/calculate_returns.py`
- `tests/scripts/test_calculate_returns.py`

### Stage 4:

- `src/portfolio_management/universes.py`
- `tests/test_universes.py`
- `config/universes.yaml`
- `scripts/manage_universes.py`
- `tests/scripts/test_manage_universes.py`
- `docs/universes.md`

### Stage 5:

- `tests/integration/test_full_pipeline.py`
- `docs/phase3_guide.md`
- `docs/api_reference.md`
- `docs/architecture.md`
- `examples/asset_selection.ipynb`
- `examples/universe_management.ipynb`

## 🔄 Workflow Pattern

For each task:

```bash
# 1. Read task details
cat PHASE3_IMPLEMENTATION_TASKS.md | grep -A 50 "Task X.Y"

# 2. Implement according to steps

# 3. Run validation
pytest tests/test_<module>.py::test_<function> -v
mypy src/portfolio_management/<module>.py

# 4. Check off task in PHASE3_IMPLEMENTATION_TASKS.md

# 5. Commit if milestone reached
git add .
git commit -m "Implement Task X.Y: <description>"

# 6. Update memory bank if significant progress
```

## ⚠️ Important Notes

### Code Quality Requirements:

- **Type hints** on all public functions and methods
- **Docstrings** on all classes and public methods
- **Logging** for important operations
- **Error handling** for edge cases
- **Tests** for new functionality

### Data Handling:

- Always use **absolute paths**
- Check **file existence** before operations
- Handle **missing data** gracefully
- **Validate inputs** before processing
- **Log progress** for long operations

### PYTHONPATH Issues:

When running scripts, use:

```bash
PYTHONPATH=/workspaces/portfolio_management:$PYTHONPATH python scripts/<script>.py
```

Or run from project root:

```bash
cd /workspaces/portfolio_management
python scripts/<script>.py
```

### Testing:

```bash
# Run specific test
pytest tests/test_selection.py::test_filter_by_data_quality -v

# Run all tests in a file
pytest tests/test_selection.py -v

# Run with coverage
pytest tests/test_selection.py --cov=src.portfolio_management.selection --cov-report=term-missing

# Run all tests
pytest tests/ -v
```

## 📈 Progress Tracking

Update this section regularly:

### Week 1 (Days 1-5):

- \[ \] Stage 1: Asset Selection Core (9 tasks)
- \[ \] Stage 2: Asset Classification (6 tasks) - START

### Week 2 (Days 6-10):

- \[ \] Stage 2: Asset Classification (6 tasks) - COMPLETE
- \[ \] Stage 3: Return Calculation (8 tasks)
- \[ \] Stage 4: Universe Management (8 tasks) - START

### Week 3 (Days 11-15):

- \[ \] Stage 4: Universe Management (8 tasks) - COMPLETE
- \[ \] Stage 5: Integration & Polish (8 tasks)
- \[ \] Final QA and documentation

## 🎓 Learning Resources

### Pandas for Price Data:

- `pd.read_csv()` for loading CSVs
- `pd.DataFrame.pct_change()` for returns
- `pd.DataFrame.resample()` for frequency conversion
- `pd.DataFrame.fillna()` for missing data

### Type Hints:

- `list[SelectedAsset]` for typed lists
- `dict[str, Any]` for typed dicts
- `pd.DataFrame` for DataFrames
- `Path` from pathlib for paths

### Testing with pytest:

- `@pytest.fixture` for test data
- `pytest.raises()` for exception testing
- `assert` for validation
- `pytest.mark.parametrize` for multiple test cases

## 🆘 Troubleshooting

### Common Issues:

**Import errors:**

```bash
# Set PYTHONPATH
export PYTHONPATH=/workspaces/portfolio_management:$PYTHONPATH
```

**Test discovery issues:**

```bash
# Run from project root
cd /workspaces/portfolio_management
pytest tests/
```

**Type checking errors:**

```bash
# Check specific file
mypy src/portfolio_management/selection.py

# Ignore pandas-stubs issues (known limitation)
# See existing mypy.ini for ignore patterns
```

**Data not found:**

```bash
# Verify data exists
ls data/metadata/tradeable_matches.csv
ls data/processed/tradeable_prices/ | head

# Regenerate if needed
PYTHONPATH=/workspaces/portfolio_management:$PYTHONPATH python scripts/prepare_tradeable_data.py
```

## 📞 Questions & Clarifications

If uncertain about implementation details:

1. Check the design in `PHASE3_PORTFOLIO_SELECTION_PLAN.md`
1. Look at similar patterns in existing code (`src/portfolio_management/`)
1. Check existing tests for examples (`tests/`)
1. Document the decision in the implementation
1. Update memory bank with the rationale

## ✅ Definition of Done

A task is complete when:

- \[ \] Code implemented according to task steps
- \[ \] Type hints added to all public APIs
- \[ \] Docstrings added to classes and methods
- \[ \] Tests written and passing
- \[ \] Validation commands run successfully
- \[ \] No mypy errors in new code
- \[ \] Checkbox marked in PHASE3_IMPLEMENTATION_TASKS.md
- \[ \] Code committed (if milestone)

## 🎉 Milestone Celebrations

- ✅ Complete Stage 1 (9 tasks) - Asset Selection working!
- ✅ Complete Stage 2 (6 tasks) - Classification system ready!
- ✅ Complete Stage 3 (8 tasks) - Returns calculated!
- ✅ Complete Stage 4 (8 tasks) - Universe management live!
- ✅ Complete Stage 5 (8 tasks) - Phase 3 DONE! 🚀

______________________________________________________________________

**Remember:** Take tasks one at a time, test continuously, and update documentation as you go. You've got this! 💪
