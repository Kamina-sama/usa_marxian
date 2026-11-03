# Data sources and access

## Principle

The default pipeline needs **no API key**. It uses public endpoints that return
the same observations as the official APIs for single series. Keys are optional
and only unlock convenience features (metadata, vintages, bulk downloads,
higher quotas).

## FRED (primary)

Keyless CSV endpoint:

```
https://fred.stlouisfed.org/graph/fredgraph.csv?id=SERIES_ID
```

Returns `observation_date,value` with `.` for missing observations. Implemented
in `src/usa_marxian/data/fred.py`.

Optional API: <https://fredaccount.stlouisfed.org/apikeys>. With a key, the
pipeline uses the official `series/observations` endpoint and falls back to the
CSV endpoint on failure.

### Series used

| Role | Series ID | Description | Units |
|---|---|---|---|
| `gdp` | `GDPA` | Gross domestic product | bn USD |
| `cfc` | `COFC` | Consumption of fixed capital | bn USD |
| `gdp_deflator` | `GDPDEF` | GDP implicit price deflator | index 2017=100 |
| `compensation` | `A033RC1A027NBEA` | Compensation of employees, paid | bn USD |
| `net_operating_surplus` | `GDINOSA` | Net operating surplus | bn USD |
| `gnp` | `GNPA` | Gross national product | bn USD |
| `taxes_on_production` | `GDITAXES` | Taxes on production and imports | bn USD |
| `corporate_profits` | `A053RC1A027NBEA` | Corporate profits before taxes | bn USD |
| `proprietors_income` | `A041RC1A027NBEA` | Proprietors' income with IVA and CCAdj | bn USD |
| `net_interest` | `W255RC1A027NBEA` | Net interest and miscellaneous payments | bn USD |
| `rental_income` | `A048RC1A027NBEA` | Rental income of persons with CCAdj | bn USD |
| `capital_stock` | `K1NTOTL1ES000` | Net stock of private nonresidential fixed assets | mn USD |
| `capital_stock_private` | `K1PTOTL1ES000` | Net stock of total private fixed assets | mn USD |
| `net_national_factor_income` | `X032RC1A027NBEA` | Net national factor income | bn USD |
| `inventories` | `K100071A027NBEA` | Net stock of private inventories (opening balance) | bn USD |
| `employment` | `CEU0500000001` | All employees, total private | thousands |
| `weekly_hours` | `AWHAETP` | Average weekly hours, total private | hours/week |
| `hours_nipa` | `B4701C0A222NBEA` | Hours worked, full- and part-time employees | mn hours |
| `hours_index` | `HOANBS` | Nonfarm business hours worked, all workers | index 2017=100 |

All series are annualised by the rules in `config/series.yaml`:

- `mean` for flows and seasonally adjusted annual rates;
- `last` for end-of-year stock levels.

The default hours series is `hours_index` (`HOANBS`) scaled to the 2017 value
of `hours_nipa` (`B4701C0A222NBEA`). The latter has total-economy coverage but
ends in 2022, which is why it is used as a benchmark rather than as the
current measure.

## BLS (optional)

Public API v1 is keyless but rate-limited:

```
POST https://api.bls.gov/publicAPI/v1/timeseries/data/
```

v2 requires a free registration key:
<https://data.bls.gov/registrationEngine/>. Implemented in
`src/usa_marxian/data/bls.py`. The default pipeline does not call BLS directly
because the relevant series are mirrored on FRED.

Useful BLS series if you want to build hours yourself:

- `CES0500000001` — all employees, total private (seasonally adjusted)
- `CES0500000002` — average weekly hours, total private
- `PRS85006032` — nonfarm business hours worked (index)

## BEA (optional)

Keyless annual NIPA flat file:

```
https://apps.bea.gov/national/Release/TXT/NipaDataA.txt
```

Format: `%SeriesCode,Period,Value`, with BEA series codes such as `A001RC`
(GDP). Parsed in `src/usa_marxian/data/bea.py`.

Optional API key: <https://apps.bea.gov/API/signup/>. Needed for quarterly
tables and arbitrary NIPA tables.

## BEA input-output (industry layer)

Keyless archive:

```
https://apps.bea.gov/industry/iTables%20Static%20Files/AllTablesIO.zip
```

The project extracts and parses
`IOUse_After_Redefinitions_PRO_1997-2023_Summary.xlsx`, which contains 27 annual
sheets and 71 summary industries each. The archive is about 16 MB and is cached
under `data/raw/bea/` with a JSON provenance sidecar.

Useful members in the same archive if you want to extend the module:

- `IOMake_After_Redefinitions_PRO_1997-2023_Summary.xlsx`
- `CxI_DR_1997-2023_Summary.xlsx`
- detail-level Use and Make tables for 2017.

The summary Use table provides intermediate consumption, compensation, taxes,
gross operating surplus, value added and gross output. It does **not** provide
industry capital stocks, consumption of fixed capital, or sector price indexes.

## Industry CFC and price indexes

Two additional keyless sources fill those gaps:

**BEA NIPA Section 6** (capital consumption by industry):

```
https://apps.bea.gov/national/Release/XLS/Survey/Section6All_xls.xlsx
```

- Table 6.13D: noncorporate capital consumption allowances.
- Table 6.22D: corporate capital consumption allowances.

The workbook is cached under `data/raw/bea/`. CFC is allocated to IO industries
by broad sector and then to government units using the residual against total
`COFC`.

**FRED GDP-by-Industry price indexes** (broad sectors, 2017=100):

- `VAPIAFH`, `VAPIM`, `VAPIU`, `VAPIC`, `VAPIMA`, `VAPIW`, `VAPIR`, `VAPIT`,
  `VAPII`, `VAPIFI`, `VAPIRL`, `VAPIPBS`, `VAPIES`, `VAPIHCSA`,
  `VAPIAERAF`, `VAPIOSEG`, `VAPIG`, `VAPIAI`.
- Corresponding `GOPI*` series for gross output.

These are index levels. The similarly named `VAPIP*`/`GOPIP*` series are percent
changes and are not used. The mapping from IO industry codes to sectors lives in
`config/sectors.yaml`.

The price series start in 2005, so real industry accounts cover 2005-2023 while
the nominal and CFC-adjusted accounts cover 1998-2023.

## BEA fixed assets (industry capital stocks)

Keyless detail workbook:

```
https://apps.bea.gov/national/FA2004/Details/xls/detailnonres_stk1.xlsx
```

It contains current-cost net stocks of private nonresidential fixed assets for
74 detailed industries, 1925-present, in millions of dollars. Each industry
sheet has three top-level totals (equipment, structures, intellectual property
products); their sum is the industry capital stock.

`config/industry_capital.yaml` maps the 74 detailed industries to the 65 IO
summary industries that have private nonresidential capital. Government and
housing capital comes from the separate Section 7 and Section 5 workbooks
described below.

Validation on the current vintage: the summed industry stocks are 34,948 bn in
2023 against the macro aggregate `K1NTOTL1ES000` of 34,771 bn, a 0.51% gap.

The same page also publishes investment, depreciation and fixed-cost stock
files if you want to extend the module:

- `detailnonres_inv1.xlsx` — investment
- `detailnonres_dep1.xlsx` — depreciation
- `detailnonres_stk2.xlsx` — fixed-cost (2017-dollar) net stock

Consumption of fixed capital by industry comes from NIPA Section 6 tables
6.13D and 6.22D, as described in `docs/industry.md`.

## BEA fixed assets: government and residential

Keyless BEA Fixed Assets workbooks:

```
https://apps.bea.gov/national/FixedAssets/Release/XLS/Section7All_xls.xlsx
https://apps.bea.gov/national/FixedAssets/Release/XLS/Section5All_xls.xlsx
```

Table 7.1 gives current-cost net stocks of government fixed assets. On the
current vintage:

- Federal fixed assets equal national defense plus nondefense, so federal
  government enterprises are zero;
- government enterprise fixed assets are therefore all state and local;
- state/local general government = general government total − federal defense −
  federal nondefense.

Table 5.1 gives residential fixed assets. Owner-occupied residential stock is
used for the housing IO industry; tenant-occupied stock is not added because the
other-real-estate industry already has actual nonresidential fixed assets.

## BEA private inventories (industry stocks)

Keyless NIPA Section 5 workbook:

```
https://apps.bea.gov/national/Release/XLS/Survey/Section5All_xls.xlsx
```

Table 5.8.5B, "Private Inventories and Domestic Final Sales by Industry",
provides quarterly private inventory stocks in current dollars. The project
uses Q4 values as year-end stocks.

Manufacturing and retail inventories come from BEA **Table 1BUC**, available
through the keyless NIPA underlying-detail API:

```
POST https://apps.bea.gov/iTable/core/data/app/GetStep
```

Table 1BUC gives current-dollar manufacturing and trade inventories, end of
period, at detailed NAICS level, 1997 forward. Its manufacturing and retail
rows map to 23 IO industries and reconcile exactly to Table 5.8.5B.

The remaining groups — farm, mining/utilities/construction, wholesale and
"other industries" — come from Table 5.8.5B:

- Farm and wholesale map directly;
- mining/utilities/construction are allocated within the group by gross output;
- "Other industries" is allocated across the remaining market industries by
  gross output.

On the current vintage total inventories are 3,805 bn in 2023, matching the
macro inventory stock. Detailed manufacturing/retail data cover 54.5% of the
total; the remaining 45.5% is broad-group allocation.

## World Bank (not used by default)

Keyless JSON API, useful for long-run cross-country comparisons:

```
https://api.worldbank.org/v2/country/USA/indicator/NY.GDP.MKTP.CD?format=json
```

## Reproducibility

Downloads are cached under `data/raw/<provider>/` (CSV for FRED series, XLSX
for BEA IO and fixed-asset files). `cache_max_age_days` in
`config/settings.yaml` controls staleness (default 30 days; industry files use
at least 365 days). Delete the cache to force a fresh download:

```bash
rm -rf data/raw
```

## Suggested keys and quotas

- FRED: free, generous; one key per user.
- BLS: free; v1 allows 25 queries/day, v2 allows 500/day.
- BEA: free; required for IO tables.

Store keys in `.env` (gitignored), never in `config/`.
