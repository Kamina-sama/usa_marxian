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

- Mean absolute deviation: **10.4%** (gross-output weighted: **9.5%**).
- Median absolute deviation: **8.7%**.
- 61.1% of observations are within ±10%; **93.1%** are within ±25%.
- Lag-1 autocorrelation: **0.957**.
- AR(1) persistence coefficient (industry and year effects): **0.709**;
  implied half-life of a deviation: **2.0 years**.
- The mean absolute deviation has a tiny positive trend (+0.04 percentage
  points per year, p=0.078): not statistically distinguishable from zero.

Panel ADF results are mixed. The Fisher combination rejects a unit root
(p<0.001), but only **15%** of industries reject individually and the median
industry p-value is 0.34. The panel test is helped by having 65 industries; the
typical industry series is too short (26 annual observations) to be decisive on
its own.

Engle-Granger cointegration between `log GO` and `log PP` gives the same
pattern: Fisher p<0.001, but only 23% of industries reject individually.

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

- `β_GO = -0.091` (s.e. 0.077, p=0.239). The sign is the one gravitation
  predicts, but the coefficient is not distinguishable from zero. The implied
  half-life of the output response would be **7.3 years**.
- `β_PP = +0.201` (s.e. 0.070, p=0.004). PP rises toward market output, and this
  is the significant channel.
- The gap itself closes: `Δd` on `d_lag` gives `β = -0.291` (p<0.001),
  half-life **2.0 years**.

**Reading:** the gap does close, but not in the direction the theory predicts.
Market output does not move toward PP by a detectable amount; PP moves toward
market output, which it must, since it is built from current costs and the
current general profit rate. That is one-way adjustment in the wrong direction.

On the stock-capital variant of the same benchmark the output coefficient is
significant (`-0.163`, p=0.015) and the adjustment is genuinely two-way. The
result is sensitive to whether `M` includes circulating capital, and the
working-capital variant is used here because it fits revenue better.

## Long-run centre of gravitation

The current-period benchmark uses current cost and the current profit rate, so
it is mechanically close to current market output. A better test of gravitation
is a slow-moving centre:

```
PP*_it = K_trend_it + R_long_t * M_trend_it
```

`K_trend` and `M_trend` are five-year trailing averages by industry; `R_long` is
the five-year trailing average general rate of profit. Results:

- Mean absolute deviation: **13.1%** (weighted 14.4%); 85.0% within ±25%.
- Autocorrelation: **0.861**; half-life **1.8 years**.
- 57% of industries reject a unit root individually; Fisher p<0.001.
- Output adjustment: `β = -0.117` (s.e. 0.041, p=0.004).
- PP adjustment: `β = +0.204` (p<0.001).
- Forecast log RMSE, 1/3/5 years: PP **0.209 / 0.269 / 0.335** vs naive
  **0.120 / 0.202 / 0.258**.

**Reading:** the long-run centre is farther away than the current benchmark
(13.1% against 10.4%), but deviations are less persistent and market output
adjusts toward it with the sign gravitation predicts. This is the clearest
gravitation evidence in the project, and the only piece of it that the switch to
a working-capital `M` strengthens rather than weakens. PP still fails the
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
| 1 year | 0.120 | 0.176 | 0.120 | 0.120 |
| 3 years | 0.202 | 0.230 | 0.174 | 0.172 |
| 5 years | 0.258 | 0.284 | 0.199 | 0.199 |

- PP is **worse than the naive forecast at every horizon**. The RMSE difference
  is +0.056 at one year, +0.028 at three years and +0.026 at five years; the
  bootstrap confidence intervals exclude zero in all three cases.
- The ECM is marginally better than AR(1) at three years (RMSE difference
  -0.0012, confidence interval excludes zero), but the gain is economically
  negligible. At one year it is indistinguishable from AR(1); at five years the
  difference is also tiny.

**Reading:** PP has no incremental predictive power for future gross output in
this panel. The contemporaneous fit is moderate (10.4% mean absolute error over
the market sample), but that is a different question from
gravitation.

## Overall verdict

In this 65-industry, 1998-2023 annual panel, with `M` including circulating
capital:

- prices of production are a **moderate contemporaneous benchmark**, not a tight
  fit (10.4% mean absolute error);
- deviations are persistent, with a half-life of about 2.0 years;
- the **current** benchmark shows one-way adjustment in the wrong direction:
  `PP` moves toward market output (`β_PP = +0.201`, p=0.004), but market output
  does not measurably move toward `PP` (`β_GO = -0.091`, p=0.239);
- the **long-run centre** behaves differently and as the theory predicts: market
  output does adjust toward it (`β_GO = -0.117`, p=0.004) as well as `PP` toward
  output (`β_PP = +0.204`, p<0.001), with a 1.8-year half-life;
- PP **does not beat a random walk** in out-of-sample forecasts, for either the
  current or the long-run benchmark.

The defensible summary is **"gravitation at the slow centre, none at the fast
one, and no forecast power either way"**. The current benchmark is built from
current costs, so it tracks output almost mechanically and cannot separate
"prices adjust to output" from "output adjusts to prices". The slow centre does
not have that problem, and on it the predicted adjustment appears. That is the
project's one piece of clean support for the regulating claim — and it depends
on taking a five-year average as the centre, which is a strong assumption in a
26-year sample.

## What changed when actual capital stocks replaced `M_i = K_i`

The market price fit is **10.4% MAE** for current PP and **15.8%** for long-run
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
- `output/figures/findings_gravitation.png` — adjustment coefficients with 95% CI
- `output/figures/findings_forecast.png` — error by horizon, current and long-run
- `data/processed/industry_capital.csv`
- `output/tables/industry_capital_coverage.csv`
