# Data Commons readback verification

## Input files
- Saved-source extraction: `C:\Users\user\Desktop\Kotlin Apps\kenya-inflation-datacommons\data\cbk_inflation_extracted.csv`
- Loader observations CSV: `C:\Users\user\Desktop\Kotlin Apps\kenya-inflation-datacommons\data\transformed_data\observations.csv`
- Actual SQLite readback: `C:\Users\user\Desktop\Kotlin Apps\kenya-inflation-datacommons\data\transformed_data\datacommons\datacommons.db`

## Row counts
- Source CSV rows: **142**
- Distinct source months: **141** (2015-01 to 2026-09)
- Expected nonmissing observations from source: **282**
- Generated observations.csv rows: **282**
- Loaded SQLite observations for Kenya and these two variables: **282**
- All SQLite observations, including any other datasets: **282**
- SQLite observations table columns: `entity, variable, date, value, provenance, unit, scaling_factor, measurement_method, observation_period, properties`

## Duplicate handling
- Identical source rows ignored by date: **1**
- 2019-04: the two original source entries had identical values; one month was retained.

## Verification method
- Independently reconstruct expected rows from the saved source extraction.
- Compare by entity, statistical variable, month, and numeric value against both generated CSV and SQLite.
- Require a single observation per key; check the CSV unit equals `Percent`.
- Missing source values are omitted, never changed to zero.
- SQLite's observations table stores numeric values; per-row units/facet metadata are not independently verified by this script.

## Result: **PASS**
- Differences detected: **0**

Every expected numeric observation matched the transformed CSV and loaded database; there were no missing, extra, or repeated dataset observations.
