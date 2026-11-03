# usa_marxian

An empirical framework for testing Fred Moseley's **macro-monetary
interpretation** of Marx's theory (*Money and Totality*, Brill 2016, ch. 2) on
US macroeconomic data.

The project downloads public US data without requiring an API key, constructs
the Marxian aggregates at the macro and industry levels, checks the accounting
identities, and runs robustness and time-series diagnostics. It is a research
skeleton, not a finished econometric study.

## The model in one page

Moseley's aggregate accounting is the circuit of money capital applied to the
whole economy:

```
M - C ... P ... C' - M'        M' = M + ΔM
```

In annual flows (his equations 1-15, ch. 2):

```
P = C + N          total value-price = constant capital + new value
N = m L            new value = MELT x labour hours
K = C + V          cost price = constant capital + variable capital
S = P - K = N - V  surplus-value
R = S / M          general rate of profit
PP_i = K_i + R M_i price of production of industry i
```

where `m` is the monetary expression of labour time (MELT), `M` is the stock of
money capital advanced, and `PP_i` are gross annual industry revenues rather
than unit prices.

The two aggregate equalities — total price = total value, and total profit =
total surplus-value — hold simultaneously by construction, because `R` is
defined from the predetermined `S` and the same money capital magnitudes are
used at both levels of abstraction.

## What can and cannot be tested

The core equations are accounting identities. Given `m := N/L`, `N = mL` is
true by definition. A "test" that total profit equals total surplus-value is
only informative if profit and surplus-value are measured independently. The
project therefore separates four kinds of work:

1. **Construction** — build `C, V, S, N, L, M, m, R` consistently from NIPA and
   fixed-asset data. The code checks the identities.
2. **Descriptive dynamics** — how do `m`, `S/V`, `M/V` and `R` evolve?
3. **Independent checks** — property income vs. `S`, industry profit-rate
   dispersion, and prices of production vs. observed gross output.
4. **Robustness** — do the conclusions survive alternative value-added,
   capital-stock, hours and MELT definitions? Do they survive unit-root,
   break and specification diagnostics?

The project implements all four. It still does not identify individual labour
values, and the industry capital-stock proxy is crude. Treat the output as
measurement and evidence, not proof.

## Quickstart

Requirements: Python 3.10+ and network access for the first run.

```bash
# with uv (fast)
uv venv --python 3.11
uv pip install -e ".[dev]"

# or with venv/pip
python3 -m venv .venv
.venv/bin/pip install -U pip
.venv/bin/pip install -e ".[dev]"
```

Run:

```bash
.venv/bin/usa-marxian info          # model, layers and series map
.venv/bin/usa-marxian fetch         # download raw series (cached)
.venv/bin/usa-marxian analyze       # macro accounts + robustness + diagnostics
.venv/bin/usa-marxian industries    # BEA IO industry accounts
.venv/bin/usa-marxian all           # both
.venv/bin/pytest                    # offline tests
```

Or with `make`:

```bash
make install
make all          # data + analysis + industries
make test
```

## Data

No key is needed by default:

- **FRED** keyless CSV endpoint for NIPA aggregates, property income, fixed
  assets, inventories, deflators and hours.
- **BEA** annual NIPA flat file as a fallback.
- **BEA input-output** archive (16 MB zip) for the 71-industry Use tables,
  1997-2023.
- **BEA NIPA Section 6** workbook for corporate and noncorporate capital
  consumption by industry.
- **FRED GDP-by-Industry price indexes** for broad-sector value-added and
  gross-output deflators.
- **BLS** public API v1 for direct BLS series (v2 with a free key).

Optional free keys unlock the official APIs and higher quotas. Copy
`.env.example` to `.env`:

```bash
cp .env.example .env
```

Every download is cached under `data/raw/<provider>/` with a JSON sidecar
recording source URL, download time, row count and date range. Set
`cache_max_age_days` in `config/settings.yaml` or pass `--refresh`.

## Macro mapping (net value-added layer)

| Variable | Series | Concept |
|---|---|---|
| `P` | `GDPA` | total value-price (GDP) |
| `C` | `COFC` | consumed constant capital (depreciation) |
| `N` | `GDPA - COFC` | new value (net domestic product) |
| `V` | `A033RC1A027NBEA` | variable capital (compensation of employees) |
| `S` | `N - V` | surplus-value |
| `M` | `K1NTOTL1ES000` + inventories | advanced capital stock |
| `L` | `HOANBS` x NIPA 2017 benchmark | total labour hours |
| `m` | `N / L` | MELT, USD of new value per hour |
| `R` | `S / M` | general rate of profit |

Because constant capital appears in both `P` and `K`, it cancels from `S`
(Moseley's "dual significance of constant capital"). A gross-output layer would
raise `C` and `P` together and leave `S` unchanged.

The default hours method is `indexed`: the nonfarm-business hours index
(`HOANBS`, 1947-present) scaled so that 2017 equals NIPA total hours worked.
Alternatives are `nipa` (total economy, ends 2022) and `ces` (private
employment x weekly hours, but the FRED weekly-hours series only starts in
2006).

## Alternative specifications

`analyze` rebuilds the accounts under eight specifications:

- baseline: NDP, nonresidential capital, inventories included, indexed hours
- no inventories
- total private fixed assets instead of nonresidential
- NNP instead of NDP
- net national factor income instead of NDP
- NIPA hours instead of indexed hours
- CES hours instead of indexed hours
- GDP as the MELT numerator

Results on the November 2026 vintage:

- LTV slope on real new value: **1.54 to 2.25** across specifications; baseline
  **2.24** (95% CI 2.08-2.40). The unit-slope restriction is rejected in every
  specification.
- Last-year profit rate: **12.9% to 26.6%**, depending mainly on whether
  capital is measured as nonresidential or total private fixed assets.
- Property-income ratio to `S`: **0.99 to 1.32**; the baseline is **1.01**.

The widest uncertainty is the capital-stock denominator, not the labour-value
relation.

## Diagnostics

The `analyze` command also writes `output/tables/diagnostics.csv`:

- ADF/KPSS/Zivot-Andrews for real MELT, the profit rate and `S/V`;
- first-difference and trend-augmented LTV regressions;
- a pairs bootstrap for the LTV slope;
- Chow tests at 1973 and 2008 and a scan for the most likely break.

Baseline results:

- Real MELT behaves like a unit-root series (ADF p=0.998, KPSS p=0.010,
  Zivot-Andrews p=0.890). Its level is not stationary.
- The profit rate: ADF and Zivot-Andrews reject a unit root (p=0.0013 and
  p=0.021); KPSS is borderline (p=0.039). The evidence leans mean-reverting,
  but it is not unanimous.
- First-difference LTV slope: **0.80** (p=0.0045 against one).
- Trend-augmented LTV slope: **0.94** (p=0.60 against one).
- Bootstrap 95% CI for the level slope: **2.17 to 2.31**.
- Chow break at 1973 p=0.007; at 2008 p<0.0001; the scan selects **2008**.

The level relation is steep, but once a trend is included the slope is close to
one and statistically indistinguishable from it. This is the central
specification sensitivity in the aggregate data.

## Property-income check

`S = N - V` is a residual. The independent check uses NIPA property income:

```
property income = corporate profits + proprietors' income
                  + net interest + rental income
property income + taxes on production  vs  S
```

Baseline mean ratio: **1.011**; mean gap **+56.8 bn** (**+2.5% of S**). The
correlation between the two series is high. Proprietors' income is mixed
income, so the property measure is an upper bound, but the agreement is close
enough to make the exercise informative.

## Industry layer

The BEA summary Use table gives, for 71 industries:

```
C_i    intermediate consumption
V_i    compensation of employees
T_i    taxes on production, less subsidies
GOS_i  gross operating surplus
N_i    value added
GO_i   gross output
```

Gross and net accounts are both constructed:

```
S_gross_i = T_i + GOS_i
K_gross_i = C_i + V_i
S_net_i   = T_i + GOS_i - CFC_i
K_net_i   = C_i + CFC_i + V_i
```

The Use table's `GOS` is gross of depreciation, so the gross split leaves CFC
inside surplus-value. The net split moves it into constant capital. Both
satisfy `K_i + S_i = GO_i`.

Capital consumption comes from BEA NIPA tables 6.13D (noncorporate) and 6.22D
(corporate), allocated within broad sectors in proportion to GOS. The residual
between total-economy CFC (`COFC`) and private CFC is allocated to government
units. On the current vintage the industry CFC total equals macro `COFC`
exactly (**4,576.4 bn** in 2023).

Prices of production follow Moseley's general formula:

```
PP_i = K_i + R M_i,        R = sum(S_i) / sum(M_i)
```

`M_i` is not in the Use table, so the proxy is explicit and switchable:

- `cost`: `M_i = K_i` (default)
- `output`: `M_i = GO_i`
- `value_added`: `M_i = N_i`

The earlier `K_i(1+R)` expression was only the `M_i = K_i` special case. The
code now computes the general formula, and `industry_proxy_sensitivity.csv`
reports how the price-fit changes with the proxy.

Because the Use table is an accounting identity, `C_i + N_i = GO_i` exactly; a
value-price test at this level would be vacuous. The informative tests are:

- dispersion of `r_i` across industries;
- distance between `PP_i` and observed gross output;
- comparison with the labour-only benchmark `PP_V`.

Results, 1998-2023, net basis:

- Market-industry rate of surplus-value on cost: **23.8%** in 2023; full sample
  including government and housing **22.6%**.
- Market weighted CV of `r_i`: **0.609** in 2023 (sample mean 0.703);
  p90/p10 **6.10**.
- Full-sample CV: **2.109** in 2023 (sample mean 2.296), dominated by housing
  and government units.
- MAE of `PP` vs gross output (sample means): **13.3%** full, **10.4%**
  market-only.
- MAE of the labour-only benchmark `PP_V`: **53.1%**.
- Correlation of `PP` with gross output: **0.894**.
- Share of industries within 25% of `PP` (sample means): **90.2%** full,
  **97.3%** market-only.
- Proxy sensitivity (full-sample MAE): cost **13.3%**, output **11.0%**,
  value-added **9.0%**.

The equalised-profit benchmark tracks gross output far better than a labour-only
markup, but industry surplus-value rates are not equalised in any strict sense.
The capital proxy is still the main limitation.

## Depreciation audit

There are two layers, and they treat depreciation differently by design:

- **Macro.** `C = CFC`, `K = C + V`, `S = N - V`, and `P = C + N`. Depreciation
  appears in both `P` and `K`, so it cancels from `S`. No double counting.
- **Industry.** `C_i` is intermediate consumption only. `GOS_i` is gross, so
  `S_gross_i` contains CFC while `K_gross_i` does not. The net accounts move CFC
  from `S` to `C`: `K_net_i = C_i + CFC_i + V_i` and `S_net_i = S_gross_i -
  CFC_i`. Again `K_net_i + S_net_i = GO_i`.

Two cautions:

1. `C_i` and `CFC_i` are distinct. Intermediate consumption is not depreciation,
   and the net accounts do not add one to the other twice.
2. Summing `GO_i` or `K_i` across industries double counts intermediate
   deliveries. Only value added sums to GDP. The code never uses the summed
   gross output as a macro value aggregate.

Reconciliation for 2023:

- industry CFC minus macro `COFC`: **0.0 bn**
- industry value added minus GDP: **-105.2 bn** (BEA IO/GDP statistical
  discrepancy, 0.38%)
- industry net value added minus NDP: **-105.2 bn** (the same discrepancy)
- industry net surplus-value minus macro `S`: **-80.3 bn** (0.9%)

## Sector deflation

The macro `melt_real` uses the GDP deflator, which is an aggregate value-added
deflator. For industry accounts the project uses broad-sector chain-type price
indexes from BEA's GDP-by-Industry release (via FRED):

- value-added deflators for `N_i`, `V_i` and `S_i`;
- gross-output deflators for `GO_i`.

This gives `N_real`, `V_real`, `S_real` and `GO_real` by industry. On
2005-2023, real industry value added grew **1.80%/yr** and real gross output
**1.67%/yr**.

A real profit rate is deliberately not constructed: deflating `N` and `GO` by
different indexes does not yield a valid real intermediate input residual, and
the summary Use table has no intermediate-input deflator. The nominal
prices-of-production comparison remains the correct one for the value-theory
question.

## Outputs

After `analyze`:

- `data/processed/raw_panel.csv`, `accounts.csv`, `data_quality.csv/json`
- `output/report.json`
- `output/tables/summary.csv`, `ltv_test.csv`, `ltv_test_nominal.csv`,
  `melt_summary.csv`, `melt_summary_real.csv`, `profit_rate_summary.csv`,
  `profit_rate_decomposition.csv`, `property_income_check.csv`,
  `robustness.csv`, `robustness_ranges.csv`, `diagnostics.csv`
- `output/figures/melt.png`, `melt_real.png`, `distribution.png`,
  `rate_of_profit.png`, `composition.png`, `robustness.png`

After `industries`:

- `data/processed/industries.csv`
- `output/industries.json`
- `output/tables/industry_summary.csv`, `industry_latest.csv`,
  `industry_proxy_sensitivity.csv`, `industry_reconciliation.csv`
- `output/figures/industry_dispersion.png`, `pp_vs_go.png`

## Project layout

```
config/            settings.yaml, series.yaml, sectors.yaml
src/usa_marxian/
  config.py        typed config + series catalog
  data/            FRED, BLS, BEA, BEA IO, sector deflators, cache, quality
  model/           MELT, equalities, robustness, industries
  analysis/        LTV, diagnostics, property check, descriptives
  viz/             plots
  pipeline.py      macro and industry pipelines
  cli.py           `usa-marxian` command
tests/             offline unit tests
docs/              model derivation, data sources, industry notes
notebooks/         exploratory notebooks
data/raw           cached downloads (gitignored)
data/processed     panels, accounts, quality reports (gitignored)
output/            tables, figures, JSON reports (gitignored)
```

## Roadmap

1. **Industry fixed assets.** Replace `M_i = K_i` with BEA fixed-asset stocks
   by industry. CFC is now handled, but the capital-stock proxy remains crude.
2. **Intermediate-input deflators.** Build a sector intermediate deflator so
   real cost prices and real profit rates can be constructed without the
   invalid `GO_real - N_real` residual.
3. **Unit prices and quantities.** Use the Make and Use tables to construct
   unit value prices and compare them with unit prices of production.
4. **Input-output value magnitudes.** Compute direct and total labour
   requirements with the Leontief inverse.
5. **Structural-break econometrics.** Bai-Perron multiple breaks, rolling
   regressions, and regime-dependent profit-rate trends.
6. **Alternative MELT measures.** Moseley's own estimates use NNP, NDP and net
   national income; the infrastructure now supports swapping the numerator.
7. **Cross-country comparison.** The World Bank endpoint is already documented;
   the same accounting can be applied to other economies.

## Reference

Moseley, Fred. 2016. *Money and Totality: A Macro-Monetary Interpretation of
Marx's Logic in Capital and the End of the 'Transformation Problem'*. Leiden:
Brill. Chapter 2 is the algebraic summary used here; the PDF is in the project
root as `money_and_totality.pdf`.

## License

MIT for the code. The book PDF is the user's own copy and is not covered by
this license.
