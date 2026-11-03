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

The tests below check each claim separately.

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

with the `M_i = K_i` capital proxy in the default run. `d` is therefore
approximately the industry profit-rate gap:

```
d_it ≈ log((1 + r_it) / (1 + R_t))
```

A value of `d = 0.10` means market gross output is about 10% above the price of
production.

## Test 1: are deviations temporary?

- Mean absolute deviation: **13.7%** (gross-output weighted: **19.7%**).
- Median absolute deviation: **10.9%**.
- 44% of observations are within ±10%; **90.5%** are within ±25%.
- Lag-1 autocorrelation: **0.987**.
- AR(1) persistence coefficient (industry and year effects): **0.746**;
  implied half-life of a deviation: **2.4 years**.
- The mean absolute deviation has a tiny positive trend (+0.03 percentage
  points per year, p=0.028).

Panel ADF results are mixed. The Fisher combination rejects a unit root
(p<0.001), but only **17%** of industries reject individually and the median
industry p-value is 0.30. The panel test is helped by having 71 industries; the
typical industry series is too short (26 annual observations) to be decisive on
its own.

Engle-Granger cointegration between `log GO` and `log PP` gives the same
pattern: Fisher p<0.001, but only 17% of industries reject individually.

**Reading:** deviations are persistent but not permanent. The half-life is about
2.4 years, so a shock is mostly gone in five years. That is consistent with slow
gravitation, but the evidence is not strong at the individual-industry level.

## Test 2: which variable does the adjusting?

Panel error-correction regressions with industry and year fixed effects,
clustered by industry:

```
Δ log GO_it = α_i + γ_t + β_GO d_i,t-1 + ε_it
Δ log PP_it = α_i + γ_t + β_PP d_i,t-1 + ε_it
```

Results:

- `β_GO = +0.078` (s.e. 0.060, p=0.188). The sign is wrong for gravitation:
  when market output is above PP, future market output does **not** grow more
  slowly. The coefficient is statistically indistinguishable from zero.
- `β_PP = +0.333` (s.e. 0.082, p<0.001). When market output is above PP,
  prices of production rise. PP moves toward GO.
- The gap itself closes: `Δd` on `d_lag` gives `β = -0.254` (p<0.001),
  half-life **2.4 years**.

**Reading:** the gap closes, but the adjustment runs from prices of production
toward market output, not from market output toward prices of production. That
is the opposite of the gravitation story. Part of this is mechanical: PP is
built from current costs and the current general profit rate, so it tracks
current market values by construction. Still, the test as specified does not
find market output being pulled toward PP.

## Test 3: does PP forecast future market output?

Expanding-window out-of-sample forecasts, 2008-2023. The models are:

- `naive`: next-period GO = current GO
- `pp`: next-period GO = current PP
- `ar1`: industry fixed effect + current log GO
- `ecm`: industry fixed effect + current log GO + current deviation `d`

Pooled log RMSE (lower is better):

| Horizon | naive | pp | ar1 | ecm |
|---|---|---|---|---|
| 1 year | 0.116 | 0.249 | 0.115 | 0.116 |
| 3 years | 0.196 | 0.297 | 0.167 | 0.168 |
| 5 years | 0.252 | 0.345 | 0.192 | 0.192 |

- PP is **worse than the naive forecast at every horizon**. The RMSE difference
  is +0.133 at one year, +0.100 at three years and +0.093 at five years; the
  bootstrap confidence intervals exclude zero.
- The ECM improves on AR(1) by essentially nothing: +0.0006 at one year,
  +0.0007 at three years, 0.0000 at five years, with confidence intervals that
  include zero.

**Reading:** PP has no incremental predictive power for future gross output in
this panel. The contemporaneous fit is good (10-13% MAE), but that is a
different question from gravitation.

## Overall verdict

In this 71-industry, 1998-2023 annual panel:

- prices of production are a good **contemporaneous accounting benchmark**;
- deviations are persistent, with a half-life of about 2.4 years;
- the adjustment runs mainly from PP toward market output, not the reverse;
- PP does not beat a random walk in out-of-sample forecasts.

The data therefore do **not** support the strong claim that prices of production
are centers of gravitation of market gross output at this frequency and with
these proxies. They also do not refute the theory: the test is limited by the
value-based output measure, the `M_i = K_i` capital proxy, annual data, and the
short sample.

## What would make the test sharper

1. **Actual industry capital stocks.** Replace `M_i = K_i` with BEA fixed-asset
   stocks by industry. The current proxy makes PP mechanically close to GO.
2. **Unit prices and quantities.** Compare prices per unit of output rather than
   gross revenue values. This requires industry quantity and price indexes.
3. **Longer and higher-frequency data.** Annual data give only 26 observations
   per industry; quarterly data and a longer sample would give the panel tests
   more power.
4. **Structural breaks and industry trends.** Allow for changing industry
   composition, regulation, and sector-specific trends.
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
