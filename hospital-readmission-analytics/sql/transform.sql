-- transform.sql
-- Turns raw_encounters (coded, messy) into a clean analytical model.
-- Run order: staging -> dimensions -> fact.

-- =========================================================================
-- 1. STAGING: decode the coded IDs, clean '?' to NULL, engineer flags.
-- =========================================================================
DROP TABLE IF EXISTS stg_encounters;
CREATE TABLE stg_encounters AS
SELECT
    e.encounter_id,
    e.patient_nbr,

    -- Demographics. The dataset uses '?' as its missing marker; convert to NULL.
    NULLIF(e.race, '?')               AS race,
    NULLIF(e.gender, '?')             AS gender,
    e.age                             AS age_band,
    -- Turn the age BAND string into a numeric midpoint for averaging/plotting.
    CASE e.age
        WHEN '[0-10)'   THEN 5   WHEN '[10-20)'  THEN 15
        WHEN '[20-30)'  THEN 25  WHEN '[30-40)'  THEN 35
        WHEN '[40-50)'  THEN 45  WHEN '[50-60)'  THEN 55
        WHEN '[60-70)'  THEN 65  WHEN '[70-80)'  THEN 75
        WHEN '[80-90)'  THEN 85  WHEN '[90-100)' THEN 95
    END                               AS age_midpoint,

    -- Decode the coded IDs by joining to the lookup tables.
    at.description                    AS admission_type,
    dd.description                    AS discharge_disposition,
    asrc.description                  AS admission_source,
    NULLIF(e.medical_specialty, '?')  AS medical_specialty,

    -- Measures
    e.time_in_hospital                AS length_of_stay,
    e.num_lab_procedures,
    e.num_procedures,
    e.num_medications,
    e.number_diagnoses,
    e.number_outpatient,
    e.number_emergency,
    e.number_inpatient,

    -- Clinical factors (diabetes-specific). These use their own value sets,
    -- e.g. A1Cresult in {None, Norm, >7, >8}; "change" in {Ch, No}.
    e."A1Cresult"                     AS a1c_result,
    e.max_glu_serum                   AS max_glu_serum,
    e."change"                        AS med_changed,      -- "change" is a SQL keyword, so quoted
    e.diabetesMed                     AS diabetes_med,
    e.insulin                         AS insulin,

    -- The target. Raw values: '<30', '>30', 'NO'.
    e.readmitted                      AS readmitted_raw,
    -- Binary 30-day readmission flag: 1 only if readmitted within 30 days.
    CASE WHEN e.readmitted = '<30' THEN 1 ELSE 0 END AS is_readmitted_30d,

    -- Readmission ELIGIBILITY. A patient who died or entered hospice cannot be
    -- readmitted, so those encounters must be excluded from readmission rates.
    -- Disposition ids 11,13,14,19,20,21 = expired / hospice (per the data
    -- dictionary and Strack et al. 2014 methodology).
    CASE WHEN e.discharge_disposition_id IN (11,13,14,19,20,21)
         THEN 0 ELSE 1 END            AS readmission_eligible

FROM raw_encounters e
LEFT JOIN map_admission_type        at   ON e.admission_type_id        = at.id
LEFT JOIN map_discharge_disposition dd   ON e.discharge_disposition_id = dd.id
LEFT JOIN map_admission_source      asrc ON e.admission_source_id      = asrc.id;

-- =========================================================================
-- 2. DIMENSIONS (star-schema lookups the fact table points to)
-- =========================================================================
DROP TABLE IF EXISTS dim_admission_type;
CREATE TABLE dim_admission_type AS
SELECT id AS admission_type_key, description AS admission_type
FROM map_admission_type;

DROP TABLE IF EXISTS dim_discharge_disposition;
CREATE TABLE dim_discharge_disposition AS
SELECT id AS discharge_disposition_key, description AS discharge_disposition
FROM map_discharge_disposition;

DROP TABLE IF EXISTS dim_admission_source;
CREATE TABLE dim_admission_source AS
SELECT id AS admission_source_key, description AS admission_source
FROM map_admission_source;

-- =========================================================================
-- 3. FACT: one clean, analysis-ready row per readmission-eligible encounter.
-- =========================================================================
DROP TABLE IF EXISTS fact_encounter;
CREATE TABLE fact_encounter AS
SELECT *
FROM stg_encounters
WHERE readmission_eligible = 1;
