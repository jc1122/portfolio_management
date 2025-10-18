import os
import sys

import pandas as pd

# Load the match and unmatched reports
try:
    matches_df = pd.read_csv("data/metadata/tradeable_matches.csv")
    unmatched_df = pd.read_csv("data/metadata/tradeable_unmatched.csv")
except FileNotFoundError:
    sys.exit()

# --- Sample Selection ---
# 150 successful matches
ok_matches = matches_df[matches_df["data_status"] == "ok"].sample(
    n=150, random_state=42,
)

# 150 matches with issues (warnings, errors, etc.)
error_matches = matches_df[matches_df["data_status"] != "ok"].sample(
    n=150, random_state=42,
)

# 100 unmatched instruments
unmatched_sample = unmatched_df.sample(n=100, random_state=42)

# Combine the samples
sampled_matches = pd.concat([ok_matches, error_matches])
all_tradeable_symbols = pd.concat(
    [sampled_matches["symbol"], unmatched_sample["symbol"]],
)

# --- File Path Extraction ---
stooq_files_to_copy = sampled_matches["stooq_path"].dropna().unique()
tradeable_source_files = (
    pd.concat([sampled_matches["source_file"], unmatched_sample["source_file"]])
    .dropna()
    .unique()
)

# --- Generate Copy Script ---
with open("copy_fixtures.sh", "w") as f:
    f.write("#!/bin/bash\n")
    f.write("set -e\n")
    f.write("echo 'Creating fixture directories...\n'")
    f.write("mkdir -p tests/fixtures/stooq\n")
    f.write("mkdir -p tests/fixtures/tradeable_instruments\n")

    # Copy stooq files
    f.write("\necho 'Copying Stooq data files...\n'")
    for file_path in stooq_files_to_copy:
        if file_path and pd.notna(file_path):
            dest_dir = os.path.dirname(f"tests/fixtures/stooq/{file_path}")
            f.write(f"mkdir -p {dest_dir}\n")
            f.write(f"cp data/stooq/{file_path} {dest_dir}/\n")

    # Create subset of tradeable instruments files
    f.write("\necho 'Creating tradeable instrument fixture files...\n'")
    for source_file in tradeable_source_files:
        if source_file and pd.notna(source_file):
            original_df = pd.read_csv(f"tradeable_instruments/{source_file}")
            # Filter rows that are in our sample
            fixture_df = original_df[original_df["symbol"].isin(all_tradeable_symbols)]
            if not fixture_df.empty:
                fixture_df.to_csv(
                    f"tests/fixtures/tradeable_instruments/{source_file}", index=False,
                )

    f.write("\necho 'Fixture creation script finished.'\n")
