# Re-runnability
# Pipeline Automation and Reproducibility
# This script automates the entire CBK inflation data ingestion pipeline.
# It runs data extraction, transformation, Docker import, and database verification.
# It automatically executes the complete pipeline twice when Run is clicked in PyCharm.
# Both runs use the same saved CBK webpage and the same SQLite database.
# The second run verifies that no duplicate records or unexpected changes occur.


# INPUT FILES:
# - data/source/cbk_inflation_YYYY-MM-DD.html : Saved source webpage.
# - env.list : Docker configuration and Data Commons API key.


# OUTPUT FOLDERS:
# - data/ : Contains extracted source data.
# - data/transformed_data/ : Contains generated Data Commons input files.
# - data/transformed_data/datacommons/ : Contains the imported SQLite database.
# - docs/ : Contains verification and reproducibility reports.

# OUTPUT FILES:
# - data/cbk_inflation_extracted.csv : Extracted inflation records.
# - data/duplicate_rows.csv : Duplicate source records when detected.
# - data/transformed_data/observations.csv : Formatted inflation observations.
# - data/transformed_data/config.json : Data Commons import configuration.
# - data/transformed_data/variables.mcf : Statistical variable definitions.
# - data/transformed_data/transformation_report.json : Transformation summary.
# - data/transformed_data/datacommons/datacommons.db : SQLite database.
# - data/transformed_data/load.log : Docker import execution log.
# - docs/readback_report.md : Data verification report.
# - docs/reproducibility_report.md : Two-run reproducibility test results.


# EXPECTED OUTPUT:
# - First run: 282 observations, 0 duplicates, 0 differences.
# - Second run: 282 observations, 0 duplicates, 0 differences.
# - The second run does not delete or recreate the existing database.
# - Displays REPRODUCIBILITY TEST: PASS when both runs succeed.


# EXECUTION:
# - Click Run in PyCharm or execute: python run_pipeline.py
# - Requires Docker Desktop running and a valid Data Commons API key.

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import re
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import fetch_cbk
import transform

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
OUTPUT = DATA / "transformed_data"
DATABASE = OUTPUT / "datacommons" / "datacommons.db"
LOG = OUTPUT / "load.log"
ENV = ROOT / "env.list"
REPORT = ROOT / "docs" / "reproducibility_report.md"
DOCKER_IMAGE = "gcr.io/datcom-ci/datacommons-data:stable"


def source_snapshot() -> Path:
    snapshots = sorted((DATA / "source").glob("cbk_inflation_*.html"))
    if snapshots:
        saved = snapshots[-1]
        print(f"Using saved source snapshot: {saved.name}", flush=True)
        return saved
    print("No snapshot found: downloading CBK webpage...", flush=True)
    return fetch_cbk.download_source()


def importer() -> None:
    if not ENV.is_file():
        raise RuntimeError("env.list is missing. Create it from env.list.example and add your API key.")
    if not shutil.which("docker"):
        raise RuntimeError("Docker command not found. Start Docker Desktop and check PATH.")

    command = [
        "docker", "run", "--rm", "--platform", "linux/amd64",
        "--env-file", str(ENV),
        "--mount", f"type=bind,source={OUTPUT.resolve()},target=/data",
        DOCKER_IMAGE,
    ]
    print("Starting Data Commons Docker import...", flush=True)
    # Redirect stderr to stdout and sanitize each line BEFORE saving to disk.
    with LOG.open("w", encoding="utf-8") as logfile:
        process = subprocess.Popen(
            command,
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
        )
        assert process.stdout is not None
        for line in process.stdout:
            line = re.sub(r"(DC API Key:\s*)\S+", r"\1[REDACTED]", line, flags=re.I)
            line = re.sub(r"(DC_API_KEY=)\S+", r"\1[REDACTED]", line, flags=re.I)
            print(line, end="", flush=True)
            logfile.write(line)
        exit_code = process.wait()
    if exit_code != 0:
        raise RuntimeError(f"Docker importer failed (exit code {exit_code}); see {LOG}")
    if not DATABASE.is_file():
        raise RuntimeError(f"Docker reported success but database is missing: {DATABASE}")


def verify_readback() -> None:
    checked = subprocess.run(
        [sys.executable, str(ROOT / "readback.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    print(checked.stdout, end="")
    if checked.stderr:
        print(checked.stderr, file=sys.stderr, end="")
    if checked.returncode != 0 or "RESULT: PASS" not in checked.stdout:
        raise RuntimeError("Readback verification FAILED. See docs/readback_report.md")


def fingerprint() -> dict[str, str | int]:
    """Compare rows and values, not the SQLite file's volatile metadata."""
    var_ids = tuple(transform.VARIABLES.values())
    with sqlite3.connect(f"file:{DATABASE.as_posix()}?mode=ro", uri=True) as db:
        rows = db.execute(
            "SELECT entity, variable, date, value, unit FROM observations "
            "WHERE entity = ? AND variable IN (?, ?) "
            "ORDER BY entity, variable, date, value, unit",
            (transform.ENTITY, *var_ids),
        ).fetchall()
    keys = [(row[0], row[1], row[2]) for row in rows]
    return {
        "rows": len(rows),
        "unique_observation_keys": len(set(keys)),
        "duplicate_observation_keys": len(rows) - len(set(keys)),
        "data_sha256": hashlib.sha256(
            json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "observations_csv_sha256": hashlib.sha256((OUTPUT / "observations.csv").read_bytes()).hexdigest(),
    }


def run_once(snapshot: Path, run_index: int) -> dict:
    print(f"\n===== PIPELINE RUN {run_index} =====", flush=True)
    df = fetch_cbk.extract_inflation_table(snapshot)
    df = fetch_cbk.clean_data(df)
    fetch_cbk.export_csv(df)
    summary = transform.generate()
    importer()
    verify_readback()
    state = fingerprint()
    expected = summary["observation_rows"]
    if state["rows"] != expected or state["unique_observation_keys"] != expected:
        raise RuntimeError(
            "Observation row count or unique-key count did not match the source: "
            f"expected {expected}, got {state['rows']} rows / "
            f"{state['unique_observation_keys']} unique keys"
        )
    if state["duplicate_observation_keys"]:
        raise RuntimeError(f"Database has {state['duplicate_observation_keys']} duplicate observation keys")
    print(
        f"PASS: {state['rows']} observations, "
        f"{state['duplicate_observation_keys']} duplicates, 0 differences.",
        flush=True,
    )
    return state


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--from-scratch", action="store_true",
        help="Back up the existing SQLite DB and create a new one on the first run",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--once", action="store_true",
        help="Only run once (for debugging); default is to run twice automatically",
    )
    mode.add_argument(
        "--verify-twice", action="store_true",
        help="Backward-compatible option; running twice is now the default",
    )
    args = parser.parse_args()
    snapshot = source_snapshot()
    if args.from_scratch and DATABASE.exists():
        backup_name = "datacommons-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f") + ".backup.db"
        backup_path = DATABASE.with_name(backup_name)
        DATABASE.rename(backup_path)
        print(f"Backed up previous database to: {backup_path}", flush=True)
    first = run_once(snapshot, 1)
    if not args.once:
        print("\nFirst run passed. Starting the second run automatically...", flush=True)
        second = run_once(snapshot, 2)
        if first != second:
            raise RuntimeError(f"Re-run changed observation data! Run 1: {first}; Run 2: {second}")
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(
            "# Pipeline reproducibility and idempotence check\n\n"
            f"Source snapshot: `{snapshot.relative_to(ROOT)}`\n\n"
            "The same archived source was processed and imported twice against the **same SQLite database** "
            "without deleting it between runs. The generated observations and loaded rows were compared.\n\n"
            f"- First run: {first['rows']} database rows; {first['duplicate_observation_keys']} duplicate keys; readback PASS\n"
            f"- Second run: {second['rows']} database rows; {second['duplicate_observation_keys']} duplicate keys; readback PASS\n"
            f"- Loaded data checksum identical: `{first['data_sha256']}`\n"
            f"- Generated CSV checksum identical: `{first['observations_csv_sha256']}`\n"
            "- Result: **PASS — no duplicates added on the second run.**\n",
            encoding="utf-8",
        )
        print(f"\nREPRODUCIBILITY TEST: PASS\nReport: {REPORT}")
    else:
        print("\nPIPELINE: PASS (single-run mode). The second-run check was skipped.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, RuntimeError, ValueError, sqlite3.Error) as exc:
        print(f"\nPIPELINE: FAIL — {exc}", file=sys.stderr)
        sys.exit(1)
