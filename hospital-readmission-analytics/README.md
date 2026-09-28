# Hospital Readmission & Length-of-Stay Analytics

An interactive Streamlit dashboard analyzing **30-day hospital readmissions** across
**99,343 real, de-identified patient encounters**, built on a SQL data pipeline that
decodes, cleans, and models raw hospital records into an analysis-ready star schema.

The dashboard surfaces *who* gets readmitted within 30 days and *what predicts it* —
the metric hospitals care about most, because Medicare financially penalizes high
readmission rates.

**Live dashboard:** _add your Streamlit URL here after deploying_

---

## Key findings

- Overall **30-day readmission rate: 11.4%** (on the readmission-eligible cohort).
- **Prior admissions are the strongest predictor:** patients with 6+ prior inpatient
  visits are readmitted **4.7× as often** as those with none (40.6% vs 8.6%).
- Readmission risk rises with **age, number of diagnoses, and medication count**.

## What's in the dashboard

- 6 KPIs and **13 interactive visualizations** across four sections: Readmission
  Drivers, Clinical Factors, Length of Stay, and Population Served.
- **Six stacking filters** (admission type, age band, gender, A1C result, medication
  change, length-of-stay range) that recompute the entire board live.
- A **risk color scale** (green→amber→red) applied to every rate chart, so high-risk
  groups are visually obvious.

## The data pipeline (SQL)

Raw source: the [Diabetes 130-US Hospitals dataset](https://archive.ics.uci.edu/dataset/296/diabetes+130-us+hospitals+for+years+1999-2008)
(UCI ML Repository), 101,766 encounters × 50 columns.

The SQL layer (`sql/transform.sql`) does the analytical heavy lifting:
1. **Decodes** coded IDs (admission type, discharge disposition, admission source) by
   joining to lookup tables.
2. **Cleans** the `?` missing-value marker to proper NULLs.
3. **Engineers** an age midpoint and a binary 30-day readmission flag.
4. **Applies a clinically-correct cohort filter** — excludes encounters ending in death
   or hospice transfer (not eligible for readmission), matching the source study's
   methodology. This removes 2,423 encounters, leaving 99,343.
5. Builds a **star schema** (`fact_encounter` + dimension tables).

## Repo structure

```
.
├── app.py                       # the Streamlit dashboard
├── requirements.txt
├── .streamlit/config.toml       # theme
├── data/
│   ├── raw/                     # original source files
│   │   ├── diabetic_data.csv
│   │   └── IDs_mapping.csv
│   └── processed/
│       └── analytics_encounters.csv   # cleaned table the app reads
├── sql/
│   └── transform.sql            # decode + clean + star schema
└── src/
    ├── build_database.py        # load raw + lookups into SQLite
    └── transform.py             # run transform.sql, validate, export
```

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

To regenerate the processed data from raw:
```bash
python src/build_database.py   # builds data/hospital.db
python src/transform.py        # runs the SQL, exports analytics_encounters.csv
```

## Changing the background theme

In `app.py`, edit the `BG` constant near the top. Options:
`#E9EEF2` (Clinical Mist), `#0F172A` (Command-Center Dark — also set `DARK = True`),
`#E8F3F2` (Teal Tint), `#EDEFF2` (Neutral Graphite), `#F1EEEA` (Warm Greige).

## Tech stack

Python · SQL (SQLite) · pandas · Plotly · Streamlit

---

*Data is de-identified and used for demonstration. Not for clinical decision-making.*
