# Synthetic Workflow Fixtures

Synthetic fixtures are generated on demand during tests to avoid storing large
CSV files in the repository. The helper `tests/synthetic_data.py` provides
`generate_synthetic_market()` which writes a complete Stooq-style directory
tree, tradeable instrument lists, and a universe configuration into a supplied
temporary directory.

Usage snippet for local experimentation:

```python
from pathlib import Path
from tests.synthetic_data import generate_synthetic_market

dataset = generate_synthetic_market(Path(\"/tmp/synthetic_market\"))
print(dataset.stooq_dir)
```

The resulting tree mirrors the layout expected by `scripts.prepare_tradeable_data`
and other CLI workflows.
