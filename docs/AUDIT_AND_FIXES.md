# Audit of the first version and what was changed

## Problems found in the first version

| # | Problem | Where | Fix |
|---|---------|-------|-----|
| 1 | **Excel workbook contained no formulas.** Every number was a pasted value, although the README and resume claimed SUMIFS, XLOOKUP, COUNTIFS, PivotTables and conditional formatting. | `excel/` | Rebuilt with 484 live formulas (SUMIFS, COUNTIFS, AVERAGEIFS, INDEX/MATCH, SUMPRODUCT, RANK), conditional formatting, 4 charts and an Excel Table ready for a PivotTable. |
| 2 | Business Dashboard sheet put a price ($/t) in the same table as trade volumes (EJ) with one "Change %" column. | `excel/` | Separate Trade and Price sheets; dashboard reads from both. |
| 3 | Trade data inconsistent between years: Russia is an exporter in 2023 but absent in 2024, so YoY and concentration silently dropped it. | data + SQL | Flagged in the quality report; comparisons use only countries present in both years; SQL Q8 lists the gap. |
| 4 | Indonesia consumption +59% in 2023 was never checked, yet it drives the "fastest consumption growth" result. | data | Automatic outlier check; warning carried into README, Excel and findings. |
| 5 | No data validation anywhere. | Python | 24 checks (nulls, duplicates, year coverage, positivity, YoY outliers, trade-share consistency, price reconciliation). |
| 6 | Python script only printed tables. Charts in `outputs/` were not produced by any code, so the project was not reproducible. | Python | One script now validates, computes metrics, draws 6 charts, writes findings. |
| 7 | YoY calculated without sorting; CAGR, indices, shares and import/export ratios missing. | Python | Sorted before `pct_change`; added CAGR (10y and 5y), indices, shares, growth gap, trade/consumption ratio, HHI lower bound. |
| 8 | Production chart: China dwarfed everything and Japan was a flat line at zero. | charts | Indexed (2014 = 100) charts with end labels; Japan omitted with a note. |
| 9 | SQL had no primary keys, no data-load step, could not be re-run (`CREATE TABLE` without drop), and Q5 divided by NULL for Russia. | SQL | Schema with keys and view, `LOAD DATA` script, 14 queries (CAGR, LAG, concentration, price vs demand, data-quality checks). All run in SQLite via `run_sql_checks.py`. |
| 10 | README insight "Indonesia produces more than it consumes" compared Mt with EJ. | README | Replaced with EJ / EJ ratios (exports vs domestic consumption). |
| 11 | README promised "Executive Summary / Business Dashboard" content that was thin and had no numbers. | README | Real findings with numbers, generated from the data. |
| 12 | SOURCE_NOTES said trade data was 2024 only; files hold 2023 and 2024. | data | Corrected. |
| 13 | No `requirements.txt`. | repo | Added. |

## Not changed (needs internet access)
- The values in `data/raw/` were **not altered** because they could not be re-checked against the Energy Institute and World Bank files in the build environment.
- Price history was **not extended** to 2014. See "Extending the price history" in the README.
