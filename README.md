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
project therefore separates five kinds of work:

1. **Construction** — build `C, V, S, N, L, M, m, R` consistently from NIPA and
   fixed-asset data. The code checks the identities.
2. **Descriptive dynamics** — how do `m`, `S/V`, `M/V` and `R` evolve?
3. **Independent checks** — property income vs. `S`, industry profit-rate
   dispersion, and prices of production vs. observed gross output.
4. **Robustness** — do the conclusions survive alternative value-added,
   capital-stock, hours and MELT definitions? Do they survive unit-root,
   break and specification diagnostics?
5. **Predictive and gravitation tests** — panel error-correction and
   out-of-sample forecasts of market gross output.

The project implements all five. It still does not identify individual labour
values, and about 11% of industry inventory value still uses broad-group
allocation. All 71 industries now use actual fixed assets, including government
and housing. Treat the output as measurement and evidence, not proof.

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
.venv/bin/usa-marxian industries    # BEA IO industry accounts + gravitation tests
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
- **BEA fixed-asset detail** for current-cost and fixed-cost net stocks,
  investment and depreciation of private nonresidential fixed assets by
  industry.
- **BEA Fixed Assets Sections 7 and 5** for government and owner-occupied
  residential capital stocks.
- **BEA NIPA Section 5** workbook for private inventory stocks by broad
  industry (Table 5.8.5B).
- **BEA NIPA underlying detail** (keyless iTable API) for detailed
  manufacturing and retail inventories (Table 1BUC).
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
  Zivot-Andrews p=0.904). Its level is not stationary.
- The profit rate also fails to reject a unit root (ADF p=0.163, KPSS p=0.100,
  Zivot-Andrews p=0.373). The evidence for mean reversion is weaker than in
  earlier versions of the sample.
- First-difference LTV slope: **0.78** (p=0.0013 against one).
- Trend-augmented LTV slope: **0.91** (p=0.417 against one).
- Bootstrap 95% CI for the level slope: **2.15 to 2.28**.
- Chow break at 1973 p=0.028; at 2008 p<0.0001; the scan selects **2008**.

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

Baseline mean ratio: **1.011**; mean gap **+58.2 bn** (**+2.5% of S**). The
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

`M_i` now combines three actual BEA sources:

- **private fixed assets** — current-cost net stock of private nonresidential
  fixed assets, mapped from 74 detailed industries to 65 IO industries;
- **government and housing capital** — federal defense/nondefense, state and
  local general government, state and local government enterprises, and
  owner-occupied residential fixed assets;
- **inventories** — year-end private inventory stocks. Manufacturing and retail
  come from BEA Table 1BUC at detailed NAICS level (23 IO industries, **54.5%**
  of inventory value); farm, mining/utilities/construction, wholesale and
  “other” industries come from Table 5.8.5B and are allocated within the broad
  group.

Coverage in 2023: **all 71 industries use actual capital**, with **no cost
proxy**. Private nonresidential fixed assets total **34,948 bn** vs the macro
aggregate **34,771 bn** (+0.51%); government and housing add **47,797 bn**;
inventories are **3,805 bn** and match the macro inventory stock. Total capital
assets are **82,746 bn**.

The full sample now includes government and housing, whose capital is very large
relative to their surplus-value; the **market sample is the headline** and
excludes them.

The older proxies remain available for sensitivity: `cost` (`M_i = K_i`),
`output` (`M_i = GO_i`), and `value_added` (`M_i = N_i`). The earlier
`K_i(1+R)` expression was only the `M_i = K_i` special case. The code now
computes the general formula, and `industry_proxy_sensitivity.csv` reports how
the price-fit changes with the proxy.

Because the Use table is an accounting identity, `C_i + N_i = GO_i` exactly; a
value-price test at this level would be vacuous. The informative tests are:

- dispersion of `r_i` across industries;
- distance between `PP_i` and observed gross output;
- comparison with the labour-only benchmark `PP_V`.

Results, 1998-2023, net basis:

- Market general rate of profit `R = S/M`: **20.2%** in 2023; full sample
  including government and housing **10.3%**.
- Market surplus-value rate on cost `S/K`: **23.8%**.
- Market weighted CV of `r_i`: **0.609** in 2023 (sample mean 0.703);
  p90/p10 **6.10**.
- Full-sample CV: **2.109** in 2023 (sample mean 2.296), dominated by housing
  and government units.
- MAE of `PP` vs gross output (sample means): **12.6%** full, **13.7%**
  market-only.
- MAE of the long-run `PP*`: **16.8%** full, **15.8%** market-only.
- MAE of the labour-only benchmark `PP_V`: **53.1%**.
- Correlation of `PP` with gross output: **0.941** full, **0.983** market-only.
- Share of industries within 25% of `PP` (sample means): **86.9%** full,
  **88.8%** market-only.
- Proxy sensitivity, full-sample MAE: fixed assets + inventories **12.6%**,
  cost **13.3%**, output **11.0%**, value-added **9.0%**. Market-only MAE:
  **13.7%**, **10.5%**, **8.7%**, **7.1%**.

The market sample is the meaningful comparison. Its fit is essentially unchanged
from the previous version; the full-sample numbers move because government and
housing capital are now actual and very large relative to their surplus-value.
That is informative, not a failure: with `M_i = K_i`, `PP_i` is mechanically
close to `GO_i`, so the old fit was partly built in. Actual capital stocks expose
the profit-rate dispersion, especially regulated utilities and capital-intensive
industries, which is exactly what the test should reveal.

The equalised-profit benchmark still tracks gross output far better than a
labour-only markup, but industry surplus-value rates are not equalised in any
strict sense.

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
- gross-output deflators for `GO_i`;
- a supplier-weighted intermediate-input deflator for `C_i`.

The intermediate-input deflator uses the 2017 Use table to weight each
industry's input bundle, and proxies each commodity's price with the
gross-output deflator of its broad sector. Real accounts are then:

```
C_real = C / (input_price / 100)
K_real = C_real + V_real
S_real = N_real - V_real
r_real = S_real / K_real
R_real = S_real / M_real
```

On 2005-2023, real industry value added grew **1.80%/yr** and real gross output
**1.67%/yr**. The real market profit rate is **20.1%** in 2023, essentially the
same as the nominal **20.2%**; real dispersion is higher (weighted CV **0.659**
vs **0.609**).

Caveats: the input weights are fixed at 2017, commodity prices are broad-sector
proxies, and capital is deflated by the industry's own gross-output index. The
nominal prices-of-production comparison remains the primary value-theory test.

## Predictive power and gravitation

A "center of gravitation" is a value that market prices are pulled toward over
time. The project tests three separate claims on the 65 market industries:

1. deviations `d = log(GO / PP)` are temporary, not permanent;
2. when market output is above `PP`, future market output grows more slowly
   (or `PP` rises), closing the gap;
3. `PP` predicts future market output better than a naive forecast.

**Deviations are persistent but not permanent.** Mean absolute deviation is
**12.4%** (gross-output weighted 11.4%; median 8.6%); 89.7% of observations are
within ±25%. Lag-1 autocorrelation is **0.972**, and the estimated half-life of
a deviation is **2.2 years**. Panel ADF rejects a unit root in the Fisher sense
(p<0.001), but only 14% of industries reject individually.

**The adjustment is now two-way, and market output does move toward PP.**
Panel error-correction with industry and year effects gives:

- market output adjustment: `β = -0.163` (p=0.015), the sign gravitation
  predicts; half-life of the output response is about 3.9 years;
- price-of-production adjustment: `β = +0.105` (p=0.035).

So the gap closes through both channels: market output moves down toward `PP`
when it is above it, and `PP` also rises toward market output. With actual
capital stocks, the first channel is statistically significant, which the old
`M_i = K_i` proxy did not deliver.

**PP still does not forecast better than a random walk.** Pooled out-of-sample
log RMSE, 2008-2023:

- 1 year: naive 0.120, AR(1) 0.120, ECM 0.120, PP **0.213**
- 3 years: naive 0.202, AR(1) 0.174, ECM 0.172, PP **0.256**
- 5 years: naive 0.258, AR(1) 0.199, ECM 0.199, PP **0.304**

The PP forecast is worse than naive at every horizon; the bootstrap confidence
interval for the RMSE difference excludes zero. The ECM is marginally better
than AR(1) at three years (RMSE difference -0.0019, confidence interval excludes
zero) but the gain is economically negligible.

**The long-run centre tells a sharper story.** I also build a slow-moving
benchmark with five-year trailing averages of cost and capital and a five-year
average profit rate:

```
PP*_it = K_trend_it + R_long_t * M_trend_it
```

- Mean absolute deviation: **15.2%**; 81.5% within ±25%.
- Autocorrelation: **0.901**; half-life **1.8 years**.
- Output adjustment: `β = -0.134` (p=0.001); PP adjustment: `β = +0.181`
  (p<0.001).
- 52% of industries reject a unit root individually.
- Forecast log RMSE, 1/3/5 years: PP **0.238 / 0.289 / 0.349** vs naive
  **0.120 / 0.202 / 0.258**.

The long-run benchmark is farther from market output, so deviations are larger,
but they are **less persistent** and market output adjusts toward it more
strongly. That is the clearest evidence of gravitation in the project. PP still
fails the out-of-sample test, so the result is slow adjustment without
forecast power.

**Verdict:** with actual capital stocks, the error-correction evidence supports
**slow, two-way gravitation**: market output does adjust toward `PP`, and `PP`
also adjusts toward market output. But the predictive claim fails: `PP` is much
worse than a random walk at every horizon. The defensible summary is "weak and
slow gravitation, no forecast power", not "prices of production are irrelevant"
and not "the theory is confirmed." The remaining limitations are the
value-based output measure, the remaining broad inventory allocation for
mining/utilities/construction and "other" industries, annual data, and only 26
years per industry.

The full derivation, tables and caveats are in `docs/gravitation.md`.

## Moseley vs Sraffa vs Shaikh

The project builds three price benchmarks from the same BEA Use table:

- **Sraffa prices of production**, `p = (1+r)(p A + w l)`, a simultaneous
  fixed point with a uniform profit rate on flow capital;
- **Shaikh iterated prices**, the same system solved by cost-plus iteration
  with an endogenous profit rate;
- **direct prices / labour values**, `lambda = l (I - A)^-1`.

Moseley's benchmark uses the stock of advanced capital and `R = S/M`; Sraffa and
Shaikh use the flow cost matrix and `r = S/K`. They are different capital
concepts, not two estimates of one parameter. `A_t` is the **deflated** annual
Use matrix (2017 dollars), and labour values now use measured FTE-based hours
rather than compensation-allocated hours.

Fit on the same 65 market industries, 2005-2023:

- **Moseley `PP`**: MAE **13.7%**, RMSE **23.0%**, corr **0.983**, slope
  **1.046**, within 25% **88.5%**, mean gap **-7.4%**.
- **Sraffa `PP_Sraffa`**: MAE **16.8%**, RMSE **20.5%**, corr **0.971**, slope
  **0.982**, within 25% **77.2%**, mean gap **-2.4%**.
- **Shaikh iterated `PP_Shaikh`**: MAE **17.2%**, RMSE **21.3%**, corr
  **0.973**, slope **0.985**, within 25% **76.9%**, mean gap **-3.1%**.
- **Direct prices (labour values)**: MAE **37.2%**, RMSE **48.8%**, corr
  **0.887**, slope **0.893**, within 25% **42.1%**, mean gap **-8.0%**.

Gravitation comparison:

- **Moseley**: mean gap 12.4%, half-life 1.7y, output adjustment `-0.240`
  (p=0.008), PP adjustment `+0.098` (p=0.164), 1y forecast RMSE 0.213.
- **Sraffa `PP_Sraffa`**: mean gap 17.1%, half-life 2.2y, output adjustment
  `+0.068` (p=0.195), PP adjustment `+0.341` (p<0.001), 1y forecast RMSE 0.253.
- **Shaikh iterated `PP_Shaikh`**: mean gap 17.3%, half-life 2.4y, output
  adjustment `+0.078` (p=0.083), PP adjustment `+0.333` (p<0.001), 1y forecast
  RMSE 0.254.
- **Direct prices**: mean gap 35.7%, half-life 2.7y, output adjustment `+0.032`
  (p=0.456), 1y forecast RMSE 0.460.
- Naive forecast RMSE: **0.120**.

The Sraffian fixed point is a static center: it fits the aggregate level well
(low RMSE, small bias, slope near one) but does not attract output — output does
not adjust toward it, while it adjusts toward output. The Shaikh iteration
starts from labour values, recomputes the profit rate each round, and converges
in **29 rounds on average** (maximum 34) to essentially the Sraffian center; the
model-implied real rate averages **35.9%** against **23.2%** observed. So the
iteration adds convergence diagnostics, not a different price benchmark. Direct
labour values fit worst.

There is no single winner. **Moseley fits typical industry errors and forecasts
better.** **Sraffa calibrates the aggregate level better.** **Shaikh's iteration
converges to Sraffa.** All three fail the random-walk forecast benchmark.

See `docs/sraffa.md` and `docs/shaikh.md`.

## State space for real competition

The project now writes the measurement layer for a stock-flow cross-dual model:
**65 market industries**, 2005-2023 for the complete state table, with 26 annual
current-price matrices (1998-2023) and 19 deflated real matrices (2005-2023).

The state table contains:

- `price` — gross-output price index, 2017 = 1
- `quantity` — real gross output, millions of 2017 dollars
- `capital` — real net fixed capital stock, millions of 2017 dollars
- `investment` — real gross investment
- `depreciation` — real depreciation
- `utilization` — output-capital ratio, normalised to 1 in 2017
- `wage_rate` — aggregate money wage, dollars per hour
- `wage_rate_i` — industry money wage, dollars per hour
- `fte`, `labour_hours`, `labour_coefficient`, `labour_coefficient_real`
- `capital_current`, `capital_real`

`technical_matrices.csv` stores the long annual matrix
`A_t[c,j] = U_t[c,j] / GO_t[j]`.

This is deliberately a **measurement dataset**, not a behavioural model yet.
It supplies every variable needed for a stock-flow cross-dual system except
demand and the adjustment parameters. The main remaining limitations are
current-price `A_t`, broad-sector deflators, an output-capital utilization
proxy, and industry hours allocated by compensation.

See `docs/state_space.md`.

## Stock-flow simulation

The state space now feeds a first stock-flow cross-dual model:

```
cost_i = (p A)_i + w l_i
r_i    = (p_i - cost_i) / cost_i
r_bar  = (p q - cost q) / (cost q)

p_i' = p_i exp(-alpha (r_i - r_bar))
q_i' = q_i + beta (D_i - q_i)
I_i  = k_i [gamma0 + gamma1 (r_i - r_bar) + gamma2 (u_i - 1)]
k_i' = k_i - depreciation_i + I_i
w'   = w [1 + phi (U - 1)]
```

Final demand is reconstructed from observed output and the real input matrix,
`F_t = q_t - A_t q_t`, and treated as exogenous. This is a dynamic adjustment
model, not a complete demand system.

Calibrated fit, 2005-2023:

- price: log RMSE **0.134**, correlation **0.284**
- quantity: log RMSE **0.108**, correlation **0.995**
- capital: log RMSE **0.237**, correlation **0.976**
- investment: log RMSE **0.582**, correlation **0.729**

Output and capital fit well. Relative prices do not. The price block is the weak
part, and `beta` and `gamma2` hit their calibration bounds. The model is a first
structural layer, not a finished real-competition model.

See `docs/stock_flow.md`.

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

- `data/processed/industries.csv`, `industries_shaikh.csv`,
  `shaikh_iterations.csv`, `industry_employment.csv`,
  `industry_employment_coverage.csv`, `state_space.csv`, `technical_matrices.csv`,
  `technical_matrices_real.csv`, `state_space_macro.csv`, `state_space.json`,
  `industry_capital.csv`,
  `industry_fixed_assets.csv`, `industry_government_housing.csv`,
  `industry_inventories.csv`
- `output/industries.json`
- `output/tables/industry_summary.csv`, `industry_latest.csv`,
  `industry_proxy_sensitivity.csv`, `industry_reconciliation.csv`,
  `industry_capital_coverage.csv`, `benchmark_comparison.csv`,
  `benchmark_gravitation.csv`
- `output/tables/gravitation_summary.csv`, `gravitation_by_year.csv`,
  `gravitation_ecm.csv`, `gravitation_forecast_metrics.csv`,
  `gravitation_forecast_comparisons.csv`
- `output/tables/gravitation_long_run_summary.csv`,
  `gravitation_long_run_ecm.csv`, `gravitation_long_run_forecast_metrics.csv`,
  `gravitation_long_run_forecast_comparisons.csv`
- `output/tables/stock_flow_metrics.csv`, `stock_flow_trajectories.csv`
- `output/gravitation.json`, `output/shaikh.json`, `output/stock_flow.json`
- `output/figures/industry_dispersion.png`, `pp_vs_go.png`,
  `gravitation_deviation.png`, `gravitation_forecast.png`

## Project layout

```
config/            settings.yaml, series.yaml, sectors.yaml, industry_capital.yaml
src/usa_marxian/
  config.py        typed config + series catalog
  data/            FRED, BLS, BEA, BEA IO, sector deflators, cache, quality
  model/           MELT, equalities, robustness, industries, Shaikh, state space, stock flow
  analysis/        LTV, diagnostics, property check, gravitation, comparison
  viz/             plots
  pipeline.py      macro and industry pipelines
  cli.py           `usa-marxian` command
tests/             offline unit tests
docs/              model derivation, data sources, industry notes, Sraffa, Shaikh, state space, stock flow
notebooks/         exploratory notebooks
data/raw           cached downloads (gitignored)
data/processed     panels, accounts, quality reports (gitignored)
output/            tables, figures, JSON reports (gitignored)
```

## Roadmap

1. **Residual inventory detail.** Manufacturing and retail inventories are
   detailed from BEA Table 1BUC, and government/housing capital is now actual.
   Still outstanding: detailed inventories for mining/utilities/construction and
   “other” industries (about 11% of inventory value).
2. **Refine the intermediate-input deflator.** It now uses 2017 Use-table
   weights and broad-sector supplier prices. Replace the broad-sector proxies
   with commodity-level prices and chain the weights over time.
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
