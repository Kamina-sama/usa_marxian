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
| `capital_stock` | `K1NTOTL1ES000` | Net stock of private nonresidential fixed assets | mn USD |
| `inventories` | `K100071A027NBEA` | Net stock of private inventories | bn USD |
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
tables, input-output tables, and arbitrary NIPA tables.

## World Bank (not used by default)

Keyless JSON API, useful for long-run cross-country comparisons:

```
https://api.worldbank.org/v2/country/USA/indicator/NY.GDP.MKTP.CD?format=json
```

## Reproducibility

Downloads are cached as CSV under `data/raw/<provider>/<series_id>.csv`.
`cache_max_age_days` in `config/settings.yaml` controls staleness (default 30
days). Delete the cache to force a fresh download:

```bash
rm -rf data/raw
```

## Suggested keys and quotas

- FRED: free, generous; one key per user.
- BLS: free; v1 allows 25 queries/day, v2 allows 500/day.
- BEA: free; required for IO tables.

Store keys in `.env` (gitignored), never in `config/`.
