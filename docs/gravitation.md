# Predictive power and gravitation

## The question in plain language

A "center of gravitation" is a value that market prices are pulled toward over
time. If prices of production are centers of gravitation, then:

1. the gap between market gross output and prices of production should be
   temporary, not a permanent industry characteristic;
2. when market output is above the price of production, future market output
   should grow more slowly (or the price of production should rise), closing
   the gap;
3. prices of production should help predict future market output better than a
   naive "same as last year" forecast.

The tests below check each claim separately. Government units and housing are
excluded: their "prices" are not market prices, even though their capital stocks
are now actual.

## What is compared

For industry `i` in year `t`:

```
d_it = log(GO_it / PP_it)
```

`GO_it` is BEA gross annual industry output (current dollars). `PP_it` is the
price of production, also a gross annual revenue:

```
PP_it = K_it + R_t M_it
```

`M_it` is the actual BEA fixed-asset stock plus private inventory stock.
Manufacturing and retail inventories are detailed (BEA Table 1BUC); the
remaining broad groups are allocated from Table 5.8.5B. `d` is approximately the
industry profit-rate gap.

A value of `d = 0.10` means market gross output is about 10% above the price of
production.

## Test 1: are deviations temporary?

Sample: 65 market industries, 1998-2023, 1,690 observations.

- Mean absolute deviation: **12.4%** (gross-output weighted: **11.4%**).
- Median absolute deviation: **8.6%**.
- 57.5% of observations are within ±10%; **89.7%** are within ±25%.
- Lag-1 autocorrelation: **0.972**.
- AR(1) persistence coefficient (industry and year effects): **0.732**;
  implied half-life of a deviation: **2.2 years**.
- The mean absolute deviation has a tiny positive trend (+0.06 percentage
  points per year, p=0.037): statistically detectable but economically
  negligible.

Panel ADF results are mixed. The Fisher combination rejects a unit root
(p<0.001), but only **14%** of industries reject individually and the median
industry p-value is 0.33. The panel test is helped by having 65 industries; the
typical industry series is too short (26 annual observations) to be decisive on
its own.

Engle-Granger cointegration between `log GO` and `log PP` gives the same
pattern: Fisher p<0.001, but only 14% of industries reject individually.

**Reading:** deviations are persistent but not permanent. The half-life is about
2.2 years, so a shock is mostly gone in five years. That is consistent with slow
gravitation, but the evidence is not strong at the individual-industry level.

## Test 2: which variable does the adjusting?

Panel error-correction regressions with industry and year fixed effects,
clustered by industry:

```
Δ log GO_it = α_i + γ_t + β_GO d_i,t-1 + ε_it
Δ log PP_it = α_i + γ_t + β_PP d_i,t-1 + ε_it
```

Results:

- `β_GO = -0.163` (s.e. 0.066, p=0.015). The sign is the one gravitation
  predicts: when market output is above PP, future market output grows more
  slowly. The implied half-life of the output response is **3.9 years**.
- `β_PP = +0.105` (s.e. 0.050, p=0.035). PP also rises toward market output.
- The gap itself closes: `Δd` on `d_lag` gives `β = -0.268` (p<0.001),
  half-life **2.2 years**.

**Reading:** the adjustment is two-way. Market output does move toward PP, which
the old `M_i = K_i` proxy did not deliver. PP also moves toward market output,
partly because it is built from current costs and the current general profit
rate. The evidence is consistent with slow gravitation, not with a strong
instantaneous pull.

## Long-run centre of gravitation

The current-period benchmark uses current cost and the current profit rate, so
it is mechanically close to current market output. A better test of gravitation
is a slow-moving centre:

```
PP*_it = K_trend_it + R_long_t * M_trend_it
```

`K_trend` and `M_trend` are five-year trailing averages by industry; `R_long` is
the five-year trailing average general rate of profit. Results:

- Mean absolute deviation: **15.2%** (weighted 16.6%); 81.5% within ±25%.
- Autocorrelation: **0.901**; half-life **1.8 years**.
- 52% of industries reject a unit root individually; Fisher p<0.001.
- Output adjustment: `β = -0.134` (p=0.001).
- PP adjustment: `β = +0.181` (p<0.001).
- Forecast log RMSE, 1/3/5 years: PP **0.238 / 0.289 / 0.349** vs naive
  **0.120 / 0.202 / 0.258**.

**Reading:** the long-run centre is farther away, so deviations are larger, but
they are less persistent and market output adjusts toward it more strongly. This
is the clearest gravitation evidence in the project. PP still fails the
out-of-sample test, so the result is slow adjustment without forecast power.

## Test 3: does PP forecast future market output?

Expanding-window out-of-sample forecasts, 2008-2023. The models are:

- `naive`: next-period GO = current GO
- `pp`: next-period GO = current PP
- `ar1`: industry fixed effect + current log GO
- `ecm`: industry fixed effect + current log GO + current deviation `d`

Pooled log RMSE (lower is better):

| Horizon | naive | pp | ar1 | ecm |
|---|---|---|---|---|
| 1 year | 0.120 | 0.213 | 0.120 | 0.120 |
| 3 years | 0.202 | 0.256 | 0.174 | 0.172 |
| 5 years | 0.258 | 0.304 | 0.199 | 0.199 |

- PP is **worse than the naive forecast at every horizon**. The RMSE difference
  is +0.093 at one year, +0.053 at three years and +0.046 at five years; the
  bootstrap confidence intervals exclude zero.
- The ECM is marginally better than AR(1) at three years (RMSE difference
  -0.0012, confidence interval excludes zero), but the gain is economically
  negligible. At one year it is indistinguishable from AR(1); at five years the
  difference is also tiny.

**Reading:** PP has no incremental predictive power for future gross output in
this panel. The contemporaneous fit is moderate (13.7% mean absolute error over
the market sample, 14.6% in 2023), but that is a different question from
gravitation.

## Overall verdict

In this 65-industry, 1998-2023 annual panel, with actual fixed-asset stocks:

- prices of production are a **moderate contemporaneous benchmark**, not a tight
  fit;
- deviations are persistent, with a half-life of about 2.2 years;
- the error-correction evidence supports **slow, two-way gravitation**: market
  output adjusts toward PP, and PP also adjusts toward market output;
- the **long-run centre** shows stronger mean reversion (`β_GO = -0.134`,
  p=0.001) and a shorter half-life of 1.8 years;
- PP **does not beat a random walk** in out-of-sample forecasts, for either the
  current or long-run benchmark.

The defensible summary is **"slow gravitation, no forecast power"**. The
data do not support a strong claim that prices of production are the immediate
centers of gravitation of market gross output. They also do not refute the
theory: the test is limited by the value-based output measure, the remaining
broad inventory allocation for mining/utilities/construction and “other”
industries, annual data, and the short sample.

## What changed when actual capital stocks replaced `M_i = K_i`

The market price fit is **13.7% MAE** for current PP and **15.8%** for long-run
PP; the full-sample figures are not comparable because government and housing
capital are now actual and very large. That is informative. With `M_i = K_i`, `PP_i` is mechanically close to
`GO_i`, so the old fit was partly built in. Actual capital stocks expose the
profit-rate dispersion, especially in regulated utilities and capital-intensive
industries. The error-correction result also changed: the coefficient on market
output became negative and significant, which the cost proxy did not produce.

## What would make the test sharper

1. **Detailed inventories for the remaining groups.** Replace the broad
   allocation for mining/utilities/construction and “other” industries with
   detailed inventory data.
2. **Unit prices and quantities.** Compare prices per unit of output rather than
   gross revenue values. This requires industry quantity and price indexes.
3. **Longer and higher-frequency data.** Annual data give only 26 observations
   per industry; quarterly data and a longer sample would give the panel tests
   more power.
4. **Industry-level CFC.** Replace the broad-sector CFC allocation with detailed
   industry data where available.

## Reproduce

```bash
.venv/bin/usa-marxian industries
# or
.venv/bin/usa-marxian all
```

Outputs:

- `output/tables/gravitation_summary.csv`
- `output/tables/gravitation_by_year.csv`
- `output/tables/gravitation_ecm.csv`
- `output/tables/gravitation_forecast_metrics.csv`
- `output/tables/gravitation_forecast_comparisons.csv`
- `output/gravitation.json`
- `output/figures/gravitation_deviation.png`
- `output/figures/gravitation_forecast.png`
- `data/processed/industry_capital.csv`
- `output/tables/industry_capital_coverage.csv`
