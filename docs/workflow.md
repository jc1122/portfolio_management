# Project Workflow Guide

## 📊 Complete System Documentation

**For comprehensive workflow documentation with complete Mermaid diagrams**, see:

- **[Complete Workflow Documentation](architecture/COMPLETE_WORKFLOW.md)** - Detailed Mermaid diagram covering all functionality from CSV ingestion through visualization, including all advanced features, data flows, and integration points.

This guide provides a simplified overview of the two primary workflows.

______________________________________________________________________

## Overview

This document outlines the two primary ways to use the portfolio management toolkit: the **Managed Workflow** and the **Manual Workflow**.

The **Managed Workflow** is the recommended approach for repeatable, consistent analysis. It uses the `config/universes.yaml` file as a central blueprint and the `scripts/manage_universes.py` script to orchestrate the data pipeline.

The **Manual Workflow** involves running each script individually and is best suited for debugging and experimentation.

______________________________________________________________________

## The Managed Workflow (Recommended)

This workflow is designed for efficiency and repeatability.

### Phase 1: One-Time Setup

These steps only need to be performed once, or whenever your raw data sources change.

- **Step 1: Prepare Raw Data**

  - **Action**: Run the `scripts/prepare_tradeable_data.py` script.
  - **Purpose**: To scan all your raw price data and generate the master list of all possible assets the system can work with (`tradeable_matches.csv`).
  - **Documentation**: `[Details](./data_preparation.md)`

- **Step 2: Define Your Universes**

  - **Action**: Manually edit the `config/universes.yaml` file.
  - **Purpose**: To define the rules and parameters for your investment strategies (universes).
  - **Documentation**: `[Details](./universes.md)`

### Phase 2: Universe-Driven Pipeline

These steps are performed whenever you want to generate data for a universe or run a backtest.

- **Step 3: Generate Universe Data**

  - **Action**: Run `python scripts/manage_universes.py load <your_universe_name>`.
  - **Purpose**: This single command reads your YAML file and automatically runs the asset selection, classification, and return calculation steps for you, saving the final returns data to a CSV file.
  - **Documentation**: `[Details](./manage_universes.md)`

- **Step 4: Construct Portfolio**

  - **Action**: Run the `scripts/construct_portfolio.py` script.
  - **Purpose**: To take the returns data from the previous step and apply a financial strategy (e.g., Mean-Variance, Risk Parity) to determine the optimal asset weights.
  - **Documentation**: `[Details](./portfolio_construction.md)`

- **Step 5: Run Backtest**

  - **Action**: Run the `scripts/run_backtest.py` script.
  - **Purpose**: To simulate the historical performance of your chosen strategy on the universe you prepared, generating a full set of analytics and reports.
  - **Documentation**: `[Details](./backtesting.md)`

______________________________________________________________________

## Manual (Ad-Hoc) Workflow

For debugging, testing, or one-off experiments, you can run the full suite of scripts individually in sequence. In this workflow, you provide all configuration via command-line arguments and pass the output file from one script as the input to the next.

The sequence is as follows:

1. **Data Preparation**: `scripts/prepare_tradeable_data.py` ([Details](./data_preparation.md))
1. **Asset Selection**: `scripts/select_assets.py` ([Details](./asset_selection.md))
1. **Asset Classification**: `scripts/classify_assets.py` ([Details](./asset_classification.md))
1. **Return Calculation**: `scripts/calculate_returns.py` ([Details](./calculate_returns.md))
1. **Portfolio Construction**: `scripts/construct_portfolio.py` ([Details](./portfolio_construction.md))
1. **Backtesting**: `scripts/run_backtest.py` ([Details](./backtesting.md))

While this approach offers maximum flexibility, it is not recommended for regular use as it can be tedious and error-prone.
