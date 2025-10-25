"""Fast unit tests for asset selection logic using mocks."""

import pytest
import pandas as pd
from portfolio_management.assets.selection.selection import AssetSelector, FilterCriteria, SelectedAsset


def create_mock_matches_df(data):
    """Helper to create a valid DataFrame for AssetSelector tests."""
    base_data = {
        'symbol': 'DEFAULT.US', 'isin': 'US0000000000', 'name': 'Default Asset',
        'market': 'US', 'region': 'North America', 'currency': 'USD', 'category': 'Stock',
        'price_start': '2010-01-01', 'price_end': '2023-12-31', 'price_rows': 3522,
        'data_status': 'ok', 'data_flags': '', 'stooq_path': 'path/default.us.txt',
        'resolved_currency': 'USD', 'currency_status': 'matched'
    }

    records = []
    for item in data:
        record = base_data.copy()
        record.update(item)
        records.append(record)

    return pd.DataFrame(records)


@pytest.mark.unit
def test_price_rows_filter_logic():
    """Test filtering based on the minimum number of price rows."""
    selector = AssetSelector()

    # Asset with enough rows vs. not enough
    mock_df = create_mock_matches_df([
        {'symbol': 'GOOD.US', 'price_rows': 200},
        {'symbol': 'BAD.US', 'price_rows': 100},
    ])

    criteria = FilterCriteria(min_price_rows=150, min_history_days=1)

    selected_assets = selector.select_assets(mock_df, criteria)

    assert len(selected_assets) == 1
    assert selected_assets[0].symbol == 'GOOD.US'


@pytest.mark.unit
def test_history_days_filter_logic():
    """Test filtering based on the minimum number of history days."""
    selector = AssetSelector()

    mock_df = create_mock_matches_df([
        {'symbol': 'LONG_HISTORY.US', 'price_start': '2020-01-01', 'price_end': '2022-01-01'}, # > 365 days
        {'symbol': 'SHORT_HISTORY.US', 'price_start': '2022-01-01', 'price_end': '2022-06-01'}, # < 365 days
    ])

    criteria = FilterCriteria(min_history_days=365, min_price_rows=1)

    selected_assets = selector.select_assets(mock_df, criteria)

    assert len(selected_assets) == 1
    assert selected_assets[0].symbol == 'LONG_HISTORY.US'


@pytest.mark.unit
def test_market_filter_logic():
    """Test filtering based on market codes."""
    selector = AssetSelector()

    mock_df = create_mock_matches_df([
        {'symbol': 'US_ASSET', 'market': 'US'},
        {'symbol': 'UK_ASSET', 'market': 'UK'},
        {'symbol': 'DE_ASSET', 'market': 'DE'},
    ])

    # Filter to only include US and UK markets
    criteria = FilterCriteria(markets=['US', 'UK'], min_price_rows=1, min_history_days=1)

    selected_assets = selector.select_assets(mock_df, criteria)
    selected_symbols = {asset.symbol for asset in selected_assets}

    assert len(selected_assets) == 2
    assert 'US_ASSET' in selected_symbols
    assert 'UK_ASSET' in selected_symbols
    assert 'DE_ASSET' not in selected_symbols
