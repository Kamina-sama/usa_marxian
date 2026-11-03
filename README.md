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

The project builds:

```
S_i = T_i + GOS_i
K_i = C_i + V_i
r_i = S_i / K_i
R_cost = sum(S_i) / sum(K_i)
PP_K_i = K_i (1 + R_cost)
PP_V_i = V_i (1 + sum(S)/sum(V))
```

`R_cost` is a **mark-up on cost**, not the macro stock-based profit rate. It is
used to construct the equalised-profit price benchmark `PP_K`. Because the Use
table is an accounting identity, `C_i + N_i = GO_i` exactly; a value-price test
at this level would be vacuous. The informative tests are:

- dispersion of `r_i` across industries;
- distance between `PP_K` and observed gross output;
- comparison with the labour-only benchmark `PP_V`.

Results, 1997-2023:

- Latest cost-price mark-up: **38.7%**.
- Full-sample weighted CV of `r_i`: **2.14**; p90/p10 in 2023: **8.72**.
  Housing and government units dominate this dispersion.
- Market industries only (excluding housing and government): CV **0.675**.
- MAE of `PP_K` vs gross output: **15.3%**; market-only **14.1%**.
- MAE of `PP_V` vs gross output: **45.8%**.
- Correlation of `PP_K` with gross output: **0.89**.
- Share of industries within 25% of `PP_K`: **84.5%** overall, **87.2%**
  market-only.

So the equalised-profit benchmark tracks gross output far better than a
labour-only markup, but profit rates are not equalised in any strict sense. The
industry capital proxy (`M_i = K_i`) is the main limitation.

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
- `output/tables/industry_summary.csv`, `industry_latest.csv`
- `output/figures/industry_dispersion.png`, `pp_vs_go.png`

## Project layout

```
config/            settings.yaml, series.yaml
src/usa_marxian/
  config.py        typed config + series catalog
  data/            FRED, BLS, BEA, BEA IO readers, cache, quality, accounts
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

1. **Industry fixed assets and CFC.** Replace `M_i = K_i` with BEA fixed-asset
   stocks by industry and subtract CFC to get net surplus-value.
2. **Unit prices and quantities.** Use the Make and Use tables to construct
   unit value prices and compare them with unit prices of production.
3. **Input-output value magnitudes.** Compute direct and total labour
   requirements with the Leontief inverse.
4. **Structural-break econometrics.** Bai-Perron multiple breaks, rolling
   regressions, and regime-dependent profit-rate trends.
5. **Alternative MELT measures.** Moseley's own estimates use NNP, NDP and net
   national income; the infrastructure now supports swapping the numerator.
6. **Cross-country comparison.** The World Bank endpoint is already documented;
   the same accounting can be applied to other economies.

## Reference

Moseley, Fred. 2016. *Money and Totality: A Macro-Monetary Interpretation of
Marx's Logic in Capital and the End of the 'Transformation Problem'*. Leiden:
Brill. Chapter 2 is the algebraic summary used here; the PDF is in the project
root as `money_and_totality.pdf`.

## License

MIT for the code. The book PDF is the user's own copy and is not covered by
this license.
