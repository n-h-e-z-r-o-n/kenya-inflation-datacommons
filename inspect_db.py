
import sqlite3
from pathlib import Path

db_path = Path(
    "data/transformed_data/datacommons/datacommons.db"
)

if not db_path.is_file():
    raise FileNotFoundError(f"Database not found: {db_path}")

with sqlite3.connect(db_path) as conn:
    tables = conn.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        ORDER BY name
    """).fetchall()

    for (table_name,) in tables:
        print(f"\nTABLE: {table_name}")

        columns = conn.execute(
            f"PRAGMA table_info('{table_name}')"
        ).fetchall()

        for column in columns:
            print(f"  {column[1]} ({column[2]})")

    print("\nSAMPLE OBSERVATIONS:")
    rows = conn.execute(
        "SELECT * FROM observations LIMIT 5"
    ).fetchall()

    for row in rows:
        print(row)
