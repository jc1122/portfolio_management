# Clustering-Based Diversification for Asset Preselection

## Overview

This feature adds an optional post-ranking clustering step that selects a diversified subset of top-ranked candidates to reduce correlation concentration in the asset universe.

## Motivation

When selecting assets for a portfolio, naive top-K selection (e.g., taking the top 50 assets by some ranking) may result in a portfolio with high internal correlation. This happens when the top-ranked assets are highly correlated with each other, reducing the benefits of diversification.

Clustering-based preselection addresses this by:
1. Taking a larger shortlist of top-ranked candidates (e.g., top 200)
2. Clustering them based on correlation of historical returns
3. Selecting one representative from each cluster to ensure diversity

## Usage

### CLI Arguments

```bash
python scripts/select_assets.py \
    --match-report data/metadata/tradeable_matches.csv \
    --output selected_assets.csv \
    --preselect-clustering hierarchical \
    --shortlist 200 \
    --top-k 50 \
    --linkage-method ward \
    --data-dir data/stooq
```

**Arguments:**

- `--preselect-clustering {none,hierarchical}`: Clustering method (default: none)
  - `none`: Disable clustering (default behavior)
  - `hierarchical`: Use hierarchical clustering on correlation

- `--shortlist N`: Number of assets to shortlist before clustering (default: 200)

- `--top-k K`: Final number of assets to select after clustering (default: 50)

- `--linkage-method {ward,average,complete,single}`: Hierarchical clustering linkage method (default: ward)
  - `ward`: Minimizes within-cluster variance (recommended)
  - `average`: Uses average linkage
  - `complete`: Uses complete linkage
  - `single`: Uses single linkage

- `--data-dir PATH`: Base directory containing Stooq data files (required when clustering enabled)

### Python API

```python
from pathlib import Path
from portfolio_management.assets.selection import (
    AssetSelector,
    FilterCriteria,
    ClusteringConfig,
    ClusteringMethod,
)

# Create clustering configuration
clustering_config = ClusteringConfig(
    method=ClusteringMethod.HIERARCHICAL,
    shortlist_size=200,
    top_k=50,
    linkage_method="ward",
    min_history_overlap=126,  # Minimum 6 months of overlapping data
)

# Create filter criteria with clustering
criteria = FilterCriteria(
    data_status=["ok"],
    min_history_days=504,  # 2 years
    clustering_config=clustering_config,
)

# Run selection with clustering
selector = AssetSelector()
data_dir = Path("data/stooq")
selected_assets = selector.select_assets(matches_df, criteria, data_dir)
```

## How It Works

### Algorithm

1. **Shortlisting**: After applying all filters, take the top N candidates (shortlist_size)

2. **Load Price Data**: Load historical price data for all shortlisted assets

3. **Calculate Returns**: Compute daily returns from prices

4. **Correlation Matrix**: Calculate pairwise correlation of returns

5. **Distance Matrix**: Convert correlation to distance: `distance = 1 - correlation`
   - Assets with correlation 1.0 have distance 0.0 (identical)
   - Assets with correlation -1.0 have distance 2.0 (opposite)

6. **Hierarchical Clustering**: Perform agglomerative clustering using specified linkage method

7. **Cluster Representatives**: Select one asset from each of K clusters
   - Within each cluster, choose the asset with lowest average correlation to other cluster members
   - Use deterministic tie-breaking (alphabetically sorted symbols)

8. **Return**: Output K diverse assets

### Linkage Methods

**Ward** (recommended): Minimizes the variance within clusters. Tends to create compact, spherical clusters.

**Average**: Uses the average distance between all pairs of points in different clusters. Balanced approach.

**Complete**: Uses the maximum distance between points in different clusters. Creates compact clusters.

**Single**: Uses the minimum distance between points in different clusters. Can create elongated clusters.

## Benefits

✅ **Reduced Correlation**: Selected assets have lower average pairwise correlation than naive top-K

✅ **Better Diversification**: Representatives from different correlation groups

✅ **Deterministic**: Same input always produces same output (alphabetical tie-breaking)

✅ **Backward Compatible**: Default behavior unchanged (clustering disabled)

✅ **No New Dependencies**: Uses scipy which is already in requirements.txt

## Validation

The implementation includes comprehensive tests that verify:

- Configuration validation
- Price data loading from multiple formats
- Returns calculation and correlation matrix
- Hierarchical clustering with different linkage methods
- Correlation reduction vs naive top-K selection
- Integration with AssetSelector pipeline

### Example Test Result

On synthetic test data with 10 assets grouped into 3 correlation clusters:
- Naive top-5 selection: average correlation ~0.65
- Clustering-based selection: average correlation ~0.35

**Reduction: ~46% lower correlation**

## Limitations

1. **Requires Historical Data**: Needs sufficient overlapping price history (default: 126 days minimum)

2. **Not Guaranteed Optimal**: Greedy approach may not find globally optimal diversification

3. **Computational Cost**: O(N²) for correlation matrix, O(N² log N) for clustering
   - Reasonable for N < 1000
   - For larger universes, consider two-stage clustering

4. **Streaming Mode**: Clustering is not supported in streaming mode (--chunk-size)
   - Clustering will be automatically disabled with a warning

5. **Market Regime Changes**: Historical correlation may not reflect future behavior

## Configuration Best Practices

**Conservative (Small Universe)**:
```bash
--shortlist 100 --top-k 30 --linkage-method ward
```

**Moderate (Medium Universe)**:
```bash
--shortlist 200 --top-k 50 --linkage-method ward
```

**Aggressive (Large Universe)**:
```bash
--shortlist 500 --top-k 100 --linkage-method average
```

**Guidelines**:
- Shortlist should be 3-5x larger than top_k
- Ward linkage works well for most cases
- Increase min_history_overlap for more stable correlations
- Decrease min_history_overlap if many assets have sparse data

## Error Handling

The implementation gracefully handles edge cases:

- **Insufficient Data**: If < top_k assets have sufficient overlapping data, returns available assets without clustering
- **Missing Price Files**: Assets with missing price data are excluded; clustering proceeds with remaining assets
- **Data Loading Errors**: Individual file errors don't stop the entire process
- **Empty Results**: If no price data can be loaded, returns original selection without clustering

## Future Enhancements

Potential improvements for future versions:

1. **Alternative Clustering**: Support k-medoids (requires scikit-learn)
2. **Custom Distance Metrics**: Allow tail correlation or other distance measures
3. **Dynamic K**: Automatically determine optimal number of clusters
4. **Multi-Objective**: Incorporate both correlation and other factors (volatility, liquidity)
5. **Incremental Clustering**: Support for very large universes via sampling

## References

- Ward, J. H. (1963). "Hierarchical Grouping to Optimize an Objective Function". Journal of the American Statistical Association.
- Müllner, D. (2013). "fastcluster: Fast Hierarchical, Agglomerative Clustering Routines for R and Python".
- scipy.cluster.hierarchy documentation: https://docs.scipy.org/doc/scipy/reference/cluster.hierarchy.html
