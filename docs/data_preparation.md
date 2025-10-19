# Data Preparation Script: `prepare_tradeable_data.py`

## Overview

This script is the first and most critical step in the portfolio management toolkit's data pipeline. Its primary purpose is to bridge the gap between the raw, bulk historical price data provided by Stooq and the specific list of instruments that are tradeable on a user's brokerage platform.

It takes the raw data as input and produces a clean, validated, and matched dataset that is ready for the subsequent stages of asset selection, return calculation, and analysis.

## Important Caveat: Data Adjustments

This toolkit assumes the historical price data it consumes has been **adjusted for corporate actions**. It is the **user's responsibility** to provide adjusted data.

The system does not have a built-in mechanism to detect or adjust for events like:

- **Stock Splits**: A 2-for-1 split in unadjusted data will be misinterpreted as a 50% loss, severely corrupting return calculations.
- **Dividends**: Unadjusted data does not account for dividend payouts, which will understate the total return of an asset.

Before using this toolkit, you must ensure that your data source provides prices that are pre-adjusted for both splits and dividends. Using unadjusted data will lead to inaccurate and unreliable results.

## Prerequisites

Before running the script, ensure you have the following:

1. **Python Environment**: Python 3.10+ with the `pandas` library installed.
1. **Stooq Data**: Raw Stooq data archives must be unpacked into a single root directory (e.g., `data/stooq/`). The script expects the standard Stooq directory structure (e.g., `d_pl_txt/`, `d_us_txt/`).
1. **Tradeable Instruments**: One or more CSV files containing the lists of instruments you can trade. These should be placed in a single directory (e.g., `tradeable_instruments/`).

## Required Data Structures

This section provides more specific detail on the data structures mentioned in the prerequisites.

### 1. Stooq Data Structure

The script is designed to work with the standard file format and directory layout provided by Stooq's bulk data downloads.

#### Directory Structure

You should have a main data directory (e.g., `data/stooq/`) inside which you unpack the Stooq ZIP archives. This will create a folder structure organized by data type and market, for example:

```
data/stooq/
├── d_pl_txt/
│   ├── data/
│   │   ├── daily/
│   │   │   ├── ale_pl.txt
│   │   │   └── cdr_pl.txt
│   │   └── ...
│   └── ...
├── d_us_txt/
│   ├── data/
│   │   ├── daily/
│   │   │   ├── aapl_us.txt
│   │   │   └── msft_us.txt
│   │   └── ...
│   └── ...
└── ...
```

The script recursively scans the entire directory, so the exact sub-folder structure is flexible, but the file naming convention (`ticker_market.txt`) is important.

#### File Format

Each `.txt` file represents a single instrument and is expected to be a CSV with a header and the following columns. The script primarily uses `Date`, `Close`, and `Volume`.

**Example (`aapl_us.txt`):**

```
<TICKER>,<PER>,<DATE>,<TIME>,<OPEN>,<HIGH>,<LOW>,<CLOSE>,<VOL>,<OPENINT>
AAPL.US,D,20231016,0,176.75,179.08,176.51,178.72,52517010,0
AAPL.US,D,20231017,0,176.65,178.42,174.2,177.15,57509245,0
...
```

### 2. Tradeable Instruments CSV Structure

This refers to the CSV file(s) you provide that list the specific assets you can trade at your brokerage. You can have one or multiple files in the directory.

The script expects these CSV files to have a header and specific columns that are used for identification, matching, and classification.

#### Required Columns

While other columns can be present, the following are essential for the script's core functionality:

| Column | Type | Description | Example |
| :--- | :--- | :--- | :--- |
| `symbol` | text | **(Critical)** The ticker or symbol used by your broker. This is the primary field used for matching against Stooq tickers. | `CDR` |
| `isin` | text | The International Securities Identification Number. Used as a stable, unique identifier. | `PLOPTTC00011` |
| `name` | text | The full name of the instrument. | `CD PROJEKT` |
| `market` | text | **(Critical)** The market/exchange code (e.g., WSE, NYSE, LSE). This is used to resolve ambiguity and correctly map symbols. | `WSE` |
| `currency` | text | The currency the instrument is traded in. | `PLN` |

**Example File (`my_tradeable_stocks.csv`):**

```csv
symbol,isin,name,market,currency
CDR,PLOPTTC00011,CD PROJEKT,WSE,PLN
AAPL,US0378331005,APPLE INC,NSQ,USD
MSFT,US5949181045,MICROSOFT CORP,NSQ,USD
```

Having these structures in place allows the script to effectively find the corresponding historical data for each of your tradeable assets and begin the quality analysis process.

## Workflow

The script performs the following sequence of operations:

1. **Index Stooq Files**: It first recursively scans the entire Stooq data directory to build a master index of every available data file. This index is then saved to a CSV file to make subsequent runs much faster.
1. **Load Tradeable Instruments**: It reads and combines all the user-provided CSV files that list the tradeable instruments.
1. **Match Symbols**: This is the core logic. The script iterates through each tradeable instrument and uses a set of heuristics to find its corresponding data file in the Stooq index.
1. **Analyze Data Quality**: For every successful match, it reads the contents of the price file and performs a series of validation checks, flagging common issues like missing data, large gaps, or periods of zero trading volume.
1. **Generate Reports**: It produces two essential CSV reports:
   - A **match report** for all successful matches, including the data quality flags.
   - An **unmatched report** for all failures, including a reason to help with debugging.
1. **Export Prices**: Finally, for every successful match, it exports the clean price history to a new CSV file in a dedicated output directory. This directory of clean price files is the primary output for the rest of the workflow.

## Script Products

The `prepare_tradeable_data.py` script produces four main products, which are a combination of final data outputs and diagnostic reports.

1. **Cleaned Price Histories (Primary Product)**

   - **Location**: The directory specified by `--prices-output` (default: `data/processed/tradeable_prices/`).
   - **Description**: This is the most important output. It's a directory filled with clean CSV files, one for each successfully matched instrument. This collection of validated price data is the foundational dataset used by the `calculate_returns.py` script and the rest of the downstream analysis.

1. **Match Report**

   - **Location**: The file specified by `--match-report` (default: `data/metadata/tradeable_matches.csv`).
   - **Description**: A CSV report listing every instrument that was successfully found and validated. It includes data quality flags and serves as the direct input for the next workflow step, `scripts/select_assets.py`.

1. **Unmatched Report**

   - **Location**: The file specified by `--unmatched-report` (default: `data/metadata/tradeable_unmatched.csv`).
   - **Description**: A diagnostic CSV report that lists every instrument the script failed to match. It includes a reason for each failure, making it an essential tool for identifying missing data or correcting instrument definitions.

1. **Stooq Metadata Index**

   - **Location**: The file specified by `--metadata-output` (default: `data/metadata/stooq_index.csv`).
   - **Description**: This is a cached index of all the raw Stooq data files found. It's an intermediate product used by the script to dramatically speed up subsequent runs, as it avoids re-scanning the entire Stooq directory each time.

## Data Quality Analysis

After an instrument is successfully matched, the script performs a series of validation checks on its price history file. The results are recorded in two columns in the Match Report: `data_flags` and `data_status`.

### Data Flags

The `data_flags` column contains a comma-separated list of any issues found. Possible flags include:

- `EMPTY_FILE`: The source Stooq file was empty or contained no usable data rows.
- `DUPLICATE_DATES`: The time-series contains two or more entries for the same date.
- `NON_POSITIVE_PRICE`: The file contains at least one `Close` price that is zero or negative.
- `ZERO_VOLUME`: The file contains days where the trading volume was zero. This can indicate an illiquid asset.
- `PRICE_GAP`: A large gap (e.g., more than 10 consecutive days) was detected between two data points, which could indicate a period where the asset was not trading.

### Data Status

The `data_status` column provides an overall grade based on the flags that were raised. This allows for easy high-level filtering in the next workflow step.

- `ok`: No significant flags were raised. The data is considered clean and reliable.
- `warning`: One or more non-critical flags were raised (e.g., `ZERO_VOLUME`, `PRICE_GAP`). The data is likely usable but may warrant closer inspection.
- `error`: A critical flag was raised (e.g., `EMPTY_FILE`, `DUPLICATE_DATES`). This indicates a serious problem, and the data is likely unreliable for analysis.

## Usage Example

Here is a typical command to run the script:

```bash
python scripts/prepare_tradeable_data.py \
    --data-dir data/stooq \
    --tradeable-dir tradeable_instruments \
    --metadata-output data/metadata/stooq_index.csv \
    --match-report data/metadata/tradeable_matches.csv \
    --unmatched-report data/metadata/tradeable_unmatched.csv \
    --prices-output data/processed/tradeable_prices \
    --overwrite-prices \
    --force-reindex
```

## Command-Line Arguments

### Input & Output Arguments

- `--data-dir`: **(Required)** The root directory containing the unpacked Stooq data. Default: `data/stooq`.
- `--tradeable-dir`: **(Required)** The directory containing your CSV files of tradeable instruments. Default: `tradeable_instruments`.
- `--metadata-output`: Path to write the Stooq metadata index file. Default: `data/metadata/stooq_index.csv`.
- `--match-report`: Path to write the report of successfully matched instruments. Default: `data/metadata/tradeable_matches.csv`.
- `--unmatched-report`: Path to write the report of unmatched instruments. Default: `data/metadata/tradeable_unmatched.csv`.
- `--prices-output`: The directory where the clean price history CSVs will be saved. Default: `data/processed/tradeable_prices`.

### Configuration Arguments

- `--force-reindex`: If specified, forces a full re-scan of the Stooq data directory, ignoring any existing index file. Use this if you have added new data.
- `--overwrite-prices`: If specified, overwrites any existing price files in the output directory. By default, existing files are skipped.
- `--include-empty-prices`: If specified, the script will still create a CSV file in the output directory even if the source Stooq file has no usable data.
- `--lse-currency-policy`: Determines how to handle currency mismatches for London Stock Exchange assets.
  - `broker` (default): Use the currency specified in the tradeable instrument file.
  - `stooq`: Use the currency inferred from the Stooq data.
  - `strict`: Raise an error if there is a mismatch.
- `--log-level`: Sets the logging verbosity. Choices: `DEBUG`, `INFO`, `WARNING`, `ERROR`. Default: `INFO`.

### Performance Arguments

- `--max-workers`: The maximum number of parallel processes to use for matching and exporting. Defaults to the number of CPU cores minus one.
- `--index-workers`: The number of parallel processes to use for the initial directory indexing. Defaults to the value of `--max-workers`.

## Output Files Explained

This section details the structure of the key files generated by the script.

### 1. Cleaned Price Histories (in `data/processed/tradeable_prices/`)

This directory contains the most important output of the script. Each file is a CSV named after the `stooq_ticker` of the matched asset (e.g., `aapl_us.csv`) and contains the cleaned, validated price history.

**Format**: A standard CSV file with the following columns, ready for time-series analysis.

| Column | Type | Description |
| :--- | :--- | :--- |
| `Date` | date | The trading date (formatted as `YYYY-MM-DD`). |
| `Open` | float | The opening price for the day. |
| `High` | float | The highest price for the day. |
| `Low` | float | The lowest price for the day. |
| `Close` | float | The closing price for the day. |
| `Volume`| integer| The trading volume for the day. |

### 2. Match Report (`tradeable_matches.csv`)

This file lists every instrument that was successfully matched to a Stooq data file. Key columns include:

- `symbol`, `isin`, `name`: Identifiers from your source tradeable instrument file.
- `market`, `region`, `currency`: Categorical information about the asset.
- `stooq_ticker`: The ticker of the matched Stooq file.
- `data_status`: A high-level summary of data quality (`ok`, `warning`, `error`).
- `data_flags`: A comma-separated list of specific data quality issues found (e.g., `ZERO_VOLUME`, `PRICE_GAP`).

### 3. Unmatched Report (`tradeable_unmatched.csv`)

This file is your primary tool for debugging. It lists every instrument that could not be matched. Key columns include:

- `symbol`, `isin`, `name`: Identifiers for the failed instrument.
- `reason`: The reason for the matching failure (e.g., `NO_STOOQ_TICKER_FOUND`).
- `suggestion`: A potential Stooq ticker that might be a close match, if one can be found.

### 4. Stooq Metadata Index (`stooq_index.csv`)

This is an intermediate file created for performance. It acts as a cache, mapping Stooq tickers to their file paths so the script doesn't need to scan the disk on every run.

| Column | Type | Description |
| :--- | :--- | :--- |
| `stooq_ticker` | text | The unique ticker used by Stooq (e.g., `aapl_us`). |
| `path` | text | The absolute file path to the corresponding data file. |
| `market` | text | The market code inferred from the path (e.g., `us`). |
| `filename` | text | The name of the data file (e.g., `aapl_us.txt`). |

## Troubleshooting

- **High Number of Unmatched Instruments**: If you see many unexpected failures in the unmatched report, first check the `reason` and `suggestion` columns. A common cause is that the required Stooq data has not been downloaded and unpacked into the `--data-dir` (e.g., you are trying to match German stocks but the `d_de_txt` directory is missing).
