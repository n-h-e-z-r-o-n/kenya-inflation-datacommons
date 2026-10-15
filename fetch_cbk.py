# Data Extraction
#
# Central Bank of Kenya url:  https://www.centralbank.go.ke/inflation-rates/
# Instead of manually copying the table, this scripts  downloads it programmatically. This gives us a reproducible record of where the data came from.
# This script downloads monthly inflation data from the Central Bank of Kenya (CBK).
# It saves a dated copy of the original webpage (HTML) for reference and verification.
# It extracts inflation records from January 2015 onwards using BeautifulSoup.
# It organizes the extracted data into a structured format using pandas.
# It checks for duplicate records, missing months, missing values, and invalid data.
# It preserves duplicate records in a separate CSV file for investigation.
# It generates cbk_inflation_extracted.csv containing the extracted inflation data.
# It also saves download metadata, including the source URL, date, and file checksum.
# The extracted CSV is used by transform.py to prepare the data for Data Commons.


# OUTPUT FOLDERS:
# - data/source/ : Stores the original downloaded webpage and its metadata.
# - data/        : Stores the extracted inflation data.


# OUTPUT FILES:
# - data/source/cbk_inflation_YYYY-MM-DD.html : Original downloaded webpage.
# - data/source/cbk_inflation_YYYY-MM-DD.json : Download metadata and file checksum.
# - data/cbk_inflation_extracted.csv : Extracted inflation dataset.
# - data/duplicate_rows.csv : Duplicate records (created only when duplicates exist).


# EXPECTED OUTPUT:
# - 142 source records, including the identical April 2019 duplicate.
# - No missing months or inflation values in the current source snapshot.
# - The extracted CSV is passed to transform.py for further processing.

import calendar
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup


# ============================================================
# CONFIGURATION
# ============================================================

SOURCE_URL = "https://www.centralbank.go.ke/inflation-rates/"
START_YEAR = 2015

BASE_DIR = Path(__file__).resolve().parent
SOURCE_DIR = BASE_DIR / "data/source"
OUTPUT_DIR = BASE_DIR / "data"

SOURCE_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DOWNLOAD_DATE = datetime.now(timezone.utc).strftime("%Y-%m-%d")

HTML_FILE = SOURCE_DIR / f"cbk_inflation_{DOWNLOAD_DATE}.html"
METADATA_FILE = SOURCE_DIR / f"cbk_inflation_{DOWNLOAD_DATE}.json"
CSV_FILE = OUTPUT_DIR / "cbk_inflation_extracted.csv"

COLUMNS = [
    "Year",
    "Month",
    "Annual Average Inflation",
    "12-Month Inflation"
]

MONTHS = {
    name.lower(): index
    for index, name in enumerate(calendar.month_name)
    if name
}

MONTHS.update({
    name.lower(): index
    for index, name in enumerate(calendar.month_abbr)
    if name
})

MONTHS["sept"] = 9

MISSING_VALUES = {"", "-", "n/a", "na", "null", "none", ".."}


# ============================================================
# STEP 1: DOWNLOAD ORIGINAL SOURCE
# ============================================================

def download_source():
    if HTML_FILE.exists():
        print("Existing dated source found.")
        print("Preserving original downloaded copy.")
        return HTML_FILE

    print("Downloading CBK inflation data...")

    response = requests.get(
        SOURCE_URL,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "text/html",
            "Accept-Language": "en-US,en;q=0.9"
        },
        timeout=60
    )

    response.raise_for_status()

    if "inflation" not in response.text.lower():
        raise ValueError(
            "Downloaded page does not appear to contain "
            "CBK inflation information."
        )

    HTML_FILE.write_bytes(response.content)

    metadata = {
        "source": "Central Bank of Kenya",
        "source_url": SOURCE_URL,
        "downloaded_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "filename": HTML_FILE.name,
        "sha256": hashlib.sha256(
            response.content
        ).hexdigest(),
        "http_status": response.status_code,
        "content_type": response.headers.get(
            "Content-Type", ""
        )
    }

    METADATA_FILE.write_text(
        json.dumps(metadata, indent=4),
        encoding="utf-8"
    )

    print(f"Source saved: {HTML_FILE}")
    print(f"Metadata saved: {METADATA_FILE}")

    return HTML_FILE


# ============================================================
# STEP 2: EXTRACT HTML TABLE
# ============================================================

def extract_inflation_table(html_path):
    print("\nExtracting inflation table...")

    html = html_path.read_text(
        encoding="utf-8",
        errors="replace"
    )

    soup = BeautifulSoup(html, "lxml")

    tables = soup.find_all("table")
    rows = soup.find_all("tr")

    print(f"HTML tables found: {len(tables)}")
    print(f"HTML rows found: {len(rows)}")

    records = []

    for row in rows:
        cells = row.find_all(
            ["td", "th"],
            recursive=False
        )

        if len(cells) != 4:
            continue

        values = [
            cell.get_text(" ", strip=True)
            for cell in cells
        ]

        year_text = values[0].strip()
        month_text = values[1].strip()

        # Skip header rows or unrelated tables
        if not re.fullmatch(r"\d{4}", year_text):
            continue

        month_key = month_text.lower().rstrip(".")

        if month_key not in MONTHS:
            continue

        year = int(year_text)

        if year < START_YEAR:
            continue

        # Normalize month names
        month_number = MONTHS[month_key]
        month_name = calendar.month_name[month_number]

        records.append([
            year,
            month_name,
            values[2].strip(),
            values[3].strip()
        ])

    if not records:
        raise ValueError(
            "No matching inflation observations were found "
            "in the saved HTML file. The website may load "
            "its table using JavaScript or AJAX. "
            f"Inspect the original file: {html_path}"
        )

    df = pd.DataFrame(records, columns=COLUMNS)

    print(f"Extracted observations: {len(df)}")

    return df


# ============================================================
# STEP 3: VALIDATE AND CLEAN DATA
# ============================================================

def clean_data(df):
    print("\nValidating observations...")

    df = df.copy()

    df["Year"] = df["Year"].astype(int)

    for column in COLUMNS[2:]:

        # Preserve missing values as null
        text_values = df[column].astype("string").str.strip()

        missing = text_values.str.lower().isin(MISSING_VALUES)
        text_values = text_values.mask(missing)

        # Reject invalid numeric values
        numeric = pd.to_numeric(
            text_values,
            errors="coerce"
        )

        invalid = text_values.notna() & numeric.isna()

        if invalid.any():
            bad_rows = df.loc[
                invalid,
                ["Year", "Month", column]
            ]

            raise ValueError(
                f"Invalid numeric values in {column}:\n"
                f"{bad_rows.to_string(index=False)}"
            )

        df[column] = numeric

    # Create a normalized monthly date
    df["month_number"] = df["Month"].map(
        lambda name: MONTHS[name.lower()]
    )

    df["date"] = (
        df["Year"].astype(str)
        + "-"
        + df["month_number"].astype(str).str.zfill(2)
    )

    # Identify duplicate observations
    duplicates = df[
        df.duplicated(subset=["date"], keep=False)
    ]

    print(f"Duplicate observation rows: {len(duplicates)}")

    if not duplicates.empty:
        print("\nDuplicate observations detected:")
        print(
            duplicates[
                COLUMNS + ["date"]
            ].to_string(index=False)
        )

        duplicate_file = OUTPUT_DIR / "duplicate_rows.csv"

        duplicates[
            COLUMNS + ["date"]
        ].to_csv(
            duplicate_file,
            index=False
        )

        print(f"Duplicate report: {duplicate_file}")

    # Check missing inflation values
    for column in COLUMNS[2:]:
        missing_count = df[column].isna().sum()
        print(f"Missing {column}: {missing_count}")

    # Check missing months
    available_dates = set(df["date"])

    last_date = df["date"].max()

    expected_dates = pd.period_range(
        start=f"{START_YEAR}-01",
        end=last_date,
        freq="M"
    ).astype(str)

    missing_months = sorted(
        set(expected_dates) - available_dates
    )

    print(f"Missing months: {len(missing_months)}")

    if missing_months:
        print("Missing month list:")
        for month in missing_months:
            print(f"  {month}")

    # Sort observations chronologically
    df = df.sort_values(
        by=["Year", "month_number"],
        kind="stable"
    ).reset_index(drop=True)

    return df


# ============================================================
# STEP 4: EXPORT EXTRACTED DATA
# ============================================================

def export_csv(df):
    print("\nExporting CSV...")

    export_columns = COLUMNS + ["date"]

    df[export_columns].to_csv(
        CSV_FILE,
        index=False,
        encoding="utf-8"
    )

    print(f"CSV saved: {CSV_FILE}")
    print(f"Total exported rows: {len(df)}")


# ============================================================
# STEP 5: DISPLAY DATA SUMMARY
# ============================================================

def print_summary(df):
    print("\n" + "=" * 60)
    print("CBK INFLATION DATA EXTRACTION REPORT")
    print("=" * 60)

    print(f"Source: {SOURCE_URL}")
    print(f"Source snapshot: {HTML_FILE.name}")
    print(f"Start year: {START_YEAR}")
    print(f"Total rows: {len(df)}")
    print(f"Unique months: {df['date'].nunique()}")

    print(
        f"Date coverage: "
        f"{df['date'].min()} to {df['date'].max()}"
    )

    print("\nFirst five observations:")
    print(
        df[COLUMNS + ["date"]]
        .head()
        .to_string(index=False)
    )

    print("\nLast five observations:")
    print(
        df[COLUMNS + ["date"]]
        .tail()
        .to_string(index=False)
    )

    print("\n" + "=" * 60)
    print("EXTRACTION COMPLETED SUCCESSFULLY")
    print("=" * 60)


# ============================================================
# MAIN ENTRY POINT
# ============================================================

def main():
    print("=" * 60)
    print("KENYA INFLATION DATA PIPELINE")
    print("Central Bank of Kenya -> Data Commons")
    print("=" * 60)

    source_file = download_source()

    df = extract_inflation_table(source_file)

    df = clean_data(df)

    export_csv(df)

    print_summary(df)


if __name__ == "__main__":
    main()
