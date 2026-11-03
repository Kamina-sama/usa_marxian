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
excluded: their "prices" are not market prices, and their capital stocks fall
back to the cost proxy.

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

`M_it` is the actual BEA fixed-asset stock plus allocated private inventory
stock. `d` is approximately the industry profit-rate gap.

A value of `d = 0.10` means market gross output is about 10% above the price of
production.

## Test 1: are deviations temporary?

Sample: 65 market industries, 1998-2023, 1,690 observations.

- Mean absolute deviation: **12.8%** (gross-output weighted: **11.6%**).
- Median absolute deviation: **8.9%**.
- 56.2% of observations are within ±10%; **89.3%** are within ±25%.
- Lag-1 autocorrelation: **0.973**.
- AR(1) persistence coefficient (industry and year effects): **0.733**;
  implied half-life of a deviation: **2.2 years**.
- The mean absolute deviation has a tiny positive trend (+0.05 percentage
  points per year, p=0.139), not statistically distinguishable from zero.

Panel ADF results are mixed. The Fisher combination rejects a unit root
(p<0.001), but only **12%** of industries reject individually and the median
industry p-value is 0.34. The panel test is helped by having 65 industries; the
typical industry series is too short (26 annual observations) to be decisive on
its own.

Engle-Granger cointegration between `log GO` and `log PP` gives the same
pattern: Fisher p<0.001, but only 17% of industries reject individually.

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

- `β_GO = -0.157` (s.e. 0.067, p=0.018). The sign is the one gravitation
  predicts: when market output is above PP, future market output grows more
  slowly. The implied half-life of the output response is **4.0 years**.
- `β_PP = +0.110` (s.e. 0.047, p=0.019). PP also rises toward market output.
- The gap itself closes: `Δd` on `d_lag` gives `β = -0.267` (p<0.001),
  half-life **2.2 years**.

**Reading:** the adjustment is two-way. Market output does move toward PP, which
the old `M_i = K_i` proxy did not deliver. PP also moves toward market output,
partly because it is built from current costs and the current general profit
rate. The evidence is consistent with slow gravitation, not with a strong
instantaneous pull.

## Test 3: does PP forecast future market output?

Expanding-window out-of-sample forecasts, 2008-2023. The models are:

- `naive`: next-period GO = current GO
- `pp`: next-period GO = current PP
- `ar1`: industry fixed effect + current log GO
- `ecm`: industry fixed effect + current log GO + current deviation `d`

Pooled log RMSE (lower is better):

| Horizon | naive | pp | ar1 | ecm |
|---|---|---|---|---|
| 1 year | 0.120 | 0.217 | 0.120 | 0.120 |
| 3 years | 0.202 | 0.255 | 0.174 | 0.172 |
| 5 years | 0.258 | 0.302 | 0.199 | 0.198 |

- PP is **worse than the naive forecast at every horizon**. The RMSE difference
  is +0.097 at one year, +0.053 at three years and +0.044 at five years; the
  bootstrap confidence intervals exclude zero.
- The ECM is marginally better than AR(1) at three years (RMSE difference
  -0.0019, confidence interval excludes zero), but the gain is economically
  negligible. At one year it is indistinguishable from AR(1); at five years the
  difference is also tiny.

**Reading:** PP has no incremental predictive power for future gross output in
this panel. The contemporaneous fit is moderate (14-17% MAE), but that is a
different question from gravitation.

## Overall verdict

In this 65-industry, 1998-2023 annual panel, with actual fixed-asset stocks:

- prices of production are a **moderate contemporaneous benchmark**, not a tight
  fit;
- deviations are persistent, with a half-life of about 2.2 years;
- the error-correction evidence supports **slow, two-way gravitation**: market
  output adjusts toward PP, and PP also adjusts toward market output;
- PP **does not beat a random walk** in out-of-sample forecasts.

The defensible summary is **"weak and slow gravitation, no forecast power"**. The
data do not support a strong claim that prices of production are the immediate
centers of gravitation of market gross output. They also do not refute the
theory: the test is limited by the value-based output measure, the within-sector
allocation of inventory stocks, annual data, and the short sample.

## What changed when actual capital stocks replaced `M_i = K_i`

The price fit got **worse on average error**, from 13.3% to 16.3% full-sample
MAE. That is informative. With `M_i = K_i`, `PP_i` is mechanically close to
`GO_i`, so the old fit was partly built in. Actual capital stocks expose the
profit-rate dispersion, especially in regulated utilities and capital-intensive
industries. The error-correction result also changed: the coefficient on market
output became negative and significant, which the cost proxy did not produce.

## What would make the test sharper

1. **Industry-level inventory data.** Replace the gross-output allocation of
   broad-sector inventory stocks with industry-level data.
2. **Actual government and housing capital.** Remove the cost-proxy fallback for
   those six industries, or keep them out of the market sample as now.
3. **Unit prices and quantities.** Compare prices per unit of output rather than
   gross revenue values. This requires industry quantity and price indexes.
4. **Longer and higher-frequency data.** Annual data give only 26 observations
   per industry; quarterly data and a longer sample would give the panel tests
   more power.
5. **A long-run PP benchmark.** Use a fixed capital stock and a long-run average
   profit rate rather than current-year K and R, so PP is not mechanically
   tied to current GO.

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
