# Sraffa's prices of production

This page describes the Sraffian component of the project and reports its
empirical result against the other benchmarks.

## What is Sraffian here

Sraffa's prices of production solve a simultaneous system with a uniform profit
rate on flow capital:

```
p = (1 + r)(p A + w l)
```

Relative prices are independent of `w`; the scale is fixed by normalising
`p . GO` to total gross output. In the code:

- `sraffa_prices_of_production(...)` — the direct solution of
  `p = w (1+r) l [I - (1+r) A]^-1`;
- `iterative_prices(...)` — the fixed-`r` cost-plus iteration, which converges
  to the same ray and is kept as a numerical check.

`A` is the **deflated** annual Use matrix (2017 dollars), and `l` is direct
labour per 2017 dollar of output. Industry labour hours are measured from BEA
Table 6.5D full-time-equivalent employees scaled to macro hours; the labour
values `lambda = l (I - A)^-1` are classical direct prices.

## Why this is not "Shaikh"

Shaikh's prices of production share the same fixed-point algebra, but his
distinctive claim is the **adjustment process** — real competition, capital
flows, entry and turbulent gravitation (see `docs/shaikh.md`). Solving the
fixed point once is Sraffa.

## Fit, 2005-2023, 65 market industries

| Benchmark | MAE | RMSE | corr | slope | within 25% | mean gap |
|---|---:|---:|---:|---:|---:|---:|
| Moseley `PP` | 13.7% | 23.0% | 0.983 | 1.046 | 88.5% | -7.4% |
| Sraffa `PP_Sraffa` | 16.8% | 20.5% | 0.971 | 0.982 | 77.2% | -2.4% |
| Shaikh iterated `PP_Shaikh` | 17.2% | 21.3% | 0.973 | 0.985 | 76.9% | -3.1% |
| Direct prices (labour values) | 37.2% | 48.8% | 0.887 | 0.893 | 42.1% | -8.0% |

Sraffa's benchmark has lower RMSE, smaller mean bias and a slope closer to one
than Moseley's. It does worse on typical absolute error and rank correlation.

## Gravitation, 2005-2023

| Benchmark | mean abs gap | half-life | GO beta | PP beta | 1y forecast RMSE |
|---|---:|---:|---:|---:|---:|
| Moseley `PP` | 12.4% | 1.7y | -0.240 (p=0.008) | +0.098 (p=0.164) | 0.213 |
| Sraffa `PP_Sraffa` | 17.1% | 2.2y | +0.068 (p=0.195) | +0.341 (p<0.001) | 0.253 |
| Shaikh iterated `PP_Shaikh` | 17.3% | 2.4y | +0.078 (p=0.083) | +0.333 (p<0.001) | 0.254 |
| Direct prices (labour values) | 35.7% | 2.7y | +0.032 (p=0.456) | +0.256 (p<0.001) | 0.460 |

Naive forecast RMSE is 0.120.

With annual `A_t` in constant prices, Sraffa's benchmark does **not** attract
market output: output does not adjust toward it, while it adjusts strongly
toward output. The center moves toward the data. Neither benchmark beats a naive
random-walk forecast.

## Verdict

- **Moseley** fits typical industry errors and forecasts better.
- **Sraffa** calibrates the aggregate level better (lower RMSE, smaller bias,
  slope closer to one) but shows no clean gravitation.
- **Shaikh's iteration** converges to essentially the same center as Sraffa, so
  it does not change the fit conclusion; it adds a model-implied profit rate.
- **Direct labour values** fit worst by a wide margin. Once labour hours are
  measured (FTE) rather than allocated by compensation, labour values are a
  poor empirical price predictor.

The Sraffian fixed point is a useful aggregate benchmark, not a center of
gravitation in this panel.
