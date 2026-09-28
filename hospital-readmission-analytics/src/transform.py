"""
transform.py
------------
Runs sql/transform.sql against data/hospital.db, validates the key metrics,
and exports the clean analytics table for the dashboard.
"""

from pathlib import Path
import sqlite3
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "hospital.db"
SQL = ROOT / "sql" / "transform.sql"
PROC = ROOT / "data" / "processed"
PROC.mkdir(exist_ok=True)

conn = sqlite3.connect(DB)
conn.executescript(SQL.read_text())   # run the whole transform script
conn.commit()

# ---- Validation: does the model produce sensible, real-world numbers? ------
def scalar(q):
    return conn.execute(q).fetchone()[0]

total_raw = scalar("SELECT COUNT(*) FROM raw_encounters")
total_stg = scalar("SELECT COUNT(*) FROM stg_encounters")
eligible = scalar("SELECT COUNT(*) FROM fact_encounter")
excluded = total_stg - eligible

readmit_rate = scalar(
    "SELECT ROUND(100.0*SUM(is_readmitted_30d)/COUNT(*),2) FROM fact_encounter")
avg_los = scalar("SELECT ROUND(AVG(length_of_stay),2) FROM fact_encounter")

print("TRANSFORMATION COMPLETE")
print("=" * 60)
print(f"Raw encounters:                        {total_raw:>8,}")
print(f"Excluded (expired / hospice):          {excluded:>8,}")
print(f"Readmission-eligible (fact table):     {eligible:>8,}")
print(f"30-day readmission rate (eligible):    {readmit_rate:>7}%")
print(f"Average length of stay (days):         {avg_los:>8}")

print("\n30-DAY READMISSION RATE BY ADMISSION TYPE")
print("-" * 60)
q = """
SELECT COALESCE(admission_type,'(unknown)') AS admission_type,
       COUNT(*) AS encounters,
       ROUND(100.0*SUM(is_readmitted_30d)/COUNT(*),2) AS readmit_pct
FROM fact_encounter
GROUP BY admission_type
HAVING COUNT(*) > 500
ORDER BY readmit_pct DESC
"""
print(pd.read_sql(q, conn).to_string(index=False))

print("\n30-DAY READMISSION RATE BY PRIOR INPATIENT VISITS")
print("-" * 60)
q2 = """
SELECT CASE WHEN number_inpatient = 0 THEN '0 prior'
            WHEN number_inpatient BETWEEN 1 AND 2 THEN '1-2 prior'
            WHEN number_inpatient BETWEEN 3 AND 5 THEN '3-5 prior'
            ELSE '6+ prior' END AS prior_inpatient,
       COUNT(*) AS encounters,
       ROUND(100.0*SUM(is_readmitted_30d)/COUNT(*),2) AS readmit_pct
FROM fact_encounter
GROUP BY prior_inpatient
ORDER BY readmit_pct
"""
print(pd.read_sql(q2, conn).to_string(index=False))

# ---- Export the flat analytics table for the dashboard --------------------
analytics = pd.read_sql("SELECT * FROM fact_encounter", conn)
analytics.to_csv(PROC / "analytics_encounters.csv", index=False)
print(f"\nExported: {PROC / 'analytics_encounters.csv'}  ({len(analytics):,} rows)")
conn.close()
