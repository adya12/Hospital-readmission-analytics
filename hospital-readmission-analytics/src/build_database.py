"""
build_database.py
-----------------
Loads the raw source files into a SQLite database (data/hospital.db):

  raw_encounters              <- diabetic_data.csv (101,766 rows, 50 cols)
  map_admission_type          <- parsed from IDs_mapping.csv
  map_discharge_disposition   <- parsed from IDs_mapping.csv
  map_admission_source        <- parsed from IDs_mapping.csv

The IDs_mapping.csv file is awkward: it's actually THREE small lookup tables
stacked in one file, separated by blank lines, each with its own header.
So we can't just read it with one read_csv call - we split it first.
"""

from pathlib import Path
import sqlite3
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
DB = ROOT / "data" / "hospital.db"

# ---------------------------------------------------------------------------
# 1. Parse the stacked mapping file into three separate lookup DataFrames.
# ---------------------------------------------------------------------------
def parse_id_mappings(path: Path) -> dict[str, pd.DataFrame]:
    """Split IDs_mapping.csv on its blank-line separators into 3 lookups."""
    raw_text = path.read_text().replace("\r\n", "\n")
    # Blank rows in this file look like ",\n" (an empty id + empty description).
    # Split the file into chunks wherever we hit such a separator line.
    chunks, current = [], []
    for line in raw_text.split("\n"):
        if line.strip() in ("", ","):       # separator or truly blank line
            if current:
                chunks.append(current)
                current = []
        else:
            current.append(line)
    if current:
        chunks.append(current)

    tables = {}
    for chunk in chunks:
        header = chunk[0].split(",")[0].strip()     # e.g. "admission_type_id"
        # rebuild this chunk as its own little CSV and parse it
        from io import StringIO
        df = pd.read_csv(StringIO("\n".join(chunk)))
        df.columns = [c.strip() for c in df.columns]
        # normalize: id column -> 'id', description -> 'description'
        df = df.rename(columns={header: "id"})
        df["description"] = df["description"].astype(str).str.strip()
        df["id"] = pd.to_numeric(df["id"], errors="coerce")
        df = df.dropna(subset=["id"])
        df["id"] = df["id"].astype(int)
        tables[header] = df[["id", "description"]]
    return tables

mappings = parse_id_mappings(RAW / "IDs_mapping.csv")

# ---------------------------------------------------------------------------
# 2. Load the main encounter file.
# ---------------------------------------------------------------------------
encounters = pd.read_csv(RAW / "diabetic_data.csv")

# ---------------------------------------------------------------------------
# 3. Write everything to SQLite.
# ---------------------------------------------------------------------------
if DB.exists():
    DB.unlink()
conn = sqlite3.connect(DB)
encounters.to_sql("raw_encounters", conn, index=False)
mappings["admission_type_id"].to_sql("map_admission_type", conn, index=False)
mappings["discharge_disposition_id"].to_sql("map_discharge_disposition", conn, index=False)
mappings["admission_source_id"].to_sql("map_admission_source", conn, index=False)
conn.commit()

print("DATABASE BUILT:", DB)
print("-" * 55)
for t in ["raw_encounters", "map_admission_type",
          "map_discharge_disposition", "map_admission_source"]:
    n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    print(f"  {t:28} {n:>7,} rows")

print("\nSample of decoded lookup (map_admission_type):")
for row in conn.execute("SELECT * FROM map_admission_type").fetchall():
    print("   ", row)
conn.close()
