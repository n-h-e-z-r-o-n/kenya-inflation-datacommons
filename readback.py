


# Data Readback Verification

# This script verifies that the inflation data loaded into Data Commons matches the original CBK data.
# It reads the original extracted CSV, transformed observations CSV, and SQLite database.
# It compares the number of records at each stage of the pipeline.
# It checks that all imported inflation values match the original source data.
# It detects missing observations, duplicate records, and incorrect values.
# It reports any differences found between the source and the database.
# It generates readback_report.md documenting the verification results.
# It displays PASS when all observations match and FAIL when differences are detected.
# It ensures data accuracy and integrity after the Data Commons import.
# The script reads your original CSV, the transformed CSV, and the actual SQLite database, then compares every inflation value.
# The script automatically generates: docs/readback_report.md


# INPUT FILES:
# - data/cbk_inflation_extracted.csv : Original extracted inflation data.
# - data/transformed_data/observations.csv : Transformed observations.
# - data/transformed_data/datacommons/datacommons.db : Imported SQLite database.

# OUTPUT FOLDER:
# - docs/ : Stores the generated verification report.

# OUTPUT FILE:
# - docs/readback_report.md : Detailed comparison and verification results.

# EXPECTED OUTPUT:
# - 142 original source rows and 141 unique months.
# - 282 generated observations and 282 loaded database observations.
# - Zero duplicate database observations.
# - Zero differences between the source and imported values.
# - Displays RESULT: PASS when all verification checks succeed.

from __future__ import annotations

import argparse
import calendar
import csv
import sqlite3
import sys
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE_DEFAULT = ROOT / "data" / "cbk_inflation_extracted.csv"
CSV_DEFAULT = ROOT / "data" / "transformed_data" / "observations.csv"
DB_DEFAULT = ROOT / "data" / "transformed_data" / "datacommons" / "datacommons.db"
REPORT_DEFAULT = ROOT / "docs" / "readback_report.md"

ENTITY = "country/KEN"
VARIABLES = {
    "Annual Average Inflation": "cbk/AnnualAverageInflationRate",
    "12-Month Inflation": "cbk/TwelveMonthInflationRate",
}
MONTHS = {name.lower(): i for i, name in enumerate(calendar.month_name) if name}
MONTHS.update({name.lower(): i for i, name in enumerate(calendar.month_abbr) if name})
MONTHS["sept"] = 9
MISSING = {"", "-", "n/a", "na", "null", "none", "nan", ".."}


def number(value, context):
    text = "" if value is None else str(value).strip()
    if text.lower() in MISSING:
        return None
    try:
        parsed = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"{context}: not a number: {text!r}") from exc
    if not parsed.is_finite():
        raise ValueError(f"{context}: non-finite number: {text!r}")
    return parsed


def source_expectations(path):
    if not path.is_file():
        raise FileNotFoundError(f"Source CSV not found: {path}")
    by_month = {}
    duplicates = []
    source_rows = 0
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        needed = {"Year", "Month", *VARIABLES}
        if not needed.issubset(reader.fieldnames or []):
            raise ValueError(f"Source CSV must contain columns: {sorted(needed)}")
        for line, row in enumerate(reader, start=2):
            source_rows += 1
            try:
                year = int(row["Year"].strip())
                month = MONTHS[row["Month"].strip().lower().rstrip(".")]
            except (ValueError, KeyError, AttributeError) as exc:
                raise ValueError(f"Invalid year/month at source CSV line {line}") from exc
            if year < 2015:
                raise ValueError(f"Source line {line}: year earlier than 2015")
            date = f"{year:04d}-{month:02d}"
            if "date" in row and row["date"] and row["date"].strip() != date:
                raise ValueError(f"Source line {line}: date disagrees with year/month")
            values = {col: number(row[col], f"Source line {line}, {col}") for col in VARIABLES}
            if date in by_month:
                if by_month[date] != values:
                    raise ValueError(f"Conflicting source entries for {date}; resolve against saved HTML")
                duplicates.append(date)
            else:
                by_month[date] = values

    expected = {}
    for date, values in by_month.items():
        for source_col, variable_id in VARIABLES.items():
            if values[source_col] is not None:  # preserve missing values: do not create zeroes
                expected[(ENTITY, variable_id, date)] = values[source_col]
    return source_rows, by_month, expected, duplicates


def read_transformed(path):
    if not path.is_file():
        raise FileNotFoundError(f"Observations CSV not found: {path}")
    results = defaultdict(list)
    row_count = 0
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if not {"entity", "variable", "date", "value", "unit"}.issubset(reader.fieldnames or []):
            raise ValueError("observations.csv requires entity, variable, date, value, unit")
        for line, row in enumerate(reader, start=2):
            row_count += 1
            key = tuple((row[f] or "").strip() for f in ("entity", "variable", "date"))
            value = number(row["value"], f"Observations CSV line {line}")
            results[key].append((value, (row["unit"] or "").strip()))
    return row_count, results


def read_database(path):
    if not path.is_file():
        raise FileNotFoundError(f"Data Commons database not found: {path}")
    results = defaultdict(list)
    with sqlite3.connect(str(path)) as connection:
        connection.execute("PRAGMA query_only = ON")
        names = [row[1] for row in connection.execute("PRAGMA table_info(observations)")]
        if not names:
            raise ValueError("The database has no 'observations' table")
        columns = {name.lower(): name for name in names}
        fields = ("entity", "variable", "date", "value")
        if not all(field in columns for field in fields):
            raise ValueError(f"Unexpected observations table columns: {names}. Share this list to adapt the script.")
        identifiers = [f'"{columns[field].replace(chr(34), chr(34) + chr(34))}"' for field in fields]
        query = (f"SELECT {', '.join(identifiers)} FROM observations "
                 f"WHERE {identifiers[0]} = ? AND {identifiers[1]} IN (?, ?)")
        rows = connection.execute(query, (ENTITY, *VARIABLES.values())).fetchall()
        total_rows = connection.execute("SELECT COUNT(*) FROM observations").fetchone()[0]
        for entity, variable, date, value in rows:
            results[(str(entity), str(variable), str(date))].append(
                number(value, f"SQLite observation {entity}/{variable}/{date}")
            )
    return total_rows, len(rows), results, names


def compare(expected, observed, stage, with_units=False):
    issues = []
    for key in sorted(set(expected) | set(observed)):
        entity, variable, date = key
        label = f"{date}, {variable}, {entity}"
        if key not in expected:
            issues.append(f"{stage}: unexpected observation {label} (not present in source)")
            continue
        if key not in observed:
            issues.append(f"{stage}: missing observation {label} (expected {expected[key]})")
            continue
        entries = observed[key]
        if len(entries) != 1:
            issues.append(f"{stage}: {len(entries)} copies of {label} (expected exactly one)")
        for entry in entries:
            value = entry[0] if with_units else entry
            if value is None or value != expected[key]:
                issues.append(f"{stage}: {label}, expected {expected[key]}, got {value} (value mismatch)")
            if with_units and entry[1] != "Percent":
                issues.append(f"{stage}: {label}, expected unit Percent, got {entry[1]!r} (unit mismatch)")
    return issues


def create_report(source_rows, months, expected, duplicates, csv_count,
                  db_all_count, db_count, db_schema, issues, report_path, paths):
    report_path.parent.mkdir(parents=True, exist_ok=True)
    month_list = sorted(months)
    lines = [
        "# Data Commons readback verification",
        "",
        "## Input files",
        f"- Saved-source extraction: `{paths[0]}`",
        f"- Loader observations CSV: `{paths[1]}`",
        f"- Actual SQLite readback: `{paths[2]}`",
        "",
        "## Row counts",
        f"- Source CSV rows: **{source_rows}**",
        f"- Distinct source months: **{len(months)}** ({month_list[0]} to {month_list[-1]})",
        f"- Expected nonmissing observations from source: **{len(expected)}**",
        f"- Generated observations.csv rows: **{csv_count}**",
        f"- Loaded SQLite observations for Kenya and these two variables: **{db_count}**",
        f"- All SQLite observations, including any other datasets: **{db_all_count}**",
        f"- SQLite observations table columns: `{', '.join(db_schema)}`",
        "",
        "## Duplicate handling",
        f"- Identical source rows ignored by date: **{len(duplicates)}**",
        *([f"- {date}: the two original source entries had identical values; one month was retained." for date in duplicates]
          or ["- No repeated source dates detected."]),
        "",
        "## Verification method",
        "- Independently reconstruct expected rows from the saved source extraction.",
        "- Compare by entity, statistical variable, month, and numeric value against both generated CSV and SQLite.",
        "- Require a single observation per key; check the CSV unit equals `Percent`.",
        "- Missing source values are omitted, never changed to zero.",
        "- SQLite's observations table stores numeric values; per-row units/facet metadata are not independently verified by this script.",
        "",
        f"## Result: **{'PASS' if not issues else 'FAIL'}**",
        f"- Differences detected: **{len(issues)}**",
    ]
    if issues:
        lines += ["", "## Differences (each with explanation)", *[f"- {issue}" for issue in issues]]
    else:
        lines += ["", "Every expected numeric observation matched the transformed CSV and loaded database; there were no missing, extra, or repeated dataset observations."]
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE_DEFAULT)
    parser.add_argument("--csv", type=Path, default=CSV_DEFAULT)
    parser.add_argument("--db", type=Path, default=DB_DEFAULT)
    parser.add_argument("--report", type=Path, default=REPORT_DEFAULT)
    args = parser.parse_args()
    source_rows, months, expected, duplicates = source_expectations(args.source)
    csv_count, generated = read_transformed(args.csv)
    db_all_count, db_count, loaded, schema = read_database(args.db)
    issues = compare(expected, generated, "Generated CSV", with_units=True)
    issues.extend(compare(expected, loaded, "SQLite database"))
    create_report(source_rows, months, expected, duplicates, csv_count,
                  db_all_count, db_count, schema, issues, args.report,
                  (args.source, args.csv, args.db))
    print(f"Source: {source_rows} rows; {len(months)} unique months; {len(duplicates)} identical duplicates")
    print(f"Expected observations: {len(expected)}")
    print(f"Generated CSV observations: {csv_count}")
    print(f"Loaded SQLite observations: {db_count}")
    print(f"Differences: {len(issues)}")
    print(f"Report: {args.report}")
    print("RESULT:", "PASS" if not issues else "FAIL")
    return 0 if not issues else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, sqlite3.Error, ValueError) as exc:
        print(f"Readback check could not complete: {exc}", file=sys.stderr)
        sys.exit(1)
