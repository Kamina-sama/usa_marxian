# usa_marxian

> **New here?** Read the [plain-language guide](docs/plain_language.md) first.
> It explains the ideas, the tests and the results without assuming economics
> or statistics.
>
> For two terms that may be confusing at first — **closing the demand side** and **the
> unit-price slope** — see [how to read the model](docs/reading_the_model.md).
>
> Want pictures instead of tables? [Reading the figures](docs/figures.md) walks
> through the six findings plots in the same plain language.

An empirical framework for testing Fred Moseley's **macro-monetary
interpretation** of Marx's theory (*Money and Totality*, Brill 2016, ch. 2) on
US macroeconomic data.

## In plain English

Marx argued that value comes from labour. Moseley argues that the aggregate
money accounts already express that value, and that competition spreads the
surplus across industries so that "prices of production" are centres around
which market prices gravitate. This project builds those accounts from US data
and asks whether that story fits.

What we find, in one breath: the accounting is consistent; Moseley's benchmark
tracks industry revenues and unit prices best, especially once taxes are treated
separately and working capital is included. Sraffa and Shaikh capture relative
prices moderately; direct labour values track prices poorly — which is what
Marx predicted, since he denied that commodities sell at their values. Gravitation
is weak, and forecasting is no better than a random walk. Prices of production
have empirical content, but the strong claim that they are centres of gravitation
is not supported by this data.

For the full non-technical walkthrough, see
[`docs/plain_language.md`](docs/plain_language.md).

## Does Moseley's interpretation hold up?

This project exists to test Fred Moseley's macro-monetary reading, so his own
claims are reported first. Six are testable; four pass.

**Passes.**

- **Total profit equals total surplus-value, measured independently.** `S` is a
  residual, so comparing it with itself would be circular. Compared with NIPA
  property income plus taxes on production: mean ratio **1.011**, mean gap
  **+58.2 bn** (+2.5% of `S`), correlation **0.997**. This is the strongest
  non-circular result in the project.
- **The price equation `PP_i = K_i + R·M_i`.** On the same 60 market industries,
  with `M` including circulating capital: Moseley **10.4%** MAE and corr 0.991,
  against Sraffa 16.5%, Shaikh 17.8% and labour values 36.5%. His own price
  equation is the best-performing benchmark in the data.
- **Capital advanced is a stock, not a flow.** The stock-based benchmark beats
  the flow-based one by 6.1 percentage points of MAE — the empirical content of
  the disagreement with Sraffa. One caveat, since it cuts against the framing:
  the headline variant adds one year of circulating capital to the stock, so it
  is a hybrid. The pure stock measure is kept as a variant and still beats
  Sraffa, by 4.1 points.
- **The MELT is a monetary aggregate.** `m ≡ P·q` holds to machine precision, so
  no transformation of values into prices passes through it. That is what the
  single-system reading asserts.

**Fails.**

- **`R` does not regulate industry rates.** `usa-marxian regulation`, with `M`
  including circulating capital: industry rates appear to converge on the
  aggregate (β = **−0.281**, p<0.0001, half-life 2.1 years), but that coefficient
  is *identical* to the one obtained against each industry's own mean — two-way
  fixed effects cannot separate them. Dispersion is flat (CV **+0.08%/yr**,
  IQR −0.02 pp/yr), and capital does not flow toward above-average profit rates
  (β = **+0.082**, p=0.252).
  The good fit of the price equation is therefore consistent with a common
  markup rather than with capital mobility equalising rates.
- **Profit rates are far from equalised**: weighted CV **0.609**, p90/p10
  **6.10** in 2023.

The defensible summary: Moseley's accounting identities and his price equation
are supported by this data; the regulating mechanism that is supposed to make
them more than a common markup is not.

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
values, and about 46% of industry inventory value still uses broad-group
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
.venv/bin/usa-marxian figures       # rebuild the findings figures from artifacts
.venv/bin/usa-marxian value-tests   # MELT identity audit + distribution test
.venv/bin/usa-marxian labour-power  # value of labour power and its identification
.venv/bin/usa-marxian regulation    # does the aggregate profit rate regulate?
.venv/bin/usa-marxian all           # everything above
.venv/bin/pytest                    # offline tests
```

Or with `make`:

```bash
make install
make all          # data + analysis + industries + figures + value tests
make figures      # just the figures (fast, no downloads)
make value-tests  # just the MELT identity audit
make labour-power # just the value of labour power
make regulation   # just the profit-rate regulation test
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
- **BEA GDP-by-Industry tables** (free key) for the 71-industry price and
  quantity indexes behind the reported industry results.
- **BLS** public API v1 for direct BLS series (v2 with a free key).

Optional free keys unlock the official APIs and higher quotas. One of them
changes results rather than quotas: without `BEA_API_KEY` the industry layer
falls back to the broad-sector FRED indexes, which start in 2005, so the real
accounts and the state space lose 1998-2004. Copy `.env.example` to `.env`:

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

- LTV slope on real new value: **1.54 to 2.24** across specifications; baseline
  **2.22** (95% CI 2.06-2.38). The unit-slope restriction is rejected in every
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
  Zivot-Andrews p=0.904). Its level is not stationary. Note that real MELT is
  *identically* real new value per hour, i.e. labour productivity, so this is a
  statement about productivity (see [`docs/value_theory.md`](docs/value_theory.md)).
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
  come from BEA Table 1BUC at detailed NAICS level (23 IO industries, **53.7%**
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

- Market general rate of profit `R = S/M`: **20.2%** in 2023 with fixed assets
  plus inventories as `M`, or **10.9%** when `M` includes circulating capital
  (the headline Moseley variant); full sample 10.3% and 7.1% respectively.
- Market surplus-value rate on cost `S/K`: **23.8%**.
- Market weighted CV of `r_i`: **0.609** in 2023 (sample mean 0.703);
  p90/p10 **6.10**.
- Full-sample CV: **2.109** in 2023 (sample mean 2.296), dominated by housing
  and government units.
- MAE of `PP` vs gross output (sample means): **11.8%** full, **10.8%**
  market-only.
- MAE of the long-run `PP*`: **15.4%** full, **13.1%** market-only.
- MAE of the labour-only benchmark `PP_V`: **53.1%**.
- Correlation of `PP` with gross output: **0.942** full, **0.990** market-only.
- Share of industries within 25% of `PP` (sample means): **88.1%** full,
  **93.1%** market-only.
- Proxy sensitivity, full-sample MAE: fixed assets + inventories **12.6%**,
  cost **13.3%**, output **11.0%**, value-added **9.0%**. Market-only MAE:
  **13.7%**, **10.5%**, **8.7%**, **7.1%**.

The market sample is the meaningful comparison. Adding circulating capital to
`M` improves its fit — market MAE 10.8%, against 13.7% on the fixed-asset stock
alone — while the full-sample numbers move because government and housing
capital are actual and very large relative to their surplus-value.
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
deflator. For industry accounts the project uses BEA's GDP-by-Industry
71-industry chain-type price indexes:

- **TableID 11** value-added deflator for `N_i`, `V_i` and `S_i`;
- **TableID 18** gross-output deflator for `GO_i`;
- **TableID 23** intermediate-inputs deflator for `C_i`.

Because all three are industry indexes, no supplier weights are needed. Real
accounts are then:

```
C_real = C / (input_price / 100)
K_real = C_real + V_real
S_real = N_real - V_real
r_real = S_real / K_real
R_real = S_real / M_real
```

Without a `BEA_API_KEY` the pipeline falls back to the broad-sector FRED `VAPI*`
and `GOPI*` series, and `C_i` is then deflated by a supplier-weighted proxy: 2017
Use-table input shares applied to the supplying sectors' gross-output deflators.
That fallback starts in 2005.

On 2005-2023, real industry value added grew **1.79%/yr** and real gross output
**1.66%/yr** (1.95%/yr and 1.93%/yr over the longer 1998-2023 span). The real
market profit rate is **20.2%** in 2023, essentially the same as the nominal
**20.2%**; real dispersion is higher (weighted CV **0.665** vs **0.609**).

Caveats: capital is deflated by the industry's own gross-output index, and the
deflated `A_t` uses the gross-output indexes of the supplying industries rather
than commodity prices. The nominal prices-of-production comparison remains the
primary value-theory test.

## Predictive power and gravitation

A "center of gravitation" is a value that market prices are pulled toward over
time. The project tests three separate claims on the 65 market industries:

1. deviations `d = log(GO / PP)` are temporary, not permanent;
2. when market output is above `PP`, future market output grows more slowly
   (or `PP` rises), closing the gap;
3. `PP` predicts future market output better than a naive forecast.

**Deviations are persistent but not permanent.** Mean absolute deviation is
**10.4%** (gross-output weighted 9.5%; median 8.7%); 93.1% of observations are
within ±25%. Lag-1 autocorrelation is **0.957**, and the estimated half-life of
a deviation is **2.0 years**. Panel ADF rejects a unit root in the Fisher sense
(p<0.001), but only 15% of industries reject individually.

**The adjustment runs the other way.** Panel error-correction with industry and
year effects, on the working-capital benchmark:

- market output adjustment: `β = -0.091` (s.e. 0.077, p=0.239) — the sign
  gravitation predicts, but not distinguishable from zero;
- price-of-production adjustment: `β = +0.201` (s.e. 0.070, p=0.004) — and this
  one is significant.

The gap does close (`Δd` on lagged `d` gives `β = -0.291`, p<0.001, half-life
2.0 years), but it closes because the benchmark moves toward market output, not
because output moves toward the benchmark. That is one-way adjustment in the
direction opposite to the theory's claim.

This is the one result that depends heavily on which `M` you use. On the
stock-capital variant the output coefficient is significant (`-0.163`, p=0.015)
and the adjustment is genuinely two-way; adding working capital to `M`
strengthens the revenue fit and weakens the adjustment evidence. Since the
working-capital variant is the better-fitting benchmark, its result is the one
reported here.

**PP still does not forecast better than a random walk.** Pooled out-of-sample
log RMSE, 2008-2023:

- 1 year: naive 0.120, AR(1) 0.120, ECM 0.120, PP **0.176**
- 3 years: naive 0.202, AR(1) 0.174, ECM 0.172, PP **0.230**
- 5 years: naive 0.258, AR(1) 0.199, ECM 0.199, PP **0.284**

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

- Mean absolute deviation: **13.1%** (weighted 14.4%); 85.0% within ±25%.
- Autocorrelation: **0.861**; half-life **1.8 years**.
- Output adjustment: `β = -0.117` (s.e. 0.041, p=0.004); PP adjustment:
  `β = +0.204` (p<0.001).
- 57% of industries reject a unit root individually.
- Forecast log RMSE, 1/3/5 years: PP **0.209 / 0.269 / 0.335** vs naive
  **0.120 / 0.202 / 0.258**.

This is the one result that the switch to working capital does **not** weaken —
it strengthens it. Deviations are smaller than on the stock measure (13.1%
against 15.2%), less persistent (autocorrelation 0.861 against 0.901), and the
output coefficient stays significant at the gravitation-predicted sign. The
contrast with the short-run benchmark is informative: current `PP` is built from
current costs, so it moves with output almost mechanically, which is why the
short-run test looks like prices chasing output. The slow centre does not have
that property, and it behaves as the theory says it should.

PP still fails the out-of-sample test, so the result is slow adjustment without
forecast power.

**Verdict:** the answer depends on which benchmark you call the centre. On the
current one there is no detectable gravitation — the benchmark moves toward
market output, not the reverse. On the slow five-year centre there is: market
output adjusts toward `PP*` with the sign the theory predicts (`β = -0.117`,
p=0.004). The predictive claim fails either way: `PP` is worse than a random
walk at every horizon. The defensible summary is "gravitation at the slow centre
only, and no forecast power", not "prices of production are irrelevant" and not
"the theory is confirmed". The remaining limitations are the value-based output
measure, the remaining broad inventory allocation for
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
Use matrix (2017 dollars), and labour values now use FTE hours split by BLS
manufacturing totals rather than compensation-allocated hours.

Fit on the same 60 market industries, 1998-2023:

- **Moseley stock-capital `PP`** (variant): MAE **12.4%**, RMSE **19.4%**, corr
  **0.983**, slope **1.043**, within 25% **89.5%**, mean gap **-5.7%**.
- **Moseley profit-rate `PP`** (taxes separate): MAE **9.3%**, RMSE **12.1%**,
  corr **0.992**, slope **1.029**, within 25% **95.8%**, mean gap **-3.9%**. This
  is the best fit of the three variants.
- **Moseley working-capital `PP`** (headline): MAE **10.4%**, RMSE **13.2%**,
  corr **0.991**, slope **1.035**, within 25% **94.2%**, mean gap **-4.4%**.
- **Sraffa `PP_Sraffa`**: MAE **16.5%**, RMSE **24.5%**, corr **0.968**, slope
  **0.987**, within 25% **84.0%**, mean gap **-5.1%**.
- **Sraffa with fixed capital**: MAE **17.5%**, RMSE **38.8%**, corr
  **0.913**, slope **0.971**, within 25% **84.7%**, mean gap **-6.4%**. Fixed
  capital improves typical errors and unit prices but worsens the RMSE tails.
- **Shaikh iterated `PP_Shaikh`**: MAE **17.8%**, RMSE **26.6%**, corr
  **0.962**, slope **0.980**, within 25% **78.8%**, mean gap **-5.2%**.
- **Shaikh with fixed capital**: MAE **19.6%**, RMSE **44.5%**, corr
  **0.888**, slope **0.966**, within 25% **80.6%**, mean gap **-7.1%**. Unit
  prices improve; revenue tails worsen.
- **Regulating capital `PP_reg`**: MAE **16.3%**, RMSE **24.1%**, corr
  **0.964**, slope **0.988**, within 25% **84.4%**, mean gap **-1.9%**.
- **Direct prices (labour values)**: MAE **36.5%**, RMSE **47.9%**, corr
  **0.888**, slope **0.872**, within 25% **43.3%**, mean gap **-8.7%**.

Gravitation comparison:

- **Moseley working-capital** (headline): mean gap 10.4%, half-life 2.0y,
  output adjustment `-0.091` (p=0.239), PP adjustment `+0.201` (p=0.004),
  1y forecast RMSE 0.176.
- **Moseley stock-capital** (variant): mean gap 12.4%, half-life 2.2y, output
  adjustment `-0.163` (p=0.015), PP adjustment `+0.105` (p=0.035), 1y forecast
  RMSE 0.213.
- **Moseley profit-rate** (variant): mean gap 9.2%, half-life 2.1y, output
  adjustment `-0.080` (p=0.330), PP adjustment `+0.207` (p=0.006), 1y forecast
  RMSE 0.165.
- **Sraffa `PP_Sraffa`**: mean gap 15.2%, half-life 5.8y, output adjustment
  `+0.107` (p=0.008), PP adjustment `+0.220` (p<0.001), 1y forecast RMSE 0.206.
- **Sraffa with fixed capital**: mean gap 15.5%, half-life 5.1y, output
  adjustment `+0.044` (p=0.039), PP adjustment `+0.171` (p<0.001), 1y forecast
  RMSE 0.227. The wrong-signed output coefficient shrinks but remains positive.
- **Shaikh iterated `PP_Shaikh`**: mean gap 16.3%, half-life 5.1y, output
  adjustment `+0.111` (p=0.006), PP adjustment `+0.237` (p<0.001), 1y forecast
  RMSE 0.214.
- **Shaikh with fixed capital**: mean gap 17.2%, half-life 5.3y, output
  adjustment `+0.036` (p=0.034), PP adjustment `+0.158` (p<0.001), 1y forecast
  RMSE 0.246. The wrong-signed output coefficient is smaller but remains
  positive.
- **Regulating capital `PP_reg`**: mean gap 15.9%, half-life 5.5y, output
  adjustment `+0.119` (p=0.008), PP adjustment `+0.237` (p<0.001), 1y forecast
  RMSE 0.220.
- **Direct prices**: mean gap 35.4%, half-life 4.4y, output adjustment `+0.081`
  (p=0.020), 1y forecast RMSE 0.451.
- Naive forecast RMSE: **0.120**.

The Sraffian fixed point is a static center: it fits the aggregate level well
(low RMSE, small bias, slope near one) but does not attract output — output does
not adjust toward it, while it adjusts toward output. The Shaikh iteration
starts from labour values, recomputes the profit rate each round, and converges
in **26.5 rounds on average** (maximum 31) to essentially the Sraffian center;
the model-implied real rate averages **26.9%** against **17.6%** observed. So the
iteration adds convergence diagnostics, not a different price benchmark. Direct
labour values fit worst.

There is no single winner. **Moseley fits typical industry errors and forecasts
better.** **Sraffa calibrates the aggregate level better.** **Shaikh's iteration
converges to Sraffa.** All three fail the random-walk forecast benchmark.

A regulating-capital benchmark `PP_reg` is available when a `CENSUS_API_KEY` is
set. It uses 6-digit Census unit costs: `factor = 1 - theta * (1 -
unit_cost_min / unit_cost)`, with `theta = 0.10`, applied to the Sraffa price.
With the live data it covers 60 of 65 market industries and gives MAE 18.5%,
mean gap -1.9% — slightly better than Sraffa's 16.5% MAE and much better
aggregate calibration. It remains a sub-industry proxy, not plant-level
regulating capitals.

See `docs/sraffa.md` and `docs/shaikh.md`.

### Unit-price test

The revenue comparison can be dominated by industry size. A separate test
compares **relative unit prices** after normalising every series to a
quantity-weighted geometric mean of one.

- **Moseley working-capital `PP/Q`** (headline): 0.090, corr **0.884**, slope 0.603.
- Moseley stock-capital `PP/Q` (variant): log MAE 0.119, corr **0.794**, slope 0.475.
- Moseley profit-rate `PP/Q` (variant): 0.080, corr **0.896**, slope 0.646.
- Sraffa: 0.132, corr **0.731**, slope 0.463.
- Sraffa with fixed capital: 0.131, corr **0.831**, slope 0.443.
- Shaikh: 0.143, corr **0.713**, slope 0.413.
- Shaikh with fixed capital: 0.152, corr **0.806**, slope 0.370.
- Regulating: 0.138, corr **0.727**, slope 0.441.
- Direct prices: 0.348, corr 0.189, slope 0.055.

`Q` is the BEA gross-output quantity index (TableID 16), not `GO/price_obs`.
With an independent quantity index, Moseley's unit-price fit is genuine:
working-capital Moseley reaches corr **0.884** and slope **0.603**. Sraffa and
Shaikh are second, and direct labour values are poor.

An earlier version used `PP/GO` as a “relative price.” That was wrong: `PP/GO`
is a price ratio, not a unit price. The BEA quantity index fixes the test.

Diagnostics: `PP/GO` has mean 1.044 and standard deviation 0.125, and the revenue
ratio accounts for 39% of the variance of Moseley unit prices. The within-sector
test is now identified: Moseley's within-sector correlation is 0.873, Sraffa
0.743, Shaikh 0.734. The value-added and gross-output deflators correlate at
0.935. The reliability correction is no longer decisive: at a 39% variance share
it would push the within-sector slopes above one, which is not credible.

See `docs/unit_prices.md`.

A caution on interpretation. This comparison is between prices and labour
*values*, so it tests proportionality — the Ricardian hypothesis. Marx denied
that commodities sell at their values and argued that prices of production
deviate from them systematically, so a poor fit here is not a rejection of his
theory. What would test him is whether the deviation follows the composition of
capital; that is a separate exercise.

## State space for real competition

The project now writes the measurement layer for a stock-flow cross-dual model:
**65 market industries**, 1998-2023 for the complete state table, with 26 annual
current-price matrices and 26 deflated real matrices.

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
industry-level rather than commodity-level price indexes, an output-capital
utilization proxy, and hours-per-FTE calibrated to BLS detail for manufacturing
only.

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

Final demand is now parsed from the BEA Use table:

```
D_i = sum_j A_ij q_j + C_i + I_i + G_i + X_i - M_i + residual_i
```

where `I_i` is simulated investment and `residual_i` is an explicit
statistical/other term (about 8% of output) that closes the observed base year.
`C`, `G`, `X` and `M` are exogenous real components; investment is endogenous.
For a plain explanation of what “closing demand” means and why the fit changed,
see [`docs/reading_the_model.md`](docs/reading_the_model.md).

Fit, 1999-2023 (63 simulated industries):

- price: log RMSE **0.304**, correlation **0.319**
- quantity: log RMSE **0.196**, correlation **0.983**
- capital: log RMSE **0.352**, correlation **0.918**
- investment: log RMSE **0.495**, correlation **0.801**

Closing demand makes the model structural but worsens the fit relative to the
exogenous-demand version (quantity 0.108, capital 0.237). Output and capital
still track the data; relative prices do not. `simulate(..., demand_shock=...)`
supports demand-shock counterfactuals.

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
  `shaikh_iterations.csv`, `unit_prices.csv`, `industry_employment.csv`,
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
- `data/processed/final_demand.csv`, `data/processed/industry_prices.csv`
- `output/tables/unit_price_comparison.csv`, `unit_price_by_year.csv`,
  `unit_price_gravitation.csv`, `price_revenue_ratio.csv`,
  `price_revenue_ratio_by_year.csv`, `price_within_sector.csv`
- `output/gravitation.json`, `output/shaikh.json`, `output/stock_flow.json`,
  `output/unit_prices.json`, `output/price_diagnostics.json`
- `output/figures/industry_dispersion.png`, `pp_vs_go.png`,
  `gravitation_deviation.png`, `gravitation_forecast.png`

After `figures` (also run at the end of `all`):

- `output/figures/findings_benchmark_fit.png` — revenue fit per benchmark
- `output/figures/findings_unit_prices.png` — relative unit prices, model vs data
- `output/figures/findings_gravitation.png` — adjustment coefficients with 95% CI
- `output/figures/findings_forecast.png` — forecast error by horizon
- `output/figures/findings_dispersion.png` — profit-rate dispersion, nominal vs real
- `output/figures/findings_capital.png` — capital composition and inventory quality

Plain-language guide to those six: [`docs/figures.md`](docs/figures.md).

After `value-tests` (also at the end of `all`):

- `output/value_theory.json` — identity audit, distribution test, concept spread
- `output/tables/melt_concept_spread.csv` — MELT level and growth by concept

After `labour-power`:

- `output/value_of_labour_power.json` — basket panel summary and identification test
- `output/tables/volp_panel.csv` — the year-by-year panel behind it

After `regulation`:

- `output/regulation.json` — convergence, capital mobility, dispersion
- `output/tables/profit_rate_regulation.csv` — dispersion by year

The value-theory material is written up in [`docs/value_theory.md`](docs/value_theory.md);
the regulation test in [`docs/model.md`](docs/model.md).

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
docs/              plain-language guide, model derivation, data sources, industry notes, Sraffa, Shaikh, state space, stock flow, unit prices, value theory, figure guide
notebooks/         exploratory notebooks
data/raw           cached downloads (gitignored)
data/processed     panels, accounts, quality reports (gitignored)
output/            tables, figures, JSON reports (gitignored)
```

## Roadmap

### Done

- **Macro accounts** — Moseley's `P, C, N, V, S, K, L, M, m, R`, with alternative
  value-added, capital-stock, hours and MELT specifications.
- **Industry accounts** — 71 BEA Use-table industries; actual fixed assets,
  government and housing capital, detailed manufacturing/retail inventories,
  industry CFC, and net surplus-value.
- **Sector deflators** — 71-industry value-added, gross-output and
  intermediate-input indexes (BEA TableIDs 11, 18 and 23), plus real profit
  rates; the keyless fallback is a supplier-weighted broad-sector proxy.
- **Property-income check** — `S = N - V` against independent NIPA property income.
- **Gravitation tests** — deviation persistence, panel unit roots, panel error
  correction, and out-of-sample forecasts for current and long-run `PP`.
- **Input-output value magnitudes** — labour values via the Leontief inverse and
  deflated annual `A_t`.
- **Sraffa prices of production** — the fixed point `p = (1+r)(pA+wl)`, plus the
  Shaikh endogenous-`r` iteration and a toy cross-dual simulation.
- **State space** — `p, q, k, I, u, w, l, A_t`, with FTE/BLS industry hours and
  industry wage rates, feeding a first stock-flow cross-dual model.
- **Regulating capitals** — a sub-industry cost-dispersion `PP_reg` proxy (Census, key-gated).
- **MELT audit** — identity check showing `m ≡ P·q` and `melt_real ≡ q`, so the
  MELT cannot be tested against distribution; the measurable question is its
  growth rate, not its level.

### Remaining, in rough priority order

1. **Value theory beyond the identity** — the MELT route is closed and the value
   of labour power is not separately identified (see
   [`docs/value_theory.md`](docs/value_theory.md)). What remains testable is
   value as a regulator of price *changes*, the predictive content of labour
   values, and temporal versus simultaneist valuation. The one positive result
   so far is the price-value gradient across uses: consumption sells 13% below
   its labour value and investment 13% above, in every year of the sample.
2. **Residual inventory detail** — mining/utilities/construction and “other”
   industries (about 46% of inventory value) still use broad-group allocation.
3. **Commodity-level intermediate-input deflator for the keyless path** — the
   keyed build already uses BEA TableID 23; without `BEA_API_KEY` the input
   deflator is still a supplier-weighted broad-sector proxy.
4. **Plant-level cost heterogeneity** — the regulating-capital benchmark is a
   concentration proxy; true regulating capitals need Census microdata or ASM
   size-class cost distributions.
5. **Demand closure** — the cross-dual/stock-flow model uses exogenous final
   demand; add consumption, investment demand, government and net exports.
6. **Estimation and inference** — the stock-flow parameters are point-calibrated;
   add bootstrap uncertainty, out-of-sample validation and identifiability checks.
7. **Industry-specific hours** — manufacturing now uses BLS CES totals; extend
   BLS CES detail to the remaining industries where series exist.
8. **Structural-break econometrics** — Bai-Perron multiple breaks, rolling
   regressions, and regime-dependent profit-rate trends.
9. **Cross-country comparison** — the World Bank endpoint is documented; the same
   accounting can be applied to other economies.

## Reference

Moseley, Fred. 2016. *Money and Totality: A Macro-Monetary Interpretation of
Marx's Logic in Capital and the End of the 'Transformation Problem'*.
Chapter 2 is the algebraic summary used here.

## License

MIT for the code. The book PDF is the user's own copy and is not covered by
this license.
