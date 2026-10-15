# Import Specification — Kenya Inflation Data Pipeline

**Status:** Final; updated 15 October 2026 after implementation and testing.  
**Scope:** Kenya, monthly inflation, January 2015–September 2026; two variables.

## Source and provenance

- **Publisher:** [Central Bank of Kenya — Inflation Rates](https://www.centralbank.go.ke/inflation-rates/); the page credits the **Kenya National Bureau of Statistics (KNBS)** as the original data source.
- **Archived source:** `data/source/cbk_inflation_2026-10-14.html`; its download timestamp, URL, and SHA-256 checksum are recorded in the accompanying `.json` file. Re-runs use this saved snapshot.
- **Frequency/revisions:** CBK updates the table monthly. Preserve a separate dated snapshot for future updates and review historical changes; automated revision comparison is not yet implemented.
- **Licence:** No explicit reuse licence was verified. Credit CBK/KNBS and confirm redistribution permissions before publicly sharing the archived webpage.

## Mapping and units

| CBK field | Data Commons mapping | Meaning |
|---|---|---|
| `Year` + `Month` | `date = YYYY-MM` | Reporting month; exclude pre-2015 data. |
| `Annual Average Inflation` | `cbk/AnnualAverageInflationRate` | Change in annual-average CPI for corresponding periods; published each month. |
| `12-Month Inflation` | `cbk/TwelveMonthInflationRate` | Change in monthly CPI versus the same month a year earlier. |
| All rows | `entity = country/KEN` | Existing national place identifier. |

Both variables have **unit `Percent`**: source `5.53` remains `5.53`, not `0.0553`. One observation is allowed per `(entity, variable, date)`.

**Loader inputs:** `data/transformed_data/observations.csv` (`entity,variable,date,value,unit`); `variables.mcf` (statistical variable definitions); `config.json` (`variablePerRow`, `importType: observations`, provenance `CBK_Inflation_Rates`). **Output database:** `data/transformed_data/datacommons/datacommons.db`.

## Data-quality policy and source notes

- **Missing dates:** Flag gaps; never generate fictional months. No missing months were found.
- **Missing figures:** Omit recognized missing values from loader observations and report them; never use zero. Reject unexpected text/non-finite figures. No missing inflation values were found.
- **Duplicates:** Keep one copy of an identical repeated month and log the discarded row; stop if figures conflict. **April 2019** appeared twice with the same annual-average (**4.91**) and 12-month (**6.58**) rates; one copy was ignored.
- **Footnotes:** CBK's saved webpage contains explanatory notes defining both inflation measures and crediting KNBS. Preserve these notes with the original HTML; investigate any annotations in data cells instead of silently changing values.
- **Revisions:** Keep original snapshots; any changes in later publications require explicit review.

## Import verification

The extract contained **142 rows** and **141 distinct months**. Transformation generated **282 observations** (141 months × 2 variables). SQLite readback matched all **282** values, with **0 differences or duplicate dataset observations**. Two successive pipeline runs against the saved source also passed with **282 observations, 0 duplicates, 0 differences**. See `docs/readback_report.md` and the locally generated reproducibility report. Numeric readback does not independently validate all database metadata/facets.

**Tools:** Python, BeautifulSoup/pandas, official Data Commons Docker container, SQLite; AI-assisted guidance and documentation were checked through executable validation and readback. Full notes: `docs/handover.md` and `docs/learning_log.md`.
