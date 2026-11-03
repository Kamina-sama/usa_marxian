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
`p . GO` to total gross output. In the code this is:

- `sraffa_prices_of_production(...)` — the direct solution of
  `p = w (1+r) l [I - (1+r) A]^-1`;
- `iterative_prices(...)` — the fixed-`r` cost-plus iteration, which converges
  to the same ray and is kept only as a numerical check.

The labour values `lambda = l (I - A)^-1` are classical direct prices, not
specifically Sraffian, but they are reported alongside.

## Why this is not "Shaikh"

Shaikh's prices of production share the same fixed-point algebra, but his
distinctive claim is the **adjustment process** — real competition, capital
flows, entry and turbulent gravitation. That process is implemented separately
(see `docs/shaikh.md`). The fixed point by itself is Sraffa.

## Fit, 1998-2023, 65 market industries

| Benchmark | MAE | RMSE | corr | slope | within 25% | mean gap |
|---|---:|---:|---:|---:|---:|---:|
| Moseley `PP` | 13.7% | 22.9% | 0.983 | 1.043 | 88.8% | -7.2% |
| Sraffa `PP_Sraffa` | 15.7% | 19.5% | 0.975 | 0.974 | 81.2% | -1.6% |
| Shaikh iterated `PP_Shaikh` | 15.7% | 19.6% | 0.976 | 0.975 | 82.0% | -1.7% |
| Direct prices (labour values) | 17.8% | 23.4% | 0.953 | 0.954 | 70.9% | -0.6% |

Sraffa's benchmark has lower RMSE, smaller mean bias and a slope closer to one
than Moseley's. It does worse on typical absolute error and rank correlation.

## Gravitation, 1998-2023

| Benchmark | mean abs gap | half-life | GO beta | PP beta | 1y forecast RMSE |
|---|---:|---:|---:|---:|---:|
| Moseley `PP` | 12.4% | 2.2y | -0.163 (p=0.015) | +0.105 (p=0.035) | 0.213 |
| Sraffa `PP_Sraffa` | 16.1% | 2.6y | +0.029 (p=0.235) | +0.264 (p<0.001) | 0.249 |
| Shaikh iterated `PP_Shaikh` | 16.1% | 2.6y | +0.038 (p=0.101) | +0.274 (p<0.001) | 0.249 |
| Direct prices (labour values) | 18.7% | 2.7y | -0.043 (p=0.199) | +0.184 (p<0.001) | 0.293 |

With annual `A_t`, Sraffa's benchmark does **not** attract market output: output
does not adjust toward it, while it adjusts strongly toward output. The center
moves toward the data, not the other way. Neither benchmark beats a naive
random-walk forecast.

## Verdict

- **Moseley** fits typical industry errors and forecasts better.
- **Sraffa** calibrates the aggregate level better (lower RMSE, smaller bias,
  slope closer to one) but shows no clean gravitation with annual `A_t`.
- **Shaikh's iteration** converges to essentially the same center as Sraffa, so
  it does not change the fit conclusion; it adds a model-implied profit rate.
- **Direct labour values** fit worst.

The Sraffian fixed point is a useful aggregate benchmark, not a center of
gravitation in this panel.
