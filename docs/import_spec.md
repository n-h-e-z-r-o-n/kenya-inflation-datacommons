# Import Specification — Kenya Inflation Data Pipeline

**Status:** Pre-import draft · **Scope:** Kenya only, monthly data from January 2015 onward, two variables.

## Source

- **Published by:** Central Bank of Kenya (CBK), [Inflation Rates](https://www.centralbank.go.ke/inflation-rates/). **Original producer:** Kenya National Bureau of Statistics (KNBS), credited by CBK.
- **Saved source:** `source/cbk_inflation_2026-10-14.html` (date shown in the download log; verify its location and preserve the matching download metadata/checksum). The local copy is the reproducible source of truth.
- **Updates:** Monthly. Historical figures may be revised; save each new download separately and compare snapshots.
- **Licence:** No explicit reuse licence was verified for this table. Credit CBK/KNBS and check redistribution permissions before publishing the source copy publicly.

## Mapping and units

| Source column | Data Commons field | Meaning |
|---|---|---|
| `Year` + `Month` | `date` (`YYYY-MM`) | Reporting month |
| `Annual Average Inflation` | `variable`: `cbk/AnnualAverageInflationRate` | Percentage change in annual-average CPI for corresponding periods |
| `12-Month Inflation` | `variable`: `cbk/TwelveMonthInflationRate` | CPI percentage change from the same month of the prior year |

- **Place:** All observations use the existing Data Commons identifier `country/KEN` (`entity`). No new place is defined.
- **Unit:** Both variables use `Percent`. Preserve CBK figures exactly: a published `5.53` becomes `5.53` (not `0.0553`). The annual-average measure is reported **each month**.
- **Unique key:** `(entity, variable, date)`; at most one value for each key.
- **Loader files:** `output/observations.csv` with `entity,variable,date,value,unit`; `output/variables.mcf` defines the two variables; `output/config.json` supplies file mapping and provenance.

## Validation and edge cases

1. **Scope/gaps:** Exclude pre-2015 records. Flag missing months; do not invent values or dates.
2. **Missing values:** Preserve missingness, never substitute `0`. Omit non-numeric observations from the loader CSV and report them. Reject unexpected text for review.
3. **Duplicates:** Detect repeated year/month keys. Collapse **identical** rows only with an audit log; if figures conflict, stop rather than guess. The live CBK table repeats April 2019; confirm this in the saved snapshot.
4. **Footnotes:** Record and investigate annotations instead of silently discarding them; do not infer modified figures.
5. **Revisions:** Keep original dated snapshots and report any changed historical values on later runs.
6. **Readback:** Compare source, generated CSV, and SQLite counts; check every loaded `(entity, variable, date, value)` against values parsed by code from the saved source. List and explain every difference.

**Tools and traceability:** Python for extraction/transformation/validation; official Data Commons Docker data container for SQLite loading. Record any AI assistance, and verify its output independently. Follow the [Data Commons custom data documentation](https://docs.datacommons.org/custom_dc/custom_data.html).
